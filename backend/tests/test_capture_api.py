
import json
import sqlite3
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from backend.app.capture import create_capture
from backend.app.capture_repository import SQLiteCaptureRepository
from backend.app.evaluation_repository import SQLiteEvaluationRepository
from backend.app.main import (
    app,
    get_capture_repository,
    get_evaluation_repository,
)
from backend.app.serpapi_client import SerpApiError


client = TestClient(app)


def sample_search_response(query="quantum computing"):
    return {
        "search_metadata": {
            "id": "search-api-123",
            "status": "Success",
            "created_at": "2026-10-09 10:00:00 UTC",
            "processed_at": "2026-10-09 10:00:01 UTC",
            "google_url": "https://www.google.com/search",
            "total_time_taken": 0.5,
        },
        "search_parameters": {
            "engine": "google",
            "q": query,
            "google_domain": "google.com",
            "hl": "en",
            "gl": "in",
            "device": "desktop",
        },
        "organic_results": [
            {
                "position": 1,
                "title": "Quantum Computing",
                "link": "https://example.com/quantum",
                "snippet": "An example source about quantum computing.",
            }
        ],
    }


@pytest.fixture
def repository(tmp_path):
    return SQLiteCaptureRepository(
        tmp_path / "captures.sqlite3"
    )


@pytest.fixture
def api_evaluation_repository(repository):
    evaluation_repository = SQLiteEvaluationRepository(
        repository.database_path
    )
    app.dependency_overrides[get_evaluation_repository] = (
        lambda: evaluation_repository
    )
    yield evaluation_repository
    app.dependency_overrides.pop(
        get_evaluation_repository,
        None,
    )


@pytest.fixture
def api_repository(repository, api_evaluation_repository):
    app.dependency_overrides[get_capture_repository] = (
        lambda: repository
    )
    yield repository
    app.dependency_overrides.pop(
        get_capture_repository,
        None,
    )


def test_create_capture_endpoint_persists_search(
    monkeypatch,
    api_repository,
):
    calls = {}

    def fake_search_google(**kwargs):
        calls.update(kwargs)
        return sample_search_response(kwargs["query"])

    monkeypatch.setattr(
        "backend.app.main.search_google",
        fake_search_google,
    )

    response = client.post(
        "/v1/captures",
        json={"query": "quantum computing"},
    )

    assert response.status_code == 201

    body = response.json()

    assert body["capture_id"]
    assert body["query"] == "quantum computing"
    assert body["search_id"] == "search-api-123"
    assert body["storage_status"] == "stored"

    assert calls["query"] == "quantum computing"

    stored = api_repository.get(body["capture_id"])
    assert stored is not None
    assert stored.search_context.query == "quantum computing"
    assert stored.raw_response["search_metadata"]["id"] == (
        "search-api-123"
    )


