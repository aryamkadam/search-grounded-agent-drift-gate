from backend.app.diff import EvidenceDiff, compare_evidence
from backend.app.schema import (
    AIOverviewEvidence,
    AIOverviewReference,
    AIOverviewTextBlock,
    NormalizedEvidence,
    OrganicEvidence,
    SurfaceState,
)


def base_evidence():
    return NormalizedEvidence(
        surfaces={
            "organic_results": SurfaceState(
                state="present",
                item_count=2,
            ),
            "ai_overview": SurfaceState(
                state="present",
                item_count=1,
            ),
        },
        organic_results=[
            OrganicEvidence(
                identity_key="url:https://example.com/a",
                position=1,
                title="Result A",
                url="https://example.com/a",
                snippet="Original snippet",
                source="Example",
            ),
            OrganicEvidence(
                identity_key="url:https://example.com/b",
                position=2,
                title="Result B",
                url="https://example.com/b",
                snippet="Second snippet",
                source="Example",
            ),
        ],
        ai_overview=AIOverviewEvidence(
            text_blocks=[
                AIOverviewTextBlock(
                    block_type="paragraph",
                    snippet="Original AI answer.",
                    reference_indexes=[0],
                )
            ],
            references=[
                AIOverviewReference(
                    identity_key="url:https://source-a.com",
                    reference_index=0,
                    title="Source A",
                    url="https://source-a.com",
                    snippet="Source A snippet",
                    source="Source A",
                )
            ],
        ),
    )


def test_identical_evidence_has_no_changes():
    baseline = base_evidence()
    current = base_evidence()

    result = compare_evidence(
        baseline,
        current,
    )

    assert result.total_added == 0
    assert result.total_removed == 0
    assert result.total_modified == 0
    assert result.total_surface_state_changes == 0
    assert result.has_changes is False


def test_rank_change_is_detected_as_modification():
    baseline = base_evidence()
    current = base_evidence()

    current.organic_results[0].position = 2
    current.organic_results[1].position = 1

    result = compare_evidence(
        baseline,
        current,
    )

    organic_changes = result.surface_diffs[
        "organic_results"
    ].changes

    assert len(organic_changes) == 2

    assert all(
        change.change_type == "modified"
        for change in organic_changes
    )

    assert all(
        change.changed_fields == ["position"]
        for change in organic_changes
    )


def test_new_organic_source_is_added():
    baseline = base_evidence()
    current = base_evidence()

    current.organic_results.append(
        OrganicEvidence(
            identity_key="url:https://example.com/c",
            position=3,
            title="Result C",
            url="https://example.com/c",
            snippet="New snippet",
            source="Example",
        )
    )

    result = compare_evidence(
        baseline,
        current,
    )

    changes = result.surface_diffs[
        "organic_results"
    ].changes

    assert any(
        change.change_type == "added"
        and change.identity_key
        == "url:https://example.com/c"
        for change in changes
    )


def test_removed_organic_source_is_detected():
    baseline = base_evidence()
    current = base_evidence()

    current.organic_results = (
        current.organic_results[:1]
    )
    current.surfaces["organic_results"] = (
        SurfaceState(
            state="present",
            item_count=1,
        )
    )

    result = compare_evidence(
        baseline,
        current,
    )

    changes = result.surface_diffs[
        "organic_results"
    ].changes

    assert any(
        change.change_type == "removed"
        and change.identity_key
        == "url:https://example.com/b"
        for change in changes
    )


def test_ai_reference_replacement_is_detected():
    baseline = base_evidence()
    current = base_evidence()

    current.ai_overview.references[0] = (
        AIOverviewReference(
            identity_key="url:https://source-b.com",
            reference_index=0,
            title="Source B",
            url="https://source-b.com",
            snippet="Source B snippet",
            source="Source B",
        )
    )

    result = compare_evidence(
        baseline,
        current,
    )

    changes = result.surface_diffs[
        "ai_overview"
    ].changes

    assert any(
        change.surface
        == "ai_overview.references"
        and change.change_type == "removed"
        and change.identity_key
        == "url:https://source-a.com"
        for change in changes
    )

    assert any(
        change.surface
        == "ai_overview.references"
        and change.change_type == "added"
        and change.identity_key
        == "url:https://source-b.com"
        for change in changes
    )


def test_ai_overview_text_change_is_detected():
    baseline = base_evidence()
    current = base_evidence()

    current.ai_overview.text_blocks[0].snippet = (
        "Changed AI answer."
    )

    result = compare_evidence(
        baseline,
        current,
    )

    changes = result.surface_diffs[
        "ai_overview"
    ].changes

    assert any(
        change.surface == "ai_overview.text"
        and change.change_type == "modified"
        for change in changes
    )


def test_surface_appearance_is_detected():
    baseline = base_evidence()
    current = base_evidence()

    baseline.surfaces["organic_results"] = (
        SurfaceState(state="missing")
    )

    result = compare_evidence(
        baseline,
        current,
    )

    changes = result.surface_diffs[
        "organic_results"
    ].changes

    assert any(
        change.change_type
        == "surface_state_changed"
        for change in changes
    )
from backend.app.diff import compare_evidence
from backend.tests.test_diff import base_evidence


def test_ai_reference_index_change_is_detected_separately():
    baseline = base_evidence()
    current = base_evidence()

    current.ai_overview.references[0].reference_index = 1

    result = compare_evidence(
        baseline,
        current,
    )

    changes = result.surface_diffs[
        "ai_overview"
    ].changes

    reference_changes = [
        change
        for change in changes
        if change.surface == "ai_overview.references"
    ]

    assert len(reference_changes) == 1
    assert reference_changes[0].change_type == "modified"
    assert reference_changes[0].changed_fields == [
        "reference_index"
    ]
def test_surface_missing_to_present_empty_is_detected():
    baseline = base_evidence()
    current = base_evidence()

    baseline.surfaces["organic_results"] = (
        SurfaceState(state="missing")
    )

    current.organic_results = []
    current.surfaces["organic_results"] = (
        SurfaceState(
            state="present_empty",
            item_count=0,
        )
    )

    result = compare_evidence(
        baseline,
        current,
    )

    changes = result.surface_diffs[
        "organic_results"
    ].changes

    assert any(
        change.change_type
        == "surface_state_changed"
        for change in changes
    )

    state_change = next(
        change
        for change in changes
        if change.change_type
        == "surface_state_changed"
    )

    assert state_change.before["state"] == "missing"
    assert state_change.after["state"] == "present_empty"


def test_has_changes_is_serialized_for_aggregate_changes():
    result = EvidenceDiff(total_removed=1)

    payload = result.model_dump()

    assert result.has_changes is True
    assert payload["has_changes"] is True
