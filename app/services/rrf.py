from __future__ import annotations


def reciprocal_rank_fusion(
    ranked_lists: dict[str, list[str]],
    *,
    k: int = 60,
    top_n: int | None = None,
) -> list[tuple[str, float]]:
    """RRF：多路有序 chunk_id 列表融合为统一分数，分数越高越靠前。"""
    scores: dict[str, float] = {}
    for _source, ids in ranked_lists.items():
        for rank, chunk_id in enumerate(ids):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank + 1)
    ordered = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    if top_n is not None:
        return ordered[:top_n]
    return ordered