def test_get_capture_endpoint_returns_stored_capture(
    api_repository,
):
    capture = create_capture(
        sample_search_response(),
        capture_id="capture-retrieval-123",
        captured_at=datetime(
            2026, 10, 9, 10, 0, tzinfo=timezone.utc
        ),
    )
    api_repository.save(capture)

    response = client.get(
        "/v1/captures/capture-retrieval-123"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["capture_id"] == "capture-retrieval-123"
    assert body["search_context"]["query"] == "quantum computing"
    assert body["raw_response"]["search_metadata"]["id"] == (
        "search-api-123"
    )


def test_get_missing_capture_returns_404(api_repository):
    response = client.get(
        "/v1/captures/does-not-exist"
    )

    assert response.status_code == 404


def test_create_capture_rejects_blank_query(
    monkeypatch,
    api_repository,
):
    def search_should_not_run(**kwargs):
        pytest.fail("Search must not run for a blank query")

    monkeypatch.setattr(
        "backend.app.main.search_google",
        search_should_not_run,
    )

    response = client.post(
        "/v1/captures",
        json={"query": "   "},
    )

    assert response.status_code == 422


def test_search_provider_failure_returns_502(
    monkeypatch,
    api_repository,
):
    def failing_search(**kwargs):
        raise SerpApiError("simulated provider failure")

    monkeypatch.setattr(
        "backend.app.main.search_google",
        failing_search,
    )

    response = client.post(
        "/v1/captures",
        json={"query": "quantum computing"},
    )

    assert response.status_code == 502


def test_storage_conflict_returns_controlled_error(
    monkeypatch,
    api_repository,
):
    from backend.app.capture_repository import CaptureConflictError

    def fake_search_google(**kwargs):
        return sample_search_response(kwargs["query"])

    monkeypatch.setattr(
        "backend.app.main.search_google",
        fake_search_google,
    )

    def reject_save(capture):
        raise CaptureConflictError("simulated conflict")

    monkeypatch.setattr(api_repository, "save", reject_save)

    response = client.post(
        "/v1/captures",
        json={"query": "quantum computing"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Capture ID conflicts with existing stored content."
    )


def persisted_answer_payload(
    identity_key="url:https://example.com/quantum",
):
    return {
        "answer_id": "answer-persisted-1",
        "text": "Quantum computing is discussed by the source.",
        "claims": [
            {
                "claim_id": "claim-persisted-1",
                "text": "The source discusses quantum computing.",
                "evidence_refs": [
                    {
                        "surface": "organic_results",
                        "identity_key": identity_key,
                        "relation": "supports",
                    }
                ],
                "importance": "important",
                "confidence": 0.9,
            }
        ],
    }


def test_persisted_evaluation_uses_stored_captures(
    api_repository,
):
    baseline = create_capture(
        sample_search_response(),
        capture_id="baseline-persisted",
    )
    current = create_capture(
        sample_search_response(),
        capture_id="current-persisted",
    )

    api_repository.save(baseline)
    api_repository.save(current)

    response = client.post(
        "/v1/evaluations/persisted",
        json={
            "baseline_capture_id": baseline.capture_id,
            "current_capture_id": current.capture_id,
            "agent_answer": persisted_answer_payload(),
        },
    )

    assert response.status_code == 200

    body = response.json()
    assert body["baseline_capture_id"] == baseline.capture_id
    assert body["current_capture_id"] == current.capture_id
    assert body["validation"]["valid"] is True
    assert body["validation"]["unresolved_claim_links"] == []
    assert body["result"] is not None


def test_persisted_evaluation_returns_404_for_missing_baseline(
    api_repository,
):
    current = create_capture(
        sample_search_response(),
        capture_id="current-existing",
    )
    api_repository.save(current)

    response = client.post(
        "/v1/evaluations/persisted",
        json={
            "baseline_capture_id": "missing-baseline",
            "current_capture_id": current.capture_id,
            "agent_answer": persisted_answer_payload(),
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Baseline capture not found."


def test_persisted_evaluation_returns_404_for_missing_current(
    api_repository,
):
    baseline = create_capture(
        sample_search_response(),
        capture_id="baseline-existing",
    )
    api_repository.save(baseline)

    response = client.post(
        "/v1/evaluations/persisted",
        json={
            "baseline_capture_id": baseline.capture_id,
            "current_capture_id": "missing-current",
            "agent_answer": persisted_answer_payload(),
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Current capture not found."


def test_persisted_evaluation_rejects_unresolved_evidence_links(
    api_repository,
):
    baseline = create_capture(
        sample_search_response(),
        capture_id="baseline-invalid-link",
    )
    current = create_capture(
        sample_search_response(),
        capture_id="current-invalid-link",
    )

    api_repository.save(baseline)
    api_repository.save(current)

    response = client.post(
        "/v1/evaluations/persisted",
        json={
            "baseline_capture_id": baseline.capture_id,
            "current_capture_id": current.capture_id,
            "agent_answer": persisted_answer_payload(
                identity_key="url:https://example.com/not-in-baseline",
            ),
        },
    )

    assert response.status_code == 200

    body = response.json()
    assert body["validation"]["valid"] is False
    assert body["validation"]["unresolved_claim_links"]
    assert body["result"] is None


def test_persisted_evaluation_is_saved_and_retrievable(
    api_repository,
    api_evaluation_repository,
):
    baseline = create_capture(
        sample_search_response(),
        capture_id="baseline-history-api",
    )
    current = create_capture(
        sample_search_response(),
        capture_id="current-history-api",
    )
    api_repository.save(baseline)
    api_repository.save(current)

    response = client.post(
        "/v1/evaluations/persisted",
        json={
            "baseline_capture_id": baseline.capture_id,
            "current_capture_id": current.capture_id,
            "agent_answer": persisted_answer_payload(),
        },
    )
    assert response.status_code == 200
    evaluation_id = response.json()["evaluation_id"]

    history_response = client.get(
        f"/v1/evaluations/{evaluation_id}"
    )
    assert history_response.status_code == 200
    history = history_response.json()

    assert history["evaluation_id"] == evaluation_id
    assert evaluation_id.startswith("eval-v1-")
    assert history["evaluator_version"] == "v1"
    assert history["baseline_capture_id"] == baseline.capture_id
    assert history["current_capture_id"] == current.capture_id
    assert history["agent_answer"]["answer_id"] == (
        "answer-persisted-1"
    )
    assert history["response"]["evaluation_id"] == evaluation_id
    assert history["response"]["result"] is not None
    assert history["created_at"]


def test_persisted_evaluation_retry_is_idempotent(
    api_repository,
    api_evaluation_repository,
):
    baseline = create_capture(
        sample_search_response(),
        capture_id="baseline-retry-api",
    )
    current = create_capture(
        sample_search_response(),
        capture_id="current-retry-api",
    )
    api_repository.save(baseline)
    api_repository.save(current)
    payload = {
        "baseline_capture_id": baseline.capture_id,
        "current_capture_id": current.capture_id,
        "agent_answer": persisted_answer_payload(),
    }

    first = client.post("/v1/evaluations/persisted", json=payload)
    second = client.post("/v1/evaluations/persisted", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json() == first.json()

    with sqlite3.connect(
        api_evaluation_repository.database_path
    ) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM evaluations WHERE evaluation_id = ?",
            (first.json()["evaluation_id"],),
        ).fetchone()[0]

    assert count == 1


def test_conflicting_persisted_evaluation_inputs_return_409(
    api_repository,
    api_evaluation_repository,
):
    baseline = create_capture(
        sample_search_response(),
        capture_id="baseline-conflict-api",
    )
    current = create_capture(
        sample_search_response(),
        capture_id="current-conflict-api",
    )
    api_repository.save(baseline)
    api_repository.save(current)
    payload = {
        "baseline_capture_id": baseline.capture_id,
        "current_capture_id": current.capture_id,
        "agent_answer": persisted_answer_payload(),
    }

    first = client.post("/v1/evaluations/persisted", json=payload)
    assert first.status_code == 200

    changed_payload = {
        **payload,
        "agent_answer": persisted_answer_payload(),
    }
    changed_payload["agent_answer"]["text"] = (
        "A changed answer with the same ID."
    )
    conflict = client.post(
        "/v1/evaluations/persisted",
        json=changed_payload,
    )

    assert conflict.status_code == 409
    assert conflict.json()["detail"] == (
        "Evaluation ID conflicts with existing content."
    )


def test_get_missing_evaluation_returns_404(api_evaluation_repository):
    response = client.get("/v1/evaluations/no-such-evaluation")

    assert response.status_code == 404
    assert response.json()["detail"] == "Evaluation not found."


def test_get_evaluation_returns_500_when_stored_record_is_tampered(
    api_repository,
    api_evaluation_repository,
):
    baseline = create_capture(
        sample_search_response(),
        capture_id="baseline-tamper-api",
    )
    current = create_capture(
        sample_search_response(),
        capture_id="current-tamper-api",
    )
    api_repository.save(baseline)
    api_repository.save(current)

    response = client.post(
        "/v1/evaluations/persisted",
        json={
            "baseline_capture_id": baseline.capture_id,
            "current_capture_id": current.capture_id,
            "agent_answer": persisted_answer_payload(),
        },
    )
    assert response.status_code == 200
    evaluation_id = response.json()["evaluation_id"]

    with sqlite3.connect(
        api_evaluation_repository.database_path
    ) as connection:
        connection.execute(
            "UPDATE evaluations SET response_json = ? "
            "WHERE evaluation_id = ?",
            (json.dumps({"tampered": True}), evaluation_id),
        )

    history_response = client.get(
        f"/v1/evaluations/{evaluation_id}"
    )
    assert history_response.status_code == 500
    assert history_response.json()["detail"] == (
        "Stored evaluation integrity verification failed."
    )


def test_existing_evaluation_retry_does_not_recompute(
    monkeypatch,
    api_repository,
    api_evaluation_repository,
):
    baseline = create_capture(
        sample_search_response(),
        capture_id="baseline-no-recompute",
    )
    current = create_capture(
        sample_search_response(),
        capture_id="current-no-recompute",
    )
    api_repository.save(baseline)
    api_repository.save(current)

    payload = {
        "baseline_capture_id": baseline.capture_id,
        "current_capture_id": current.capture_id,
        "agent_answer": persisted_answer_payload(),
    }

    first = client.post("/v1/evaluations/persisted", json=payload)
    assert first.status_code == 200

    def unexpected_evaluation(*args, **kwargs):
        pytest.fail("An existing evaluation should not be recomputed.")

    monkeypatch.setattr(
        "backend.app.main.evaluate_capture_drift",
        unexpected_evaluation,
    )

    retry = client.post("/v1/evaluations/persisted", json=payload)

    assert retry.status_code == 200
    assert retry.json() == first.json()


def test_list_captures_returns_empty_list(api_repository):
    response = client.get("/v1/captures")
    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "total": 0,
        "limit": 50,
        "offset": 0,
    }


def test_list_captures_returns_newest_first(api_repository):
    older = create_capture(
        sample_search_response("older query"),
        capture_id="capture-list-old",
        captured_at=datetime(
            2026, 10, 8, 10, 0, tzinfo=timezone.utc
        ),
    )
    newer = create_capture(
        sample_search_response("newer query"),
        capture_id="capture-list-new",
        captured_at=datetime(
            2026, 10, 9, 10, 0, tzinfo=timezone.utc
        ),
    )
    api_repository.save(older)
    api_repository.save(newer)

    response = client.get("/v1/captures")
    assert response.status_code == 200
    body = response.json()

    assert body["total"] == 2
    assert [
        item["capture_id"] for item in body["items"]
    ] == ["capture-list-new", "capture-list-old"]
    assert body["items"][0]["query"] == "newer query"
    assert "raw_response" not in body["items"][0]


def test_list_captures_supports_pagination(api_repository):
    for index in range(3):
        capture = create_capture(
            sample_search_response(f"query {index}"),
            capture_id=f"capture-page-{index}",
            captured_at=datetime(
                2026, 10, 8, 10 + index, 0, tzinfo=timezone.utc
            ),
        )
        api_repository.save(capture)

    response = client.get(
        "/v1/captures",
        params={"limit": 1, "offset": 1},
    )
    assert response.status_code == 200
    body = response.json()

    assert body["total"] == 3
    assert body["limit"] == 1
    assert body["offset"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["capture_id"] == "capture-page-1"


@pytest.mark.parametrize(
    "query_string",
    ["?limit=0", "?limit=101", "?offset=-1", "?limit=abc"],
)
def test_list_captures_rejects_invalid_pagination(
    api_repository,
    query_string,
):
    response = client.get(f"/v1/captures{query_string}")
    assert response.status_code == 422


def test_list_captures_returns_500_when_capture_is_tampered(
    api_repository,
):
    capture = create_capture(
        sample_search_response(),
        capture_id="capture-list-tampered",
    )
    api_repository.save(capture)

    with sqlite3.connect(api_repository.database_path) as connection:
        connection.execute(
            "UPDATE captures SET capture_json = ? WHERE capture_id = ?",
            (json.dumps({"tampered": True}), capture.capture_id),
        )

    response = client.get("/v1/captures")
    assert response.status_code == 500
    assert response.json()["detail"] == (
        "Stored capture integrity verification failed."
    )


def test_persisted_block_decision_is_saved_and_retrievable(
    api_repository,
    api_evaluation_repository,
):
    baseline = create_capture(
        sample_search_response(),
        capture_id="baseline-support-loss-block",
    )

    current_response = sample_search_response()
    current_response["organic_results"] = []

    current = create_capture(
        current_response,
        capture_id="current-support-loss-block",
    )

    api_repository.save(baseline)
    api_repository.save(current)

    response = client.post(
        "/v1/evaluations/persisted",
        json={
            "baseline_capture_id": baseline.capture_id,
            "current_capture_id": current.capture_id,
            "agent_answer": persisted_answer_payload(),
        },
    )

    assert response.status_code == 200

    body = response.json()
    assert body["validation"]["valid"] is True
    assert body["result"]["gate"]["decision"] == "block"
    assert body["result"]["gate"]["material_claim_ids"] == [
        "claim-persisted-1"
    ]

    evaluation_id = body["evaluation_id"]

    history_response = client.get(
        f"/v1/evaluations/{evaluation_id}"
    )

    assert history_response.status_code == 200

    history = history_response.json()
    assert history["evaluation_id"] == evaluation_id
    assert history["response"]["result"]["gate"]["decision"] == "block"
    assert history["response"]["result"]["gate"]["material_claim_ids"] == [
        "claim-persisted-1"
    ]


@pytest.mark.parametrize(
    "origin",
    [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
)
def test_vite_origins_are_allowed_by_cors(origin):
    response = client.options(
        "/v1/captures",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert "GET" in response.headers["access-control-allow-methods"]


def test_replay_capture_returns_stored_snapshot_without_search(
    monkeypatch,
    api_repository,
):
    capture = create_capture(
        sample_search_response("offline replay test"),
        capture_id="offline-replay-capture",
    )
    api_repository.save(capture)

    def fail_if_search_called(**kwargs):
        raise AssertionError("Replay must not call SerpApi")

    monkeypatch.setattr(
        "backend.app.main.search_google",
        fail_if_search_called,
    )

    response = client.post(
        f"/v1/captures/{capture.capture_id}/replay"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["replay_id"]
    assert body["capture_id"] == capture.capture_id
    assert body["status"] == "completed"
    assert body["mode"] == "offline"
    assert body["captured_at"] == (
        capture.captured_at.isoformat().replace("+00:00", "Z")
    )
    assert body["search_context"]["query"] == "offline replay test"
    assert body["normalized_evidence"] == (
        capture.normalized_evidence.model_dump(mode="json")
    )


def test_replay_capture_returns_404_for_unknown_capture(
    api_repository,
):
    response = client.post(
        "/v1/captures/does-not-exist/replay"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Capture not found."


def test_list_evaluations_returns_empty_page(
    api_repository,
):
    response = client.get("/v1/evaluations")

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "total": 0,
        "limit": 50,
        "offset": 0,
    }


def test_list_evaluations_returns_paginated_summaries(
    api_repository,
):
    baseline = create_capture(
        sample_search_response(),
        capture_id="evaluation-list-baseline",
    )

    current_response = sample_search_response()
    current_response["organic_results"] = []

    current = create_capture(
        current_response,
        capture_id="evaluation-list-current",
    )

    api_repository.save(baseline)
    api_repository.save(current)

    created_evaluation_ids = []

    for answer_id in (
        "evaluation-list-answer-1",
        "evaluation-list-answer-2",
    ):
        answer = persisted_answer_payload()
        answer["answer_id"] = answer_id

        response = client.post(
            "/v1/evaluations/persisted",
            json={
                "baseline_capture_id": baseline.capture_id,
                "current_capture_id": current.capture_id,
                "agent_answer": answer,
            },
        )

        assert response.status_code == 200
        created_evaluation_ids.append(response.json()["evaluation_id"])

    first_page = client.get(
        "/v1/evaluations",
        params={"limit": 1, "offset": 0},
    )

    assert first_page.status_code == 200
    first_body = first_page.json()

    assert first_body["total"] == 2
    assert first_body["limit"] == 1
    assert first_body["offset"] == 0
    assert len(first_body["items"]) == 1

    first_item = first_body["items"][0]

    assert first_item["evaluation_id"] in created_evaluation_ids
    assert first_item["created_at"]
    assert first_item["baseline_capture_id"] == baseline.capture_id
    assert first_item["current_capture_id"] == current.capture_id
    assert first_item["decision"] in ("pass", "warn", "block")
    assert first_item["severity"] in ("none", "low", "medium", "high")
    assert isinstance(first_item["affected_claim_count"], int)
    assert isinstance(first_item["material_claim_count"], int)

    second_page = client.get(
        "/v1/evaluations",
        params={"limit": 1, "offset": 1},
    )

    assert second_page.status_code == 200
    second_body = second_page.json()

    assert second_body["total"] == 2
    assert len(second_body["items"]) == 1
    assert (
        second_body["items"][0]["evaluation_id"]
        != first_item["evaluation_id"]
    )
