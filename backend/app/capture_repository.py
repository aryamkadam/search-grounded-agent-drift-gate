import hashlib
import json
import sqlite3
from pathlib import Path

from .schema import Capture


class CaptureConflictError(Exception):
    """Raised when a capture ID already exists with different content."""


class CaptureIntegrityError(Exception):
    """Raised when stored capture content fails integrity verification."""


class SQLiteCaptureRepository:
    """Persistent, immutable capture repository backed by SQLite."""

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
                CREATE TABLE IF NOT EXISTS captures (
                    capture_id TEXT PRIMARY KEY,
                    captured_at TEXT NOT NULL,
                    search_id TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    schema_version INTEGER NOT NULL,
                    capture_json TEXT NOT NULL
                )
                """
            )

    @staticmethod
    def _serialize_capture(capture: Capture) -> str:
        payload = capture.model_dump(mode="json")

        return json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    @classmethod
    def _hash_serialized(cls, serialized: str) -> str:
        return hashlib.sha256(
            serialized.encode("utf-8")
        ).hexdigest()

    def save(self, capture: Capture) -> None:
        """Save an immutable capture.

        Identical content under the same ID is idempotent.
        Different content under the same ID raises CaptureConflictError.
        """
        serialized = self._serialize_capture(capture)
        content_hash = self._hash_serialized(serialized)

        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO captures (
                    capture_id,
                    captured_at,
                    search_id,
                    content_hash,
                    schema_version,
                    capture_json
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(capture_id) DO NOTHING
                """,
                (
                    capture.capture_id,
                    capture.captured_at.isoformat(),
                    capture.serpapi_metadata.search_id,
                    content_hash,
                    self.SCHEMA_VERSION,
                    serialized,
                ),
            )

            if cursor.rowcount == 1:
                return

            existing = connection.execute(
                """
                SELECT content_hash
                FROM captures
                WHERE capture_id = ?
                """,
                (capture.capture_id,),
            ).fetchone()

            if existing is None:
                raise RuntimeError(
                    "Capture insert was skipped but no existing record was found."
                )

            if existing["content_hash"] == content_hash:
                return

            raise CaptureConflictError(
                f"Capture '{capture.capture_id}' already exists "
                "with different content."
            )

    def get(self, capture_id: str) -> Capture | None:
        """Load one capture and verify its stored integrity."""

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT capture_json, content_hash, schema_version
                FROM captures
                WHERE capture_id = ?
                """,
                (capture_id,),
            ).fetchone()

        if row is None:
            return None

        if row["schema_version"] != self.SCHEMA_VERSION:
            raise CaptureIntegrityError(
                f"Capture '{capture_id}' uses an unsupported schema version."
            )

        serialized = row["capture_json"]
        expected_hash = row["content_hash"]

        actual_hash = self._hash_serialized(serialized)

        if actual_hash != expected_hash:
            raise CaptureIntegrityError(
                f"Capture '{capture_id}' failed integrity verification."
            )

        try:
            payload = json.loads(serialized)
            return Capture.model_validate(payload)
        except Exception as exc:
            raise CaptureIntegrityError(
                f"Capture '{capture_id}' contains invalid stored data."
            ) from exc

    def list_captures(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Capture], int]:
        """List captures newest-first and verify stored integrity."""
        if limit < 1:
            raise ValueError("limit must be at least 1")
        if offset < 0:
            raise ValueError("offset must not be negative")
        with self._connect() as connection:
            total = connection.execute("SELECT COUNT(*) FROM captures").fetchone()[0]
            rows = connection.execute("SELECT capture_id FROM captures ORDER BY captured_at DESC, capture_id ASC LIMIT ? OFFSET ?", (limit, offset)).fetchall()
        captures = []
        for row in rows:
            capture_id = row["capture_id"]
            capture = self.get(capture_id)
            if capture is None:
                raise CaptureIntegrityError(f"Capture '{capture_id}' disappeared while listing.")
            captures.append(capture)
        return captures, total

    def exists(self, capture_id: str) -> bool:
        """Return whether a capture exists."""

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM captures
                WHERE capture_id = ?
                """,
                (capture_id,),
            ).fetchone()

        return row is not None
