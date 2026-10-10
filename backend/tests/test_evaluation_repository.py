import hashlib
import json
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from backend.app.capture import create_capture
from backend.app.claims import AgentAnswer, Claim, EvidenceRef
from backend.app.evaluation import (
    DriftEvaluationRequest,
    evaluate_capture_drift,
)
from backend.app.evaluation_repository import (
    EvaluationConflictError,
    EvaluationIntegrityError,
    EvaluationRecord,
    SQLiteEvaluationRepository,
)


def make_capture(capture_id):
    raw = {
        "search_metadata": {
            "id": f"search-{capture_id}",
            "status": "Success",
        },
        "search_parameters": {
            "engine": "google",
            "q": "quantum computing",
            "google_domain": "google.com",
            "hl": "en",
            "gl": "in",
            "device": "desktop",
        },
        "organic_results": [
            {
                "position": 1,
                "title": "Quantum Computing",
                "link": "https://example.com/quantum",
                "snippet": "An example source about quantum computing.",
            }
        ],
    }
    return create_capture(raw, capture_id=capture_id)


def make_record(answer_text="A quantum computing answer."):
    baseline = make_capture("baseline-evaluation-test")
    current = make_capture("current-evaluation-test")

    answer = AgentAnswer(
        answer_id="answer-evaluation-test",
        text=answer_text,
        claims=[
            Claim(
                claim_id="claim-evaluation-test",
                text="The source discusses quantum computing.",
                evidence_refs=[
                    EvidenceRef(
                        surface="organic_results",
                        identity_key="url:https://example.com/quantum",
                        relation="supports",
                    )
                ],
                importance="important",
                confidence=0.9,
            )
        ],
    )

    response = evaluate_capture_drift(
        DriftEvaluationRequest(
            baseline_capture=baseline,
            current_capture=current,
            agent_answer=answer,
        )
    )

    return EvaluationRecord(
        evaluation_id=response.evaluation_id,
        created_at=datetime.now(timezone.utc),
        baseline_capture_id=baseline.capture_id,
        current_capture_id=current.capture_id,
        agent_answer=answer,
        response=response,
    )


@pytest.fixture
def repository(tmp_path):
    return SQLiteEvaluationRepository(
        tmp_path / "captures.sqlite3"
    )


def test_save_and_get_round_trip(repository):
    record = make_record()

    repository.save(record)
    loaded = repository.get(record.evaluation_id)

    assert loaded == record
    assert loaded.agent_answer == record.agent_answer
    assert loaded.response == record.response


def test_identical_retry_is_idempotent(repository):
    original = make_record()
    repository.save(original)

    retry = original.model_copy(
        update={
            "created_at": original.created_at
            + timedelta(minutes=5)
        }
    )

    loaded = repository.save(retry)

    assert loaded == original
    assert repository.get(original.evaluation_id) == original


def test_reusing_evaluation_id_with_different_answer_conflicts(
    repository,
):
    original = make_record()
    changed = make_record(answer_text="A different answer.")

    assert changed.evaluation_id == original.evaluation_id

    repository.save(original)

    with pytest.raises(EvaluationConflictError):
        repository.save(changed)

    assert repository.get(original.evaluation_id) == original


def test_missing_evaluation_returns_none(repository):
    assert repository.get("missing-evaluation") is None


def test_tampered_evaluation_is_rejected(repository):
    record = make_record()
    repository.save(record)

    with sqlite3.connect(repository.database_path) as connection:
        row = connection.execute(
            """
            SELECT response_json
            FROM evaluations
            WHERE evaluation_id = ?
            """,
            (record.evaluation_id,),
        ).fetchone()

        payload = json.loads(row[0])
        payload["baseline_capture_id"] = "tampered-baseline"

        connection.execute(
            """
            UPDATE evaluations
            SET response_json = ?
            WHERE evaluation_id = ?
            """,
            (
                json.dumps(payload),
                record.evaluation_id,
            ),
        )

    with pytest.raises(EvaluationIntegrityError):
        repository.get(record.evaluation_id)


def test_unsupported_schema_version_is_rejected(repository):
    record = make_record()
    repository.save(record)

    with sqlite3.connect(repository.database_path) as connection:
        connection.execute(
            """
            UPDATE evaluations
            SET schema_version = ?
            WHERE evaluation_id = ?
            """,
            (999, record.evaluation_id),
        )

    with pytest.raises(EvaluationIntegrityError):
        repository.get(record.evaluation_id)

