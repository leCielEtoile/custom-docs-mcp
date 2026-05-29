from __future__ import annotations
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

_DB_BASE = "~/.docs-mcp"


@dataclass
class SourceConfig:
    id: str
    url: str
    paths: list[str]
    extensions: list[str] = field(default_factory=lambda: [".md", ".mdx", ".txt", ".rst"])
    description: str | None = None
    branch: str = "main"
    token: str | None = None

    def __post_init__(self) -> None:
        if self.token:
            self.token = _expand_env(self.token)

    def resolved_description(self) -> str:
        if self.description:
            return self.description
        repo_name = self.url.rstrip("/").split("/")[-1]
        paths_str = ", ".join(self.paths)
        return f"Documentation from {repo_name} ({paths_str})"


@dataclass
class EmbeddingConfig:
    provider: Literal["openai", "local"] = "openai"
    model: str = "text-embedding-3-small"


@dataclass
class TransportConfig:
    mode: Literal["stdio", "http"] = "stdio"
    host: str = "0.0.0.0"
    port: int = 8000


@dataclass
class Config:
    sources: list[SourceConfig]
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    schedule: str = "0 2 * * *"
    transport: TransportConfig = field(default_factory=TransportConfig)
    db_path: str | None = None   # None = auto-derive from embedding provider + model
    chunk_max_tokens: int = 512

    def resolved_db_path(self) -> str:
        """Return the actual DB path, deriving it from the embedding config if not set."""
        if self.db_path:
            return self.db_path
        return derive_db_path(self.embedding.provider, self.embedding.model)


def derive_db_path(provider: str, model: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", model.lower()).strip("-")
    return f"{_DB_BASE}/index-{provider}-{slug}.db"


def load_config(path: str | Path) -> Config:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    sources = [_parse_source(s) for s in data.get("sources", [])]

    emb_data = data.get("embedding", {})
    embedding = EmbeddingConfig(
        provider=emb_data.get("provider", "openai"),
        model=emb_data.get("model", "text-embedding-3-small"),
    )

    transport_raw = data.get("transport", {})
    if isinstance(transport_raw, str):
        transport = TransportConfig(mode=transport_raw)  # type: ignore[arg-type]
    else:
        transport = TransportConfig(
            mode=transport_raw.get("mode", "stdio"),
            host=transport_raw.get("host", "0.0.0.0"),
            port=transport_raw.get("port", 8000),
        )

    return Config(
        sources=sources,
        embedding=embedding,
        schedule=data.get("schedule", "0 2 * * *"),
        transport=transport,
        db_path=data.get("db_path"),  # None if not set → auto-derived
        chunk_max_tokens=data.get("chunk_max_tokens", 512),
    )


def _parse_source(data: dict[str, Any]) -> SourceConfig:
    return SourceConfig(
        id=data["id"],
        url=data["url"],
        paths=data.get("paths", ["/"]),
        extensions=data.get("extensions", [".md", ".mdx", ".txt", ".rst"]),
        description=data.get("description"),
        branch=data.get("branch", "main"),
        token=data.get("token"),
    )


def _expand_env(value: str) -> str:
    def replace(m: re.Match) -> str:
        return os.environ.get(m.group(1), "")
    return re.sub(r"\$\{([^}]+)\}", replace, value)
