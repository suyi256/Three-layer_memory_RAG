from typing import Any

import httpx
from elasticsearch import AsyncElasticsearch
from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health")
async def health(request: Request) -> dict[str, Any]:
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
