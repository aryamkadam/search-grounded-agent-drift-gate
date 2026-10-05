from backend.app.claims import (
    AgentAnswer,
    Claim,
    EvidenceRef,
)
from backend.app.diff import compare_evidence
from backend.app.impact import evaluate_claim_impact
from backend.app.schema import (
    NormalizedEvidence,
    OrganicEvidence,
    SurfaceState,
)


def evidence_with_sources(*sources):
    results = [
        OrganicEvidence(
            identity_key=f"url:https://example.com/{source}",
            position=index,
            title=source,
            url=f"https://example.com/{source}",
            snippet=f"Evidence from {source}",
            source="Example",
        )
        for index, source in enumerate(
            sources,
            start=1,
        )
    ]

    return NormalizedEvidence(
        surfaces={
            "organic_results": SurfaceState(
                state=(
                    "present"
                    if results
                    else "present_empty"
                ),
                item_count=len(results),
            )
        },
        organic_results=results,
    )


def support_claim(
    *sources,
    importance="important",
):
    return Claim(
        claim_id="claim-1",
        text="Example factual claim.",
        importance=importance,
        evidence_refs=[
            EvidenceRef(
                surface="organic_results",
                identity_key=(
                    f"url:https://example.com/{source}"
                ),
                relation="supports",
            )
            for source in sources
        ],
    )


def test_rank_only_change_does_not_affect_claim():
    baseline = evidence_with_sources("a")
    current = evidence_with_sources("a")

    current.organic_results[0].position = 2

    diff = compare_evidence(
        baseline,
        current,
    )

    impact = evaluate_claim_impact(
        support_claim("a"),
        diff,
    )

    assert impact.affected is False
    assert impact.material is False
    assert impact.severity == "none"
    assert impact.dependency_status == "intact"


def test_one_of_two_supports_removed_is_not_material():
    baseline = evidence_with_sources("a", "b")
    current = evidence_with_sources("a")

    diff = compare_evidence(
        baseline,
        current,
    )

    impact = evaluate_claim_impact(
        support_claim("a", "b"),
        diff,
    )

    assert impact.affected is True
    assert impact.material is False
    assert impact.severity == "high"
    assert impact.dependency_status == "partially_degraded"

    assert len(impact.changed_dependencies) == 1
    assert (
        impact.changed_dependencies[0].status
        == "lost"
    )


def test_all_support_removed_is_material_for_important_claim():
    baseline = evidence_with_sources("a")
    current = evidence_with_sources()

    diff = compare_evidence(
        baseline,
        current,
    )

    impact = evaluate_claim_impact(
        support_claim(
            "a",
            importance="important",
        ),
        diff,
    )

    assert impact.affected is True
    assert impact.material is True
    assert impact.severity == "high"
    assert impact.dependency_status == "lost"

    assert len(impact.changed_dependencies) == 1
    assert (
        impact.changed_dependencies[0].status
        == "lost"
    )


def test_all_support_removed_is_material_for_critical_claim():
    baseline = evidence_with_sources("a")
    current = evidence_with_sources()

    diff = compare_evidence(
        baseline,
        current,
    )

    impact = evaluate_claim_impact(
        support_claim(
            "a",
            importance="critical",
        ),
        diff,
    )

    assert impact.affected is True
    assert impact.material is True
    assert impact.severity == "high"
    assert impact.dependency_status == "lost"


def test_all_support_removed_is_not_gate_material_for_contextual_claim():
    baseline = evidence_with_sources("a")
    current = evidence_with_sources()

    diff = compare_evidence(
        baseline,
        current,
    )

    impact = evaluate_claim_impact(
        support_claim(
            "a",
            importance="contextual",
        ),
        diff,
    )

    assert impact.affected is True
    assert impact.material is False
    assert impact.severity == "high"

    # The dependency itself is completely lost.
    # Importance controls gate materiality separately.
    assert impact.dependency_status == "lost"

    assert len(impact.changed_dependencies) == 1
    assert (
        impact.changed_dependencies[0].status
        == "lost"
    )


def test_supporting_content_change_is_potential_but_not_material():
    baseline = evidence_with_sources("a")
    current = evidence_with_sources("a")

    current.organic_results[0].snippet = (
        "Changed evidence content"
    )

    diff = compare_evidence(
        baseline,
        current,
    )

    impact = evaluate_claim_impact(
        support_claim("a"),
        diff,
    )

    assert impact.affected is True
    assert impact.material is False
    assert impact.severity == "medium"
    assert impact.dependency_status == "changed"


