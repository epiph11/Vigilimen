"""The edge's durable queue: SQLite in WAL mode, the AUTHORITY for what has not reached the broker (ADR-020 point 7).

A message leaves the queue only when the broker has acknowledged it (ack). After a reconnect the edge replays
what is still in the queue, in seq order, and the consumer de-duplicates on (edge_id, seq).

The queue is bounded. When it is full the OLDEST BASELINE message goes first (a baseline is a periodic repeat; an
exception is a change someone may need), and only if there is no baseline left the oldest exception. Every drop
is counted in the database and reported through `on_drop`: loss is visible, never silent.

`seq` comes from a counter kept in the database, in the same transaction as the insert, so it is strictly
increasing across restarts and never reused even when the queue is empty.

Not in this file: the MQTT connection, the OPC UA reads, the choice of what to publish (reporter.py).
"""

from __future__ import annotations

import sqlite3
import threading
from typing import Callable

KINDS = ("baseline", "exception")


class EdgeQueue:
    _synchronous = "FULL"                       # a power cut must not lose an acknowledged enqueue

    def __init__(self, path: str, max_items: int = 20000, on_drop: Callable[[int, str], None] | None = None):
        self.max_items = max_items
        self.on_drop = on_drop
        self._lock = threading.Lock()
        self.db = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute(f"PRAGMA synchronous={self._synchronous}")
        self.db.execute("CREATE TABLE IF NOT EXISTS msg (seq INTEGER PRIMARY KEY, topic TEXT NOT NULL, payload BLOB NOT NULL,"
                        " kind TEXT NOT NULL CHECK (kind IN ('baseline','exception')))")
        self.db.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value INTEGER NOT NULL)")
        for k in ("next_seq", "dropped_baseline", "dropped_exception"):
            self.db.execute("INSERT OR IGNORE INTO meta VALUES (?, ?)", (k, 1 if k == "next_seq" else 0))

    # -- small hooks (each one is a decision FF-39 can break on purpose) --------------------------------
    def _alloc_seq(self) -> int:
        return self._meta("next_seq")

    def _payload_seq(self, seq: int) -> int:
        return seq

    def _enforce_bound(self) -> list[tuple[int, str]]:
        dropped = []
        while self.db.execute("SELECT COUNT(*) FROM msg").fetchone()[0] > self.max_items:
            v = self._victim()
            self.db.execute("DELETE FROM msg WHERE seq=?", (v[0],))
            self._count_drop(v[1])
            dropped.append(v)
        return dropped

    def _victim(self) -> tuple[int, str]:
        row = self.db.execute("SELECT seq, kind FROM msg WHERE kind='baseline' ORDER BY seq LIMIT 1").fetchone()
        return row or self.db.execute("SELECT seq, kind FROM msg ORDER BY seq LIMIT 1").fetchone()

    def _count_drop(self, kind: str) -> None:
        self.db.execute("UPDATE meta SET value = value + 1 WHERE key=?", (f"dropped_{kind}",))

    def _order(self) -> str:
        return "ASC"

    # -- API ---------------------------------------------------------------------------------------------
    def _meta(self, key: str) -> int:
        return self.db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()[0]

    def enqueue(self, kind: str, topic: str, make_payload: Callable[[int], bytes]) -> int:
        if kind not in KINDS:
            raise ValueError(f"kind {kind!r}: baseline or exception")
        with self._lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                seq = self._alloc_seq()
                self.db.execute("INSERT INTO msg VALUES (?,?,?,?)", (seq, topic, make_payload(self._payload_seq(seq)), kind))
                self.db.execute("UPDATE meta SET value=? WHERE key='next_seq'", (seq + 1,))
                dropped = self._enforce_bound()
                self.db.execute("COMMIT")
            except Exception:
                self.db.execute("ROLLBACK")
                raise
        for seq_d, kind_d in dropped:
            if self.on_drop:
                self.on_drop(seq_d, kind_d)
        return seq

    def peek(self, after_seq: int = 0, limit: int = 100) -> list[tuple[int, str, bytes, str]]:
        with self._lock:
            return self.db.execute(f"SELECT seq, topic, payload, kind FROM msg WHERE seq>? ORDER BY seq {self._order()} LIMIT ?",
                                   (after_seq, limit)).fetchall()

    def ack(self, seq: int) -> bool:
        with self._lock:
            return self.db.execute("DELETE FROM msg WHERE seq=?", (seq,)).rowcount == 1

    def stats(self) -> dict:
        with self._lock:
            return {"depth": self.db.execute("SELECT COUNT(*) FROM msg").fetchone()[0], "next_seq": self._meta("next_seq"),
                    "dropped_baseline": self._meta("dropped_baseline"), "dropped_exception": self._meta("dropped_exception")}

    def pragmas(self) -> tuple[str, int]:
        return (self.db.execute("PRAGMA journal_mode").fetchone()[0], self.db.execute("PRAGMA synchronous").fetchone()[0])

    def close(self) -> None:
        self.db.close()
