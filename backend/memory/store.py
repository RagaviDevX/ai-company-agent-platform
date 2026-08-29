import sqlite3
from pathlib import Path

from backend.config.settings import settings
from backend.utils.paths import ensure_dirs


class MemoryStore:
    def __init__(self, db_path: str | None = None) -> None:
        ensure_dirs()
        self.db_path = db_path or settings.sqlite_db
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        schema = Path(__file__).resolve().parents[2] / "database" / "schema.sql"
        with self._connect() as conn:
            conn.executescript(schema.read_text(encoding="utf-8"))
            conn.execute(
                "INSERT OR IGNORE INTO users (id, name, email) VALUES (1, 'Founder', 'founder@local')"
            )
            conn.commit()

    def add_conversation(self, user_id: int, message: str, response: str) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO conversations (user_id, message, response) VALUES (?, ?, ?)",
                (user_id, message, response),
            )
            conn.commit()
            return int(cur.lastrowid)

    def list_conversations(self, user_id: int, limit: int = 50) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM conversations WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def add_memory(self, user_id: int, memory: str) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO memories (user_id, memory) VALUES (?, ?)",
                (user_id, memory),
            )
            conn.commit()
            return int(cur.lastrowid)

    def list_memories(self, user_id: int) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM memories WHERE user_id = ? ORDER BY id DESC",
                (user_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def add_document(self, filename: str, document_type: str) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO documents (filename, document_type) VALUES (?, ?)",
                (filename, document_type),
            )
            conn.commit()
            return int(cur.lastrowid)

    def list_documents(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM documents ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]

    def add_agent_log(
        self,
        conversation_id: int | None,
        agent_name: str,
        model: str,
        input_preview: str,
        output_preview: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO agent_logs (conversation_id, agent_name, model, input_preview, output_preview)
                VALUES (?, ?, ?, ?, ?)
                """,
                (conversation_id, agent_name, model, input_preview[:500], output_preview[:500]),
            )
            conn.commit()

    def list_agent_logs(self, limit: int = 100) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM agent_logs ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]
