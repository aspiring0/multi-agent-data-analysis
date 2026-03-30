"""
会话持久化存储
使用 SQLite 存储会话历史，页面刷新后可恢复。

表结构：
- sessions: 会话元信息（id, name, created_at, updated_at）
- messages: 对话消息（session_id, role, content, timestamp）
- datasets: 数据集元信息（session_id, meta JSON）
- artifacts: 代码/图表/报告等产物（session_id, type, content, path）
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from configs.settings import settings

logger = logging.getLogger(__name__)

# 数据库默认路径
DEFAULT_DB_PATH = settings.PROJECT_ROOT / "data" / "sessions.db"


class SessionStore:
    """SQLite 会话持久化存储"""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = str(db_path or DEFAULT_DB_PATH)
        self._ensure_tables()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _ensure_tables(self):
        """创建必要的表"""
        conn = self._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                );

                CREATE TABLE IF NOT EXISTS datasets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    meta_json TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                );

                CREATE TABLE IF NOT EXISTS artifacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    artifact_type TEXT NOT NULL,
                    content TEXT,
                    file_path TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                );

                CREATE INDEX IF NOT EXISTS idx_messages_session
                    ON messages(session_id);
                CREATE INDEX IF NOT EXISTS idx_datasets_session
                    ON datasets(session_id);
                CREATE INDEX IF NOT EXISTS idx_artifacts_session
                    ON artifacts(session_id);
            """)
            conn.commit()
        finally:
            conn.close()

    # ---- Session CRUD ----

    def create_session(self, session_id: str, name: str) -> dict:
        """创建新会话"""
        now = datetime.now().isoformat()
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT INTO sessions (id, name, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (session_id, name, now, now),
            )
            conn.commit()
            return {"id": session_id, "name": name, "created_at": now, "updated_at": now}
        finally:
            conn.close()

    def list_sessions(self) -> list[dict]:
        """列出所有会话（按更新时间倒序）"""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM sessions ORDER BY updated_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_session(self, session_id: str) -> dict | None:
        """获取单个会话"""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def update_session_name(self, session_id: str, name: str):
        """更新会话名称"""
        conn = self._get_conn()
        try:
            conn.execute(
                "UPDATE sessions SET name = ?, updated_at = ? WHERE id = ?",
                (name, datetime.now().isoformat(), session_id),
            )
            conn.commit()
        finally:
            conn.close()

    def delete_session(self, session_id: str):
        """删除会话及其所有关联数据"""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM datasets WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM artifacts WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            conn.commit()
        finally:
            conn.close()

    def touch_session(self, session_id: str):
        """更新会话最后活跃时间"""
        conn = self._get_conn()
        try:
            conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (datetime.now().isoformat(), session_id),
            )
            conn.commit()
        finally:
            conn.close()

    # ---- Messages ----

    def add_message(self, session_id: str, role: str, content: str):
        """添加消息"""
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT INTO messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (session_id, role, content, datetime.now().isoformat()),
            )
            conn.commit()
            self.touch_session(session_id)
        finally:
            conn.close()

    def get_messages(self, session_id: str) -> list[dict]:
        """获取会话的所有消息"""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT role, content, timestamp FROM messages WHERE session_id = ? ORDER BY id",
                (session_id,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # ---- Datasets ----

    def save_datasets(self, session_id: str, datasets: list[dict]):
        """保存数据集元信息（覆盖式）"""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM datasets WHERE session_id = ?", (session_id,))
            for ds in datasets:
                conn.execute(
                    "INSERT INTO datasets (session_id, meta_json) VALUES (?, ?)",
                    (session_id, json.dumps(ds, ensure_ascii=False)),
                )
            conn.commit()
        finally:
            conn.close()

    def get_datasets(self, session_id: str) -> list[dict]:
        """获取会话的数据集元信息"""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT meta_json FROM datasets WHERE session_id = ?",
                (session_id,),
            ).fetchall()
            return [json.loads(r["meta_json"]) for r in rows]
        finally:
            conn.close()

    # ---- Artifacts ----

    def save_artifact(
        self, session_id: str, artifact_type: str,
        content: str = "", file_path: str = "",
    ):
        """保存产物（代码、报告、图表路径等）"""
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT INTO artifacts (session_id, artifact_type, content, file_path, timestamp) "
                "VALUES (?, ?, ?, ?, ?)",
                (session_id, artifact_type, content, file_path, datetime.now().isoformat()),
            )
            conn.commit()
        finally:
            conn.close()

    def get_artifacts(self, session_id: str, artifact_type: str = None) -> list[dict]:
        """获取会话的产物"""
        conn = self._get_conn()
        try:
            if artifact_type:
                rows = conn.execute(
                    "SELECT * FROM artifacts WHERE session_id = ? AND artifact_type = ? ORDER BY id",
                    (session_id, artifact_type),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM artifacts WHERE session_id = ? ORDER BY id",
                    (session_id,),
                ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
