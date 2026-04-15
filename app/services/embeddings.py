from __future__ import annotations

import httpx

from app.config import Settings


class EmbeddingClient:
    """OpenAI 兼容 Embeddings API。"""

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
        items = sorted(data["data"], key=lambda x: x["index"])
        return [item["embedding"] for item in items]

    async def embed_query(self, text: str) -> list[float]:
        vecs = await self.embed_texts([text])
        return vecs[0]
