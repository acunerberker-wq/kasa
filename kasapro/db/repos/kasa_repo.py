# -*- coding: utf-8 -*-

from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional

from ...utils import parse_date_smart, safe_float


class KasaRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def add(
        self,
        tarih: Any,
        tip: str,
        tutar: float,
        para: str,
        odeme: str,
        kategori: str,
        cari_id: Optional[int],
        aciklama: str,
        belge: str,
        etiket: str,
    ) -> None:
        self.conn.execute(
            """INSERT INTO kasa_hareket(tarih,tip,tutar,para,odeme,kategori,cari_id,aciklama,belge,etiket)
               VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (
                parse_date_smart(tarih),
                tip,
                float(tutar),
                para,
                odeme,
                kategori,
                int(cari_id) if cari_id else None,
                aciklama,
                belge,
                etiket,
            ),
        )
        self.conn.commit()

    def list(
        self,
        q: str = "",
        date_from: str = "",
        date_to: str = "",
        tip: str = "",
        kategori: str = "",
        has_cari: Optional[bool] = None,
    ) -> List[sqlite3.Row]:
        clauses = []
        params: List[Any] = []
        if tip:
            clauses.append("k.tip=?")
            params.append(tip)
        if kategori:
            clauses.append("k.kategori=?")
            params.append(kategori)
        if has_cari is True:
            clauses.append("k.cari_id IS NOT NULL")
        elif has_cari is False:
            clauses.append("k.cari_id IS NULL")
        if (q or "").strip():
            clauses.append("(k.aciklama LIKE ? OR k.kategori LIKE ? OR k.etiket LIKE ? OR k.belge LIKE ?)")
            params += [f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"]
        if (date_from or "").strip():
            clauses.append("k.tarih>=?")
            params.append(parse_date_smart(date_from))
        if (date_to or "").strip():
            clauses.append("k.tarih<=?")
            params.append(parse_date_smart(date_to))
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"""
        SELECT k.*, c.ad cari_ad
        FROM kasa_hareket k
        LEFT JOIN cariler c ON c.id=k.cari_id
        {where}
        ORDER BY k.tarih DESC, k.id DESC
        """
        return list(self.conn.execute(sql, tuple(params)))

    def get(self, kid: int) -> Optional[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM kasa_hareket WHERE id=?", (int(kid),)).fetchone()

    def update(
        self,
        kid: int,
        tarih: Any,
        tip: str,
        tutar: float,
        para: str,
        odeme: str,
        kategori: str,
        cari_id: Optional[int],
        aciklama: str,
        belge: str,
        etiket: str,
    ) -> None:
        self.conn.execute(
            """UPDATE kasa_hareket
               SET tarih=?, tip=?, tutar=?, para=?, odeme=?, kategori=?, cari_id=?, aciklama=?, belge=?, etiket=?
               WHERE id=?""",
            (
                parse_date_smart(tarih),
                tip,
                float(tutar),
                para,
                odeme,
                kategori,
                int(cari_id) if cari_id else None,
                aciklama,
                belge,
                etiket,
                int(kid),
            ),
        )
        self.conn.commit()

    def delete(self, kid: int) -> None:
        self.conn.execute("DELETE FROM kasa_hareket WHERE id=?", (int(kid),))
        self.conn.commit()

    # ---- raporlar ----
    def toplam(self, date_from: str = "", date_to: str = "") -> Dict[str, float]:
        return self._toplam(date_from=date_from, date_to=date_to, has_cari=None)

    def _toplam(self, date_from: str = "", date_to: str = "", has_cari: Optional[bool] = None) -> Dict[str, float]:
        clauses = []
        params: List[Any] = []
        if (date_from or "").strip():
            clauses.append("tarih>=?")
            params.append(parse_date_smart(date_from))
        if (date_to or "").strip():
            clauses.append("tarih<=?")
            params.append(parse_date_smart(date_to))
        if has_cari is True:
            clauses.append("cari_id IS NOT NULL")
        elif has_cari is False:
            clauses.append("cari_id IS NULL")
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        cur = self.conn.execute(
            f"""SELECT
                SUM(CASE WHEN tip='Gelir' THEN tutar ELSE 0 END) gelir,
                SUM(CASE WHEN tip='Gider' THEN tutar ELSE 0 END) gider
               FROM kasa_hareket {where}""",
            tuple(params),
        )
        row = cur.fetchone()
        gelir = safe_float(row[0] if row else 0)
        gider = safe_float(row[1] if row else 0)
        return {"gelir": gelir, "gider": gider, "net": gelir - gider}

    def toplam_filtered(self, date_from: str = "", date_to: str = "", has_cari: Optional[bool] = None) -> Dict[str, float]:
        """toplam() ile aynı ama cari filtresi opsiyonel."""
        return self._toplam(date_from=date_from, date_to=date_to, has_cari=has_cari)

    def gunluk(self, date_from: str, date_to: str, has_cari: Optional[bool] = None) -> List[sqlite3.Row]:
        dfrom = parse_date_smart(date_from)
        dto = parse_date_smart(date_to)
        extra = ""
        params: List[Any] = [dfrom, dto]
        if has_cari is True:
            extra = " AND cari_id IS NOT NULL"
        elif has_cari is False:
            extra = " AND cari_id IS NULL"
        sql = """
        SELECT tarih,
               SUM(CASE WHEN tip='Gelir' THEN tutar ELSE 0 END) gelir,
               SUM(CASE WHEN tip='Gider' THEN tutar ELSE 0 END) gider
        FROM kasa_hareket
        WHERE tarih>=? AND tarih<=?{extra}
        GROUP BY tarih
        ORDER BY tarih DESC
        """
        return list(self.conn.execute(sql.format(extra=extra), tuple(params)))

    def kategori_ozet(self, date_from: str, date_to: str, tip: str = "Gider", has_cari: Optional[bool] = None) -> List[sqlite3.Row]:
        dfrom = parse_date_smart(date_from)
        dto = parse_date_smart(date_to)
        extra = ""
        params: List[Any] = [tip, dfrom, dto]
        if has_cari is True:
            extra = " AND cari_id IS NOT NULL"
        elif has_cari is False:
            extra = " AND cari_id IS NULL"
        sql = """
        SELECT kategori,
               COUNT(*) adet,
               SUM(tutar) toplam
        FROM kasa_hareket
        WHERE tip=? AND tarih>=? AND tarih<=?{extra}
        GROUP BY kategori
        ORDER BY toplam DESC
        """
        return list(self.conn.execute(sql.format(extra=extra), tuple(params)))

    def aylik_ozet(self, limit: int = 24, has_cari: Optional[bool] = None) -> List[sqlite3.Row]:
        """Aylık gelir/gider/net özeti.

        tarih alanı ISO (YYYY-MM-DD) olduğu varsayımıyla substr(tarih,1,7) kullanır.
        """
        try:
            lim = int(limit)
        except Exception:
            lim = 24
        if lim <= 0:
            lim = 24
        extra = ""
        params: List[Any] = []
        if has_cari is True:
            extra = "WHERE cari_id IS NOT NULL"
        elif has_cari is False:
            extra = "WHERE cari_id IS NULL"
        params.append(lim)

        sql = """
        SELECT
            SUBSTR(tarih, 1, 7) AS ay,
            SUM(CASE WHEN tip='Gelir' THEN tutar ELSE 0 END) AS gelir,
            SUM(CASE WHEN tip='Gider' THEN tutar ELSE 0 END) AS gider,
            SUM(CASE WHEN tip='Gelir' THEN tutar ELSE 0 END) - SUM(CASE WHEN tip='Gider' THEN tutar ELSE 0 END) AS net
        FROM kasa_hareket
        {extra}
        GROUP BY SUBSTR(tarih, 1, 7)
        ORDER BY ay DESC
        LIMIT ?
        """
        return list(self.conn.execute(sql.format(extra=extra), tuple(params)))
