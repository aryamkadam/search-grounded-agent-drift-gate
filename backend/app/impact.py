from typing import Literal

from pydantic import BaseModel, Field

from .claims import AgentAnswer, Claim, EvidenceRef
from .diff import EvidenceChange, EvidenceDiff


ImpactSeverity = Literal[
    "none",
    "low",
    "medium",
    "high",
]


# Status of ONE evidence dependency.
DependencyStatus = Literal[
    "intact",
    "changed",
    "lost",
    "context_changed",
]


# Aggregate status of ALL supporting dependencies for ONE claim.
ClaimDependencyStatus = Literal[
    "intact",
    "changed",
    "partially_degraded",
    "lost",
    "context_changed",
]


class DependencyImpact(BaseModel):
    """Impact of drift on one baseline claim dependency."""

    evidence_ref: EvidenceRef

    status: DependencyStatus
    severity: ImpactSeverity

    material_candidate: bool = False

    changes: list[EvidenceChange] = Field(
        default_factory=list
    )

    reasons: list[str] = Field(
        default_factory=list
    )


class ClaimImpact(BaseModel):
    """Aggregated impact of evidence drift on one claim."""

    claim_id: str
    importance: str

    affected: bool
    material: bool

    severity: ImpactSeverity
    dependency_status: ClaimDependencyStatus

    changed_dependencies: list[DependencyImpact] = Field(
        default_factory=list
    )

    reasons: list[str] = Field(
        default_factory=list
    )


def _all_changes(
    evidence_diff: EvidenceDiff,
) -> list[EvidenceChange]:
    return [
        change
        for surface_diff in evidence_diff.surface_diffs.values()
        for change in surface_diff.changes
    ]


def _changes_for_ref(
    evidence_ref: EvidenceRef,
    changes: list[EvidenceChange],
) -> list[EvidenceChange]:
    """
    Match only the exact baseline dependency.

    We deliberately do not fuzzy-match sources here.
    """

    matched = []

    for change in changes:
        if (
            change.surface == evidence_ref.surface
            and change.identity_key
            == evidence_ref.identity_key
        ):
            matched.append(change)

    return matched


def _is_position_only_change(
    change: EvidenceChange,
) -> bool:
    return (
        change.surface == "organic_results"
        and change.change_type == "modified"
        and set(change.changed_fields) <= {"position"}
    )


def _is_reference_index_only_change(
    change: EvidenceChange,
) -> bool:
    return (
        change.surface == "ai_overview.references"
        and change.change_type == "modified"
        and set(change.changed_fields)
        <= {"reference_index"}
    )


def _classify_dependency(
    evidence_ref: EvidenceRef,
    changes: list[EvidenceChange],
) -> DependencyImpact:
    """
    Classify drift affecting one exact evidence dependency.

    Important distinction:

    - DependencyImpact describes ONE dependency.
    - ClaimImpact later aggregates multiple dependencies.

    Therefore a removed supporting source is always "lost" here,
    regardless of the claim's importance or whether the gate should fail.
    """

    if not changes:
        return DependencyImpact(
            evidence_ref=evidence_ref,
            status="intact",
            severity="none",
        )

    # Presentation-only changes do not degrade the dependency.
    meaningful_changes = [
        change
        for change in changes
        if not _is_position_only_change(change)
        and not _is_reference_index_only_change(change)
    ]

    if not meaningful_changes:
        return DependencyImpact(
            evidence_ref=evidence_ref,
            status="intact",
            severity="none",
            changes=changes,
            reasons=[
                (
                    "Only presentation-level metadata changed; "
                    "the underlying evidence identity remains intact."
                )
            ],
        )

    # Removal of a baseline dependency.
    if any(
        change.change_type == "removed"
        for change in meaningful_changes
    ):
        if evidence_ref.relation == "supports":
            return DependencyImpact(
                evidence_ref=evidence_ref,
                status="lost",
                severity="high",
                material_candidate=True,
                changes=meaningful_changes,
                reasons=[
                    "A supporting evidence dependency was removed."
                ],
            )

        return DependencyImpact(
            evidence_ref=evidence_ref,
            status="context_changed",
            severity="medium",
            material_candidate=False,
            changes=meaningful_changes,
            reasons=[
                (
                    "A contradicting evidence dependency was "
                    "removed."
                )
            ],
        )

    # Modification of existing evidence.
    if any(
        change.change_type == "modified"
        for change in meaningful_changes
    ):
        if evidence_ref.relation == "supports":
            return DependencyImpact(
                evidence_ref=evidence_ref,
                status="changed",
                severity="medium",
                material_candidate=False,
                changes=meaningful_changes,
                reasons=[
                    (
                        "Supporting evidence changed, but this "
                        "engine does not infer semantic claim "
                        "failure from field changes alone."
                    )
                ],
            )

        return DependencyImpact(
            evidence_ref=evidence_ref,
            status="changed",
            severity="medium",
            material_candidate=False,
            changes=meaningful_changes,
            reasons=[
                (
                    "Contradicting evidence changed, but this "
                    "engine does not infer semantic meaning from "
                    "the change alone."
                )
            ],
        )

    return DependencyImpact(
        evidence_ref=evidence_ref,
        status="context_changed",
        severity="low",
        material_candidate=False,
        changes=meaningful_changes,
        reasons=[
            "The evidence dependency changed."
        ],
    )


