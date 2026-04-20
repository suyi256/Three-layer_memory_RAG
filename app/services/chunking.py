"""
文本分块：将 ParsedSegment 列表转为带稳定 chunk_id 的 TextChunk。

设计要点：
- `chunk_id` 由 doc_id、version、序号与文本摘要哈希生成，便于 Chroma/ES 以同一主键对齐；
- 超长单段使用滑动窗口 + overlap，减轻截断边界信息丢失。
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from app.services.word_parser import ParsedSegment


@dataclass(frozen=True)
class TextChunk:
    """入库与索引的最小单元；chunk_id 在向量库与 ES 中必须一致。"""

    chunk_id: str
    doc_id: str
    version: int
    text: str
    heading_path: str
    ordinal: int


def _hash_chunk_id(doc_id: str, version: int, ordinal: int, text: str) -> str:
    """生成稳定且较短的 chunk 主键（截断 SHA256）。"""
    raw = f"{doc_id}|{version}|{ordinal}|{text[:512]}".encode("utf-8", errors="ignore")
    return hashlib.sha256(raw).hexdigest()[:40]


def build_chunks(
    doc_id: str,
    version: int,
    segments: list[ParsedSegment],
    max_chars: int,
    overlap: int,
) -> list[TextChunk]:
    """按段落/表格块分块；超长块使用带重叠的滑动窗口。"""
    chunks: list[TextChunk] = []
    ordinal = 0
    for seg in segments:
        text = seg.text.strip()
        if not text:
            continue
        path = seg.heading_path
        n = len(text)
        if n <= max_chars:
            chunks.append(
                TextChunk(
                    chunk_id=_hash_chunk_id(doc_id, version, ordinal, text),
                    doc_id=doc_id,
                    version=version,
                    text=text,
                    heading_path=path,
                    ordinal=ordinal,
                )
            )
            ordinal += 1
            continue
        start = 0
        while start < n:
            end = min(n, start + max_chars)
            piece = text[start:end]
            chunks.append(
                TextChunk(
                    chunk_id=_hash_chunk_id(doc_id, version, ordinal, piece),
                    doc_id=doc_id,
                    version=version,
                    text=piece,
                    heading_path=path,
                    ordinal=ordinal,
                )
            )
            ordinal += 1
            if end == n:
                break
            start = max(0, end - overlap)
    return chunks
