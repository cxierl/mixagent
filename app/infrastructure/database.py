from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


class SqliteStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_schema(self) -> None:
        schema_path = Path(__file__).with_name("schema.sql")
        schema = schema_path.read_text(encoding="utf-8")
        with self._connect() as conn:
            conn.executescript(schema)
            self._apply_compat_upgrades(conn)

    def _apply_compat_upgrades(self, conn: sqlite3.Connection) -> None:
        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(workflow_round_submissions)").fetchall()
        }
        if "is_promoted_to_issue" not in columns:
            conn.execute(
                """
                ALTER TABLE workflow_round_submissions
                ADD COLUMN is_promoted_to_issue INTEGER NOT NULL DEFAULT 0
                """
            )

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def fetch_one(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(sql, params).fetchone()
            return dict(row) if row else None

    def fetch_all(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(x) for x in rows]

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> None:
        with self.connection() as conn:
            conn.execute(sql, params)
