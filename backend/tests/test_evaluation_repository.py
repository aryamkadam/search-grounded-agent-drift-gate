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
