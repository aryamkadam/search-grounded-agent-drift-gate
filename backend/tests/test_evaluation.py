
from datetime import datetime, timezone

import pytest

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
    assert response.validation.incompatible_search_context == []

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
    assert response.validation.incompatible_search_context == []
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

    assert response.validation.incompatible_search_context == []
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


def test_different_queries_do_not_produce_gate_decision():
    baseline = make_capture(capture_id="baseline")
    current = make_capture(capture_id="current")
    current.search_context.query = "different query"

    response = evaluate_capture_drift(
        DriftEvaluationRequest(
            baseline_capture=baseline,
            current_capture=current,
            agent_answer=make_answer(),
        )
    )

    assert response.validation.valid is False
    assert response.result is None

    assert len(response.validation.incompatible_search_context) == 1

    mismatch = response.validation.incompatible_search_context[0]

    assert mismatch.field == "query"
    assert mismatch.baseline_value == "test query"
    assert mismatch.current_value == "different query"


def test_matching_search_context_allows_evaluation():
    baseline = make_capture(capture_id="baseline")
    current = make_capture(capture_id="current")

    response = evaluate_capture_drift(
        DriftEvaluationRequest(
            baseline_capture=baseline,
            current_capture=current,
            agent_answer=make_answer(),
        )
    )

    assert response.validation.valid is True
    assert response.validation.incompatible_search_context == []
    assert response.result is not None


@pytest.mark.parametrize(
    ("field", "different_value"),
    [
        ("engine", "bing"),
        ("google_domain", "google.co.uk"),
        ("language", "fr"),
        ("country", "uk"),
        ("location", "London"),
        ("device", "mobile"),
    ],
)
def test_different_search_context_fields_prevent_evaluation(
    field,
    different_value,
):
    baseline = make_capture(capture_id="baseline")
    current = make_capture(capture_id="current")

    setattr(current.search_context, field, different_value)

    response = evaluate_capture_drift(
        DriftEvaluationRequest(
            baseline_capture=baseline,
            current_capture=current,
            agent_answer=make_answer(),
        )
    )

    assert response.validation.valid is False
    assert response.result is None

    mismatches = response.validation.incompatible_search_context

    assert len(mismatches) == 1
    assert mismatches[0].field == field
    assert mismatches[0].baseline_value == getattr(
        baseline.search_context,
        field,
    )
    assert mismatches[0].current_value == different_value


def test_explicit_evaluator_versions_produce_distinct_ids():
    baseline = make_capture(capture_id="baseline")
    current = make_capture(capture_id="current")
    answer = make_answer()

    request = DriftEvaluationRequest(
        baseline_capture=baseline,
        current_capture=current,
        agent_answer=answer,
    )

    legacy = evaluate_capture_drift(request)
    version_one = evaluate_capture_drift(
        request,
        evaluator_version="v1",
    )
    version_two = evaluate_capture_drift(
        request,
        evaluator_version="v2",
    )

    # The existing stateless endpoint's legacy ID must remain unchanged.
    assert legacy.evaluation_id == "baseline:current:answer-1"

    # Explicit evaluator versions must produce different stable IDs.
    assert version_one.evaluation_id.startswith("eval-v1-")
    assert version_two.evaluation_id.startswith("eval-v2-")
    assert version_one.evaluation_id != version_two.evaluation_id

    # Versioning changes evaluation identity, not the current algorithm's
    # result for otherwise identical inputs.
    assert version_one.result == version_two.result