def test_same_inputs_keep_original_record_when_result_changes(
    repository,
):
    original = make_record()
    repository.save(original)

    changed_response = original.response.model_copy(deep=True)
    changed_response.validation.valid = False

    retry = original.model_copy(
        update={"response": changed_response}
    )

    saved = repository.save(retry)

    assert saved == original
    assert repository.get(original.evaluation_id) == original

def test_v1_database_migrates_to_legacy_evaluation_records(tmp_path):
    database_path = tmp_path / "legacy-evaluations.sqlite3"
    record = make_record()

    created_at = record.created_at.isoformat()
    request_json = SQLiteEvaluationRepository._serialize_json(
        SQLiteEvaluationRepository._request_payload(record)
    )
    response_json = SQLiteEvaluationRepository._serialize_json(
        SQLiteEvaluationRepository._response_payload(record)
    )

    # Reproduce the original schema-v1 hash format exactly.
    hash_payload = {
        "evaluation_id": record.evaluation_id,
        "created_at": created_at,
        "baseline_capture_id": record.baseline_capture_id,
        "current_capture_id": record.current_capture_id,
        "request_json": request_json,
        "response_json": response_json,
        "schema_version": 1,
    }
    serialized_hash_payload = json.dumps(
        hash_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    content_hash = hashlib.sha256(
        serialized_hash_payload.encode("utf-8")
    ).hexdigest()

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE evaluations (
                evaluation_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                baseline_capture_id TEXT NOT NULL,
                current_capture_id TEXT NOT NULL,
                request_json TEXT NOT NULL,
                response_json TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                schema_version INTEGER NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO evaluations (
                evaluation_id,
                created_at,
                baseline_capture_id,
                current_capture_id,
                request_json,
                response_json,
                content_hash,
                schema_version
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.evaluation_id,
                created_at,
                record.baseline_capture_id,
                record.current_capture_id,
                request_json,
                response_json,
                content_hash,
                1,
            ),
        )

    # Opening a repository should migrate the legacy table safely.
    migrated_repository = SQLiteEvaluationRepository(database_path)
    migrated = migrated_repository.get(record.evaluation_id)

    assert migrated is not None
    assert migrated.evaluator_version == "legacy"
    assert migrated.agent_answer == record.agent_answer
    assert migrated.response == record.response
    assert migrated.baseline_capture_id == record.baseline_capture_id
    assert migrated.current_capture_id == record.current_capture_id

    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(evaluations)"
            ).fetchall()
        }
        schema_version = connection.execute(
            "SELECT schema_version FROM evaluations WHERE evaluation_id = ?",
            (record.evaluation_id,),
        ).fetchone()[0]

    assert "evaluator_version" in columns
    assert schema_version == 2

def test_v1_migration_rejects_corrupted_legacy_record(tmp_path):
    database_path = tmp_path / "corrupted-legacy.sqlite3"
    record = make_record()

    created_at = record.created_at.isoformat()
    request_json = SQLiteEvaluationRepository._serialize_json(
        SQLiteEvaluationRepository._request_payload(record)
    )
    response_json = SQLiteEvaluationRepository._serialize_json(
        SQLiteEvaluationRepository._response_payload(record)
    )

    # Use a valid old-schema hash, then corrupt the stored content.
    hash_payload = {
        "evaluation_id": record.evaluation_id,
        "created_at": created_at,
        "baseline_capture_id": record.baseline_capture_id,
        "current_capture_id": record.current_capture_id,
        "request_json": request_json,
        "response_json": response_json,
        "schema_version": 1,
    }
    content_hash = hashlib.sha256(
        json.dumps(
            hash_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE evaluations (
                evaluation_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                baseline_capture_id TEXT NOT NULL,
                current_capture_id TEXT NOT NULL,
                request_json TEXT NOT NULL,
                response_json TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                schema_version INTEGER NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO evaluations VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.evaluation_id,
                created_at,
                record.baseline_capture_id,
                record.current_capture_id,
                request_json,
                response_json,
                content_hash,
                1,
            ),
        )
        connection.execute(
            """
            UPDATE evaluations
            SET response_json = ?
            WHERE evaluation_id = ?
            """,
            ('{"tampered":true}', record.evaluation_id),
        )

    with pytest.raises(EvaluationIntegrityError):
        SQLiteEvaluationRepository(database_path)

    # Failed migration must leave the old schema and version intact.
    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(evaluations)"
            ).fetchall()
        }
        schema_version = connection.execute(
            "SELECT schema_version FROM evaluations"
        ).fetchone()[0]

    assert "evaluator_version" not in columns
    assert schema_version == 1
