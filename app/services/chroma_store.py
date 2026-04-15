from __future__ import annotations

from datetime import datetime, timezone

import chromadb

from app.config import Settings
from app.services.chunking import TextChunk


class ChromaStore:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
        self._collection = self._client.get_or_create_collection(
            name=settings.chroma_collection,
            metadata={"hnsw:space": "cosine"},
        )

    def delete_by_doc_id(self, doc_id: str) -> None:
        self._collection.delete(where={"doc_id": doc_id})

    def upsert_chunks(
        self,
        chunks: list[TextChunk],
        embeddings: list[list[float]],
        source_name: str,
    ) -> None:
        if not chunks:
            return
        ids = [c.chunk_id for c in chunks]
        documents = [c.text for c in chunks]
        metadatas = [
            {
                "doc_id": c.doc_id,
                "chunk_id": c.chunk_id,
                "heading_path": c.heading_path or "",
                "version": int(c.version),
                "source": source_name,
                "ingested_at": datetime.now(timezone.utc).isoformat(),
            }
            for c in chunks
        ]
        self._collection.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)

    def query(self, embedding: list[float], k: int, doc_id: str | None = None) -> list[str]:
        kwargs: dict = {
            "query_embeddings": [embedding],
            "n_results": k,
            "include": ["distances"],
        }
        if doc_id:
            kwargs["where"] = {"doc_id": doc_id}
        result = self._collection.query(**kwargs)
        ids = result.get("ids") or []
        if not ids or not ids[0]:
            return []
        return list(ids[0])

    def get_by_ids(self, ids: list[str]) -> dict[str, dict]:
        """返回 chunk_id -> {text, metadata}。"""
        if not ids:
            return {}
        res = self._collection.get(ids=ids, include=["documents", "metadatas"])
        out: dict[str, dict] = {}
        for cid, doc, meta in zip(res["ids"], res["documents"], res["metadatas"]):
            out[str(cid)] = {"text": doc or "", "metadata": meta or {}}
        return out
