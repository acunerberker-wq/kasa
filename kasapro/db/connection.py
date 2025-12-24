# -*- coding: utf-8 -*-

from __future__ import annotations

import sqlite3


def connect(path: str) -> sqlite3.Connection:
    # Allow using the same connection from worker threads (UI spawns threads)
    # Note: this makes the connection usable across threads; ensure higher-level
    # synchronization if concurrent writes are possible.
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA busy_timeout = 5000;")
    except Exception:
        pass
    return conn
