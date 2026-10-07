from typing import Literal

from pydantic import BaseModel, Field

from .impact import ClaimImpact


GateDecision = Literal[
    "pass",
    "warn",
    "block",
]


GateSeverity = Literal[
    "none",
    "low",
    "medium",
    "high",
]


class DriftGateResult(BaseModel):
    """Final policy decision produced by the Drift Gate."""

    decision: GateDecision
    severity: GateSeverity

    affected_claim_ids: list[str] = Field(
        default_factory=list
    )

    material_claim_ids: list[str] = Field(
        default_factory=list
    )

    reasons: list[str] = Field(
        default_factory=list
    )


def _max_severity(
    impacts: list[ClaimImpact],
) -> GateSeverity:
    rank = {
        "none": 0,
        "low": 1,
        "medium": 2,
        "high": 3,
    }

    if not impacts:
        return "none"

    return max(
        (
            impact.severity
            for impact in impacts
        ),
        key=lambda value: rank[value],
    )


def _reason_for_material_claim(
    impact: ClaimImpact,
) -> str:
    return (
        f"Claim '{impact.claim_id}' lost all baseline "
        f"support and is classified as {impact.importance}."
    )


def _reason_for_warning(
    impact: ClaimImpact,
) -> str:
    if impact.dependency_status == "partially_degraded":
        return (
            f"Claim '{impact.claim_id}' lost part of its "
            "supporting evidence."
        )

    if impact.dependency_status == "changed":
        return (
            f"Supporting evidence for claim "
            f"'{impact.claim_id}' changed."
        )

    if impact.dependency_status == "context_changed":
        return (
            f"Evidence context for claim "
            f"'{impact.claim_id}' changed."
        )

    if impact.dependency_status == "lost":
        return (
            f"Claim '{impact.claim_id}' was affected by "
            "complete support loss, but the claim is not "
            "gate-material."
        )

    return (
        f"Claim '{impact.claim_id}' was affected by "
        "evidence drift."
    )


def evaluate_drift_gate(
    impacts: list[ClaimImpact],
) -> DriftGateResult:
    """
    Convert claim-level impact analysis into a deterministic
    Drift Gate decision.

    Policy:

    - Material claim impact -> BLOCK.
    - Non-material but meaningful claim impact -> WARN.
    - Contextual complete support loss -> PASS.
    - No affected claims -> PASS.

    Gate policy is intentionally separate from evidence
    classification and claim impact analysis.
    """

    affected = [
        impact
        for impact in impacts
        if impact.affected
    ]

    material = [
        impact
        for impact in impacts
        if impact.material
    ]

    affected_claim_ids = [
        impact.claim_id
        for impact in affected
    ]

    material_claim_ids = [
        impact.claim_id
        for impact in material
    ]

    reasons = []

    # ---------------------------------------------------------
    # BLOCK
    # ---------------------------------------------------------

    if material:
        for impact in material:
            reason = _reason_for_material_claim(
                impact
            )

            if reason not in reasons:
                reasons.append(reason)

        return DriftGateResult(
            decision="block",
            severity=_max_severity(material),
            affected_claim_ids=affected_claim_ids,
            material_claim_ids=material_claim_ids,
            reasons=reasons,
        )

    # ---------------------------------------------------------
    # WARN
    # ---------------------------------------------------------

    for impact in affected:
        # A contextual claim with complete support loss is
        # intentionally non-gate-material.
        #
        # It remains affected at the claim layer, but does
        # not require a gate warning.
        if (
            impact.dependency_status == "lost"
            and impact.importance == "contextual"
            and not impact.material
        ):
            continue

        reason = _reason_for_warning(
            impact
        )

        if reason not in reasons:
            reasons.append(reason)

    if reasons:
        return DriftGateResult(
            decision="warn",
            severity=_max_severity(affected),
            affected_claim_ids=affected_claim_ids,
            material_claim_ids=material_claim_ids,
            reasons=reasons,
        )

    # ---------------------------------------------------------
    # PASS
    # ---------------------------------------------------------

    return DriftGateResult(
        decision="pass",
        severity="none",
        affected_claim_ids=affected_claim_ids,
        material_claim_ids=material_claim_ids,
        reasons=[],
    )
