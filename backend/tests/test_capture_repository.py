
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from backend.app.capture import create_capture
from backend.app.capture_repository import (
    CaptureConflictError,
    CaptureIntegrityError,
    SQLiteCaptureRepository,
)


def make_capture(capture_id="capture-123"):
    raw = {
        "search_metadata": {
            "id": "search-123",
            "status": "Success",
        },
        "search_parameters": {
            "engine": "google",
            "q": "test query",
            "google_domain": "google.com",
            "hl": "en",
            "gl": "us",
            "device": "desktop",
        },
        "organic_results": [
            {
                "position": 1,
                "title": "Example Source",
                "link": "https://example.com/source",
                "snippet": "Example evidence.",
            }
        ],
    }

    return create_capture(
        raw,
        capture_id=capture_id,
    )


def test_save_and_get_round_trip(tmp_path):
    repository = SQLiteCaptureRepository(
        tmp_path / "captures.sqlite3"
    )

    capture = make_capture()
    repository.save(capture)

    loaded = repository.get(capture.capture_id)

    assert loaded == capture


def test_get_missing_capture_returns_none(tmp_path):
    repository = SQLiteCaptureRepository(
        tmp_path / "captures.sqlite3"
    )

    assert repository.get("missing-capture") is None


def test_saving_same_capture_is_idempotent(tmp_path):
    repository = SQLiteCaptureRepository(
        tmp_path / "captures.sqlite3"
    )

    capture = make_capture()

    repository.save(capture)
    repository.save(capture)

    assert repository.get(capture.capture_id) == capture


def test_saving_same_id_with_different_content_raises_conflict(
    tmp_path,
):
    repository = SQLiteCaptureRepository(
        tmp_path / "captures.sqlite3"
    )

    original = make_capture()
    changed = original.model_copy(deep=True)
    changed.raw_response["extra"] = "changed"

    repository.save(original)

    with pytest.raises(CaptureConflictError):
        repository.save(changed)


def test_tampered_capture_is_rejected(tmp_path):
    database_path = tmp_path / "captures.sqlite3"
    repository = SQLiteCaptureRepository(database_path)

    capture = make_capture()
    repository.save(capture)

    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            """
            SELECT capture_json
            FROM captures
            WHERE capture_id = ?
            """,
            (capture.capture_id,),
        ).fetchone()

        payload = json.loads(row[0])
        payload["raw_response"]["tampered"] = True

        connection.execute(
            """
            UPDATE captures
            SET capture_json = ?
            WHERE capture_id = ?
            """,
            (
                json.dumps(payload),
                capture.capture_id,
            ),
        )
        connection.commit()

    with pytest.raises(CaptureIntegrityError):
        repository.get(capture.capture_id)


def test_concurrent_saves_with_same_id_are_handled_safely(
    tmp_path,
):
    database_path = tmp_path / "captures.sqlite3"

    repository_a = SQLiteCaptureRepository(database_path)
    repository_b = SQLiteCaptureRepository(database_path)

    original = make_capture()
    changed = original.model_copy(deep=True)
    changed.raw_response["extra"] = "different content"

    barrier = Barrier(2)

    def save_capture(repository, capture):
        barrier.wait()

        try:
            repository.save(capture)
            return "saved"
        except CaptureConflictError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_a = executor.submit(
            save_capture, repository_a, original
        )
        future_b = executor.submit(
            save_capture, repository_b, changed
        )

        outcomes = [
            future_a.result(),
            future_b.result(),
        ]

    assert outcomes.count("saved") == 1
    assert outcomes.count("conflict") == 1

    stored = repository_a.get(original.capture_id)
    assert stored in (original, changed)
def test_unsupported_schema_version_is_rejected(tmp_path):
    database_path = tmp_path / "captures.sqlite3"
    repository = SQLiteCaptureRepository(database_path)
    capture = make_capture()

    repository.save(capture)

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            UPDATE captures
            SET schema_version = ?
            WHERE capture_id = ?
            """,
            (999, capture.capture_id),
        )

    with pytest.raises(CaptureIntegrityError):
        repository.get(capture.capture_id)
