from backend.app.claims import (
    AgentAnswer,
    Claim,
    EvidenceRef,
    evidence_ref_exists,
    validate_claim_links,
    unresolved_claim_links,
)
from backend.app.schema import (
    AIOverviewEvidence,
    AIOverviewReference,
    NormalizedEvidence,
    OrganicEvidence,
    SurfaceState,
)


def base_evidence():
    return NormalizedEvidence(
        surfaces={
            "organic_results": SurfaceState(
                state="present",
                item_count=1,
            ),
            "ai_overview": SurfaceState(
                state="present",
                item_count=1,
            ),
        },
        organic_results=[
            OrganicEvidence(
                identity_key="url:https://example.com/source-a",
                position=1,
                title="Source A",
                url="https://example.com/source-a",
                snippet="Evidence for claim A.",
                source="Example",
            )
        ],
        ai_overview=AIOverviewEvidence(
            references=[
                AIOverviewReference(
                    identity_key="url:https://example.com/source-b",
                    reference_index=0,
                    title="Source B",
                    url="https://example.com/source-b",
                    snippet="Evidence for claim B.",
                    source="Example",
                )
            ]
        ),
    )


def test_organic_evidence_reference_resolves():
    evidence = base_evidence()

    ref = EvidenceRef(
        surface="organic_results",
        identity_key="url:https://example.com/source-a",
    )

    assert evidence_ref_exists(
        evidence,
        ref,
    ) is True


def test_ai_reference_resolves():
    evidence = base_evidence()

    ref = EvidenceRef(
        surface="ai_overview.references",
        identity_key="url:https://example.com/source-b",
    )

    assert evidence_ref_exists(
        evidence,
        ref,
    ) is True


def test_unknown_evidence_reference_does_not_resolve():
    evidence = base_evidence()

    ref = EvidenceRef(
        surface="organic_results",
        identity_key="url:https://example.com/missing",
    )

    assert evidence_ref_exists(
        evidence,
        ref,
    ) is False


def test_claim_links_are_validated():
    evidence = base_evidence()

    answer = AgentAnswer(
        answer_id="answer-1",
        text="Example answer.",
        claims=[
            Claim(
                claim_id="claim-1",
                text="Source A supports this claim.",
                evidence_refs=[
                    EvidenceRef(
                        surface="organic_results",
                        identity_key=(
                            "url:https://example.com/source-a"
                        ),
                    )
                ],
            ),
            Claim(
                claim_id="claim-2",
                text="This claim has missing evidence.",
                evidence_refs=[
                    EvidenceRef(
                        surface="organic_results",
                        identity_key=(
                            "url:https://example.com/missing"
                        ),
                    )
                ],
            ),
        ],
    )

    results = validate_claim_links(
        answer,
        evidence,
    )

    assert len(results) == 2
    assert results[0].resolved is True
    assert results[1].resolved is False


def test_unresolved_claim_links_returns_only_failures():
    evidence = base_evidence()

    answer = AgentAnswer(
        answer_id="answer-2",
        text="Example answer.",
        claims=[
            Claim(
                claim_id="claim-1",
                text="Supported claim.",
                evidence_refs=[
                    EvidenceRef(
                        surface="organic_results",
                        identity_key=(
                            "url:https://example.com/source-a"
                        ),
                    )
                ],
            ),
            Claim(
                claim_id="claim-2",
                text="Unsupported link.",
                evidence_refs=[
                    EvidenceRef(
                        surface="organic_results",
                        identity_key=(
                            "url:https://example.com/missing"
                        ),
                    )
                ],
            ),
        ],
    )

    unresolved = unresolved_claim_links(
        answer,
        evidence,
    )

    assert len(unresolved) == 1
    assert unresolved[0].claim_id == "claim-2"
    assert unresolved[0].resolved is False


def test_claim_without_evidence_links_is_allowed():
    answer = AgentAnswer(
        answer_id="answer-3",
        text="Answer without explicit citations.",
        claims=[
            Claim(
                claim_id="claim-1",
                text="Some claim.",
            )
        ],
    )

    results = validate_claim_links(
        answer,
        base_evidence(),
    )

    assert results == []
def test_evidence_relationship_belongs_to_each_reference():
    answer = AgentAnswer(
        answer_id="answer-4",
        text="Conflicting evidence example.",
        claims=[
            Claim(
                claim_id="claim-4",
                text="Example claim.",
                evidence_refs=[
                    EvidenceRef(
                        surface="organic_results",
                        identity_key=(
                            "url:https://example.com/support"
                        ),
                        relation="supports",
                    ),
                    EvidenceRef(
                        surface="organic_results",
                        identity_key=(
                            "url:https://example.com/contradict"
                        ),
                        relation="contradicts",
                    ),
                ],
            )
        ],
    )

    assert (
        answer.claims[0].evidence_refs[0].relation
        == "supports"
    )

    assert (
        answer.claims[0].evidence_refs[1].relation
        == "contradicts"
    )
