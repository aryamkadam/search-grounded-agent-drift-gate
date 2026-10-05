from typing import Literal

from pydantic import BaseModel, Field

from .schema import NormalizedEvidence


DependencyType = Literal[
    "supports",
    "contradicts",
]

ClaimImportance = Literal[
    "critical",
    "important",
    "contextual",
]


class EvidenceRef(BaseModel):
    """
    Stable reference to one normalized evidence item.
    """

    surface: str
    identity_key: str

    relation: DependencyType = "supports"


class Claim(BaseModel):
    """
    One factual claim made by an agent.

    Claim text is supplied by the evaluation harness.
    Extraction is intentionally separate.
    """

    claim_id: str
    text: str

    evidence_refs: list[EvidenceRef] = Field(
        default_factory=list
    )

    importance: ClaimImportance = "important"

    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )


class AgentAnswer(BaseModel):
    """
    Agent answer plus explicit claim/evidence dependencies.
    """

    answer_id: str
    text: str

    claims: list[Claim] = Field(
        default_factory=list
    )


class LinkValidation(BaseModel):
    """Result of validating one claim's evidence reference."""

    claim_id: str
    evidence_ref: EvidenceRef

    resolved: bool

    reason: str | None = None


def _evidence_identity_set(
    evidence: NormalizedEvidence,
    surface: str,
) -> set[str]:
    if surface == "organic_results":
        return {
            item.identity_key
            for item in evidence.organic_results
        }

    if surface == "ai_overview.references":
        if evidence.ai_overview is None:
            return set()

        return {
            item.identity_key
            for item in evidence.ai_overview.references
        }

    if surface == "perspectives":
        return {
            item.identity_key
            for item in evidence.perspectives
        }

    if surface == "related_questions":
        return {
            item.identity_key
            for item in evidence.related_questions
        }

    if surface == "inline_images":
        return {
            item.identity_key
            for item in evidence.inline_images
        }

    if surface == "inline_videos":
        return {
            item.identity_key
            for item in evidence.inline_videos
        }

    return set()


def evidence_ref_exists(
    evidence: NormalizedEvidence,
    evidence_ref: EvidenceRef,
) -> bool:
    """Return whether an evidence reference resolves."""

    return evidence_ref.identity_key in _evidence_identity_set(
        evidence,
        evidence_ref.surface,
    )


def validate_claim_links(
    answer: AgentAnswer,
    evidence: NormalizedEvidence,
) -> list[LinkValidation]:
    """
    Validate every claim ? evidence dependency.

    This verifies existence only. It does not judge truth.
    """

    validations = []

    for claim in answer.claims:
        for evidence_ref in claim.evidence_refs:
            resolved = evidence_ref_exists(
                evidence,
                evidence_ref,
            )

            validations.append(
                LinkValidation(
                    claim_id=claim.claim_id,
                    evidence_ref=evidence_ref,
                    resolved=resolved,
                    reason=(
                        None
                        if resolved
                        else (
                            "Evidence reference does not "
                            "exist in this capture."
                        )
                    ),
                )
            )

    return validations


def unresolved_claim_links(
    answer: AgentAnswer,
    evidence: NormalizedEvidence,
) -> list[LinkValidation]:
    """Return only claim dependencies that fail to resolve."""

    return [
        validation
        for validation in validate_claim_links(
            answer,
            evidence,
        )
        if not validation.resolved
    ]
