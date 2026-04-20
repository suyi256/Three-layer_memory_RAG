"""聚合 v1 下所有子路由（健康检查、入库、RAG 问答）。"""

from fastapi import APIRouter

from app.routers import health, ingest, rag

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
api_router.include_router(rag.router, tags=["rag"])
