
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from .capture import create_capture
from .claims import AgentAnswer
from .capture_repository import (
    CaptureConflictError,
    CaptureIntegrityError,
    SQLiteCaptureRepository,
)
from .evaluation import (
    DriftEvaluationRequest,
    DriftEvaluationResponse,
    build_evaluation_id,
    evaluate_capture_drift,
)
from .evaluation_repository import (
    EvaluationConflictError,
    EvaluationIntegrityError,
    EvaluationRecord,
    SQLiteEvaluationRepository,
)
from .schema import Capture
from .serpapi_client import SerpApiError, search_google


app = FastAPI(
    title="Search-Grounded AI Agent Drift Gate",
    version="0.1.0",
)

# Allow the local frontend development servers to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


BACKEND_DIR = Path(__file__).resolve().parents[1]
DATABASE_PATH = BACKEND_DIR / "data" / "captures.sqlite3"


class PersistedEvaluationRequest(BaseModel):
    """Request to evaluate drift using stored capture IDs."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    baseline_capture_id: str = Field(min_length=1, max_length=200)
    current_capture_id: str = Field(min_length=1, max_length=200)
    agent_answer: AgentAnswer


class CaptureCreateRequest(BaseModel):
    """Parameters for acquiring a new search-evidence capture."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    query: str = Field(min_length=1, max_length=500)
    language: str = Field(default="en", min_length=2, max_length=12)
    country: str = Field(default="in", min_length=2, max_length=8)
    device: Literal["desktop", "mobile", "tablet"] = "desktop"
    location: str | None = Field(default=None, max_length=200)
    no_cache: bool = False


class CaptureCreateResponse(BaseModel):
    """Receipt returned after a capture is stored."""

    capture_id: str
    captured_at: datetime
    query: str
    search_id: str
    storage_status: Literal["stored"]


class CaptureSummary(BaseModel):
    """Compact metadata for a stored capture."""

    capture_id: str
    captured_at: datetime
    query: str
    engine: str
    country: str
    device: str
    search_id: str


class CaptureListResponse(BaseModel):
    """Paginated list of stored captures."""

    items: list[CaptureSummary]
    total: int
    limit: int
    offset: int


@lru_cache(maxsize=1)
def get_capture_repository() -> SQLiteCaptureRepository:
    """Return the process-wide capture repository."""

    return SQLiteCaptureRepository(DATABASE_PATH)


@lru_cache(maxsize=1)
def get_evaluation_repository() -> SQLiteEvaluationRepository:
    """Return the process-wide evaluation repository."""

    return SQLiteEvaluationRepository(DATABASE_PATH)


@app.get("/health")
def health():
    """Report API health."""

    return {"status": "ok"}


@app.post(
    "/v1/captures",
    status_code=201,
    response_model=CaptureCreateResponse,
)
def create_capture_endpoint(
    request: CaptureCreateRequest,
    repository: SQLiteCaptureRepository = Depends(
        get_capture_repository
    ),
) -> CaptureCreateResponse:
    """Search, normalize, and persist an immutable evidence capture."""

    try:
        raw_response = search_google(
            query=request.query,
            language=request.language,
            country=request.country,
            device=request.device,
            location=request.location,
            no_cache=request.no_cache,
        )
    except SerpApiError as exc:
        raise HTTPException(
            status_code=502,
            detail="Search provider request failed.",
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail="Search provider is not configured.",
        ) from exc

    try:
        capture = create_capture(raw_response)
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail="Search provider returned an invalid response.",
        ) from exc

    try:
        repository.save(capture)
    except CaptureConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail="Capture ID conflicts with existing stored content.",
        ) from exc

    return CaptureCreateResponse(
        capture_id=capture.capture_id,
        captured_at=capture.captured_at,
        query=capture.search_context.query,
        search_id=capture.serpapi_metadata.search_id,
        storage_status="stored",
    )


@app.get(
    "/v1/captures",
    response_model=CaptureListResponse,
)
def list_captures_endpoint(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    repository: SQLiteCaptureRepository = Depends(
        get_capture_repository
    ),
) -> CaptureListResponse:
    """List stored captures with pagination and integrity verification."""

    try:
        captures, total = repository.list_captures(
            limit=limit,
            offset=offset,
        )
    except CaptureIntegrityError as exc:
        raise HTTPException(
            status_code=500,
            detail="Stored capture integrity verification failed.",
        ) from exc

    items = [
        CaptureSummary(
            capture_id=capture.capture_id,
            captured_at=capture.captured_at,
            query=capture.search_context.query,
            engine=capture.search_context.engine,
            country=capture.search_context.country,
            device=capture.search_context.device,
            search_id=capture.serpapi_metadata.search_id,
        )
        for capture in captures
    ]

    return CaptureListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@app.get(
    "/v1/captures/{capture_id}",
    response_model=Capture,
)
def get_capture_endpoint(
    capture_id: str,
    repository: SQLiteCaptureRepository = Depends(
        get_capture_repository
    ),
) -> Capture:
    """Retrieve a stored capture after verifying its integrity."""

    try:
        capture = repository.get(capture_id)
    except CaptureIntegrityError as exc:
        raise HTTPException(
            status_code=500,
            detail="Stored capture integrity verification failed.",
        ) from exc

    if capture is None:
        raise HTTPException(
            status_code=404,
            detail="Capture not found.",
        )

    return capture


