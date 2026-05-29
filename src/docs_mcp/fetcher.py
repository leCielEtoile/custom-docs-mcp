from __future__ import annotations
import asyncio
import logging
import re
from typing import TYPE_CHECKING

import httpx

from .config import SourceConfig
from .parser import Chunk, parse_chunks

if TYPE_CHECKING:
    from .config import Config
    from .db import Database
    from .embeddings import EmbeddingProvider

logger = logging.getLogger(__name__)

_FETCH_CONCURRENCY_AUTHENTICATED = 40
_FETCH_CONCURRENCY_ANONYMOUS = 10


# ── GitHub fetcher ────────────────────────────────────────────────────────────

def _parse_github_url(url: str) -> tuple[str, str, str]:
    m = re.match(r"https://github\.com/([^/]+)/([^/]+?)(?:/tree/([^/]+))?/?$", url)
    if not m:
        raise ValueError(f"Unsupported GitHub URL: {url}")
    owner, repo, branch = m.groups()
    return owner, repo.rstrip("/"), branch or "main"


async def list_source_files(source: SourceConfig) -> list[dict[str, str]]:
    owner, repo, branch = _parse_github_url(source.url)
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if source.token:
        headers["Authorization"] = f"Bearer {source.token}"

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1",
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()

    files: list[dict[str, str]] = []
    for item in data.get("tree", []):
        if item["type"] != "blob":
            continue
        path: str = item["path"]
        if not any(path.startswith(p.lstrip("/")) for p in source.paths):
            continue
        dot = path.rfind(".")
        ext = path[dot:] if dot != -1 else ""
        if ext not in source.extensions:
            continue
        files.append(
            {
                "path": path,
                "url": f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}",
                "extension": ext,
            }
        )
    return files


async def fetch_raw(url: str, token: str | None, client: httpx.AsyncClient) -> str:
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = await client.get(url, headers=headers)
    resp.raise_for_status()
    return resp.text


async def ingest_source(
    source: SourceConfig,
    max_tokens: int,
) -> list[Chunk]:
    files = await list_source_files(source)
    concurrency = _FETCH_CONCURRENCY_AUTHENTICATED if source.token else _FETCH_CONCURRENCY_ANONYMOUS
    sem = asyncio.Semaphore(concurrency)

    async def fetch_and_parse(file_info: dict[str, str]) -> list[Chunk]:
        async with sem:
            try:
                content = await fetch_raw(file_info["url"], source.token, client)
            except Exception:
                return []
        return parse_chunks(
            content,
            url=file_info["url"],
            source_id=source.id,
            extension=file_info["extension"],
            max_tokens=max_tokens,
        )

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        results = await asyncio.gather(*[fetch_and_parse(f) for f in files])

    return [chunk for chunks in results for chunk in chunks]


# ── Ingestion runner ──────────────────────────────────────────────────────────

async def _ingest_one_source(
    source: SourceConfig,
    config: Config,
    db: Database,
    provider: EmbeddingProvider,
) -> None:
    logger.info("Ingesting source: %s", source.id)
    db.delete_source(source.id)

    chunks = await ingest_source(source, config.chunk_max_tokens)
    count = 0

    for i in range(0, len(chunks), 32):
        batch = chunks[i : i + 32]
        embeddings = await provider.embed([c.content for c in batch])
        for c, emb in zip(batch, embeddings):
            db.upsert_chunk(c, emb)
        db.commit()
        count += len(batch)

    logger.info("Ingested %d chunks from source: %s", count, source.id)


async def run_ingestion(config: Config, db: Database, provider: EmbeddingProvider) -> None:
    await asyncio.gather(*[
        _ingest_one_source(source, config, db, provider)
        for source in config.sources
    ])
