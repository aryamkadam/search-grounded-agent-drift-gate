
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
from .schema import Capture, SearchContext


class SearchContextMismatch(BaseModel):
    """A field that differs between baseline and current searches."""

    field: str
    baseline_value: str | None
    current_value: str | None


class EvaluationValidation(BaseModel):
    """Validation status for an evaluation request."""

    valid: bool

    unresolved_claim_links: list[LinkValidation] = Field(
        default_factory=list
    )
    incompatible_search_context: list[SearchContextMismatch] = Field(
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


def compare_search_contexts(
    baseline: SearchContext,
    current: SearchContext,
) -> list[SearchContextMismatch]:
    """Identify differences in the contexts of two search captures."""

    fields = (
        "query",
        "engine",
        "google_domain",
        "language",
        "country",
        "location",
        "device",
    )

    mismatches = []

    for field in fields:
        baseline_value = getattr(baseline, field)
        current_value = getattr(current, field)

        if baseline_value != current_value:
            mismatches.append(
                SearchContextMismatch(
                    field=field,
                    baseline_value=baseline_value,
                    current_value=current_value,
                )
            )

    return mismatches


def evaluate_capture_drift(
    request: DriftEvaluationRequest,
    *,
    evaluator_version: str | None = None,
) -> DriftEvaluationResponse:
    """
    Validate and evaluate one baseline/current capture pair.

    Claim evidence links must resolve against the baseline capture.
    Both captures must also have matching search contexts before
    drift analysis can proceed.

    Invalid evidence links or incompatible search contexts are
    reported as validation failures, without producing a gate result.
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

    context_mismatches = compare_search_contexts(
        request.baseline_capture.search_context,
        request.current_capture.search_context,
    )

    validation = EvaluationValidation(
        valid=not unresolved and not context_mismatches,
        unresolved_claim_links=unresolved,
        incompatible_search_context=context_mismatches,
    )

    if unresolved or context_mismatches:
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
