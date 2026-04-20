"""
文档入库 HTTP 接口：当前支持 Word（.docx）上传。
"""

from fastapi import APIRouter, File, Form, UploadFile

from app.deps import DbSession, RagService
from app.schemas.rag import IngestWordResponse

router = APIRouter()


@router.post("/word", response_model=IngestWordResponse)
async def ingest_word(
    db: DbSession,
    rag: RagService,
    file: UploadFile = File(..., description=".docx 文件"),
    doc_id: str | None = Form(default=None, description="可选，固定文档 ID；不传则自动生成"),
) -> dict:
    """读取上传文件字节流并交给编排器完成解析、嵌入与双写。"""
    raw = await file.read()
    filename = file.filename or "upload.docx"
    return await rag.ingest_word(db, file_bytes=raw, filename=filename, doc_id=doc_id)
