from __future__ import annotations
import logging
from typing import Optional

from fastmcp import FastMCP
from pydantic import Field

from .config import Config
from .db import Database
from .embeddings import EmbeddingProvider
from .search import hybrid_search

logger = logging.getLogger(__name__)


def _source_param_description(config: Config) -> str:
    lines = [
        "Documentation source to search. Omit to search across all sources.",
        "",
        "Available sources:",
    ]
    for s in config.sources:
        lines.append(f'  "{s.id}": {s.resolved_description()}')
    return "\n".join(lines)


def create_server(
    config: Config,
    db: Database,
    provider: EmbeddingProvider,
    lifespan=None,
) -> FastMCP:
    mcp = FastMCP("docs-mcp", lifespan=lifespan)
    source_desc = _source_param_description(config)

    @mcp.tool()
    async def search_docs(
        query: str = Field(description="Natural language search query"),
        source: Optional[str] = Field(None, description=source_desc),
        limit: int = Field(10, ge=1, le=50, description="Maximum number of results to return"),
    ) -> list[dict]:
        """Search documentation using hybrid semantic and full-text search (RRF ranking).

        Returns a ranked list of chunks. Each result contains:
        - source_id: which documentation source the chunk comes from
        - url: raw document URL, usable with read_doc or read_sections
        - heading: section heading of the chunk
        - snippet: first 600 characters of the chunk
        - score: relevance score (higher is better)
        """
        return await hybrid_search(db, provider, query, source, limit)

    @mcp.tool()
    async def read_doc(
        url: str = Field(description="Raw document URL returned by search_docs"),
    ) -> str:
        """Read the full content of a documentation page as Markdown.

        Retrieves all indexed chunks for the given URL and concatenates them
        in document order. Use this when a search result snippet is not enough
        and you need the complete page.
        """
        chunks = db.get_chunks_by_url(url)
        if not chunks:
            return f"No indexed content found for URL: {url}"

        parts: list[str] = []
        prev_heading = None
        for chunk in chunks:
            heading = chunk["heading"]
            if heading and heading != prev_heading:
                parts.append(heading)
                prev_heading = heading
            parts.append(chunk["content"])

        return "\n\n".join(parts)

    @mcp.tool()
    async def read_sections(
        url: str = Field(description="Raw document URL returned by search_docs"),
        sections: list[str] = Field(
            description=(
                "Heading text(s) to retrieve. "
                "Case-insensitive partial match against chunk headings. "
                "Example: ['Installation', 'Quick Start']"
            )
        ),
    ) -> str:
        """Read specific sections of a documentation page by heading.

        Filters indexed chunks whose headings contain any of the provided
        section strings (case-insensitive partial match). Use this to retrieve
        a targeted section without loading the entire page.
        """
        chunks = db.get_chunks_by_url(url)
        if not chunks:
            return f"No indexed content found for URL: {url}"

        lower_terms = [s.lower() for s in sections]
        matched = [
            c for c in chunks
            if any(term in c["heading"].lower() for term in lower_terms)
        ]
        if not matched:
            available = sorted({c["heading"] for c in chunks if c["heading"]})
            hint = ", ".join(f'"{h}"' for h in available[:10])
            return f"No sections matched {sections!r}. Available headings: {hint}"

        parts: list[str] = []
        for chunk in matched:
            if chunk["heading"]:
                parts.append(chunk["heading"])
            parts.append(chunk["content"])

        return "\n\n".join(parts)

    return mcp
