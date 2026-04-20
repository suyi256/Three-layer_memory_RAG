"""
Word（.docx）解析：将段落与表格转为「带标题路径」的文本片段，供后续分块。

关键点：
- 通过 Word 样式识别标题（中英样式名），维护 `heading_stack` 表示当前章节路径；
- 表格按行拼接为制表符分隔文本，并继承当前标题路径。
"""

from __future__ import annotations

import io
from dataclasses import dataclass

from docx import Document


@dataclass(frozen=True)
class ParsedSegment:
    """来自 Word 的一段连续文本及其标题路径（用于检索展示与分块上下文）。"""

    text: str
    heading_path: str


def _is_heading(style_name: str | None) -> bool:
    """判断段落是否为标题样式（兼容中英文模板）。"""
    if not style_name:
        return False
    s = style_name.lower()
    return s.startswith("heading") or "标题" in style_name


def parse_docx_bytes(data: bytes) -> list[ParsedSegment]:
    """解析 .docx：段落走标题栈；表格单独成段。"""
    doc = Document(io.BytesIO(data))
    heading_stack: list[str] = []
    segments: list[ParsedSegment] = []

    for para in doc.paragraphs:
        text = (para.text or "").strip()
        style_name = para.style.name if para.style is not None else None
        if _is_heading(style_name) and text:
            # Heading 1..6：用样式名中的数字推断层级，裁剪栈以保持大纲正确
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
