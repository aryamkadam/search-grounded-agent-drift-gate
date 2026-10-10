import hashlib
import json
import re

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


def build_evaluation_id(
    *,
    baseline_capture_id: str,
    current_capture_id: str,
    answer_id: str,
    evaluator_version: str | None = None,
) -> str:
    """Build a legacy ID or a deterministic versioned ID."""

    if evaluator_version is None:
        return (
            f"{baseline_capture_id}:"
            f"{current_capture_id}:"
            f"{answer_id}"
        )

    if re.fullmatch(r"v[1-9][0-9]*", evaluator_version) is None:
        raise ValueError(
            "Evaluator version must use the form 'v1', 'v2', etc."
        )

    identity = {
        "baseline_capture_id": baseline_capture_id,
        "current_capture_id": current_capture_id,
        "answer_id": answer_id,
        "evaluator_version": evaluator_version,
    }
    canonical_json = json.dumps(
        identity,
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(
        canonical_json.encode("utf-8")
    ).hexdigest()

    return f"eval-{evaluator_version}-{digest}"



class DriftEvaluationResponse(BaseModel):
    """Auditable result of one drift evaluation."""

    evaluation_id: str

    baseline_capture_id: str
    current_capture_id: str

    validation: EvaluationValidation

    result: DriftEvaluationResult | None = None


def evaluate_capture_drift(
    request: DriftEvaluationRequest,
    *,
    evaluator_version: str | None = None,
) -> DriftEvaluationResponse:
    """
    Validate and evaluate one baseline/current capture pair.

    The baseline answer's evidence dependencies must resolve
    against the baseline capture before drift analysis proceeds.

    Invalid claim/evidence links are reported as validation
    failures rather than being converted into a gate decision.
    """

    evaluation_id = build_evaluation_id(
        baseline_capture_id=request.baseline_capture.capture_id,
        current_capture_id=request.current_capture.capture_id,
        answer_id=request.agent_answer.answer_id,
        evaluator_version=evaluator_version,
    )

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
            evaluation_id=evaluation_id,
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
        evaluation_id=evaluation_id,
        baseline_capture_id=(
            request.baseline_capture.capture_id
        ),
        current_capture_id=(
            request.current_capture.capture_id
        ),
        validation=validation,
        result=result,
    )
