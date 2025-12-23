# -*- coding: utf-8 -*-

from __future__ import annotations

import sqlite3
from typing import Dict, List


class SearchRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def global_search(self, q: str, limit: int = 300) -> Dict[str, List[sqlite3.Row]]:
        q = (q or "").strip()
        if not q:
            return {"cariler": [], "cari_hareket": [], "kasa": []}

        like = f"%{q}%"

        cariler = list(
            self.conn.execute(
                "SELECT * FROM cariler WHERE ad LIKE ? OR telefon LIKE ? OR notlar LIKE ? ORDER BY ad LIMIT ?",
                (like, like, like, int(limit)),
            )
        )

        ch = list(
            self.conn.execute(
                """
                SELECT h.*, c.ad cari_ad
                FROM cari_hareket h JOIN cariler c ON c.id=h.cari_id
                WHERE c.ad LIKE ? OR h.aciklama LIKE ? OR h.etiket LIKE ? OR h.belge LIKE ?
                ORDER BY h.tarih DESC LIMIT ?""",
                (like, like, like, like, int(limit)),
            )
        )

        kasa = list(
            self.conn.execute(
                """
                SELECT k.*, c.ad cari_ad
                FROM kasa_hareket k LEFT JOIN cariler c ON c.id=k.cari_id
                WHERE k.aciklama LIKE ? OR k.kategori LIKE ? OR k.etiket LIKE ? OR k.belge LIKE ?
                ORDER BY k.tarih DESC LIMIT ?""",
                (like, like, like, like, int(limit)),
            )
        )

        return {"cariler": cariler, "cari_hareket": ch, "kasa": kasa}
