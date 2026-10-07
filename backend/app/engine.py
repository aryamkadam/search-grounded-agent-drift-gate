from pydantic import BaseModel, Field

from .claims import AgentAnswer
from .diff import EvidenceDiff, compare_evidence
from .gate import DriftGateResult, evaluate_drift_gate
from .impact import ClaimImpact, evaluate_claim_impacts
from .schema import NormalizedEvidence


class DriftEvaluationResult(BaseModel):
    """Complete result of one end-to-end drift evaluation."""

    evidence_diff: EvidenceDiff

    claim_impacts: list[ClaimImpact] = Field(
        default_factory=list
    )

    gate: DriftGateResult


def evaluate_drift(
    baseline_evidence: NormalizedEvidence,
    current_evidence: NormalizedEvidence,
    agent_answer: AgentAnswer,
) -> DriftEvaluationResult:
    """
    Run the complete deterministic Drift Gate pipeline.

    Pipeline:

        baseline + current evidence
                ↓
           evidence diff
                ↓
           claim impact
                ↓
             drift gate
                ↓
          final evaluation
    """

    evidence_diff = compare_evidence(
        baseline_evidence,
        current_evidence,
    )

    claim_impacts = evaluate_claim_impacts(
        answer=agent_answer,
        evidence_diff=evidence_diff,
    )

    gate = evaluate_drift_gate(
        claim_impacts
    )

    return DriftEvaluationResult(
        evidence_diff=evidence_diff,
        claim_impacts=claim_impacts,
        gate=gate,
    )