import os
import json
import sqlite3
import threading
from typing import Dict, Optional, Tuple


class ConversationStore:
    """将会话记录持久化到 SQLite 数据库。"""

    def __init__(self, db_path: str = ""):
        if not db_path:
            db_path = os.path.join(
                os.path.abspath(os.path.dirname(__file__)), "giftia.db"
            )
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.execute("PRAGMA journal_mode=WAL")
        return self._local.conn

    def _init_db(self):
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                user_id TEXT PRIMARY KEY,
                data TEXT NOT NULL
            )
        """)
        conn.commit()

    def save(self, user_id: str, conversations: Dict, current_id: str):
        data = json.dumps(
            {"current_id": current_id, "conversations": conversations},
            ensure_ascii=False,
        )
        conn = self._get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO conversations (user_id, data) VALUES (?, ?)",
            (user_id, data),
        )
        conn.commit()

    def load(self, user_id: str) -> Tuple[Optional[Dict], Optional[str]]:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT data FROM conversations WHERE user_id = ?", (user_id,)
        ).fetchone()
        if not row:
            return None, None
        try:
            data = json.loads(row[0])
            return data.get("conversations", {}), data.get("current_id")
        except (json.JSONDecodeError, KeyError):
            return None, None
