from __future__ import annotations
import asyncio
from typing import Any
from .db import Database
from .embeddings import EmbeddingProvider

_RRF_K = 60


async def hybrid_search(
    db: Database,
    provider: EmbeddingProvider,
    query: str,
    source_id: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    fetch_n = limit * 3  # over-fetch to have enough candidates after RRF merge

    loop = asyncio.get_running_loop()
    [embedding] = await provider.embed([query])

    vec_results, fts_results = await asyncio.gather(
        loop.run_in_executor(None, db.vector_search, embedding, source_id, fetch_n),
        loop.run_in_executor(None, db.fts_search, query, source_id, fetch_n),
    )

    scores: dict[str, float] = {}
    for rank, (chunk_id, _) in enumerate(vec_results):
        scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (_RRF_K + rank + 1)
    for rank, (chunk_id, _) in enumerate(fts_results):
        scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (_RRF_K + rank + 1)

    ranked_ids = sorted(scores, key=lambda cid: scores[cid], reverse=True)[:limit]
    rows = {r["id"]: r for r in db.get_chunks_by_ids(ranked_ids)}

    return [
        {
            "source_id": rows[cid]["source_id"],
            "url": rows[cid]["url"],
            "heading": rows[cid]["heading"],
            "snippet": rows[cid]["content"][:600],
            "score": round(scores[cid], 6),
        }
        for cid in ranked_ids
        if cid in rows
    ]
