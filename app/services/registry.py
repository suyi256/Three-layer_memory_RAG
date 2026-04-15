from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import DocumentRegistry


def next_version(db: Session, doc_id: str) -> int:
    stmt = select(func.coalesce(func.max(DocumentRegistry.version), 0)).where(DocumentRegistry.doc_id == doc_id)
    v = db.execute(stmt).scalar_one()
    return int(v) + 1


def get_registry_row(db: Session, doc_id: str, version: int) -> DocumentRegistry | None:
    stmt = select(DocumentRegistry).where(
        DocumentRegistry.doc_id == doc_id,
        DocumentRegistry.version == version,
    )
    return db.execute(stmt).scalar_one_or_none()


def create_registry_row(
    db: Session,
    *,
    doc_id: str,
    version: int,
    filename: str | None,
    content_hash: str | None,
    status: str,
) -> DocumentRegistry:
    row = DocumentRegistry(
        doc_id=doc_id,
        version=version,
        filename=filename,
        content_hash=content_hash,
        status=status,
        chunk_count=0,
        error_message=None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_registry(
    db: Session,
    row: DocumentRegistry,
    *,
    status: str | None = None,
    chunk_count: int | None = None,
    error_message: str | None = None,
) -> None:
    if status is not None:
        row.status = status
    if chunk_count is not None:
        row.chunk_count = chunk_count
    if error_message is not None:
        row.error_message = error_message
    db.add(row)
    db.commit()
