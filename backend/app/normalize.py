from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import re
from typing import Any

from .schema import (
    AIOverviewEvidence,
    AIOverviewReference,
    AIOverviewTextBlock,
    InlineImageEvidence,
    InlineVideoEvidence,
    NormalizedEvidence,
    OrganicEvidence,
    PerspectiveEvidence,
    RelatedQuestionEvidence,
    SurfaceState,
)


TRACKING_PARAMETERS = {
    "gclid",
    "fbclid",
    "msclkid",
    "ref",
}


KNOWN_SURFACES = (
    "organic_results",
    "news_results",
    "local_results",
    "ads",
    "knowledge_graph",
    "answer_box",
    "ai_overview",
    "perspectives",
    "related_questions",
    "inline_images",
    "inline_videos",
)


def normalize_text(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value)

    text = re.sub(r"\s+", " ", text).strip()

    return text or None


def canonicalize_url(value: Any) -> str | None:
    """
    Normalize a URL for evidence identity.

    This intentionally performs only conservative normalization.
    Meaningful query parameters are preserved.
    """
    if not value or not isinstance(value, str):
        return None

    value = value.strip()

    try:
        parts = urlsplit(value)

        if not parts.scheme or not parts.netloc:
            return value.rstrip("/")

        scheme = parts.scheme.lower()
        hostname = (parts.hostname or "").lower()

        netloc = hostname

        if parts.port:
            default_port = (
                (scheme == "http" and parts.port == 80)
                or (scheme == "https" and parts.port == 443)
            )

            if not default_port:
                netloc = f"{hostname}:{parts.port}"

        path = parts.path or "/"

        if path != "/":
            path = path.rstrip("/")

        query_pairs = [
            (key, val)
            for key, val in parse_qsl(
                parts.query,
                keep_blank_values=True,
            )
            if key.lower() not in TRACKING_PARAMETERS
            and not key.lower().startswith("utm_")
        ]

        query_pairs.sort()

        query = urlencode(query_pairs, doseq=True)

        return urlunsplit(
            (
                scheme,
                netloc,
                path,
                query,
                "",
            )
        )

    except ValueError:
        return value.rstrip("/")


def make_identity(
    *,
    url: Any = None,
    fallback: Any = None,
) -> str:
    canonical_url = canonicalize_url(url)

    if canonical_url:
        return f"url:{canonical_url}"

    normalized_fallback = normalize_text(fallback)

    if normalized_fallback:
        return f"text:{normalized_fallback.lower()}"

    return "unknown"


def surface_state(
    data: dict[str, Any],
    name: str,
) -> SurfaceState:
    if name not in data:
        return SurfaceState(state="missing")

    value = data[name]

    if isinstance(value, list):
        if not value:
            return SurfaceState(
                state="present_empty",
                item_count=0,
            )

        return SurfaceState(
            state="present",
            item_count=len(value),
        )

    return SurfaceState(
        state="present",
        item_count=1,
    )


def _extra(
    item: dict[str, Any],
    known: set[str],
) -> dict[str, Any]:
    return {
        key: value
        for key, value in item.items()
        if key not in known
    }


def normalize_organic(
    results: list[dict[str, Any]],
) -> list[OrganicEvidence]:
    normalized = []

    known = {
        "position",
        "title",
        "link",
        "displayed_link",
        "snippet",
        "source",
    }

    for result in results:
        normalized.append(
            OrganicEvidence(
                identity_key=make_identity(
                    url=result.get("link"),
                    fallback=result.get("title"),
                ),
                position=result.get("position"),
                title=normalize_text(result.get("title")),
                url=canonicalize_url(result.get("link")),
                displayed_link=normalize_text(
                    result.get("displayed_link")
                ),
                snippet=normalize_text(result.get("snippet")),
                source=normalize_text(result.get("source")),
                extra=_extra(result, known),
            )
        )

    return normalized


