
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException
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
    evaluate_capture_drift,
)
from .schema import Capture
from .serpapi_client import SerpApiError, search_google


app = FastAPI(
    title="Search-Grounded AI Agent Drift Gate",
    version="0.1.0",
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


@lru_cache(maxsize=1)
def get_capture_repository() -> SQLiteCaptureRepository:
    """Return the process-wide repository using a stable database path."""

    return SQLiteCaptureRepository(DATABASE_PATH)


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
    repository: SQLiteCaptureRepository = Depends(get_capture_repository),
) -> DriftEvaluationResponse:
    """Evaluate drift using two previously stored captures."""

    try:
        baseline_capture = repository.get(request.baseline_capture_id)
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

    try:
        current_capture = repository.get(request.current_capture_id)
    except CaptureIntegrityError as exc:
        raise HTTPException(
            status_code=500,
            detail="Stored capture integrity verification failed.",
        ) from exc

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

    return evaluate_capture_drift(evaluation_request)


@app.post(
    "/v1/evaluations",
    response_model=DriftEvaluationResponse,
)
def create_evaluation(
    request: DriftEvaluationRequest,
) -> DriftEvaluationResponse:
    """Evaluate evidence drift for an existing agent answer."""

    return evaluate_capture_drift(request)
