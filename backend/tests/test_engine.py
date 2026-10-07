from backend.app.engine import evaluate_drift
from backend.app.schema import (
    NormalizedEvidence,
    OrganicEvidence,
    SurfaceState,
)
from backend.app.claims import (
    AgentAnswer,
    Claim,
    EvidenceRef,
)


def make_evidence(
    *,
    url="https://example.com/source",
    title="Example Source",
    snippet="Original evidence",
    position=1,
):
    organic = OrganicEvidence(
        identity_key=f"url:{url}",
        position=position,
        title=title,
        url=url,
        displayed_link="example.com",
        snippet=snippet,
        source="Example",
    )

    return NormalizedEvidence(
        query="test query",
        surfaces={
            "organic_results": SurfaceState(
                state="present",
                item_count=1,
            )
        },
        organic_results=[organic],
        ai_overview=None,
        perspectives=[],
        related_questions=[],
        inline_images=[],
        inline_videos=[],
    )


def make_answer(
    *,
    importance="important",
    relation="supports",
):
    return AgentAnswer(
        answer_id="answer-1",
        text="The example claim is supported.",
        claims=[
            Claim(
                claim_id="claim-1",
                text="The example claim is true.",
                importance=importance,
                confidence=0.9,
                evidence_refs=[
                    EvidenceRef(
                        surface="organic_results",
                        identity_key=(
                            "url:https://example.com/source"
                        ),
                        relation=relation,
                    )
                ],
            )
        ],
    )


def test_identical_evidence_passes():
    baseline = make_evidence()
    current = make_evidence()
    answer = make_answer()

    result = evaluate_drift(
        baseline_evidence=baseline,
        current_evidence=current,
        agent_answer=answer,
    )

    assert result.evidence_diff.has_changes is False
    assert len(result.claim_impacts) == 1

    impact = result.claim_impacts[0]

    assert impact.affected is False
    assert impact.dependency_status == "intact"

    assert result.gate.decision == "pass"
    assert result.gate.severity == "none"


def test_rank_only_change_passes():
    baseline = make_evidence(position=1)
    current = make_evidence(position=2)
    answer = make_answer()

    result = evaluate_drift(
        baseline_evidence=baseline,
        current_evidence=current,
        agent_answer=answer,
    )

    assert result.evidence_diff.has_changes is True

    impact = result.claim_impacts[0]

    assert impact.affected is False
    assert impact.dependency_status == "intact"

    assert result.gate.decision == "pass"


def test_supporting_evidence_change_warns():
    baseline = make_evidence(
        title="Original Source",
        snippet="Original evidence",
    )

    current = make_evidence(
        title="Updated Source",
        snippet="Updated evidence",
    )

    answer = make_answer()

    result = evaluate_drift(
        baseline_evidence=baseline,
        current_evidence=current,
        agent_answer=answer,
    )

    impact = result.claim_impacts[0]

    assert impact.affected is True
    assert impact.material is False
    assert impact.dependency_status == "changed"

    assert result.gate.decision == "warn"
    assert result.gate.severity == "medium"


def test_complete_support_loss_blocks_important_claim():
    baseline = make_evidence()

    current = NormalizedEvidence(
        query="test query",
        surfaces={
            "organic_results": SurfaceState(
                state="present",
                item_count=0,
            )
        },
        organic_results=[],
        ai_overview=None,
        perspectives=[],
        related_questions=[],
        inline_images=[],
        inline_videos=[],
    )

    answer = make_answer(
        importance="important"
    )

    result = evaluate_drift(
        baseline_evidence=baseline,
        current_evidence=current,
        agent_answer=answer,
    )

    impact = result.claim_impacts[0]

    assert impact.affected is True
    assert impact.material is True
    assert impact.dependency_status == "lost"

    assert result.gate.decision == "block"
    assert result.gate.severity == "high"
    assert result.gate.material_claim_ids == ["claim-1"]


def test_complete_support_loss_for_contextual_claim_passes():
    baseline = make_evidence()

    current = NormalizedEvidence(
        query="test query",
        surfaces={
            "organic_results": SurfaceState(
                state="present",
                item_count=0,
            )
        },
        organic_results=[],
        ai_overview=None,
        perspectives=[],
        related_questions=[],
        inline_images=[],
        inline_videos=[],
    )

    answer = make_answer(
        importance="contextual"
    )

    result = evaluate_drift(
        baseline_evidence=baseline,
        current_evidence=current,
        agent_answer=answer,
    )

    impact = result.claim_impacts[0]

    assert impact.affected is True
    assert impact.material is False
    assert impact.dependency_status == "lost"

    assert result.gate.decision == "pass"


def test_multiple_claims_are_orchestrated():
    baseline = make_evidence()

    current = NormalizedEvidence(
        query="test query",
        surfaces={
            "organic_results": SurfaceState(
                state="present",
                item_count=0,
            )
        },
        organic_results=[],
        ai_overview=None,
        perspectives=[],
        related_questions=[],
        inline_images=[],
        inline_videos=[],
    )

    answer = AgentAnswer(
        answer_id="answer-2",
        text="Two claims.",
        claims=[
            Claim(
                claim_id="claim-important",
                text="Important claim.",
                importance="important",
                confidence=0.9,
                evidence_refs=[
                    EvidenceRef(
                        surface="organic_results",
                        identity_key=(
                            "url:https://example.com/source"
                        ),
                        relation="supports",
                    )
                ],
            ),
            Claim(
                claim_id="claim-context",
                text="Contextual claim.",
                importance="contextual",
                confidence=0.8,
                evidence_refs=[
                    EvidenceRef(
                        surface="organic_results",
                        identity_key=(
                            "url:https://example.com/source"
                        ),
                        relation="supports",
                    )
                ],
            ),
        ],
    )

    result = evaluate_drift(
        baseline_evidence=baseline,
        current_evidence=current,
        agent_answer=answer,
    )

    assert len(result.claim_impacts) == 2

    assert result.claim_impacts[0].claim_id == (
        "claim-important"
    )
    assert result.claim_impacts[0].material is True

    assert result.claim_impacts[1].claim_id == (
        "claim-context"
    )
    assert result.claim_impacts[1].material is False

    assert result.gate.decision == "block"
    assert result.gate.material_claim_ids == [
        "claim-important"
    ]