# -*- coding: utf-8 -*-

from __future__ import annotations

import sqlite3


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA busy_timeout = 5000;")
    except Exception:
        pass
    return conn
