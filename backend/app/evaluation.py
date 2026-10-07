from pydantic import BaseModel, Field

from .claims import (
    AgentAnswer,
    LinkValidation,
    unresolved_claim_links,
)
from .engine import DriftEvaluationResult, evaluate_drift
from .schema import Capture


class EvaluationValidation(BaseModel):
    """Validation status for an evaluation request."""

    valid: bool

    unresolved_claim_links: list[LinkValidation] = Field(
        default_factory=list
    )


class DriftEvaluationRequest(BaseModel):
    """Complete input required for one drift evaluation."""

    baseline_capture: Capture
    current_capture: Capture
    agent_answer: AgentAnswer


class DriftEvaluationResponse(BaseModel):
    """Auditable result of one drift evaluation."""

    evaluation_id: str

    baseline_capture_id: str
    current_capture_id: str

    validation: EvaluationValidation

    result: DriftEvaluationResult | None = None


def evaluate_capture_drift(
    request: DriftEvaluationRequest,
) -> DriftEvaluationResponse:
    """
    Validate and evaluate one baseline/current capture pair.

    The baseline answer's evidence dependencies must resolve
    against the baseline capture before drift analysis proceeds.

    Invalid claim/evidence links are reported as validation
    failures rather than being converted into a gate decision.
    """

    unresolved = unresolved_claim_links(
        request.agent_answer,
        request.baseline_capture.normalized_evidence,
    )

    validation = EvaluationValidation(
        valid=not unresolved,
        unresolved_claim_links=unresolved,
    )

    if unresolved:
        return DriftEvaluationResponse(
            evaluation_id=(
                f"{request.baseline_capture.capture_id}:"
                f"{request.current_capture.capture_id}:"
                f"{request.agent_answer.answer_id}"
            ),
            baseline_capture_id=(
                request.baseline_capture.capture_id
            ),
            current_capture_id=(
                request.current_capture.capture_id
            ),
            validation=validation,
            result=None,
        )

    result = evaluate_drift(
        baseline_evidence=(
            request.baseline_capture.normalized_evidence
        ),
        current_evidence=(
            request.current_capture.normalized_evidence
        ),
        agent_answer=request.agent_answer,
    )

    return DriftEvaluationResponse(
        evaluation_id=(
            f"{request.baseline_capture.capture_id}:"
            f"{request.current_capture.capture_id}:"
            f"{request.agent_answer.answer_id}"
        ),
        baseline_capture_id=(
            request.baseline_capture.capture_id
        ),
        current_capture_id=(
            request.current_capture.capture_id
        ),
        validation=validation,
        result=result,
    )
