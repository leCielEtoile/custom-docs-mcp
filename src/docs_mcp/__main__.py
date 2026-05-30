from __future__ import annotations
import argparse
import logging
import os
from typing import Literal, cast

from .app import build_app
from .config import DEFAULT_CONFIG_PATH, ensure_default_config, load_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="docs-mcp: Documentation MCP server")
    parser.add_argument(
        "--config",
        default=None,
        help=f"Path to config YAML (default: {DEFAULT_CONFIG_PATH})",
    )
    parser.add_argument(
        "--provider",
        choices=["openai", "local"],
        help="Embedding provider — overrides config.yaml embedding.provider",
    )
    parser.add_argument(
        "--model",
        help="Embedding model — overrides config.yaml embedding.model",
    )
    args = parser.parse_args()

    config_path = args.config or str(DEFAULT_CONFIG_PATH)
    if args.config is None:
        ensure_default_config()
    config = load_config(config_path)

    # Priority: CLI arg > env var > config file
    provider_override = args.provider or os.environ.get("DOCS_MCP_PROVIDER")
    model_override = args.model or os.environ.get("DOCS_MCP_MODEL")
    if provider_override:
        config.embedding.provider = cast(Literal["openai", "local"], provider_override)
    if model_override:
        config.embedding.model = model_override

    logger.info("Using config: %s", config_path)
    logger.info("Using DB: %s", config.resolved_db_path())

    mcp = build_app(config)

    if config.transport.mode == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(
            transport="streamable-http",
            host=config.transport.host,
            port=config.transport.port,
        )


if __name__ == "__main__":
    main()