@app.post(
    "/v1/evaluations/persisted",
    response_model=DriftEvaluationResponse,
)
def create_persisted_evaluation(
    request: PersistedEvaluationRequest,
    repository: SQLiteCaptureRepository = Depends(
        get_capture_repository
    ),
    evaluation_repository: SQLiteEvaluationRepository = Depends(
        get_evaluation_repository
    ),
) -> DriftEvaluationResponse:
    """Evaluate stored captures and persist the immutable result."""

    # The persisted API owns the evaluator version. Clients cannot
    # choose a version and accidentally select a different gate policy.
    evaluator_version = "v1"

    evaluation_id = build_evaluation_id(
        baseline_capture_id=request.baseline_capture_id,
        current_capture_id=request.current_capture_id,
        answer_id=request.agent_answer.answer_id,
        evaluator_version=evaluator_version,
    )

    try:
        existing_record = evaluation_repository.get(evaluation_id)
    except EvaluationIntegrityError as exc:
        raise HTTPException(
            status_code=500,
            detail="Stored evaluation integrity verification failed.",
        ) from exc

    if existing_record is not None:
        if (
            existing_record.baseline_capture_id
            == request.baseline_capture_id
            and existing_record.current_capture_id
            == request.current_capture_id
            and existing_record.agent_answer == request.agent_answer
        ):
            return existing_record.response

        raise HTTPException(
            status_code=409,
            detail="Evaluation ID conflicts with existing content.",
        )

    try:
        baseline_capture = repository.get(request.baseline_capture_id)
        current_capture = repository.get(request.current_capture_id)
    except CaptureIntegrityError as exc:
        raise HTTPException(
            status_code=500,
            detail="Stored capture integrity verification failed.",
        ) from exc

    if baseline_capture is None:
        raise HTTPException(
            status_code=404,
            detail="Baseline capture not found.",
        )

    if current_capture is None:
        raise HTTPException(
            status_code=404,
            detail="Current capture not found.",
        )

    evaluation_request = DriftEvaluationRequest(
        baseline_capture=baseline_capture,
        current_capture=current_capture,
        agent_answer=request.agent_answer,
    )

    response = evaluate_capture_drift(
        evaluation_request,
        evaluator_version=evaluator_version,
    )

    record = EvaluationRecord(
        evaluation_id=response.evaluation_id,
        created_at=datetime.now(timezone.utc),
        baseline_capture_id=baseline_capture.capture_id,
        current_capture_id=current_capture.capture_id,
        agent_answer=request.agent_answer,
        response=response,
        evaluator_version=evaluator_version,
    )

    try:
        saved_record = evaluation_repository.save(record)
    except EvaluationConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail="Evaluation ID conflicts with existing content.",
        ) from exc
    except EvaluationIntegrityError as exc:
        raise HTTPException(
            status_code=500,
            detail="Stored evaluation integrity verification failed.",
        ) from exc

    # Preserve the existing endpoint's response contract.
    return saved_record.response


@app.get(
    "/v1/evaluations/{evaluation_id}",
    response_model=EvaluationRecord,
)
def get_evaluation_endpoint(
    evaluation_id: str,
    repository: SQLiteEvaluationRepository = Depends(
        get_evaluation_repository
    ),
) -> EvaluationRecord:
    """Retrieve a historical evaluation after integrity verification."""

    try:
        record = repository.get(evaluation_id)
    except EvaluationIntegrityError as exc:
        raise HTTPException(
            status_code=500,
            detail="Stored evaluation integrity verification failed.",
        ) from exc

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="Evaluation not found.",
        )

    return record


@app.post(
    "/v1/evaluations",
    response_model=DriftEvaluationResponse,
)
def create_evaluation(
    request: DriftEvaluationRequest,
) -> DriftEvaluationResponse:
    """Evaluate evidence drift for an existing agent answer."""

    return evaluate_capture_drift(request)
