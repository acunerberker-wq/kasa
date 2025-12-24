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
            return {"cariler": [], "cari_hareket": [], "kasa": [], "stok_urun": [], "stok_hareket": []}

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

        stok_urun = list(
            self.conn.execute(
                """
                SELECT u.*, c.ad tedarikci_ad
                FROM stok_urun u LEFT JOIN cariler c ON c.id=u.tedarikci_id
                WHERE u.kod LIKE ? OR u.ad LIKE ? OR u.kategori LIKE ? OR u.barkod LIKE ?
                ORDER BY u.ad LIMIT ?""",
                (like, like, like, like, int(limit)),
            )
        )

        stok_hareket = list(
            self.conn.execute(
                """
                SELECT h.*, u.kod urun_kod, u.ad urun_ad
                FROM stok_hareket h JOIN stok_urun u ON u.id=h.urun_id
                WHERE u.kod LIKE ? OR u.ad LIKE ? OR h.tip LIKE ? OR h.aciklama LIKE ?
                ORDER BY h.tarih DESC LIMIT ?""",
                (like, like, like, like, int(limit)),
            )
        )

        return {
            "cariler": cariler,
            "cari_hareket": ch,
            "kasa": kasa,
            "stok_urun": stok_urun,
            "stok_hareket": stok_hareket,
        }