def normalize_ai_overview(
    value: dict[str, Any],
) -> AIOverviewEvidence:
    blocks = []

    for block in value.get("text_blocks", []):
        reference_indexes = block.get(
            "reference_indexes",
            [],
        )

        if not isinstance(reference_indexes, list):
            reference_indexes = []

        blocks.append(
            AIOverviewTextBlock(
                block_type=str(
                    block.get("type", "unknown")
                ),
                snippet=normalize_text(
                    block.get("snippet")
                ),
                reference_indexes=[
                    int(index)
                    for index in reference_indexes
                    if isinstance(index, int)
                ],
                extra=_extra(
                    block,
                    {
                        "type",
                        "snippet",
                        "reference_indexes",
                    },
                ),
            )
        )

    references = []

    for reference in value.get("references", []):
        references.append(
            AIOverviewReference(
                identity_key=make_identity(
                    url=reference.get("link"),
                    fallback=reference.get("title"),
                ),
                reference_index=reference["index"],
                title=normalize_text(
                    reference.get("title")
                ),
                url=canonicalize_url(
                    reference.get("link")
                ),
                snippet=normalize_text(
                    reference.get("snippet")
                ),
                source=normalize_text(
                    reference.get("source")
                ),
                extra=_extra(
                    reference,
                    {
                        "index",
                        "title",
                        "link",
                        "snippet",
                        "source",
                    },
                ),
            )
        )

    return AIOverviewEvidence(
        text_blocks=blocks,
        references=references,
        page_token_present=bool(
            value.get("page_token")
        ),
    )


def normalize_perspectives(
    results: list[dict[str, Any]],
) -> list[PerspectiveEvidence]:
    normalized = []

    known = {
        "author",
        "source",
        "title",
        "link",
        "date",
    }

    for result in results:
        normalized.append(
            PerspectiveEvidence(
                identity_key=make_identity(
                    url=result.get("link"),
                    fallback=result.get("title"),
                ),
                author=normalize_text(result.get("author")),
                source=normalize_text(result.get("source")),
                title=normalize_text(result.get("title")),
                url=canonicalize_url(result.get("link")),
                date=normalize_text(result.get("date")),
                extra=_extra(result, known),
            )
        )

    return normalized


def normalize_related_questions(
    results: list[dict[str, Any]],
) -> list[RelatedQuestionEvidence]:
    normalized = []

    for result in results:
        question = normalize_text(result.get("question")) or ""

        normalized.append(
            RelatedQuestionEvidence(
                identity_key=make_identity(
                    fallback=question
                ),
                question=question,
                question_type=normalize_text(
                    result.get("type")
                ),
                page_token_present=bool(
                    result.get("page_token")
                ),
                next_page_token_present=bool(
                    result.get("next_page_token")
                ),
            )
        )

    return normalized


def normalize_inline_images(
    results: list[dict[str, Any]],
) -> list[InlineImageEvidence]:
    normalized = []

    for result in results:
        identity = make_identity(
            url=(
                result.get("original")
                or result.get("source")
                or result.get("thumbnail")
            ),
            fallback=result.get("title"),
        )

        normalized.append(
            InlineImageEvidence(
                identity_key=identity,
                title=normalize_text(result.get("title")),
                source=canonicalize_url(
                    result.get("source")
                ),
                source_name=normalize_text(
                    result.get("source_name")
                ),
                thumbnail_url=canonicalize_url(
                    result.get("thumbnail")
                ),
                original_url=canonicalize_url(
                    result.get("original")
                ),
            )
        )

    return normalized


def normalize_inline_videos(
    results: list[dict[str, Any]],
) -> list[InlineVideoEvidence]:
    normalized = []

    for result in results:
        normalized.append(
            InlineVideoEvidence(
                identity_key=make_identity(
                    url=result.get("link"),
                    fallback=result.get("title"),
                ),
                position=result.get("position"),
                title=normalize_text(result.get("title")),
                url=canonicalize_url(result.get("link")),
                thumbnail_url=canonicalize_url(
                    result.get("thumbnail")
                ),
                channel=normalize_text(result.get("channel")),
                duration=normalize_text(result.get("duration")),
                platform=normalize_text(result.get("platform")),
                date=normalize_text(result.get("date")),
                snippet=normalize_text(result.get("snippet")),
            )
        )

    return normalized


def normalize_search_response(
    data: dict[str, Any],
) -> NormalizedEvidence:
    """
    Convert a raw SerpApi Google response into normalized evidence.

    The raw response is never modified.
    """
    surfaces = {
        name: surface_state(data, name)
        for name in KNOWN_SURFACES
    }

    ai_overview = None

    if isinstance(data.get("ai_overview"), dict):
        ai_overview = normalize_ai_overview(
            data["ai_overview"]
        )

    return NormalizedEvidence(
        surfaces=surfaces,
        organic_results=normalize_organic(
            data.get("organic_results", [])
        ),
        ai_overview=ai_overview,
        perspectives=normalize_perspectives(
            data.get("perspectives", [])
        ),
        related_questions=normalize_related_questions(
            data.get("related_questions", [])
        ),
        inline_images=normalize_inline_images(
            data.get("inline_images", [])
        ),
        inline_videos=normalize_inline_videos(
            data.get("inline_videos", [])
        ),
    )
