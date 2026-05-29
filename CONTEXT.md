# docs-mcp

An MCP server that ingests documentation from Git repositories and enables AI assistants to search and retrieve content from official documentation.

## Language

**Source**:
A Git repository registered in the configuration file as a documentation target. Defined by an `id` (used as the MCP parameter enum value), an optional `description` (embedded into the tool schema for AI awareness; auto-generated from URL and paths when omitted), a raw HTTP-accessible URL, and a list of paths and file extensions to include.
_Avoid_: repository, repo, doc site

**Ingestion**:
The pipeline that fetches raw document files from a Source, parses them into Chunks, and writes them to the Index. Runs at server startup and on a configurable cron schedule.
_Avoid_: sync, crawl, scraping, indexing

**Chunk**:
A unit of document content split at heading boundaries (`#`, `##`, `###`), with an overflow split applied when a section exceeds the maximum token limit. The atomic unit stored and retrieved from the Index.
_Avoid_: segment, passage, fragment, document

**Index**:
The SQLite database that stores Chunks along with their vector embeddings (sqlite-vec) and full-text entries (FTS5). The single source of truth for all searchable content.
_Avoid_: database, store, cache, knowledge base

**Hybrid Search**:
The retrieval strategy that runs vector search and full-text search in parallel and merges the ranked results using RRF. Used by the `search_docs` tool.
_Avoid_: combined search, multi-search

**RRF (Reciprocal Rank Fusion)**:
The algorithm used to merge ranked result lists from vector search and full-text search. Operates on rank positions only, requiring no score normalization.
_Avoid_: score fusion, rank merging

**Provider**:
The source of the embedding model used during Ingestion and search. Either `openai` (remote API) or `local` (sentence-transformers running in-process). Configured per deployment.
_Avoid_: backend, engine, model source
