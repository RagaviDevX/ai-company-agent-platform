import uuid

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams

from backend.config.settings import settings
from backend.rag.embeddings import embed_query, embed_texts
from backend.utils.paths import ensure_dirs

_CLIENT: QdrantClient | None = None


def get_client() -> QdrantClient:
    global _CLIENT
    if _CLIENT is None:
        if settings.qdrant_url:
            # Talk to a real Qdrant server (e.g. the one started by
            # `docker compose up -d`) when QDRANT_URL is configured.
            _CLIENT = QdrantClient(url=settings.qdrant_url)
        else:
            # Zero-config default: embedded, on-disk Qdrant. Note this mode
            # locks the storage directory to a single process, so it is not
            # safe to combine with QDRANT_URL unset across multiple worker
            # processes (e.g. `uvicorn --workers N`).
            ensure_dirs()
            _CLIENT = QdrantClient(path=settings.qdrant_path)
    return _CLIENT


class VectorStore:
    def __init__(self) -> None:
        self.client = get_client()
        self.collection = settings.collection_name
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        names = {c.name for c in self.client.get_collections().collections}
        if self.collection not in names:
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE),
            )

    def upsert_chunks(self, filename: str, chunks: list[str]) -> int:
        if not chunks:
            return 0
        vectors = embed_texts(chunks)
        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vec,
                payload={"filename": filename, "text": chunk, "chunk_index": i},
            )
            for i, (chunk, vec) in enumerate(zip(chunks, vectors))
        ]
        self.client.upsert(collection_name=self.collection, points=points)
        return len(points)

    def search(self, query: str, limit: int = 5) -> list[dict]:
        vector = embed_query(query)
        hits = self.client.search(
            collection_name=self.collection,
            query_vector=vector,
            limit=limit,
        )
        return [
            {
                "score": float(h.score),
                "filename": h.payload.get("filename"),
                "text": h.payload.get("text"),
            }
            for h in hits
        ]

    def list_sources(self) -> list[str]:
        files: set[str] = set()
        points, _ = self.client.scroll(collection_name=self.collection, limit=256)
        for p in points:
            name = (p.payload or {}).get("filename")
            if name:
                files.add(name)
        return sorted(files)
