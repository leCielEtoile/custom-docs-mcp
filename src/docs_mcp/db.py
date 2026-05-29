from __future__ import annotations
import re
import sqlite3
import struct
from pathlib import Path
from typing import TYPE_CHECKING

import sqlite_vec

if TYPE_CHECKING:
    from .parser import Chunk


def _serialize(vector: list[float]) -> bytes:
    return struct.pack(f"{len(vector)}f", *vector)


class Database:
    def __init__(self, path: str, embedding_dim: int) -> None:
        db_path = Path(path).expanduser()
        db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.enable_load_extension(True)
        sqlite_vec.load(self.conn)
        self.conn.enable_load_extension(False)

        self._dim = embedding_dim
        self._init_schema()

    def _init_schema(self) -> None:
        # Base tables that are safe to create idempotently
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS meta (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS chunks (
                id       TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                url      TEXT NOT NULL,
                heading  TEXT NOT NULL DEFAULT '',
                content  TEXT NOT NULL,
                token_count INTEGER NOT NULL DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_chunks_url    ON chunks(url);
            CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source_id);

            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                id       UNINDEXED,
                source_id UNINDEXED,
                content,
                tokenize='unicode61 remove_diacritics 1'
            );
        """)
        self.conn.commit()

        # Validate stored embedding dimension; wipe vector index on mismatch
        stored = self.conn.execute(
            "SELECT value FROM meta WHERE key = 'embedding_dim'"
        ).fetchone()

        if stored is None or int(stored["value"]) != self._dim:
            import logging
            logging.getLogger(__name__).warning(
                "Embedding dimension mismatch (stored=%s, current=%s). Clearing index.",
                stored["value"] if stored else "none",
                self._dim,
            )
            self.conn.executescript("""
                DELETE FROM chunks;
                DELETE FROM chunks_fts;
                DROP TABLE IF EXISTS vec_chunks;
            """)
            self.conn.execute(
                """INSERT INTO meta(key, value) VALUES ('embedding_dim', ?)
                   ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
                (str(self._dim),),
            )
            self.conn.commit()
            self._create_vec_table()
        # else: dimension matches — vec table already exists, nothing to do

    def _create_vec_table(self) -> None:
        self.conn.execute(
            f"CREATE VIRTUAL TABLE IF NOT EXISTS vec_chunks USING vec0(embedding float[{self._dim}])"
        )
        self.conn.commit()

    # ── Write operations ──────────────────────────────────────────────────────

    def upsert_chunk(self, chunk: Chunk, embedding: list[float]) -> None:
        existing = self.conn.execute(
            "SELECT rowid FROM chunks WHERE id = ?", (chunk.id,)
        ).fetchone()

        if existing:
            rowid: int = existing["rowid"]
            self.conn.execute(
                "UPDATE chunks SET source_id=?, url=?, heading=?, content=?, token_count=? WHERE id=?",
                (chunk.source_id, chunk.url, chunk.heading, chunk.content, chunk.token_count, chunk.id),
            )
            self.conn.execute("DELETE FROM chunks_fts WHERE id = ?", (chunk.id,))
            self.conn.execute("DELETE FROM vec_chunks WHERE rowid = ?", (rowid,))
        else:
            cur = self.conn.execute(
                "INSERT INTO chunks (id, source_id, url, heading, content, token_count) VALUES (?,?,?,?,?,?)",
                (chunk.id, chunk.source_id, chunk.url, chunk.heading, chunk.content, chunk.token_count),
            )
            rowid = cur.lastrowid  # type: ignore[assignment]

        self.conn.execute(
            "INSERT INTO chunks_fts(rowid, id, source_id, content) VALUES (?,?,?,?)",
            (rowid, chunk.id, chunk.source_id, chunk.content),
        )
        self.conn.execute(
            "INSERT INTO vec_chunks(rowid, embedding) VALUES (?,?)",
            (rowid, _serialize(embedding)),
        )

    def commit(self) -> None:
        self.conn.commit()

    def delete_source(self, source_id: str) -> None:
        rows = self.conn.execute(
            "SELECT rowid, id FROM chunks WHERE source_id = ?", (source_id,)
        ).fetchall()
        if not rows:
            return

        rowids = [r["rowid"] for r in rows]
        ids = [r["id"] for r in rows]

        self.conn.execute("DELETE FROM chunks WHERE source_id = ?", (source_id,))

        ph = ",".join("?" * len(ids))
        self.conn.execute(f"DELETE FROM chunks_fts WHERE id IN ({ph})", ids)
        self.conn.execute(f"DELETE FROM vec_chunks WHERE rowid IN ({ph})", rowids)
        self.conn.commit()

    # ── Read operations ───────────────────────────────────────────────────────

    def vector_search(
        self, embedding: list[float], source_id: str | None, limit: int
    ) -> list[tuple[str, float]]:
        # Fetch extra candidates to allow source filtering after the vec search
        fetch_n = limit * 3 if source_id else limit
        vec_rows = self.conn.execute(
            "SELECT rowid, distance FROM vec_chunks WHERE embedding MATCH ? ORDER BY distance LIMIT ?",
            (_serialize(embedding), fetch_n),
        ).fetchall()

        if not vec_rows:
            return []

        rowid_to_dist = {r["rowid"]: r["distance"] for r in vec_rows}
        ph = ",".join("?" * len(rowid_to_dist))
        chunk_rows = self.conn.execute(
            f"SELECT rowid, id, source_id FROM chunks WHERE rowid IN ({ph})",
            list(rowid_to_dist.keys()),
        ).fetchall()

        results: list[tuple[str, float]] = []
        for row in sorted(chunk_rows, key=lambda r: rowid_to_dist[r["rowid"]]):
            if source_id and row["source_id"] != source_id:
                continue
            results.append((row["id"], rowid_to_dist[row["rowid"]]))
            if len(results) >= limit:
                break

        return results

    def fts_search(
        self, query: str, source_id: str | None, limit: int
    ) -> list[tuple[str, float]]:
        fts_query = _build_fts_query(query)
        if not fts_query:
            return []
        try:
            if source_id:
                rows = self.conn.execute(
                    "SELECT id, rank FROM chunks_fts WHERE content MATCH ? AND source_id = ? ORDER BY rank LIMIT ?",
                    (fts_query, source_id, limit),
                ).fetchall()
            else:
                rows = self.conn.execute(
                    "SELECT id, rank FROM chunks_fts WHERE content MATCH ? ORDER BY rank LIMIT ?",
                    (fts_query, limit),
                ).fetchall()
        except sqlite3.OperationalError:
            return []

        return [(r["id"], r["rank"]) for r in rows]

    def get_chunks_by_ids(self, ids: list[str]) -> list[sqlite3.Row]:
        if not ids:
            return []
        ph = ",".join("?" * len(ids))
        return self.conn.execute(
            f"SELECT * FROM chunks WHERE id IN ({ph})", ids
        ).fetchall()

    def get_chunks_by_url(self, url: str) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM chunks WHERE url = ? ORDER BY rowid", (url,)
        ).fetchall()


# ── FTS query builder ─────────────────────────────────────────────────────────

def _build_fts_query(query: str) -> str:
    """Convert natural language query to FTS5 prefix-match format.

    Each word becomes a prefix token (e.g. "avatar models" → "avatar* models*")
    so that "avatars" and "modeling" are matched without stemming.
    FTS5 special characters are stripped to prevent syntax errors.
    """
    tokens = re.findall(r"\w+", query)
    if not tokens:
        return ""
    return " ".join(f"{t}*" for t in tokens)
