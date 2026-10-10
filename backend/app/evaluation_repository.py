import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, model_validator

from .claims import AgentAnswer
from .evaluation import DriftEvaluationResponse, build_evaluation_id


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
    evaluator_version: str = "legacy"

    @model_validator(mode="after")
    def validate_consistent_ids(self):
        if self.evaluation_id != self.response.evaluation_id:
            raise ValueError("Evaluation IDs do not match.")

        if self.baseline_capture_id != self.response.baseline_capture_id:
            raise ValueError("Baseline capture IDs do not match.")

        if self.current_capture_id != self.response.current_capture_id:
            raise ValueError("Current capture IDs do not match.")

        version = (
            None if self.evaluator_version == "legacy"
            else self.evaluator_version
        )
        expected_id = build_evaluation_id(
            baseline_capture_id=self.baseline_capture_id,
            current_capture_id=self.current_capture_id,
            answer_id=self.agent_answer.answer_id,
            evaluator_version=version,
        )
        if self.evaluation_id != expected_id:
            raise ValueError(
                "Evaluation ID does not match its inputs and evaluator version."
            )

        return self


class SQLiteEvaluationRepository:
    """Persistent evaluation records backed by SQLite."""

    SCHEMA_VERSION = 2
    LEGACY_SCHEMA_VERSION = 1

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
                    evaluator_version TEXT NOT NULL,
                    schema_version INTEGER NOT NULL
                )
                """
            )

            columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(evaluations)"
                ).fetchall()
            }

            if "evaluator_version" not in columns:
                self._migrate_v1(connection)

    @staticmethod
    def _serialize_json(payload: dict) -> str:
        return json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    @classmethod
    def _hash_fields_v1(
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
        """Reproduce the original schema-v1 hash format exactly."""

        payload = {
            "evaluation_id": evaluation_id,
            "created_at": created_at,
            "baseline_capture_id": baseline_capture_id,
            "current_capture_id": current_capture_id,
            "request_json": request_json,
            "response_json": response_json,
            "schema_version": schema_version,
        }

        return hashlib.sha256(
            cls._serialize_json(payload).encode("utf-8")
        ).hexdigest()

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
        evaluator_version: str,
        schema_version: int,
    ) -> str:
        """Hash all schema-v2 fields, including evaluator version."""

        payload = {
            "evaluation_id": evaluation_id,
            "created_at": created_at,
            "baseline_capture_id": baseline_capture_id,
            "current_capture_id": current_capture_id,
            "request_json": request_json,
            "response_json": response_json,
            "evaluator_version": evaluator_version,
            "schema_version": schema_version,
        }

        return hashlib.sha256(
            cls._serialize_json(payload).encode("utf-8")
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

    def _migrate_v1(self, connection: sqlite3.Connection) -> None:
        """Verify every legacy record before atomically upgrading its schema."""

        connection.execute("BEGIN IMMEDIATE")

        rows = connection.execute(
            "SELECT * FROM evaluations ORDER BY evaluation_id"
        ).fetchall()

        # Validate all rows before making any schema or data changes.
        for row in rows:
            if row["schema_version"] != self.LEGACY_SCHEMA_VERSION:
                raise EvaluationIntegrityError(
                    f"Evaluation '{row['evaluation_id']}' uses an "
                    "unsupported legacy schema version."
                )

            expected_hash = self._hash_fields_v1(
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
                    f"Legacy evaluation '{row['evaluation_id']}' "
                    "failed integrity verification; migration aborted."
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

                # Validate the data and preserve the old identity.
                EvaluationRecord(
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
                    evaluator_version="legacy",
                )
            except Exception as exc:
                raise EvaluationIntegrityError(
                    f"Legacy evaluation '{row['evaluation_id']}' "
                    "contains invalid data; migration aborted."
                ) from exc

        connection.execute(
            """
            ALTER TABLE evaluations
            ADD COLUMN evaluator_version TEXT NOT NULL DEFAULT 'legacy'
            """
        )

        for row in rows:
            new_hash = self._hash_fields(
                evaluation_id=row["evaluation_id"],
                created_at=row["created_at"],
                baseline_capture_id=row["baseline_capture_id"],
                current_capture_id=row["current_capture_id"],
                request_json=row["request_json"],
                response_json=row["response_json"],
                evaluator_version="legacy",
                schema_version=self.SCHEMA_VERSION,
            )

            connection.execute(
                """
                UPDATE evaluations
                SET evaluator_version = ?,
                    content_hash = ?,
                    schema_version = ?
                WHERE evaluation_id = ?
                """,
                (
                    "legacy",
                    new_hash,
                    self.SCHEMA_VERSION,
                    row["evaluation_id"],
                ),
            )

    def save(self, record: EvaluationRecord) -> EvaluationRecord:
        """Save once; retries with identical inputs return the original."""

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
            evaluator_version=normalized.evaluator_version,
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
                    evaluator_version,
                    content_hash,
                    schema_version
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(evaluation_id) DO NOTHING
                """,
                (
                    normalized.evaluation_id,
                    created_at,
                    normalized.baseline_capture_id,
                    normalized.current_capture_id,
                    request_json,
                    response_json,
                    normalized.evaluator_version,
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

        # The first successful result remains authoritative for these inputs.
        if (
            existing.baseline_capture_id == normalized.baseline_capture_id
            and existing.current_capture_id == normalized.current_capture_id
            and existing.agent_answer == normalized.agent_answer
            and existing.evaluator_version == normalized.evaluator_version
        ):
            return existing

        raise EvaluationConflictError(
            f"Evaluation '{normalized.evaluation_id}' already exists "
            "with different inputs."
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
            evaluator_version=row["evaluator_version"],
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
                evaluator_version=row["evaluator_version"],
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
