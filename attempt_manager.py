"""SQLite-backed sessions, attempts, and game snapshots."""
from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Generator


SESSION_TTL_SECONDS = 30 * 24 * 60 * 60


class AttemptManager:
    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.database_path, timeout=30, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        db.execute("PRAGMA busy_timeout = 30000")
        return db

    def initialize(self) -> None:
        db = self.connect()
        try:
            db.execute("PRAGMA journal_mode = WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    expires_at INTEGER NOT NULL,
                    active_attempt_id TEXT
                );
                CREATE TABLE IF NOT EXISTS attempts (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                    chapter_json TEXT NOT NULL,
                    flow_json TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS attempts_session_idx
                    ON attempts(session_id, updated_at);
                CREATE TABLE IF NOT EXISTS games (
                    id TEXT PRIMARY KEY,
                    attempt_id TEXT NOT NULL REFERENCES attempts(id) ON DELETE CASCADE,
                    kind TEXT NOT NULL,
                    review_only INTEGER NOT NULL DEFAULT 0,
                    state_json TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS games_attempt_idx
                    ON games(attempt_id, kind, created_at);
            """)
        finally:
            db.close()

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        db = self.connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @contextmanager
    def read_transaction(self) -> Generator[sqlite3.Connection, None, None]:
        db = self.connect()
        try:
            db.execute("BEGIN")
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def create_session(self, db: sqlite3.Connection, session_id: str | None = None) -> str:
        session_id = session_id or uuid.uuid4().hex + uuid.uuid4().hex
        db.execute(
            "INSERT INTO sessions(id, expires_at) VALUES (?, ?)",
            (session_id, int(time.time()) + SESSION_TTL_SECONDS),
        )
        return session_id

    def get_session(self, db: sqlite3.Connection, session_id: str | None) -> sqlite3.Row | None:
        if not session_id:
            return None
        row = db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if row is None:
            return None
        if row["expires_at"] <= int(time.time()):
            db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            return None
        return row

    def create_attempt(
        self, db: sqlite3.Connection, session_id: str, chapter: dict | None = None
    ) -> str:
        attempt_id = uuid.uuid4().hex
        now = int(time.time())
        flow = {
            "done": {
                "fill_blank": False, "matching": False, "quiz": False, "final_test": False,
            },
            "results": {},
            "games": {},
            "review_games": {},
        }
        db.execute(
            """INSERT INTO attempts(id, session_id, chapter_json, flow_json, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (attempt_id, session_id, json.dumps(chapter), json.dumps(flow), now, now),
        )
        db.execute(
            "UPDATE sessions SET active_attempt_id = ? WHERE id = ?",
            (attempt_id, session_id),
        )
        return attempt_id

    def owned_attempt(
        self, db: sqlite3.Connection, session_id: str, attempt_id: str | None = None
    ) -> sqlite3.Row:
        session = self.get_session(db, session_id)
        if session is None:
            raise PermissionError("Phiên không hợp lệ hoặc đã hết hạn.")
        attempt_id = attempt_id or session["active_attempt_id"]
        if not attempt_id:
            raise ValueError("Chưa có lượt ôn tập.")
        row = db.execute(
            "SELECT * FROM attempts WHERE id = ? AND session_id = ?",
            (attempt_id, session_id),
        ).fetchone()
        if row is None:
            raise PermissionError("Lượt ôn tập không tồn tại hoặc bạn không có quyền truy cập.")
        return row

    def load_game(
        self, db: sqlite3.Connection, attempt_id: str, game_id: str, kind: str
    ) -> sqlite3.Row:
        row = db.execute(
            "SELECT * FROM games WHERE id = ? AND attempt_id = ? AND kind = ?",
            (game_id, attempt_id, kind),
        ).fetchone()
        if row is None:
            raise PermissionError("Ván chơi không tồn tại trong lượt ôn tập này.")
        return row

    def save_flow(self, db: sqlite3.Connection, attempt_id: str, chapter: dict, flow: dict) -> None:
        db.execute(
            "UPDATE attempts SET chapter_json = ?, flow_json = ?, updated_at = ? WHERE id = ?",
            (json.dumps(chapter, ensure_ascii=False), json.dumps(flow, ensure_ascii=False),
             int(time.time()), attempt_id),
        )

    def store_game(
        self, db: sqlite3.Connection, attempt_id: str, kind: str, state: dict,
        review_only: bool = False,
    ) -> str:
        game_id = state["id"]
        db.execute(
            """INSERT INTO games(id, attempt_id, kind, review_only, state_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (game_id, attempt_id, kind, int(review_only),
             json.dumps(state, ensure_ascii=False), int(time.time())),
        )
        return game_id

    def update_game(self, db: sqlite3.Connection, game_id: str, state: dict) -> None:
        db.execute("UPDATE games SET state_json = ? WHERE id = ?",
                   (json.dumps(state, ensure_ascii=False), game_id))

    def delete_game(self, db: sqlite3.Connection, game_id: str) -> None:
        db.execute("DELETE FROM games WHERE id = ?", (game_id,))

    def delete_attempt_games(self, db: sqlite3.Connection, attempt_id: str) -> None:
        db.execute("DELETE FROM games WHERE attempt_id = ?", (attempt_id,))

    def read_game_state(self, db: sqlite3.Connection, game_id: str) -> str | None:
        row = db.execute("SELECT state_json FROM games WHERE id = ?", (game_id,)).fetchone()
        return row["state_json"] if row else None

    def list_attempts(self, db: sqlite3.Connection, session_id: str) -> list[sqlite3.Row]:
        return db.execute(
            """SELECT id, chapter_json, flow_json, created_at, updated_at
               FROM attempts WHERE session_id = ? ORDER BY updated_at DESC""",
            (session_id,),
        ).fetchall()

    def reset(self) -> None:
        """Reset database contents for isolated tests."""
        with self.transaction() as db:
            db.execute("DELETE FROM games")
            db.execute("DELETE FROM attempts")
            db.execute("DELETE FROM sessions")


def default_database_path(root: Path) -> Path:
    configured = os.environ.get("EDUGAME_DB_PATH")
    return Path(configured) if configured else root / "data" / "edugame.sqlite3"
