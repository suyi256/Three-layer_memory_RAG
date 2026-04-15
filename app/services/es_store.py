from __future__ import annotations

from datetime import datetime, timezone

from elasticsearch import AsyncElasticsearch

from app.config import Settings
from app.services.chunking import TextChunk


class ESStore:
    def __init__(self, settings: Settings, client: AsyncElasticsearch) -> None:
        self._settings = settings
        self._client = client

    @property
    def index(self) -> str:
        return self._settings.es_index

    async def delete_by_doc_id(self, doc_id: str) -> None:
        await self._client.delete_by_query(
            index=self.index,
            query={"term": {"doc_id": doc_id}},
            refresh=True,
        )

    async def index_chunks(self, chunks: list[TextChunk], source_name: str) -> None:
        if not chunks:
            return
        now = datetime.now(timezone.utc).isoformat()
        ops: list[dict] = []
        for c in chunks:
            ops.append({"index": {"_index": self.index, "_id": c.chunk_id}})
            ops.append(
                {
                    "chunk_id": c.chunk_id,
                    "doc_id": c.doc_id,
                    "text": c.text,
                    "heading_path": c.heading_path or "",
                    "source": source_name,
                    "ingested_at": now,
                }
            )
        resp = await self._client.bulk(operations=ops, refresh=True)
        if resp.get("errors"):
            raise RuntimeError(f"Elasticsearch bulk 部分失败: {resp}")

    async def search_lexical(self, query: str, k: int, doc_id: str | None = None) -> list[str]:
        must = [{"match": {"text": {"query": query}}}]
        if doc_id:
            q = {"bool": {"must": must, "filter": [{"term": {"doc_id": doc_id}}]}}
        else:
            q = {"bool": {"must": must}}
        resp = await self._client.search(index=self.index, size=k, query=q, _source=False)
        hits = resp.get("hits", {}).get("hits", [])
        return [str(h["_id"]) for h in hits if h.get("_id")]
