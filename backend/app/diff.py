from typing import Any, Literal

from pydantic import BaseModel, Field

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


ChangeType = Literal[
    "added",
    "removed",
    "modified",
    "surface_state_changed",
]


class EvidenceChange(BaseModel):
    """One evidence change detected between two captures."""

    surface: str
    change_type: ChangeType
    identity_key: str | None = None

    changed_fields: list[str] = Field(
        default_factory=list
    )

    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None


class SurfaceDiff(BaseModel):
    """Changes detected within one evidence surface."""

    surface: str

    baseline_state: SurfaceState
    current_state: SurfaceState

    changes: list[EvidenceChange] = Field(
        default_factory=list
    )

    unchanged_count: int = 0


class EvidenceDiff(BaseModel):
    """Complete comparison between baseline and current evidence."""

    surface_diffs: dict[str, SurfaceDiff] = Field(
        default_factory=dict
    )

    total_added: int = 0
    total_removed: int = 0
    total_modified: int = 0
    total_surface_state_changes: int = 0

    @property
    def has_changes(self) -> bool:
        return any(
            surface.changes
            for surface in self.surface_diffs.values()
        )


def _dump(
    item: BaseModel,
    fields: tuple[str, ...],
) -> dict[str, Any]:
    """
    Dump only fields explicitly considered relevant to drift.
    """

    values = item.model_dump(
        mode="json",
        exclude_none=False,
    )

    return {
        field: values.get(field)
        for field in fields
    }


def _changed_fields(
    before: dict[str, Any],
    after: dict[str, Any],
) -> list[str]:
    return [
        field
        for field in before
        if before.get(field) != after.get(field)
    ]


def _compare_collection(
    *,
    surface: str,
    baseline: list[BaseModel],
    current: list[BaseModel],
    fields: tuple[str, ...],
) -> list[EvidenceChange]:
    baseline_by_id = {
        item.identity_key: item
        for item in baseline
    }

    current_by_id = {
        item.identity_key: item
        for item in current
    }

    changes: list[EvidenceChange] = []

    for identity in sorted(
        current_by_id.keys() - baseline_by_id.keys()
    ):
        item = current_by_id[identity]

        changes.append(
            EvidenceChange(
                surface=surface,
                change_type="added",
                identity_key=identity,
                after=_dump(item, fields),
            )
        )

    for identity in sorted(
        baseline_by_id.keys() - current_by_id.keys()
    ):
        item = baseline_by_id[identity]

        changes.append(
            EvidenceChange(
                surface=surface,
                change_type="removed",
                identity_key=identity,
                before=_dump(item, fields),
            )
        )

    for identity in sorted(
        baseline_by_id.keys() & current_by_id.keys()
    ):
        before = _dump(
            baseline_by_id[identity],
            fields,
        )

        after = _dump(
            current_by_id[identity],
            fields,
        )

        changed = _changed_fields(
            before,
            after,
        )

        if changed:
            changes.append(
                EvidenceChange(
                    surface=surface,
                    change_type="modified",
                    identity_key=identity,
                    changed_fields=changed,
                    before=before,
                    after=after,
                )
            )

    return changes


def _compare_ai_overview(
    baseline: AIOverviewEvidence,
    current: AIOverviewEvidence,
) -> list[EvidenceChange]:
    changes: list[EvidenceChange] = []

    reference_changes = _compare_collection(
        surface="ai_overview.references",
        baseline=baseline.references,
        current=current.references,
        fields=(
            "reference_index",
            "title",
            "url",
            "snippet",
            "source",
        ),
    )

    changes.extend(reference_changes)

    baseline_blocks = [
        block.model_dump(
            mode="json",
            exclude_none=False,
        )
        for block in baseline.text_blocks
    ]

    current_blocks = [
        block.model_dump(
            mode="json",
            exclude_none=False,
        )
        for block in current.text_blocks
    ]

    if baseline_blocks != current_blocks:
        changes.append(
            EvidenceChange(
                surface="ai_overview.text",
                change_type="modified",
                changed_fields=[
                    "text_blocks",
                ],
                before={
                    "text_blocks": baseline_blocks,
                },
                after={
                    "text_blocks": current_blocks,
                },
            )
        )

    return changes


def _surface_state(
    evidence: NormalizedEvidence,
    surface: str,
) -> SurfaceState:
    return evidence.surfaces.get(
        surface,
        SurfaceState(state="missing"),
    )


