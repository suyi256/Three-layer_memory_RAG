"""
与 RAG 相关的 Pydantic 请求/响应模型（OpenAPI / 校验用）。
"""

from pydantic import BaseModel, Field


class IngestWordResponse(BaseModel):
    """入库结果摘要：业务 doc_id、版本与分块数量。"""

    doc_id: str
    version: int
    chunk_count: int
    status: str


class QueryRequest(BaseModel):
    """问答请求：自然语言问题 + 可选文档范围。"""

    question: str = Field(..., min_length=1, max_length=8000)
    doc_id: str | None = Field(default=None, description="限定检索范围到指定文档")


class SourceItem(BaseModel):
    """单条引用：含融合分数与正文摘要（列表展示用截断）。"""

    chunk_id: str
    doc_id: str
    heading_path: str
    score: float
    text: str


class QueryResponse(BaseModel):
    """问答响应：模型答案 + 结构化引用列表。"""

    answer: str
    sources: list[SourceItem]
