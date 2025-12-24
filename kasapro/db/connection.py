# -*- coding: utf-8 -*-

from __future__ import annotations

import sqlite3
import threading
from typing import Any


class ConnectionProxy:
    """Proxy that provides a per-thread sqlite3.Connection while
    exposing a connection-like API used by repos (execute, cursor, commit, etc.).

    This avoids using a single sqlite Connection across threads and keeps
    repository code unchanged (they still call `conn.execute(...)`).
    """

    def __init__(self, path: str):
        self.path = path
        self._local = threading.local()

    def _ensure(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.path, check_same_thread=True)
            conn.row_factory = sqlite3.Row
            try:
                conn.execute("PRAGMA foreign_keys = ON;")
                conn.execute("PRAGMA busy_timeout = 5000;")
            except Exception:
                pass
            self._local.conn = conn
        return conn

    def execute(self, *args: Any, **kwargs: Any):
        return self._ensure().execute(*args, **kwargs)

    def executemany(self, *args: Any, **kwargs: Any):
        return self._ensure().executemany(*args, **kwargs)

    def cursor(self, *args: Any, **kwargs: Any):
        return self._ensure().cursor(*args, **kwargs)

    def commit(self):
        return self._ensure().commit()

    def rollback(self):
        return self._ensure().rollback()

    def close(self):
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
            try:
                del self._local.conn
            except Exception:
                pass

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass


def connect(path: str) -> ConnectionProxy:
    """Return a ConnectionProxy for given DB path."""
    return ConnectionProxy(path)
