from datetime import datetime, timezone

from backend.app.claims import (
    AgentAnswer,
    Claim,
    EvidenceRef,
)
from backend.app.evaluation import (
    DriftEvaluationRequest,
    evaluate_capture_drift,
)
from backend.app.schema import (
    Capture,
    NormalizedEvidence,
    OrganicEvidence,
    SearchContext,
    SerpApiMetadata,
    SurfaceState,
)


def make_capture(
    *,
    capture_id="capture-1",
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

    evidence = NormalizedEvidence(
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

    return Capture(
        capture_id=capture_id,
        captured_at=datetime.now(timezone.utc),
        search_context=SearchContext(
            query="test query",
            engine="google",
        ),
        serpapi_metadata=SerpApiMetadata(
            search_id=f"search-{capture_id}",
            status="Success",
        ),
        raw_response={},
        normalized_evidence=evidence,
    )


def make_answer(
    *,
    identity_key="url:https://example.com/source",
    importance="important",
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
                        identity_key=identity_key,
                        relation="supports",
                    )
                ],
            )
        ],
    )


def test_valid_evaluation_returns_complete_result():
    baseline = make_capture(
        capture_id="baseline"
    )

    current = make_capture(
        capture_id="current"
    )

    answer = make_answer()

    request = DriftEvaluationRequest(
        baseline_capture=baseline,
        current_capture=current,
        agent_answer=answer,
    )

    response = evaluate_capture_drift(request)

    assert response.validation.valid is True
    assert response.validation.unresolved_claim_links == []

    assert response.evaluation_id == (
        "baseline:current:answer-1"
    )

    assert response.baseline_capture_id == "baseline"
    assert response.current_capture_id == "current"

    assert response.result is not None

    assert response.result.evidence_diff.has_changes is False

    assert len(response.result.claim_impacts) == 1

    assert response.result.claim_impacts[0].claim_id == (
        "claim-1"
    )

    assert response.result.gate.decision == "pass"
    assert response.result.gate.severity == "none"


def test_valid_evaluation_detects_complete_support_loss():
    baseline = make_capture(
        capture_id="baseline"
    )

    current = Capture(
        capture_id="current",
        captured_at=datetime.now(timezone.utc),
        search_context=SearchContext(
            query="test query",
            engine="google",
        ),
        serpapi_metadata=SerpApiMetadata(
            search_id="search-current",
            status="Success",
        ),
        raw_response={},
        normalized_evidence=NormalizedEvidence(
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
        ),
    )

    answer = make_answer(
        importance="important"
    )

    response = evaluate_capture_drift(
        DriftEvaluationRequest(
            baseline_capture=baseline,
            current_capture=current,
            agent_answer=answer,
        )
    )

    assert response.validation.valid is True
    assert response.result is not None

    assert response.result.claim_impacts[0].material is True
    assert response.result.claim_impacts[0].dependency_status == (
        "lost"
    )

    assert response.result.gate.decision == "block"
    assert response.result.gate.material_claim_ids == [
        "claim-1"
    ]


def test_unresolved_baseline_link_is_validation_failure():
    baseline = make_capture(
        capture_id="baseline"
    )

    current = make_capture(
        capture_id="current"
    )

    answer = make_answer(
        identity_key="url:https://example.com/nonexistent"
    )

    response = evaluate_capture_drift(
        DriftEvaluationRequest(
            baseline_capture=baseline,
            current_capture=current,
            agent_answer=answer,
        )
    )

    assert response.validation.valid is False

    assert len(
        response.validation.unresolved_claim_links
    ) == 1

    validation = (
        response.validation.unresolved_claim_links[0]
    )

    assert validation.claim_id == "claim-1"
    assert validation.resolved is False
    assert validation.reason is not None

    assert response.result is None


def test_validation_failure_does_not_produce_gate_decision():
    baseline = make_capture(
        capture_id="baseline"
    )

    current = make_capture(
        capture_id="current"
    )

    answer = make_answer(
        identity_key="url:https://invalid.example/source"
    )

    response = evaluate_capture_drift(
        DriftEvaluationRequest(
            baseline_capture=baseline,
            current_capture=current,
            agent_answer=answer,
        )
    )

    assert response.validation.valid is False
    assert response.result is None