def _supporting_refs(
    claim: Claim,
) -> list[EvidenceRef]:
    return [
        ref
        for ref in claim.evidence_refs
        if ref.relation == "supports"
    ]


def _material_from_support_loss(
    dependency_impacts: list[DependencyImpact],
    claim: Claim,
) -> bool:
    """
    Determine whether support loss should trigger the drift gate.

    Materiality is deliberately separate from dependency health.

    A dependency can be completely lost while the claim remains
    non-material if the claim is only contextual.
    """

    supporting = _supporting_refs(claim)

    if not supporting:
        return False

    removed_supports = [
        impact
        for impact in dependency_impacts
        if (
            impact.evidence_ref.relation == "supports"
            and impact.status == "lost"
        )
    ]

    all_supports_lost = (
        len(removed_supports) == len(supporting)
    )

    # Materiality requires complete loss of baseline support.
    # We do not fail a claim merely because one redundant source
    # disappeared.
    if not all_supports_lost:
        return False

    # Contextual claims can be affected without triggering the gate.
    return claim.importance in {
        "critical",
        "important",
    }


def _claim_dependency_status(
    impacts: list[DependencyImpact],
) -> ClaimDependencyStatus:
    """
    Aggregate individual dependency states into a claim-level state.

    This is intentionally separate from materiality.

    Examples:

    - A lost, B intact
        -> partially_degraded

    - A lost, B lost
        -> lost

    - A changed, B intact
        -> changed

    - No dependency drift
        -> intact
    """

    supporting_impacts = [
        impact
        for impact in impacts
        if impact.evidence_ref.relation == "supports"
    ]

    if supporting_impacts:
        lost_supports = [
            impact
            for impact in supporting_impacts
            if impact.status == "lost"
        ]

        if len(lost_supports) == len(supporting_impacts):
            return "lost"

        if lost_supports:
            return "partially_degraded"

    if any(
        impact.status == "changed"
        for impact in impacts
    ):
        return "changed"

    if any(
        impact.status == "context_changed"
        for impact in impacts
    ):
        return "context_changed"

    return "intact"


def _max_severity(
    impacts: list[DependencyImpact],
) -> ImpactSeverity:
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


def evaluate_claim_impact(
    claim: Claim,
    evidence_diff: EvidenceDiff,
) -> ClaimImpact:
    """
    Evaluate evidence drift against the dependencies declared by
    the baseline agent answer.

    This function does not invent new claim/evidence relationships.
    """

    changes = _all_changes(evidence_diff)

    dependency_impacts = []

    for evidence_ref in claim.evidence_refs:
        dependency_impacts.append(
            _classify_dependency(
                evidence_ref,
                _changes_for_ref(
                    evidence_ref,
                    changes,
                ),
            )
        )

    changed_dependencies = [
        impact
        for impact in dependency_impacts
        if impact.status != "intact"
    ]

    material = _material_from_support_loss(
        dependency_impacts,
        claim,
    )

    affected = bool(changed_dependencies)

    reasons = []

    for impact in changed_dependencies:
        for reason in impact.reasons:
            if reason not in reasons:
                reasons.append(reason)

    if material:
        reasons.append(
            "All baseline supporting evidence for the claim was lost."
        )

    return ClaimImpact(
        claim_id=claim.claim_id,
        importance=claim.importance,
        affected=affected,
        material=material,
        severity=_max_severity(
            dependency_impacts
        ),
        dependency_status=_claim_dependency_status(
            dependency_impacts,
        ),
        changed_dependencies=changed_dependencies,
        reasons=reasons,
    )


def evaluate_claim_impacts(
    answer: AgentAnswer,
    evidence_diff: EvidenceDiff,
) -> list[ClaimImpact]:
    """Evaluate all baseline claims against an evidence diff."""

    return [
        evaluate_claim_impact(
            claim,
            evidence_diff,
        )
        for claim in answer.claims
    ]
