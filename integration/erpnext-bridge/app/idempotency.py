"""Idempotency store for write/approval tool calls (mục 9.5).

Every write tool call must carry an `idempotency_key` (the skill generates
one per user intent, e.g. hash of task_id+action+minute-bucket). If the
same key is seen again, the bridge returns the previously recorded result
instead of executing the write a second time — this is what makes
"Không retry mù write operation" and "Write operation không chạy trùng"
(mục 9.5, Phase 6 gate) actually true rather than aspirational.
"""

import json
import sqlite3
import threading
import time

from .config import settings

_lock = threading.Lock()


def _connect():
    conn = sqlite3.connect(settings.idempotency_db_path, check_same_thread=False)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS idempotent_calls (
            profile TEXT NOT NULL,
            idempotency_key TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            result_json TEXT NOT NULL,
            created_at REAL NOT NULL,
            PRIMARY KEY (profile, idempotency_key)
        )
        """
    )
    return conn


_conn = None


def get_conn():
    global _conn
    if _conn is None:
        _conn = _connect()
    return _conn


def get_cached_result(profile: str, idempotency_key: str):
    with _lock:
        row = get_conn().execute(
            "SELECT result_json FROM idempotent_calls WHERE profile = ? AND idempotency_key = ?",
            (profile, idempotency_key),
        ).fetchone()
    return json.loads(row[0]) if row else None


def store_result(profile: str, idempotency_key: str, tool_name: str, result: dict):
    with _lock:
        conn = get_conn()
        conn.execute(
            "INSERT OR IGNORE INTO idempotent_calls (profile, idempotency_key, tool_name, result_json, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (profile, idempotency_key, tool_name, json.dumps(result), time.time()),
        )
        conn.commit()
