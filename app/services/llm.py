from __future__ import annotations

import httpx

from app.config import Settings


class ChatClient:
    """OpenAI 兼容 Chat Completions。"""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def chat(self, system: str, user: str) -> str:
        if not self._settings.openai_api_key:
            raise RuntimeError("未配置 OPENAI_API_KEY，无法调用大模型。")
        url = f"{self._settings.openai_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._settings.chat_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
