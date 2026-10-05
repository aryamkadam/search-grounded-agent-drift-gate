from unittest.mock import Mock

import pytest

from backend.app import serpapi_client


def fake_settings():
    return Mock(serpapi_key="test-key")


def fake_response(status_code, payload):
    response = Mock()
    response.status_code = status_code
    response.json.return_value = payload
    return response


def test_empty_query_is_rejected(monkeypatch):
    monkeypatch.setattr(
        serpapi_client,
        "get_settings",
        fake_settings,
    )

    with pytest.raises(ValueError, match="query must not be empty"):
        serpapi_client.search_google(query="   ")


def test_successful_search_returns_raw_json(monkeypatch):
    response = fake_response(
        200,
        {
            "search_metadata": {
                "id": "test-search-id",
                "status": "Success",
            },
            "search_parameters": {
                "engine": "google",
                "q": "test query",
            },
            "organic_results": [
                {
                    "position": 1,
                    "title": "Example",
                    "link": "https://example.com",
                }
            ],
        },
    )

    mocked_get = Mock(return_value=response)

    monkeypatch.setattr(
        serpapi_client,
        "get_settings",
        fake_settings,
    )
    monkeypatch.setattr(
        serpapi_client.httpx,
        "get",
        mocked_get,
    )

    result = serpapi_client.search_google(
        query="test query",
    )

    assert result["search_metadata"]["status"] == "Success"
    assert result["search_metadata"]["id"] == "test-search-id"

    mocked_get.assert_called_once()

    call_kwargs = mocked_get.call_args.kwargs

    assert call_kwargs["params"]["engine"] == "google"
    assert call_kwargs["params"]["q"] == "test query"
    assert call_kwargs["params"]["api_key"] == "test-key"


def test_no_cache_is_sent_when_requested(monkeypatch):
    response = fake_response(
        200,
        {
            "search_metadata": {
                "id": "test-id",
                "status": "Success",
            }
        },
    )

    mocked_get = Mock(return_value=response)

    monkeypatch.setattr(
        serpapi_client,
        "get_settings",
        fake_settings,
    )
    monkeypatch.setattr(
        serpapi_client.httpx,
        "get",
        mocked_get,
    )

    serpapi_client.search_google(
        query="test",
        no_cache=True,
    )

    params = mocked_get.call_args.kwargs["params"]

    assert params["no_cache"] == "true"


def test_http_error_response_raises_serpapi_error(monkeypatch):
    response = fake_response(
        400,
        {
            "error": "Invalid API key",
        },
    )

    monkeypatch.setattr(
        serpapi_client,
        "get_settings",
        fake_settings,
    )
    monkeypatch.setattr(
        serpapi_client.httpx,
        "get",
        Mock(return_value=response),
    )

    with pytest.raises(
        serpapi_client.SerpApiError,
        match="Invalid API key",
    ):
        serpapi_client.search_google(query="test")


def test_missing_search_metadata_raises_serpapi_error(monkeypatch):
    response = fake_response(
        200,
        {
            "organic_results": [],
        },
    )

    monkeypatch.setattr(
        serpapi_client,
        "get_settings",
        fake_settings,
    )
    monkeypatch.setattr(
        serpapi_client.httpx,
        "get",
        Mock(return_value=response),
    )

    with pytest.raises(
        serpapi_client.SerpApiError,
        match="missing search_metadata",
    ):
        serpapi_client.search_google(query="test")


def test_api_error_status_raises_serpapi_error(monkeypatch):
    response = fake_response(
        200,
        {
            "search_metadata": {
                "id": "test-id",
                "status": "Error",
            },
            "error": "Search failed",
        },
    )

    monkeypatch.setattr(
        serpapi_client,
        "get_settings",
        fake_settings,
    )
    monkeypatch.setattr(
        serpapi_client.httpx,
        "get",
        Mock(return_value=response),
    )

    with pytest.raises(
        serpapi_client.SerpApiError,
        match="Search failed",
    ):
        serpapi_client.search_google(query="test")


def test_invalid_json_raises_serpapi_error(monkeypatch):
    response = Mock()
    response.status_code = 200
    response.json.side_effect = ValueError("invalid JSON")

    monkeypatch.setattr(
        serpapi_client,
        "get_settings",
        fake_settings,
    )
    monkeypatch.setattr(
        serpapi_client.httpx,
        "get",
        Mock(return_value=response),
    )

    with pytest.raises(
        serpapi_client.SerpApiError,
        match="non-JSON response",
    ):
        serpapi_client.search_google(query="test")
