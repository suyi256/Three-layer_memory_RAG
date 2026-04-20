"""
文本嵌入：调用 OpenAI 兼容 `/v1/embeddings`。

注意：
- 返回向量顺序必须与请求 `input` 文本顺序一致（按 index 排序）；
- 大批量文本在编排层分批，避免单次请求体过大。
"""

from __future__ import annotations

import httpx

from app.config import Settings


class EmbeddingClient:
    """OpenAI 兼容 Embeddings API 的轻量封装。"""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not self._settings.openai_api_key:
            raise RuntimeError("未配置 OPENAI_API_KEY，无法计算向量。")
        if not texts:
            return []
        url = f"{self._settings.openai_base_url.rstrip('/')}/embeddings"
        headers = {
            "Authorization": f"Bearer {self._settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": self._settings.embedding_model, "input": texts}
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        # API 可能乱序返回 data[]，必须按 index 还原顺序
        items = sorted(data["data"], key=lambda x: x["index"])
        return [item["embedding"] for item in items]

    async def embed_query(self, text: str) -> list[float]:
        """单条查询嵌入，供向量检索使用。"""
        vecs = await self.embed_texts([text])
        return vecs[0]
