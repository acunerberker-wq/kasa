# -*- coding: utf-8 -*-

from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional

from ...utils import parse_date_smart, safe_float


class CariHareketRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def add(
        self,
        tarih: Any,
        cari_id: int,
        tip: str,
        tutar: float,
        para: str,
        aciklama: str,
        odeme: str,
        belge: str,
        etiket: str,
    ) -> None:
        self.conn.execute(
            """INSERT INTO cari_hareket(tarih,cari_id,tip,tutar,para,aciklama,odeme,belge,etiket)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (parse_date_smart(tarih), int(cari_id), tip, float(tutar), para, aciklama, odeme, belge, etiket),
        )
        self.conn.commit()

    def list(
        self,
        cari_id: Optional[int] = None,
        q: str = "",
        date_from: str = "",
        date_to: str = "",
    ) -> List[sqlite3.Row]:
        clauses = []
        params: List[Any] = []
        if cari_id:
            clauses.append("h.cari_id=?")
            params.append(int(cari_id))
        if (q or "").strip():
            clauses.append("(c.ad LIKE ? OR h.aciklama LIKE ? OR h.etiket LIKE ? OR h.belge LIKE ?)")
            params += [f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"]
        if (date_from or "").strip():
            clauses.append("h.tarih>=?")
            params.append(parse_date_smart(date_from))
        if (date_to or "").strip():
            clauses.append("h.tarih<=?")
            params.append(parse_date_smart(date_to))
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"""
        SELECT h.*, c.ad cari_ad
        FROM cari_hareket h
        JOIN cariler c ON c.id=h.cari_id
        {where}
        ORDER BY h.tarih DESC, h.id DESC
        """
        return list(self.conn.execute(sql, tuple(params)))

    def get(self, hid: int) -> Optional[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM cari_hareket WHERE id=?", (int(hid),)).fetchone()

    def update(
        self,
        hid: int,
        tarih: Any,
        cari_id: int,
        tip: str,
        tutar: float,
        para: str,
        aciklama: str,
        odeme: str,
        belge: str,
        etiket: str,
    ) -> None:
        self.conn.execute(
            """UPDATE cari_hareket
               SET tarih=?, cari_id=?, tip=?, tutar=?, para=?, aciklama=?, odeme=?, belge=?, etiket=?
               WHERE id=?""",
            (parse_date_smart(tarih), int(cari_id), tip, float(tutar), para, aciklama, odeme, belge, etiket, int(hid)),
        )
        self.conn.commit()

    def delete(self, hid: int) -> None:
        self.conn.execute("DELETE FROM cari_hareket WHERE id=?", (int(hid),))
        self.conn.commit()

    def bakiye(self, cid: int, acilis: float = 0.0) -> Dict[str, float]:
        cur = self.conn.execute(
            """SELECT
                 SUM(CASE WHEN tip='Borç' THEN tutar ELSE 0 END) borc,
                 SUM(CASE WHEN tip='Alacak' THEN tutar ELSE 0 END) alacak
               FROM cari_hareket WHERE cari_id=?""",
            (int(cid),),
        )
        row = cur.fetchone()
        borc = safe_float(row[0] if row else 0)
        alacak = safe_float(row[1] if row else 0)
        return {"borc": borc, "alacak": alacak, "bakiye": (alacak - borc) + float(acilis), "acilis": float(acilis)}

    def ekstre(
        self,
        cid: int,
        acilis: float,
        date_from: str = "",
        date_to: str = "",
        q: str = "",
    ) -> Dict[str, Any]:
        df = parse_date_smart(date_from) if (date_from or "").strip() else ""
        dt = parse_date_smart(date_to) if (date_to or "").strip() else ""

        opening = float(acilis)
        if df:
            cur = self.conn.execute(
                """SELECT
                     SUM(CASE WHEN tip='Borç' THEN tutar ELSE 0 END) borc,
                     SUM(CASE WHEN tip='Alacak' THEN tutar ELSE 0 END) alacak
                   FROM cari_hareket
                   WHERE cari_id=? AND tarih<?""",
                (int(cid), df),
            )
            row = cur.fetchone()
            opening = float(acilis) + (safe_float(row[1] if row else 0) - safe_float(row[0] if row else 0))

        clauses = ["cari_id=?"]
        params: List[Any] = [int(cid)]
        if df:
            clauses.append("tarih>=?")
            params.append(df)
        if dt:
            clauses.append("tarih<=?")
            params.append(dt)
        if (q or "").strip():
            clauses.append("(aciklama LIKE ? OR etiket LIKE ? OR belge LIKE ?)")
            like = f"%{q.strip()}%"
            params += [like, like, like]

        where = " WHERE " + " AND ".join(clauses)
        rows = list(
            self.conn.execute(
                f"""SELECT *
                    FROM cari_hareket
                    {where}
                    ORDER BY tarih ASC, id ASC""",
                tuple(params),
            )
        )

        running = opening
        out_rows: List[Dict[str, Any]] = []
        total_borc = 0.0
        total_alacak = 0.0

        for r in rows:
            tip = (r["tip"] or "").strip()
            tutar = safe_float(r["tutar"])
            borc = tutar if tip == "Borç" else 0.0
            alacak = tutar if tip == "Alacak" else 0.0
            total_borc += borc
            total_alacak += alacak
            running += (alacak - borc)

            out_rows.append(
                {
                    "id": r["id"],
                    "tarih": r["tarih"],
                    "tip": tip,
                    "borc": borc,
                    "alacak": alacak,
                    "tutar": tutar,
                    "para": r["para"] or "TL",
                    "odeme": r["odeme"] or "",
                    "belge": r["belge"] or "",
                    "etiket": r["etiket"] or "",
                    "aciklama": r["aciklama"] or "",
                    "bakiye": running,
                }
            )

        return {
            "opening": opening,
            "closing": running,
            "total_borc": total_borc,
            "total_alacak": total_alacak,
            "net_degisim": (total_alacak - total_borc),
            "rows": out_rows,
            "df": df,
            "dt": dt,
            "q": (q or "").strip(),
        }
