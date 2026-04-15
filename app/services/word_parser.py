from __future__ import annotations

import io
from dataclasses import dataclass

from docx import Document


@dataclass(frozen=True)
class ParsedSegment:
    """来自 Word 的一段连续文本及其标题路径。"""

    text: str
    heading_path: str


def _is_heading(style_name: str | None) -> bool:
    if not style_name:
        return False
    s = style_name.lower()
    return s.startswith("heading") or "标题" in style_name


def parse_docx_bytes(data: bytes) -> list[ParsedSegment]:
    """解析 .docx，按段落提取文本并附带当前标题路径。"""
    doc = Document(io.BytesIO(data))
    heading_stack: list[str] = []
    segments: list[ParsedSegment] = []

    for para in doc.paragraphs:
        text = (para.text or "").strip()
        style_name = para.style.name if para.style is not None else None
        if _is_heading(style_name) and text:
            level = 1
            if style_name and style_name.lower().startswith("heading"):
                parts = style_name.split()
                if len(parts) > 1 and parts[1].isdigit():
                    level = int(parts[1])
            level = max(1, min(level, 6))
            while len(heading_stack) >= level:
                heading_stack.pop()
            heading_stack.append(text)
            continue
        if not text:
            continue
        path = " / ".join(heading_stack) if heading_stack else ""
        segments.append(ParsedSegment(text=text, heading_path=path))

    for table in doc.tables:
        rows_out: list[str] = []
        for row in table.rows:
            cells = [((c.text or "").strip()) for c in row.cells]
            if any(cells):
                rows_out.append("\t".join(cells))
        if rows_out:
            block = "\n".join(rows_out)
            path = " / ".join(heading_stack) if heading_stack else ""
            segments.append(ParsedSegment(text=block, heading_path=path))

    return segments
