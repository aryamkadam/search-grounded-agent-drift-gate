from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import re
from typing import Any


TRACKING_PARAMETERS = {
    "gclid",
    "fbclid",
    "msclkid",
}


def normalize_text(value: Any) -> str | None:
    """Normalize text for identity fallback purposes."""

    if value is None:
        return None

    text = re.sub(r"\s+", " ", str(value)).strip()

    return text or None


def canonicalize_url(value: Any) -> str | None:
    """
    Conservatively canonicalize a URL for evidence matching.

    This removes obvious tracking noise and fragments but does not
    attempt semantic URL rewriting.
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


def url_identity(
    url: Any,
    *,
    fallback: Any = None,
) -> str:
    """
    Generate an identity from a URL, falling back to normalized text.
    """

    canonical_url = canonicalize_url(url)

    if canonical_url:
        return f"url:{canonical_url}"

    normalized_fallback = normalize_text(fallback)

    if normalized_fallback:
        return f"text:{normalized_fallback.lower()}"

    return "unknown"


def text_identity(value: Any) -> str:
    """Generate a deterministic identity from normalized text."""

    normalized = normalize_text(value)

    if normalized:
        return f"text:{normalized.lower()}"

    return "unknown"


def identity_for_organic(
    url: Any,
    *,
    title: Any = None,
) -> str:
    return url_identity(
        url,
        fallback=title,
    )


def identity_for_ai_reference(
    url: Any,
    *,
    title: Any = None,
) -> str:
    return url_identity(
        url,
        fallback=title,
    )


def identity_for_perspective(
    url: Any,
    *,
    title: Any = None,
) -> str:
    return url_identity(
        url,
        fallback=title,
    )


def identity_for_related_question(
    question: Any,
) -> str:
    return text_identity(question)


def identity_for_inline_video(
    url: Any,
    *,
    title: Any = None,
) -> str:
    return url_identity(
        url,
        fallback=title,
    )


def identity_for_inline_image(
    original_url: Any,
    source_url: Any = None,
    thumbnail_url: Any = None,
    *,
    title: Any = None,
) -> str:
    return url_identity(
        original_url or source_url or thumbnail_url,
        fallback=title,
    )
