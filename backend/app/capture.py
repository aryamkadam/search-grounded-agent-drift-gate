from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from .normalize import normalize_search_response
from .schema import Capture, SearchContext, SerpApiMetadata


def build_search_context(
    data: dict[str, Any],
) -> SearchContext:
    """Build search context from SerpApi search parameters."""

    parameters = data.get("search_parameters", {})

    return SearchContext(
        query=parameters["q"],
        engine=parameters["engine"],
        google_domain=parameters.get("google_domain"),
        language=parameters.get("hl"),
        country=parameters.get("gl"),
        location=parameters.get("location"),
        device=parameters.get("device"),
    )


def build_serpapi_metadata(
    data: dict[str, Any],
) -> SerpApiMetadata:
    """Extract the stable metadata we need from SerpApi."""

    metadata = data["search_metadata"]

    return SerpApiMetadata(
        search_id=metadata["id"],
        status=metadata["status"],
        created_at=metadata.get("created_at"),
        processed_at=metadata.get("processed_at"),
        google_url=metadata.get("google_url"),
        total_time_taken=metadata.get("total_time_taken"),
    )


def create_capture(
    raw_response: dict[str, Any],
    *,
    capture_id: str | None = None,
    captured_at: datetime | None = None,
) -> Capture:
    """
    Create one complete capture from one SerpApi search response.

    The raw response is preserved unchanged. Normalized evidence is
    derived from the raw response and does not replace it.
    """

    if not isinstance(raw_response, dict):
        raise TypeError("raw_response must be a dictionary")

    capture = Capture(
        capture_id=capture_id or str(uuid4()),
        captured_at=captured_at or datetime.now(timezone.utc),
        search_context=build_search_context(raw_response),
        serpapi_metadata=build_serpapi_metadata(raw_response),
        raw_response=raw_response,
        normalized_evidence=normalize_search_response(
            raw_response
        ),
    )

    return capture
