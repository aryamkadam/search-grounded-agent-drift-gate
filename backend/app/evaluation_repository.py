import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, model_validator

from .claims import AgentAnswer
from .evaluation import DriftEvaluationResponse


class EvaluationConflictError(Exception):
    """Raised when an evaluation ID is reused for different inputs."""


class EvaluationIntegrityError(Exception):
    """Raised when a stored evaluation fails integrity verification."""


class EvaluationRecord(BaseModel):
    """Immutable historical record of an evaluation and its inputs."""

    evaluation_id: str
    created_at: datetime
    baseline_capture_id: str
    current_capture_id: str
    agent_answer: AgentAnswer
    response: DriftEvaluationResponse

    @model_validator(mode="after")
    def validate_consistent_ids(self):
        if self.evaluation_id != self.response.evaluation_id:
            raise ValueError("Evaluation IDs do not match.")

        if self.baseline_capture_id != self.response.baseline_capture_id:
            raise ValueError("Baseline capture IDs do not match.")

        if self.current_capture_id != self.response.current_capture_id:
            raise ValueError("Current capture IDs do not match.")

        return self


class SQLiteEvaluationRepository:
    """Persistent evaluation records backed by SQLite."""

    SCHEMA_VERSION = 1

    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)

        if self.database_path.parent != Path("."):
            self.database_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

        self._initialize_database()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize_database(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS evaluations (
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

    @staticmethod
    def _serialize_json(payload: dict) -> str:
        return json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    @classmethod
    def _hash_fields(
        cls,
        *,
        evaluation_id: str,
        created_at: str,
        baseline_capture_id: str,
        current_capture_id: str,
        request_json: str,
        response_json: str,
        schema_version: int,
    ) -> str:
        payload = {
            "evaluation_id": evaluation_id,
            "created_at": created_at,
            "baseline_capture_id": baseline_capture_id,
            "current_capture_id": current_capture_id,
            "request_json": request_json,
            "response_json": response_json,
            "schema_version": schema_version,
        }

        serialized = cls._serialize_json(payload)
        return hashlib.sha256(
            serialized.encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _request_payload(record: EvaluationRecord) -> dict:
        return {
            "baseline_capture_id": record.baseline_capture_id,
            "current_capture_id": record.current_capture_id,
            "agent_answer": record.agent_answer.model_dump(mode="json"),
        }

    @staticmethod
    def _response_payload(record: EvaluationRecord) -> dict:
        return record.response.model_dump(mode="json")

    def save(self, record: EvaluationRecord) -> EvaluationRecord:
        """Save once; identical retries return the original record."""

        if (
            record.created_at.tzinfo is None
            or record.created_at.utcoffset() is None
        ):
            raise ValueError("Evaluation timestamp must include a timezone.")

        normalized = record.model_copy(
            update={
                "created_at": record.created_at.astimezone(timezone.utc)
            }
        )

        created_at = normalized.created_at.isoformat()

        request_json = self._serialize_json(
            self._request_payload(normalized)
        )
        response_json = self._serialize_json(
            self._response_payload(normalized)
        )

        content_hash = self._hash_fields(
            evaluation_id=normalized.evaluation_id,
            created_at=created_at,
            baseline_capture_id=normalized.baseline_capture_id,
            current_capture_id=normalized.current_capture_id,
            request_json=request_json,
            response_json=response_json,
            schema_version=self.SCHEMA_VERSION,
        )

        with self._connect() as connection:
            cursor = connection.execute(
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
                ON CONFLICT(evaluation_id) DO NOTHING
                """,
                (
                    normalized.evaluation_id,
                    created_at,
                    normalized.baseline_capture_id,
                    normalized.current_capture_id,
                    request_json,
                    response_json,
                    content_hash,
                    self.SCHEMA_VERSION,
                ),
            )

            if cursor.rowcount == 1:
                return normalized

            row = connection.execute(
                """
                SELECT *
                FROM evaluations
                WHERE evaluation_id = ?
                """,
                (normalized.evaluation_id,),
            ).fetchone()

        if row is None:
            raise RuntimeError(
                "Evaluation insert was skipped but no record was found."
            )

        existing = self._deserialize_row(row)

        # Ignore the new timestamp when deciding whether this is an
        # identical retry. The original timestamp remains authoritative.
        if (
            existing.baseline_capture_id == normalized.baseline_capture_id
            and existing.current_capture_id == normalized.current_capture_id
            and existing.agent_answer == normalized.agent_answer
            and existing.response == normalized.response
        ):
            return existing

        raise EvaluationConflictError(
            f"Evaluation '{normalized.evaluation_id}' already exists "
            "with different inputs or output."
        )

    def _deserialize_row(self, row: sqlite3.Row) -> EvaluationRecord:
        if row["schema_version"] != self.SCHEMA_VERSION:
            raise EvaluationIntegrityError(
                f"Evaluation '{row['evaluation_id']}' uses an "
                "unsupported schema version."
            )

        expected_hash = self._hash_fields(
            evaluation_id=row["evaluation_id"],
            created_at=row["created_at"],
            baseline_capture_id=row["baseline_capture_id"],
            current_capture_id=row["current_capture_id"],
            request_json=row["request_json"],
            response_json=row["response_json"],
            schema_version=row["schema_version"],
        )

        if expected_hash != row["content_hash"]:
            raise EvaluationIntegrityError(
                f"Evaluation '{row['evaluation_id']}' failed "
                "integrity verification."
            )

        try:
            request_payload = json.loads(row["request_json"])
            response_payload = json.loads(row["response_json"])

            if (
                request_payload["baseline_capture_id"]
                != row["baseline_capture_id"]
                or request_payload["current_capture_id"]
                != row["current_capture_id"]
            ):
                raise ValueError("Stored capture IDs are inconsistent.")

            return EvaluationRecord(
                evaluation_id=row["evaluation_id"],
                created_at=datetime.fromisoformat(row["created_at"]),
                baseline_capture_id=row["baseline_capture_id"],
                current_capture_id=row["current_capture_id"],
                agent_answer=AgentAnswer.model_validate(
                    request_payload["agent_answer"]
                ),
                response=DriftEvaluationResponse.model_validate(
                    response_payload
                ),
            )
        except Exception as exc:
            raise EvaluationIntegrityError(
                f"Evaluation '{row['evaluation_id']}' contains "
                "invalid stored data."
            ) from exc

    def get(self, evaluation_id: str) -> EvaluationRecord | None:
        """Retrieve a stored evaluation after integrity verification."""

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM evaluations
                WHERE evaluation_id = ?
                """,
                (evaluation_id,),
            ).fetchone()

        if row is None:
            return None

        return self._deserialize_row(row)
