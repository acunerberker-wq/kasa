# -*- coding: utf-8 -*-

from __future__ import annotations

import sqlite3
from typing import List

from ...utils import now_iso


class LogsRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def log(self, islem: str, detay: str = "") -> None:
        self.conn.execute(
            "INSERT INTO logs(ts,islem,detay) VALUES(?,?,?)",
            (now_iso(), islem, detay or ""),
        )
        self.conn.commit()

    def list(self, limit: int = 800) -> List[sqlite3.Row]:
        return list(self.conn.execute("SELECT * FROM logs ORDER BY id DESC LIMIT ?", (int(limit),)))
