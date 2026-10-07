from datetime import datetime, timezone

import pytest

from backend.app.capture import create_capture


def sample_serpapi_response():
    return {
        "search_metadata": {
            "id": "search-123",
            "status": "Success",
            "created_at": "2026-10-07 12:00:00 UTC",
            "processed_at": "2026-10-07 12:00:01 UTC",
            "google_url": "https://www.google.com/search?q=test",
            "total_time_taken": 1.2,
        },
        "search_parameters": {
            "engine": "google",
            "q": "test query",
            "google_domain": "google.com",
            "hl": "en",
            "gl": "us",
            "location": "United States",
            "device": "desktop",
        },
        "organic_results": [
            {
                "position": 1,
                "title": "Example Source",
                "link": "https://example.com/source",
                "displayed_link": "example.com",
                "snippet": "Example evidence.",
            }
        ],
    }


def test_create_capture_builds_complete_capture():
    raw = sample_serpapi_response()

    capture = create_capture(
        raw,
        capture_id="capture-123",
    )

    assert capture.capture_id == "capture-123"

    assert capture.search_context.query == "test query"
    assert capture.search_context.engine == "google"
    assert capture.search_context.google_domain == "google.com"
    assert capture.search_context.language == "en"
    assert capture.search_context.country == "us"
    assert capture.search_context.location == "United States"
    assert capture.search_context.device == "desktop"

    assert capture.serpapi_metadata.search_id == "search-123"
    assert capture.serpapi_metadata.status == "Success"
    assert capture.serpapi_metadata.google_url == (
        "https://www.google.com/search?q=test"
    )
    assert capture.serpapi_metadata.total_time_taken == 1.2


def test_create_capture_preserves_raw_response():
    raw = sample_serpapi_response()

    capture = create_capture(
        raw,
        capture_id="capture-123",
    )

    assert capture.raw_response == raw


def test_create_capture_normalizes_organic_evidence():
    raw = sample_serpapi_response()

    capture = create_capture(
        raw,
        capture_id="capture-123",
    )

    evidence = capture.normalized_evidence

    assert len(evidence.organic_results) == 1

    result = evidence.organic_results[0]

    assert result.identity_key == (
        "url:https://example.com/source"
    )
    assert result.position == 1
    assert result.title == "Example Source"
    assert result.url == "https://example.com/source"
    assert result.snippet == "Example evidence."


def test_create_capture_accepts_explicit_timestamp():
    raw = sample_serpapi_response()

    timestamp = datetime(
        2026,
        10,
        7,
        12,
        30,
        tzinfo=timezone.utc,
    )

    capture = create_capture(
        raw,
        capture_id="capture-123",
        captured_at=timestamp,
    )

    assert capture.captured_at == timestamp


def test_create_capture_generates_capture_id_when_missing():
    raw = sample_serpapi_response()

    capture = create_capture(raw)

    assert capture.capture_id
    assert isinstance(capture.capture_id, str)


def test_create_capture_rejects_non_dictionary():
    with pytest.raises(
        TypeError,
        match="raw_response must be a dictionary",
    ):
        create_capture([])


def test_create_capture_preserves_additional_raw_fields():
    raw = sample_serpapi_response()

    raw["ai_overview"] = {
        "text_blocks": [
            {
                "snippet": "AI-generated text",
            }
        ]
    }

    capture = create_capture(
        raw,
        capture_id="capture-123",
    )

    assert capture.raw_response["ai_overview"] == {
        "text_blocks": [
            {
                "snippet": "AI-generated text",
            }
        ]
    }