def test_contradicting_source_removal_is_not_material():
    baseline = evidence_with_sources("a", "b")
    current = evidence_with_sources("a")

    diff = compare_evidence(
        baseline,
        current,
    )

    claim = Claim(
        claim_id="claim-2",
        text="Example factual claim.",
        evidence_refs=[
            EvidenceRef(
                surface="organic_results",
                identity_key="url:https://example.com/a",
                relation="supports",
            ),
            EvidenceRef(
                surface="organic_results",
                identity_key="url:https://example.com/b",
                relation="contradicts",
            ),
        ],
    )

    impact = evaluate_claim_impact(
        claim,
        diff,
    )

    assert impact.affected is True
    assert impact.material is False
    assert impact.dependency_status == "context_changed"


def test_unrelated_new_source_does_not_affect_claim():
    baseline = evidence_with_sources("a")
    current = evidence_with_sources("a", "b")

    diff = compare_evidence(
        baseline,
        current,
    )

    impact = evaluate_claim_impact(
        support_claim("a"),
        diff,
    )

    assert impact.affected is False
    assert impact.material is False
    assert impact.dependency_status == "intact"


def test_reference_number_change_does_not_affect_claim():
    from backend.app.schema import (
        AIOverviewEvidence,
        AIOverviewReference,
    )

    baseline = NormalizedEvidence(
        surfaces={
            "ai_overview": SurfaceState(
                state="present",
                item_count=1,
            )
        },
        ai_overview=AIOverviewEvidence(
            references=[
                AIOverviewReference(
                    identity_key="url:https://example.com/source",
                    reference_index=0,
                    title="Source",
                    url="https://example.com/source",
                )
            ]
        ),
    )

    current = NormalizedEvidence(
        surfaces={
            "ai_overview": SurfaceState(
                state="present",
                item_count=1,
            )
        },
        ai_overview=AIOverviewEvidence(
            references=[
                AIOverviewReference(
                    identity_key="url:https://example.com/source",
                    reference_index=1,
                    title="Source",
                    url="https://example.com/source",
                )
            ]
        ),
    )

    diff = compare_evidence(
        baseline,
        current,
    )

    claim = Claim(
        claim_id="claim-3",
        text="AI-supported claim.",
        evidence_refs=[
            EvidenceRef(
                surface="ai_overview.references",
                identity_key="url:https://example.com/source",
                relation="supports",
            )
        ],
    )

    impact = evaluate_claim_impact(
        claim,
        diff,
    )

    assert impact.affected is False
    assert impact.material is False
    assert impact.dependency_status == "intact"


def test_claim_with_no_dependencies_is_unchanged():
    baseline = evidence_with_sources("a")
    current = evidence_with_sources("b")

    diff = compare_evidence(
        baseline,
        current,
    )

    claim = Claim(
        claim_id="claim-4",
        text="Unlinked claim.",
    )

    impact = evaluate_claim_impact(
        claim,
        diff,
    )

    assert impact.affected is False
    assert impact.material is False
    assert impact.dependency_status == "intact"


def test_full_answer_claims_are_evaluated():
    baseline = evidence_with_sources("a", "b")
    current = evidence_with_sources("a")

    diff = compare_evidence(
        baseline,
        current,
    )

    answer = AgentAnswer(
        answer_id="answer-1",
        text="Example answer.",
        claims=[
            support_claim("a", "b"),
            Claim(
                claim_id="claim-2",
                text="Unlinked claim.",
            ),
        ],
    )

    from backend.app.impact import evaluate_claim_impacts

    impacts = evaluate_claim_impacts(
        answer,
        diff,
    )

    assert len(impacts) == 2
    assert impacts[0].affected is True
    assert impacts[0].material is False
    assert impacts[0].dependency_status == "partially_degraded"

    assert impacts[1].affected is False
    assert impacts[1].material is False
    assert impacts[1].dependency_status == "intact"


def test_all_support_removed_from_contextual_claim_is_still_lost():
    baseline = evidence_with_sources("a")
    current = evidence_with_sources()

    diff = compare_evidence(
        baseline,
        current,
    )

    impact = evaluate_claim_impact(
        support_claim(
            "a",
            importance="contextual",
        ),
        diff,
    )

    assert impact.affected is True
    assert impact.material is False
    assert impact.severity == "high"
    assert impact.dependency_status == "lost"

    assert len(impact.changed_dependencies) == 1
    assert (
        impact.changed_dependencies[0].status
        == "lost"
    )
