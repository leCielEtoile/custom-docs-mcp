from __future__ import annotations
from typing import Protocol, runtime_checkable

from .config import EmbeddingConfig

_OPENAI_DIMS: dict[str, int] = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}

_LOCAL_DIMS: dict[str, int] = {
    "all-MiniLM-L6-v2": 384,
    "all-mpnet-base-v2": 768,
    "paraphrase-multilingual-MiniLM-L12-v2": 384,
}


@runtime_checkable
class EmbeddingProvider(Protocol):
    @property
    def dimension(self) -> int: ...
    async def embed(self, texts: list[str]) -> list[list[float]]: ...


def create_provider(config: EmbeddingConfig) -> EmbeddingProvider:
    if config.provider == "openai":
        return OpenAIProvider(config.model)
    if config.provider == "local":
        return LocalProvider(config.model)
    raise ValueError(f"Unknown embedding provider: {config.provider!r}")


class OpenAIProvider:
    def __init__(self, model: str) -> None:
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI()
        self._model = model
        self._dim = _OPENAI_DIMS.get(model, 1536)

    @property
    def dimension(self) -> int:
        return self._dim

    async def embed(self, texts: list[str]) -> list[list[float]]:
        response = await self._client.embeddings.create(input=texts, model=self._model)
        return [item.embedding for item in response.data]


class LocalProvider:
    def __init__(self, model: str) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers is required for local embedding. "
                "Install it with: uv add 'docs-mcp[local]'"
            ) from exc

        self._model = SentenceTransformer(model)
        self._dim = _LOCAL_DIMS.get(model) or int(
            self._model.get_sentence_embedding_dimension()
        )

    @property
    def dimension(self) -> int:
        return self._dim

    async def embed(self, texts: list[str]) -> list[list[float]]:
        import asyncio
        loop = asyncio.get_event_loop()
        result: list[list[float]] = await loop.run_in_executor(
            None,
            lambda: self._model.encode(texts, convert_to_numpy=True).tolist(),
        )
        return result
