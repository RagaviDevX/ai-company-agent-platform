from pathlib import Path

from backend.memory.store import MemoryStore


def test_memory_roundtrip(tmp_path):
    db = tmp_path / "memory.db"
    store = MemoryStore(str(db))
    store.add_memory(1, "Prefers FastAPI")
    rows = store.list_memories(1)
    assert rows[0]["memory"] == "Prefers FastAPI"
    cid = store.add_conversation(1, "hello", "hi")
    assert cid > 0
