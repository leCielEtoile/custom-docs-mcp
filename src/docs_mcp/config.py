from __future__ import annotations
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

logger = logging.getLogger(__name__)

_DOCS_MCP_DIR = Path("~/.docs-mcp")
_DB_BASE = str(_DOCS_MCP_DIR)
DEFAULT_CONFIG_PATH = _DOCS_MCP_DIR.expanduser() / "config.yaml"

_DEFAULT_CONFIG_TEMPLATE = """\
# docs-mcp configuration — add your documentation sources below.
# Full reference: https://github.com/leCielEtoile/custom-docs-mcp/blob/main/config.example.yaml

sources: []
  # - id: my-docs
  #   url: https://github.com/my-org/my-repo
  #   branch: main
  #   paths:
  #     - docs/
  #   extensions:
  #     - .md

schedule: "0 2 * * *"
"""


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


def ensure_default_config() -> None:
    """Create ~/.docs-mcp/config.yaml from a minimal template if it does not exist."""
    if DEFAULT_CONFIG_PATH.exists():
        return
    DEFAULT_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_CONFIG_PATH.write_text(_DEFAULT_CONFIG_TEMPLATE, encoding="utf-8")
    logger.info(
        "Created default config at %s — edit it to add your documentation sources.",
        DEFAULT_CONFIG_PATH,
    )


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
