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
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_es_client(request: Request) -> AsyncElasticsearch:
    return request.app.state.es


def get_chroma(request: Request) -> ChromaStore:
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
    if not request.app.state.openai_enabled:
        raise HTTPException(status_code=503, detail="未配置 OPENAI_API_KEY，无法进行嵌入与生成。")
    return RAGOrchestrator(request.app.state.settings, es, chroma, embedder, chat)


DbSession = Annotated[Session, Depends(get_db)]
RagService = Annotated[RAGOrchestrator, Depends(get_rag)]
