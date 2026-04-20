"""
倒数排名融合（Reciprocal Rank Fusion, RRF）。

将多路检索返回的有序 chunk_id 列表合并为统一分数：
    score(d) = sum_i 1 / (k + rank_i(d))
其中 rank 从 0 开始。k 越大则排名差异被平滑得越多（常用 k=60）。

用途：在不做分数归一化的情况下，稳定融合「向量路」与「词法路」结果。
"""

from __future__ import annotations


def reciprocal_rank_fusion(
    ranked_lists: dict[str, list[str]],
    *,
    k: int = 60,
    top_n: int | None = None,
) -> list[tuple[str, float]]:
    """
    多路有序 chunk_id 列表融合为 (chunk_id, score)，分数越高越靠前。

    :param ranked_lists: 每一路的名称 -> 有序 chunk_id 列表（越前排名越高）
    :param k: RRF 平滑常数
    :param top_n: 仅保留前 N 个（None 表示全部返回）
    """
    scores: dict[str, float] = {}
    for _source, ids in ranked_lists.items():
        for rank, chunk_id in enumerate(ids):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank + 1)
    ordered = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    if top_n is not None:
        return ordered[:top_n]
    return ordered
