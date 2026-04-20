"""
RAG 问答 HTTP 接口：混合检索 + 大模型生成。
"""

from fastapi import APIRouter

from app.deps import RagService
from app.schemas.rag import QueryRequest, QueryResponse

router = APIRouter(prefix="/rag")


@router.post("/query", response_model=QueryResponse)
async def rag_query(rag: RagService, body: QueryRequest) -> dict:
    """根据用户问题检索证据并生成回答；可选 doc_id 限定单文档检索范围。"""
    result = await rag.query(question=body.question, doc_id=body.doc_id)
    return result
