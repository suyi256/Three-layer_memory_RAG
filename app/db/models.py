"""
ORM 模型：与 `database/mysql/init` 中表结构对齐。

当前 RAG 链路主要读写 `document_registry`，用于索引状态与错误信息治理。
"""

from sqlalchemy import BigInteger, Column, DateTime, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class DocumentRegistry(Base):
    """文档入库与索引状态；与 Chroma/ES 双写进度对应。"""

    __tablename__ = "document_registry"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    doc_id = Column(String(64), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    filename = Column(String(512))
    content_hash = Column(String(128))
    # 与 MySQL ENUM 兼容，按字符串读写（避免 SQLAlchemy 与原生 ENUM 映射差异）
    status = Column(String(32), nullable=False, default="pending")
    error_message = Column(Text)
    chunk_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=False), server_default=func.now())
    updated_at = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now())
