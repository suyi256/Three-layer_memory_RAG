"""
FastAPI 依赖注入：数据库会话、外部客户端、RAG 编排器。

注意：
- `Session` 必须在同一请求线程内使用，勿与 `anyio.to_thread` 混用同一 session；
- `get_rag` 在无 OPENAI_API_KEY 时直接 503，避免半初始化链路。
"""

from typing import Annotated

from elasticsearch import AsyncElasticsearch
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.services.chroma_store import ChromaStore
from app.services.embeddings import EmbeddingClient
from app.services.llm import ChatClient
from app.services.rag_orchestrator import RAGOrchestrator


def get_db() -> Session:
    """每个请求一个短生命周期 Session，结束时关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_es_client(request: Request) -> AsyncElasticsearch:
    """来自 lifespan 的异步 ES 客户端单例。"""
    return request.app.state.es


def get_chroma(request: Request) -> ChromaStore:
    """来自 lifespan 的 Chroma 封装（内部为同步 HttpClient）。"""
    return request.app.state.chroma


def get_embedder(request: Request) -> EmbeddingClient:
    return request.app.state.embedder


def get_chat(request: Request) -> ChatClient:
    return request.app.state.chat


def get_rag(
    request: Request,
    es: Annotated[AsyncElasticsearch, Depends(get_es_client)],
    chroma: Annotated[ChromaStore, Depends(get_chroma)],
    embedder: Annotated[EmbeddingClient, Depends(get_embedder)],
    chat: Annotated[ChatClient, Depends(get_chat)],
) -> RAGOrchestrator:
    """组装 RAG 编排器；嵌入与对话强依赖 API Key。"""
    if not request.app.state.openai_enabled:
        raise HTTPException(status_code=503, detail="未配置 OPENAI_API_KEY，无法进行嵌入与生成。")
    return RAGOrchestrator(request.app.state.settings, es, chroma, embedder, chat)


DbSession = Annotated[Session, Depends(get_db)]
RagService = Annotated[RAGOrchestrator, Depends(get_rag)]
