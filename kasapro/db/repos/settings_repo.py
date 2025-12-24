# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import re
import sqlite3
from typing import List, Optional, Callable

from ...config import (
    DEFAULT_CURRENCIES,
    DEFAULT_PAYMENTS,
    DEFAULT_CATEGORIES,
    DEFAULT_STOCK_UNITS,
    DEFAULT_STOCK_CATEGORIES,
)


class SettingsRepo:
    def __init__(self, conn: sqlite3.Connection, log_fn: Optional[Callable[[str, str], None]] = None):
        self.conn = conn
        self.log_fn = log_fn

    def get(self, key: str) -> Optional[str]:
        cur = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,))
        row = cur.fetchone()
        return row[0] if row else None

    def set(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        self.conn.commit()

    def _get_list(self, key: str, default: List[str]) -> List[str]:
        s = self.get(key)
        if not s:
            return default[:]
        try:
            v = json.loads(s)
            if isinstance(v, list) and v:
                return [str(x) for x in v]
        except Exception:
            pass
        return default[:]

    def list_currencies(self) -> List[str]:
        return self._get_list("currencies", DEFAULT_CURRENCIES)

    def list_payments(self) -> List[str]:
        return self._get_list("payments", DEFAULT_PAYMENTS)

    def list_categories(self) -> List[str]:
        return self._get_list("categories", DEFAULT_CATEGORIES)

    def list_stock_units(self) -> List[str]:
        return self._get_list("stock_units", DEFAULT_STOCK_UNITS)

    def list_stock_categories(self) -> List[str]:
        return self._get_list("stock_categories", DEFAULT_STOCK_CATEGORIES)

    def _scan_max_belge_seq(self) -> int:
        maxn = 0
        try:
            for table in ("kasa_hareket", "cari_hareket"):
                for row in self.conn.execute(
                    f"SELECT belge FROM {table} WHERE belge IS NOT NULL AND TRIM(belge) <> ''"
                ):
                    b = str(row[0] if row else "").strip()
                    if not b:
                        continue
                    m = re.search(r"(\d+)\s*$", b)
                    if m:
                        try:
                            maxn = max(maxn, int(m.group(1)))
                        except Exception:
                            pass
        except Exception:
            pass
        return maxn

    def next_belge_no(self, prefix: str = "BLG") -> str:
        prefix = (prefix or "BLG").strip().upper()
        prefix = re.sub(r"[^A-Z0-9]+", "", prefix)[:6] or "BLG"

        key = "belge_seq_global"
        cur = self.get(key)
        if cur and str(cur).strip().isdigit():
            seq = int(str(cur).strip())
        else:
            seq = self._scan_max_belge_seq()

        seq += 1
        self.set(key, str(seq))
        return f"{prefix}-{seq:06d}"
