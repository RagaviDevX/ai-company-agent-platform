import hashlib
from pathlib import Path

from backend.cache.cache import get_cache
from backend.memory.store import MemoryStore
from backend.rag.bm25_index import BM25Index
from backend.rag.hybrid import reciprocal_rank_fusion
from backend.rag.vectorstore import VectorStore
from backend.tools.documents import chunk_text, extract_text

# How many candidates each retriever contributes before fusion narrows
# down to the caller's requested `limit`. Wider than `limit` so RRF has
# enough overlap between the two ranked lists to actually matter.
_CANDIDATE_POOL = 15


class RAGPipeline:
    def __init__(self) -> None:
        self.store = VectorStore()
        self.memory = MemoryStore()
        self.bm25 = BM25Index(self.store.list_all_chunks)
        # Bumped on every ingest and folded into the retrieval cache key,
        # so a newly-ingested document is reflected on the very next query
        # instead of waiting out cache_ttl_seconds.
        self._generation = 0

    def ingest_file(self, path: str) -> dict:
        file_path = Path(path)
        text = extract_text(str(file_path))
        chunks = chunk_text(text)
        n = self.store.upsert_chunks(file_path.name, chunks)
        self.bm25.invalidate()
        self._generation += 1
        self.memory.add_document(file_path.name, file_path.suffix.lower().lstrip("."))
        return {"filename": file_path.name, "chunks": n, "chars": len(text)}

    def retrieve(self, query: str, limit: int = 5) -> list[dict]:
        """Hybrid retrieval: dense (vector) + sparse (BM25), fused with RRF.

        Dense embeddings are strong on semantic/paraphrase matches; BM25 is
        strong on exact tokens (IDs, function names, error codes, acronyms)
        that embeddings tend to blur together. Fusing both catches queries
        either retriever alone would miss. Results are cached (Redis, or
        the in-memory fallback) since repeated identical queries -- e.g. a
        user re-running the same /rag search, or the graph re-answering a
        similar task -- are common and embeddings/BM25 scoring isn't free.
        """
        cache = get_cache()
        cache_key = f"rag:{self._generation}:" + hashlib.sha256(f"{query}|{limit}".encode("utf-8")).hexdigest()
        cached = cache.get_json(cache_key)
        if cached is not None:
            return cached

        pool = max(limit, _CANDIDATE_POOL)
        dense_hits = self.store.search(query, limit=pool)
        sparse_hits = self.bm25.search(query, limit=pool)
        hits = reciprocal_rank_fusion(dense_hits, sparse_hits, limit=limit)
        cache.set_json(cache_key, hits)
        return hits

    def context_block(self, query: str, limit: int = 5) -> str:
        hits = self.retrieve(query, limit=limit)
        if not hits:
            return ""
        parts = []
        for i, h in enumerate(hits, 1):
            parts.append(f"[{i}] {h.get('filename')} (score={h.get('score'):.3f})\n{h.get('text')}")
        return "\n\n".join(parts)


_PIPELINE: RAGPipeline | None = None


def get_rag_pipeline() -> RAGPipeline:
    """Process-wide RAGPipeline singleton.

    Previously `backend/api/main.py` and `backend/graph/workflow.py` each
    constructed their own separate RAGPipeline() instance. That was
    already wasteful (each one re-checks the Qdrant collection on
    construction); with the retrieval cache above keyed on an in-process
    `_generation` counter, it would also be a correctness bug -- a
    document uploaded via `/upload` (main.py's instance) would never
    invalidate the graph's cached retrievals (workflow.py's instance).
    Both call sites now share this single instance instead.
    """
    global _PIPELINE
    if _PIPELINE is None:
        _PIPELINE = RAGPipeline()
    return _PIPELINE