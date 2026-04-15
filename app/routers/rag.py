from fastapi import APIRouter

from app.deps import RagService
from app.schemas.rag import QueryRequest, QueryResponse

router = APIRouter(prefix="/rag")


@router.post("/query", response_model=QueryResponse)
async def rag_query(rag: RagService, body: QueryRequest) -> dict:
    result = await rag.query(question=body.question, doc_id=body.doc_id)
    return result
