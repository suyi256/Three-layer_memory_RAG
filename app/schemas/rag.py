from pydantic import BaseModel, Field


class IngestWordResponse(BaseModel):
    doc_id: str
    version: int
    chunk_count: int
    status: str


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=8000)
    doc_id: str | None = Field(default=None, description="限定检索范围到指定文档")


class SourceItem(BaseModel):
    chunk_id: str
    doc_id: str
    heading_path: str
    score: float
    text: str


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceItem]
