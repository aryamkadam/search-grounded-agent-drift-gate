from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SearchContext(BaseModel):
    """Inputs that define the search context."""

    query: str
    engine: str
    google_domain: str | None = None
    language: str | None = None
    country: str | None = None
    location: str | None = None
    device: str | None = None


class SerpApiMetadata(BaseModel):
    """Metadata returned by SerpApi for a search."""

    search_id: str
    status: str
    created_at: str | None = None
    processed_at: str | None = None
    google_url: str | None = None
    total_time_taken: float | None = None


class OrganicEvidence(BaseModel):
    """Normalized representation of an organic search result."""

    model_config = ConfigDict(extra="forbid")

    surface: str = "organic"
    identity_key: str

    position: int | None = None
    title: str | None = None
    url: str | None = None
    displayed_link: str | None = None
    snippet: str | None = None
    source: str | None = None

    extra: dict[str, Any] = Field(default_factory=dict)


class AIOverviewTextBlock(BaseModel):
    """A content block inside an AI Overview."""

    model_config = ConfigDict(extra="forbid")

    block_type: str
    snippet: str | None = None
    reference_indexes: list[int] = Field(default_factory=list)

    extra: dict[str, Any] = Field(default_factory=dict)


class AIOverviewReference(BaseModel):
    """A source referenced by an AI Overview."""

    model_config = ConfigDict(extra="forbid")

    identity_key: str

    reference_index: int
    title: str | None = None
    url: str | None = None
    snippet: str | None = None
    source: str | None = None

    extra: dict[str, Any] = Field(default_factory=dict)


class AIOverviewEvidence(BaseModel):
    """Normalized AI Overview evidence."""

    text_blocks: list[AIOverviewTextBlock] = Field(default_factory=list)
    references: list[AIOverviewReference] = Field(default_factory=list)

    page_token_present: bool = False


class PerspectiveEvidence(BaseModel):
    """A result from Google's Perspectives surface."""

    identity_key: str

    author: str | None = None
    source: str | None = None
    title: str | None = None
    url: str | None = None
    date: str | None = None

    extra: dict[str, Any] = Field(default_factory=dict)


class RelatedQuestionEvidence(BaseModel):
    """A related question returned by the search."""

    identity_key: str

    question: str
    question_type: str | None = None

    page_token_present: bool = False
    next_page_token_present: bool = False


class InlineImageEvidence(BaseModel):
    """An image result returned inline with the search."""

    identity_key: str

    title: str | None = None
    source: str | None = None
    source_name: str | None = None
    thumbnail_url: str | None = None
    original_url: str | None = None


class InlineVideoEvidence(BaseModel):
    """A video result returned inline with the search."""

    identity_key: str

    position: int | None = None
    title: str | None = None
    url: str | None = None
    thumbnail_url: str | None = None
    channel: str | None = None
    duration: str | None = None
    platform: str | None = None
    date: str | None = None
    snippet: str | None = None


class SurfaceState(BaseModel):
    """Whether a surface existed in the SerpApi response."""

    state: str

    item_count: int | None = None


class NormalizedEvidence(BaseModel):
    """Derived evidence representation used by the drift engine."""

    surfaces: dict[str, SurfaceState] = Field(default_factory=dict)

    organic_results: list[OrganicEvidence] = Field(default_factory=list)

    ai_overview: AIOverviewEvidence | None = None

    perspectives: list[PerspectiveEvidence] = Field(default_factory=list)

    related_questions: list[RelatedQuestionEvidence] = Field(
        default_factory=list
    )

    inline_images: list[InlineImageEvidence] = Field(default_factory=list)

    inline_videos: list[InlineVideoEvidence] = Field(
        default_factory=list
    )

    additional_surfaces: dict[str, Any] = Field(default_factory=dict)


class Capture(BaseModel):
    """A complete search-evidence capture."""

    capture_id: str
    captured_at: datetime

    search_context: SearchContext
    serpapi_metadata: SerpApiMetadata

    raw_response: dict[str, Any]

    normalized_evidence: NormalizedEvidence
