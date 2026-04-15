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
    settings = get_settings()
    app.state.settings = settings
    app.state.openai_enabled = bool(settings.openai_api_key)
    app.state.embedder = EmbeddingClient(settings)
    app.state.chat = ChatClient(settings)
    app.state.es = AsyncElasticsearch(hosts=[settings.es_url])
    app.state.chroma = ChromaStore(settings)
    yield
    await app.state.es.close()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.include_router(api_router, prefix="/v1")

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"service": settings.app_name, "docs": "/docs"}

    return app


app = create_app()
