"""
FastAPI 应用入口。

职责：
- 在 lifespan 中初始化 ES、Chroma、嵌入与对话客户端，并挂到 app.state；
- 挂载版本化 API 路由（/v1）。
"""

from contextlib import asynccontextmanager

from elasticsearch import AsyncElasticsearch
from fastapi import FastAPI

from app.config import get_settings
from app.routers import api_router
from app.services.chroma_store import ChromaStore
from app.services.embeddings import EmbeddingClient
from app.services.llm import ChatClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动时创建外部依赖，关闭时释放（如 ES 异步客户端）。"""
    settings = get_settings()
    app.state.settings = settings
    # 仅用于健康检查与是否放行 RAG：无 Key 时仍可启动服务，但入库/问答会 503
    app.state.openai_enabled = bool(settings.openai_api_key)
    app.state.embedder = EmbeddingClient(settings)
    app.state.chat = ChatClient(settings)
    app.state.es = AsyncElasticsearch(hosts=[settings.es_url])
    app.state.chroma = ChromaStore(settings)
    yield
    await app.state.es.close()


def create_app() -> FastAPI:
    """工厂函数：便于测试时替换配置或挂载额外中间件。"""
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.include_router(api_router, prefix="/v1")

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"service": settings.app_name, "docs": "/docs"}

    return app


app = create_app()
