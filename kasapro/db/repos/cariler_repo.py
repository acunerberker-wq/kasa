# -*- coding: utf-8 -*-

from __future__ import annotations

import sqlite3
from typing import List, Optional


class CarilerRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def list(self, q: str = "", *, only_active: bool = False) -> List[sqlite3.Row]:
        q = (q or "").strip()
        clauses = []
        params: List[object] = []
        if q:
            clauses.append("ad LIKE ?")
            params.append(f"%{q}%")
        if only_active:
            clauses.append("aktif=1")
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        return list(self.conn.execute(f"SELECT * FROM cariler {where} ORDER BY ad", tuple(params)))

    def get_by_name(self, ad: str) -> Optional[sqlite3.Row]:
        cur = self.conn.execute("SELECT * FROM cariler WHERE ad=?", (ad.strip(),))
        return cur.fetchone()

    def get(self, cid: int) -> Optional[sqlite3.Row]:
        cur = self.conn.execute("SELECT * FROM cariler WHERE id=?", (int(cid),))
        return cur.fetchone()

    def upsert(
        self,
        ad: str,
        tur: str = "",
        telefon: str = "",
        notlar: str = "",
        acilis_bakiye: float = 0.0,
        aktif: int = 1,
    ) -> int:
        ad = (ad or "").strip()
        if not ad:
            raise ValueError("Cari adı boş.")

        ex = self.get_by_name(ad)
        if ex:
            self.conn.execute(
                "UPDATE cariler SET tur=?, telefon=?, notlar=?, acilis_bakiye=?, aktif=? WHERE id=?",
                (tur.strip(), telefon.strip(), notlar.strip(), float(acilis_bakiye), int(aktif), int(ex["id"])),
            )
            self.conn.commit()
            return int(ex["id"])

        self.conn.execute(
            "INSERT INTO cariler(ad,tur,telefon,notlar,acilis_bakiye,aktif) VALUES(?,?,?,?,?,?)",
            (ad, tur.strip(), telefon.strip(), notlar.strip(), float(acilis_bakiye), int(aktif)),
        )
        self.conn.commit()
        return int(self.conn.execute("SELECT last_insert_rowid() id").fetchone()[0])

    def set_active(self, cid: int, aktif: int) -> None:
        """Cariyi aktif/pasif yapar. (0 = aktif değil)"""
        self.conn.execute("UPDATE cariler SET aktif=? WHERE id=?", (int(aktif), int(cid)))
        self.conn.commit()

    def delete(self, cid: int) -> None:
        cur = self.conn.execute("SELECT COUNT(*) FROM cari_hareket WHERE cari_id=?", (int(cid),))
        if int(cur.fetchone()[0]) > 0:
            raise ValueError("Bu carinin hareketleri var. Önce hareketleri silmelisin.")
        self.conn.execute("DELETE FROM cariler WHERE id=?", (int(cid),))
        self.conn.commit()
