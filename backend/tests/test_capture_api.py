from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from backend.app.capture import create_capture
from backend.app.capture_repository import SQLiteCaptureRepository
from backend.app.main import app, get_capture_repository
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
def api_repository(repository):
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
