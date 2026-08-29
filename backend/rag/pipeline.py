from pathlib import Path

from backend.memory.store import MemoryStore
from backend.rag.vectorstore import VectorStore
from backend.tools.documents import chunk_text, extract_text


class RAGPipeline:
    def __init__(self) -> None:
        self.store = VectorStore()
        self.memory = MemoryStore()

    def ingest_file(self, path: str) -> dict:
        file_path = Path(path)
        text = extract_text(str(file_path))
        chunks = chunk_text(text)
        n = self.store.upsert_chunks(file_path.name, chunks)
        self.memory.add_document(file_path.name, file_path.suffix.lower().lstrip("."))
        return {"filename": file_path.name, "chunks": n, "chars": len(text)}

    def retrieve(self, query: str, limit: int = 5) -> list[dict]:
        return self.store.search(query, limit=limit)

    def context_block(self, query: str, limit: int = 5) -> str:
        hits = self.retrieve(query, limit=limit)
        if not hits:
            return ""
        parts = []
        for i, h in enumerate(hits, 1):
            parts.append(f"[{i}] {h.get('filename')} (score={h.get('score'):.3f})\n{h.get('text')}")
        return "\n\n".join(parts)
