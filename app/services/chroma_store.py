"""
ChromaDB 向量存储：负责语义检索与按 chunk_id 取回正文。

约定：
- Collection 使用余弦距离（`hnsw:space: cosine`），与常见嵌入归一化习惯一致；
- `ids` 与 ES 文档 `_id` 均等于 `chunk_id`，便于混合检索融合与对账；
- metadata 仅放标量/字符串，避免 Chroma 类型不一致问题。
"""

from __future__ import annotations

from datetime import datetime, timezone

import chromadb

from app.config import Settings
from app.services.chunking import TextChunk


class ChromaStore:
    """Chroma HttpClient + collection 封装。"""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
        self._collection = self._client.get_or_create_collection(
            name=settings.chroma_collection,
            metadata={"hnsw:space": "cosine"},
        )

    def delete_by_doc_id(self, doc_id: str) -> None:
        """同一 doc 重索引前清空旧向量（按 metadata 过滤）。"""
        self._collection.delete(where={"doc_id": doc_id})

    def upsert_chunks(
        self,
        chunks: list[TextChunk],
        embeddings: list[list[float]],
        source_name: str,
    ) -> None:
        """写入向量与文档正文；metadata 与 ES 字段保持同一语义。"""
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
        """返回最相近的 chunk_id 列表（不含文本，文本由 get_by_ids 补全）。"""
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
        """批量按 chunk_id 取回正文与 metadata，用于拼装 LLM 证据。"""
        if not ids:
            return {}
        res = self._collection.get(ids=ids, include=["documents", "metadatas"])
        out: dict[str, dict] = {}
        for cid, doc, meta in zip(res["ids"], res["documents"], res["metadatas"]):
            out[str(cid)] = {"text": doc or "", "metadata": meta or {}}
        return out
