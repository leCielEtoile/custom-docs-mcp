from __future__ import annotations
import hashlib
import re
from dataclasses import dataclass

import tiktoken

_TOKENIZER = tiktoken.get_encoding("cl100k_base")

# Matches Markdown headings up to level 3
_MD_HEADING_RE = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
# Matches RST section underline characters (any repeated punctuation)
_RST_UNDERLINE_RE = re.compile(r"^([!\"#$%&'()*+,\-./:;<=>?@\[\\\]^_`{|}~])\1+$")
# Strips MDX JSX components (block and inline)
_MDX_JSX_RE = re.compile(r"<[A-Z][A-Za-z]*[^>]*/?>|<[A-Z][A-Za-z]*[^>]*>.*?</[A-Z][A-Za-z]*>", re.DOTALL)


@dataclass
class Chunk:
    id: str
    source_id: str
    url: str
    heading: str
    content: str
    token_count: int


# ── Token helpers ────────────────────────────────────────────────────────────

def _count_tokens(text: str) -> int:
    return len(_TOKENIZER.encode(text))


def _split_by_token_limit(text: str, max_tokens: int) -> list[str]:
    tokens = _TOKENIZER.encode(text)
    if len(tokens) <= max_tokens:
        return [text]
    return [
        _TOKENIZER.decode(tokens[i : i + max_tokens])
        for i in range(0, len(tokens), max_tokens)
    ]


def _chunk_id(source_id: str, url: str, index: int) -> str:
    raw = f"{source_id}:{url}:{index}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ── Parsers ──────────────────────────────────────────────────────────────────

def parse_chunks(
    content: str,
    url: str,
    source_id: str,
    extension: str,
    max_tokens: int,
) -> list[Chunk]:
    if extension == ".mdx":
        content = _MDX_JSX_RE.sub("", content)
        return _chunk_markdown(content, url, source_id, max_tokens)
    if extension == ".md":
        return _chunk_markdown(content, url, source_id, max_tokens)
    if extension == ".rst":
        return _chunk_rst(content, url, source_id, max_tokens)
    return _chunk_plaintext(content, url, source_id, max_tokens)


def _emit_chunks(
    sections: list[tuple[str, str]],
    url: str,
    source_id: str,
    max_tokens: int,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    for heading, body in sections:
        body = body.strip()
        if not body and not heading:
            continue
        full = f"{heading}\n\n{body}" if heading else body
        for sub in _split_by_token_limit(full, max_tokens):
            sub = sub.strip()
            if not sub:
                continue
            chunks.append(
                Chunk(
                    id=_chunk_id(source_id, url, len(chunks)),
                    source_id=source_id,
                    url=url,
                    heading=heading,
                    content=sub,
                    token_count=_count_tokens(sub),
                )
            )
    return chunks


def _chunk_markdown(content: str, url: str, source_id: str, max_tokens: int) -> list[Chunk]:
    parts = re.split(r"(^#{1,3}\s+.+$)", content, flags=re.MULTILINE)
    sections: list[tuple[str, str]] = []
    current_heading = ""
    body_parts: list[str] = []

    for part in parts:
        if _MD_HEADING_RE.match(part.strip()):
            if body_parts or current_heading:
                sections.append((current_heading, "\n".join(body_parts)))
            current_heading = part.strip()
            body_parts = []
        else:
            body_parts.append(part)

    if body_parts or current_heading:
        sections.append((current_heading, "\n".join(body_parts)))

    chunks = _emit_chunks(sections, url, source_id, max_tokens)
    if not chunks and content.strip():
        chunks = _chunk_plaintext(content, url, source_id, max_tokens)
    return chunks


def _chunk_rst(content: str, url: str, source_id: str, max_tokens: int) -> list[Chunk]:
    lines = content.splitlines()
    sections: list[tuple[str, str]] = []
    current_heading = ""
    body_lines: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]
        next_line = lines[i + 1] if i + 1 < len(lines) else ""

        is_underline = (
            next_line
            and _RST_UNDERLINE_RE.match(next_line)
            and len(next_line.strip()) >= len(line.strip())
            and line.strip()
        )
        if is_underline:
            if body_lines or current_heading:
                sections.append((current_heading, "\n".join(body_lines)))
            current_heading = line.strip()
            body_lines = []
            i += 2  # skip underline
        else:
            body_lines.append(line)
            i += 1

    if body_lines or current_heading:
        sections.append((current_heading, "\n".join(body_lines)))

    chunks = _emit_chunks(sections, url, source_id, max_tokens)
    if not chunks:
        chunks = _chunk_plaintext(content, url, source_id, max_tokens)
    return chunks


def _chunk_plaintext(content: str, url: str, source_id: str, max_tokens: int) -> list[Chunk]:
    paragraphs = re.split(r"\n{2,}", content)
    chunks: list[Chunk] = []
    buffer = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        candidate = f"{buffer}\n\n{para}" if buffer else para
        if _count_tokens(candidate) <= max_tokens:
            buffer = candidate
        else:
            if buffer:
                for sub in _split_by_token_limit(buffer, max_tokens):
                    sub = sub.strip()
                    if sub:
                        chunks.append(
                            Chunk(
                                id=_chunk_id(source_id, url, len(chunks)),
                                source_id=source_id,
                                url=url,
                                heading="",
                                content=sub,
                                token_count=_count_tokens(sub),
                            )
                        )
            buffer = para

    if buffer:
        for sub in _split_by_token_limit(buffer, max_tokens):
            sub = sub.strip()
            if sub:
                chunks.append(
                    Chunk(
                        id=_chunk_id(source_id, url, len(chunks)),
                        source_id=source_id,
                        url=url,
                        heading="",
                        content=sub,
                        token_count=_count_tokens(sub),
                    )
                )
    return chunks