def _surface_diff(
    *,
    surface: str,
    baseline: NormalizedEvidence,
    current: NormalizedEvidence,
    changes: list[EvidenceChange],
    unchanged_count: int = 0,
) -> SurfaceDiff:
    baseline_state = _surface_state(
        baseline,
        surface,
    )

    current_state = _surface_state(
        current,
        surface,
    )

    if (
        baseline_state.state
        != current_state.state
    ):
        changes = [
            EvidenceChange(
                surface=surface,
                change_type="surface_state_changed",
                changed_fields=[
                    "state",
                    "item_count",
                ],
                before=baseline_state.model_dump(),
                after=current_state.model_dump(),
            ),
            *changes,
        ]

    return SurfaceDiff(
        surface=surface,
        baseline_state=baseline_state,
        current_state=current_state,
        changes=changes,
        unchanged_count=unchanged_count,
    )


def compare_evidence(
    baseline: NormalizedEvidence,
    current: NormalizedEvidence,
) -> EvidenceDiff:
    """
    Compare normalized evidence without looking at raw SerpApi JSON.

    The comparison is surface-aware and identity-based.
    """

    surface_diffs: dict[str, SurfaceDiff] = {}

    organic_changes = _compare_collection(
        surface="organic_results",
        baseline=baseline.organic_results,
        current=current.organic_results,
        fields=(
            "position",
            "title",
            "url",
            "displayed_link",
            "snippet",
            "source",
        ),
    )

    baseline_organic_ids = {
        item.identity_key
        for item in baseline.organic_results
    }

    current_organic_ids = {
        item.identity_key
        for item in current.organic_results
    }

    organic_unchanged = len(
        baseline_organic_ids
        & current_organic_ids
    ) - sum(
        1
        for change in organic_changes
        if change.change_type == "modified"
    )

    surface_diffs["organic_results"] = _surface_diff(
        surface="organic_results",
        baseline=baseline,
        current=current,
        changes=organic_changes,
        unchanged_count=max(organic_unchanged, 0),
    )

    ai_changes: list[EvidenceChange] = []

    if (
        baseline.ai_overview is not None
        and current.ai_overview is not None
    ):
        ai_changes = _compare_ai_overview(
            baseline.ai_overview,
            current.ai_overview,
        )
    elif (
        baseline.ai_overview is None
        and current.ai_overview is not None
    ):
        ai_changes.append(
            EvidenceChange(
                surface="ai_overview",
                change_type="added",
                before=None,
                after={
                    "present": True,
                },
            )
        )
    elif (
        baseline.ai_overview is not None
        and current.ai_overview is None
    ):
        ai_changes.append(
            EvidenceChange(
                surface="ai_overview",
                change_type="removed",
                before={
                    "present": True,
                },
                after=None,
            )
        )

    surface_diffs["ai_overview"] = _surface_diff(
        surface="ai_overview",
        baseline=baseline,
        current=current,
        changes=ai_changes,
    )

    perspective_changes = _compare_collection(
        surface="perspectives",
        baseline=baseline.perspectives,
        current=current.perspectives,
        fields=(
            "author",
            "source",
            "title",
            "url",
            "date",
        ),
    )

    surface_diffs["perspectives"] = _surface_diff(
        surface="perspectives",
        baseline=baseline,
        current=current,
        changes=perspective_changes,
    )

    question_changes = _compare_collection(
        surface="related_questions",
        baseline=baseline.related_questions,
        current=current.related_questions,
        fields=(
            "question",
            "question_type",
        ),
    )

    surface_diffs["related_questions"] = _surface_diff(
        surface="related_questions",
        baseline=baseline,
        current=current,
        changes=question_changes,
    )

    image_changes = _compare_collection(
        surface="inline_images",
        baseline=baseline.inline_images,
        current=current.inline_images,
        fields=(
            "title",
            "source",
            "source_name",
            "original_url",
        ),
    )

    surface_diffs["inline_images"] = _surface_diff(
        surface="inline_images",
        baseline=baseline,
        current=current,
        changes=image_changes,
    )

    video_changes = _compare_collection(
        surface="inline_videos",
        baseline=baseline.inline_videos,
        current=current.inline_videos,
        fields=(
            "position",
            "title",
            "url",
            "channel",
            "duration",
            "platform",
            "date",
            "snippet",
        ),
    )

    surface_diffs["inline_videos"] = _surface_diff(
        surface="inline_videos",
        baseline=baseline,
        current=current,
        changes=video_changes,
    )

    total_added = 0
    total_removed = 0
    total_modified = 0
    total_surface_state_changes = 0

    for diff in surface_diffs.values():
        for change in diff.changes:
            if change.change_type == "added":
                total_added += 1
            elif change.change_type == "removed":
                total_removed += 1
            elif change.change_type == "modified":
                total_modified += 1
            elif change.change_type == "surface_state_changed":
                total_surface_state_changes += 1

    return EvidenceDiff(
        surface_diffs=surface_diffs,
        total_added=total_added,
        total_removed=total_removed,
        total_modified=total_modified,
        total_surface_state_changes=(
            total_surface_state_changes
        ),
    )
