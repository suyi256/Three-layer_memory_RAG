"""
健康检查：用于编排依赖是否就绪（不校验 MySQL 连接，可按需扩展）。
"""

from typing import Any

import httpx
from elasticsearch import AsyncElasticsearch
from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health")
async def health(request: Request) -> dict[str, Any]:
    """返回整体状态、ES 集群信息、Chroma HTTP 心跳与是否配置了 OpenAI Key。"""
    settings = request.app.state.settings
    es: AsyncElasticsearch = request.app.state.es
    out: dict[str, Any] = {"status": "ok", "openai_configured": bool(request.app.state.openai_enabled)}
    try:
        out["elasticsearch"] = await es.cluster.health()
    except Exception as e:  # noqa: BLE001
        out["elasticsearch"] = {"ok": False, "error": str(e)}
    chroma_url = f"http://{settings.chroma_host}:{settings.chroma_port}/api/v2/heartbeat"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(chroma_url)
            out["chroma"] = {"ok": r.is_success, "status_code": r.status_code}
    except Exception as e:  # noqa: BLE001
        out["chroma"] = {"ok": False, "error": str(e)}
    return out
