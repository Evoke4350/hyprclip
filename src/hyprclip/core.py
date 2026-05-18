from __future__ import annotations

import hashlib
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Clip:
    id: int
    text: str
    mime: str
    created_at: float
    last_used_at: float


class ClipStore:
    def __init__(self, db_path: str | Path, max_items: int = 250):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.max_items = max_items
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS clips (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    digest TEXT NOT NULL UNIQUE,
                    text TEXT NOT NULL,
                    mime TEXT NOT NULL DEFAULT 'text/plain',
                    created_at REAL NOT NULL,
                    last_used_at REAL NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_clips_last_used ON clips(last_used_at DESC)")

    @staticmethod
    def digest(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8", errors="surrogatepass")).hexdigest()

    def add(self, text: str, mime: str = "text/plain") -> int | None:
        text = text.strip("\x00")
        if not text.strip():
            return None
        digest = self.digest(text)
        now = time.time()
        with self._connect() as conn:
            row = conn.execute("SELECT id FROM clips WHERE digest = ?", (digest,)).fetchone()
            if row:
                clip_id = int(row["id"])
                conn.execute("UPDATE clips SET last_used_at = ?, mime = ? WHERE id = ?", (now, mime, clip_id))
            else:
                cur = conn.execute(
                    "INSERT INTO clips(digest, text, mime, created_at, last_used_at) VALUES (?, ?, ?, ?, ?)",
                    (digest, text, mime, now, now),
                )
                clip_id = int(cur.lastrowid)
            self._trim_locked(conn)
            return clip_id

    def get(self, clip_id: int) -> Clip | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM clips WHERE id = ?", (clip_id,)).fetchone()
        return _clip_from_row(row) if row else None

    def touch(self, clip_id: int) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE clips SET last_used_at = ? WHERE id = ?", (time.time(), clip_id))

    def list(self, limit: int = 50, query: str | None = None) -> list[Clip]:
        params: list[object] = []
        where = ""
        if query:
            where = "WHERE lower(text) LIKE ?"
            params.append(f"%{query.lower()}%")
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM clips {where} ORDER BY last_used_at DESC, id DESC LIMIT ?",
                params,
            ).fetchall()
        return [_clip_from_row(row) for row in rows]

    def clear(self) -> int:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM clips")
            return int(cur.rowcount)

    def _trim_locked(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            DELETE FROM clips
            WHERE id NOT IN (
                SELECT id FROM clips ORDER BY last_used_at DESC, id DESC LIMIT ?
            )
            """,
            (self.max_items,),
        )


def _clip_from_row(row: sqlite3.Row) -> Clip:
    return Clip(
        id=int(row["id"]),
        text=str(row["text"]),
        mime=str(row["mime"]),
        created_at=float(row["created_at"]),
        last_used_at=float(row["last_used_at"]),
    )


def truncate_middle(text: str, max_len: int) -> str:
    if max_len < 2:
        return text[:max_len]
    if len(text) <= max_len:
        return text
    keep = max_len - 1
    left = keep // 2
    right = keep - left
    return f"{text[:left]}…{text[-right:]}"


def preview_text(text: str, max_preview: int = 120) -> str:
    return truncate_middle(" ⏎ ".join(line.strip() for line in text.splitlines()), max_preview)


def format_menu_line(clip_id: int, text: str, max_preview: int = 120) -> str:
    return f"{clip_id}\t{preview_text(text, max_preview)}"


def parse_menu_selection(selection: str) -> int:
    first = selection.split("\t", 1)[0].strip()
    if not first.isdigit():
        raise ValueError(f"Invalid clipboard selection: {selection!r}")
    return int(first)
