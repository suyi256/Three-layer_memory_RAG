"""
Elasticsearch 词法索引：BM25 检索：仅存可检索文本与过滤字段，不存向量。

要点：
- `_id` 使用 chunk_id，与 Chroma 的 id 对齐；
- `delete_by_query` 在重索引前按 doc_id 清理旧文档；
- `search_lexical` 关闭 _source，仅用 hit._id 作为 chunk_id 列表参与 RRF。
"""

from __future__ import annotations

from datetime import datetime, timezone

from elasticsearch import AsyncElasticsearch

from app.config import Settings
from app.services.chunking import TextChunk


class ESStore:
    """异步 ES 客户端上的索引与检索封装。"""

    def __init__(self, settings: Settings, client: AsyncElasticsearch) -> None:
        self._settings = settings
        self._client = client

    @property
    def index(self) -> str:
        return self._settings.es_index

    async def delete_by_doc_id(self, doc_id: str) -> None:
        """按业务 doc_id 删除该文档下全部 chunk 文档。"""
        await self._client.delete_by_query(
            index=self.index,
            query={"term": {"doc_id": doc_id}},
            refresh=True,
        )

    async def index_chunks(self, chunks: list[TextChunk], source_name: str) -> None:
        """bulk 写入；每条 op 为 index 头 + source 体（ES 8 bulk operations 格式）。"""
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
        """对 text 字段做 match；可选按 doc_id 过滤。返回 chunk_id 列表（即 ES _id）。"""
        must = [{"match": {"text": {"query": query}}}]
        if doc_id:
            q = {"bool": {"must": must, "filter": [{"term": {"doc_id": doc_id}}]}}
        else:
            q = {"bool": {"must": must}}
        resp = await self._client.search(index=self.index, size=k, query=q, _source=False)
        hits = resp.get("hits", {}).get("hits", [])
        return [str(h["_id"]) for h in hits if h.get("_id")]
