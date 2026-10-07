from fastapi import FastAPI

from .evaluation import (
    DriftEvaluationRequest,
    DriftEvaluationResponse,
    evaluate_capture_drift,
)


app = FastAPI(
    title="Search-Grounded AI Agent Drift Gate",
    version="0.1.0",
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post(
    "/v1/evaluations",
    response_model=DriftEvaluationResponse,
)
def create_evaluation(
    request: DriftEvaluationRequest,
) -> DriftEvaluationResponse:
    """Evaluate evidence drift for an existing agent answer."""

    return evaluate_capture_drift(request)
