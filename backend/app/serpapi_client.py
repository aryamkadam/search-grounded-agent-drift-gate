from typing import Any

import httpx

from .config import get_settings


SERPAPI_SEARCH_URL = "https://serpapi.com/search.json"


class SerpApiError(RuntimeError):
    """Raised when a SerpApi request fails."""


def search_google(
    *,
    query: str,
    language: str = "en",
    country: str = "in",
    device: str = "desktop",
    location: str | None = None,
    no_cache: bool = False,
) -> dict[str, Any]:
    """Execute one Google search and return raw SerpApi JSON."""

    query = query.strip()

    if not query:
        raise ValueError("query must not be empty")

    settings = get_settings()

    params: dict[str, Any] = {
        "engine": "google",
        "q": query,
        "hl": language,
        "gl": country,
        "device": device,
        "api_key": settings.serpapi_key,
    }

    if location:
        params["location"] = location

    if no_cache:
        params["no_cache"] = "true"

    try:
        response = httpx.get(
            SERPAPI_SEARCH_URL,
            params=params,
            timeout=30,
        )
    except httpx.HTTPError as exc:
        raise SerpApiError(
            f"SerpApi HTTP request failed: {exc}"
        ) from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise SerpApiError(
            f"SerpApi returned non-JSON response "
            f"(HTTP {response.status_code})"
        ) from exc

    if response.status_code >= 400:
        raise SerpApiError(
            data.get(
                "error",
                f"HTTP {response.status_code}",
            )
        )

    metadata = data.get("search_metadata")

    if not isinstance(metadata, dict):
        raise SerpApiError(
            "SerpApi response is missing search_metadata"
        )

    if metadata.get("status") == "Error":
        raise SerpApiError(
            data.get("error", "SerpApi search failed")
        )

    return data
