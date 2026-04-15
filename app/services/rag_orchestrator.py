from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass

import anyio
from elasticsearch import AsyncElasticsearch
from sqlalchemy.orm import Session

from app.config import Settings
from app.services.chunking import build_chunks
from app.services.chroma_store import ChromaStore
from app.services.embeddings import EmbeddingClient
from app.services.es_store import ESStore
from app.services.llm import ChatClient
from app.services.registry import create_registry_row, get_registry_row, next_version, update_registry
from app.services.rrf import reciprocal_rank_fusion
from app.services.word_parser import parse_docx_bytes


@dataclass(frozen=True)
class SourceSnippet:
    chunk_id: str
    doc_id: str
    text: str
    heading_path: str
    score: float


class RAGOrchestrator:
    """编排：入库（Word→双写）与问答（混合检索→生成）。"""

    def __init__(
        self,
        settings: Settings,
        es_client: AsyncElasticsearch,
        chroma: ChromaStore,
        embedder: EmbeddingClient,
        chat: ChatClient,
    ) -> None:
        self._settings = settings
        self._es_client = es_client
        self._chroma = chroma
        self._embedder = embedder
        self._chat = chat
        self._es = ESStore(settings, es_client)

    async def _embed_many(self, texts: list[str]) -> list[list[float]]:
        batch = 64
        out: list[list[float]] = []
        for i in range(0, len(texts), batch):
            part = texts[i : i + batch]
            out.extend(await self._embedder.embed_texts(part))
        return out

    async def ingest_word(
        self,
        db: Session,
        *,
        file_bytes: bytes,
        filename: str,
        doc_id: str | None,
    ) -> dict:
        if not filename.lower().endswith((".docx",)):
            raise ValueError("仅支持 .docx 文件")

        doc_key = doc_id or uuid.uuid4().hex
        content_hash = hashlib.sha256(file_bytes).hexdigest()
        version = next_version(db, doc_key)
        create_registry_row(
            db,
            doc_id=doc_key,
            version=version,
            filename=filename,
            content_hash=content_hash,
            status="parsing",
        )

        try:
            segments = parse_docx_bytes(file_bytes)
            chunks = build_chunks(
                doc_key,
                version,
                segments,
                self._settings.chunk_max_chars,
                self._settings.chunk_overlap,
            )
            if not chunks:
                raise ValueError("文档解析后为空，未生成任何分块")

            row = get_registry_row(db, doc_key, version)
            if row:
                update_registry(db, row, status="indexing")

            texts = [c.text for c in chunks]
            embeddings = await self._embed_many(texts)

            await self._es.delete_by_doc_id(doc_key)
            await anyio.to_thread.run_sync(self._chroma.delete_by_doc_id, doc_key)

            await self._es.index_chunks(chunks, filename)
            await anyio.to_thread.run_sync(
                lambda: self._chroma.upsert_chunks(chunks, embeddings, filename),
            )

            row = get_registry_row(db, doc_key, version)
            if row:
                update_registry(db, row, status="indexed", chunk_count=len(chunks), error_message=None)

            return {
                "doc_id": doc_key,
                "version": version,
                "chunk_count": len(chunks),
                "status": "indexed",
            }
        except Exception as e:  # noqa: BLE001
            row = get_registry_row(db, doc_key, version)
            if row:
                update_registry(db, row, status="failed", error_message=str(e)[:4000])
            raise

    async def query(
        self,
        *,
        question: str,
        doc_id: str | None = None,
    ) -> dict:
        q_emb = await self._embedder.embed_query(question)

        vec_ids = await anyio.to_thread.run_sync(
            lambda: self._chroma.query(
                q_emb,
                self._settings.retrieve_k_vector,
                doc_id=doc_id,
            ),
        )
        lex_ids = await self._es.search_lexical(
            question,
            self._settings.retrieve_k_lexical,
            doc_id=doc_id,
        )

        fused = reciprocal_rank_fusion(
            {"vector": vec_ids, "lexical": lex_ids},
            k=self._settings.rrf_k,
            top_n=self._settings.fusion_top_n,
        )
        top_ids = [cid for cid, _ in fused][: self._settings.context_top_n]

        by_id = await anyio.to_thread.run_sync(self._chroma.get_by_ids, top_ids)
        sources: list[SourceSnippet] = []
        score_map = dict(fused)
        for cid in top_ids:
            item = by_id.get(cid)
            if not item:
                continue
            meta = item["metadata"]
            sources.append(
                SourceSnippet(
                    chunk_id=cid,
                    doc_id=str(meta.get("doc_id", "")),
                    text=item["text"],
                    heading_path=str(meta.get("heading_path", "")),
                    score=float(score_map.get(cid, 0.0)),
                )
            )

        evidence_blocks = []
        for i, s in enumerate(sources, start=1):
            head = f"[{i}] chunk_id={s.chunk_id} doc_id={s.doc_id}"
            if s.heading_path:
                head += f" heading={s.heading_path}"
            evidence_blocks.append(f"{head}\n{s.text}")
        evidence = "\n\n".join(evidence_blocks)
        if not evidence.strip():
            evidence = "（检索未命中任何片段；请直接说明无法从知识库作答，不要编造事实。）"

        system = (
            "你是企业知识库问答助手。请仅依据用户提供的「证据」作答；"
            "若证据不足请明确说明无法从材料中得出答案。"
            "回答使用简体中文，并在句末用 [编号] 引用对应证据段落。"
        )
        user = f"问题：{question}\n\n证据：\n{evidence}"
        answer = await self._chat.chat(system, user)

        return {
            "answer": answer,
            "sources": [
                {
                    "chunk_id": s.chunk_id,
                    "doc_id": s.doc_id,
                    "heading_path": s.heading_path,
                    "score": s.score,
                    "text": s.text[:500] + ("…" if len(s.text) > 500 else ""),
                }
                for s in sources
            ],
        }
