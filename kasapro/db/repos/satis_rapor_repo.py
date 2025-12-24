# -*- coding: utf-8 -*-

from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Tuple

from ...utils import parse_date_smart, safe_float


def _norm(s: Any) -> str:
    try:
        return str(s or "").strip()
    except Exception:
        return ""


def _like(s: str) -> str:
    return f"%{s}%"


class SatisRaporRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    # -----------------
    # Filtre yardımcıları
    # -----------------
    def _base_filters(
        self,
        filters: Dict[str, Any],
        *,
        include_product: bool = True,
        include_payment: bool = True,
    ) -> Tuple[str, List[Any]]:
        clauses: List[str] = ["f.tur IN ('Satış','İade')"]
        params: List[Any] = []

        durum = _norm(filters.get("durum"))
        if durum and durum != "(Tümü)":
            clauses.append("f.durum=?")
            params.append(durum)

        date_from = _norm(filters.get("date_from"))
        if date_from:
            clauses.append("f.tarih>=?")
            params.append(parse_date_smart(date_from))

        date_to = _norm(filters.get("date_to"))
        if date_to:
            clauses.append("f.tarih<=?")
            params.append(parse_date_smart(date_to))

        cari_id = filters.get("cari_id")
        if cari_id:
            clauses.append("f.cari_id=?")
            params.append(int(cari_id))

        sube = _norm(filters.get("sube"))
        if sube:
            clauses.append("f.sube LIKE ?")
            params.append(_like(sube))

        depo = _norm(filters.get("depo"))
        if depo:
            clauses.append("f.depo LIKE ?")
            params.append(_like(depo))

        temsilci = _norm(filters.get("temsilci"))
        if temsilci:
            clauses.append("f.satis_temsilcisi=?")
            params.append(temsilci)

        if include_product:
            urun = _norm(filters.get("urun"))
            if urun:
                clauses.append(
                    "EXISTS (SELECT 1 FROM fatura_kalem fk WHERE fk.fatura_id=f.id AND fk.urun LIKE ?)"
                )
                params.append(_like(urun))

            kategori = _norm(filters.get("kategori"))
            if kategori:
                clauses.append(
                    "EXISTS (SELECT 1 FROM fatura_kalem fk WHERE fk.fatura_id=f.id AND fk.kategori LIKE ?)"
                )
                params.append(_like(kategori))

        if include_payment:
            odeme = _norm(filters.get("odeme"))
            if odeme:
                clauses.append(
                    "EXISTS (SELECT 1 FROM fatura_odeme fo WHERE fo.fatura_id=f.id AND fo.odeme=?)"
                )
                params.append(odeme)

        where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        return where_sql, params

    def _payment_filters(self, filters: Dict[str, Any]) -> Tuple[str, List[Any]]:
        where_sql, params = self._base_filters(filters, include_payment=False)
        extra_clauses: List[str] = []

        odeme = _norm(filters.get("odeme"))
        if odeme:
            extra_clauses.append("o.odeme=?")
            params.append(odeme)

        date_from = _norm(filters.get("date_from"))
        if date_from:
            extra_clauses.append("o.tarih>=?")
            params.append(parse_date_smart(date_from))

        date_to = _norm(filters.get("date_to"))
        if date_to:
            extra_clauses.append("o.tarih<=?")
            params.append(parse_date_smart(date_to))

        if extra_clauses:
            if where_sql:
                where_sql = f"{where_sql} AND " + " AND ".join(extra_clauses)
            else:
                where_sql = "WHERE " + " AND ".join(extra_clauses)
        return where_sql, params

    # -----------------
    # Liste yardımcıları
    # -----------------
    def list_products(self) -> List[str]:
        rows = self.conn.execute(
            "SELECT DISTINCT urun FROM fatura_kalem WHERE COALESCE(urun,'')<>'' ORDER BY urun"
        ).fetchall()
        return [str(r[0]) for r in rows if r and r[0]]

    def list_categories(self) -> List[str]:
        rows = self.conn.execute(
            "SELECT DISTINCT kategori FROM fatura_kalem WHERE COALESCE(kategori,'')<>'' ORDER BY kategori"
        ).fetchall()
        return [str(r[0]) for r in rows if r and r[0]]

    def list_sube(self) -> List[str]:
        rows = self.conn.execute(
            "SELECT DISTINCT sube FROM fatura WHERE COALESCE(sube,'')<>'' ORDER BY sube"
        ).fetchall()
        return [str(r[0]) for r in rows if r and r[0]]

    def list_depo(self) -> List[str]:
        rows = self.conn.execute(
            "SELECT DISTINCT depo FROM fatura WHERE COALESCE(depo,'')<>'' ORDER BY depo"
        ).fetchall()
        return [str(r[0]) for r in rows if r and r[0]]

    def list_temsilci(self) -> List[str]:
        rows = self.conn.execute(
            "SELECT DISTINCT satis_temsilcisi FROM fatura WHERE COALESCE(satis_temsilcisi,'')<>'' ORDER BY satis_temsilcisi"
        ).fetchall()
        return [str(r[0]) for r in rows if r and r[0]]

    # -----------------
    # Raporlar
    # -----------------
    def daily_summary(self, filters: Dict[str, Any], limit: int, offset: int) -> Dict[str, Any]:
        where_sql, params = self._base_filters(filters)
        sql = f"""
        SELECT
            f.tarih,
            SUM(CASE WHEN f.tur='Satış' THEN f.genel_toplam ELSE 0 END) AS ciro,
            SUM(CASE WHEN f.tur='Satış' THEN f.iskonto_toplam ELSE 0 END) AS iskonto,
            SUM(CASE WHEN f.tur='İade' THEN f.genel_toplam ELSE 0 END) AS iade,
            COUNT(CASE WHEN f.tur='Satış' THEN 1 END) AS satis_adet,
            COUNT(CASE WHEN f.tur='İade' THEN 1 END) AS iade_adet
        FROM fatura f
        {where_sql}
        GROUP BY f.tarih
        ORDER BY f.tarih DESC
        LIMIT ? OFFSET ?
        """
        rows = list(self.conn.execute(sql, tuple(params + [int(limit), int(offset)])))

        count_sql = f"""
        SELECT COUNT(*) FROM (
            SELECT f.tarih
            FROM fatura f
            {where_sql}
            GROUP BY f.tarih
        ) t
        """
        total = int(self.conn.execute(count_sql, tuple(params)).fetchone()[0])

        pay_where, pay_params = self._payment_filters(filters)
        pay_sql = f"""
        SELECT o.tarih, SUM(o.tutar) AS tahsilat
        FROM fatura_odeme o
        JOIN fatura f ON f.id=o.fatura_id
        {pay_where}
        GROUP BY o.tarih
        """
        pay_rows = self.conn.execute(pay_sql, tuple(pay_params)).fetchall()
        payments = {str(r[0]): float(safe_float(r[1])) for r in pay_rows if r}

        out_rows: List[Dict[str, Any]] = []
        for r in rows:
            out_rows.append({
                "tarih": r["tarih"],
                "ciro": float(safe_float(r["ciro"])),
                "iskonto": float(safe_float(r["iskonto"])),
                "iade": float(safe_float(r["iade"])),
                "satis_adet": int(r["satis_adet"] or 0),
                "iade_adet": int(r["iade_adet"] or 0),
                "tahsilat": float(safe_float(payments.get(str(r["tarih"]), 0))),
            })

        return {"rows": out_rows, "total": total}

    def customer_summary(self, filters: Dict[str, Any], limit: int, offset: int) -> Dict[str, Any]:
        where_sql, params = self._base_filters(filters)
        odeme = _norm(filters.get("odeme"))
        pay_clause = "WHERE odeme=?" if odeme else ""
        pay_params = [odeme] if odeme else []

        sql = f"""
        SELECT
            f.cari_id,
            COALESCE(NULLIF(f.cari_ad,''), c.ad, '(Bilinmeyen)') AS cari_ad,
            SUM(CASE WHEN f.tur='Satış' THEN f.genel_toplam ELSE 0 END) AS satis,
            SUM(CASE WHEN f.tur='İade' THEN f.genel_toplam ELSE 0 END) AS iade,
            SUM(CASE WHEN f.tur='Satış' THEN f.iskonto_toplam ELSE 0 END) AS iskonto,
            SUM(COALESCE(p.odendi,0)) AS tahsilat
        FROM fatura f
        LEFT JOIN cariler c ON c.id=f.cari_id
        LEFT JOIN (
            SELECT fatura_id, SUM(tutar) AS odendi
            FROM fatura_odeme
            {pay_clause}
            GROUP BY fatura_id
        ) p ON p.fatura_id=f.id
        {where_sql}
        GROUP BY f.cari_id, cari_ad
        ORDER BY (SUM(CASE WHEN f.tur='Satış' THEN f.genel_toplam ELSE 0 END) -
                  SUM(CASE WHEN f.tur='İade' THEN f.genel_toplam ELSE 0 END)) DESC
        LIMIT ? OFFSET ?
        """
        rows = list(self.conn.execute(sql, tuple(pay_params + params + [int(limit), int(offset)])))

        count_sql = f"""
        SELECT COUNT(*) FROM (
            SELECT f.cari_id
            FROM fatura f
            {where_sql}
            GROUP BY f.cari_id
        ) t
        """
        total = int(self.conn.execute(count_sql, tuple(params)).fetchone()[0])

        out_rows: List[Dict[str, Any]] = []
        for r in rows:
            satis = float(safe_float(r["satis"]))
            iade = float(safe_float(r["iade"]))
            tahsilat = float(safe_float(r["tahsilat"]))
            net = satis - iade
            bakiye = net - tahsilat
            out_rows.append({
                "cari_id": r["cari_id"],
                "cari_ad": r["cari_ad"],
                "satis": satis,
                "iade": iade,
                "iskonto": float(safe_float(r["iskonto"])),
                "tahsilat": tahsilat,
                "net": net,
                "bakiye": bakiye,
            })

        return {"rows": out_rows, "total": total}

    def product_summary(self, filters: Dict[str, Any], limit: int, offset: int) -> Dict[str, Any]:
        where_sql, params = self._base_filters(filters)
        sql = f"""
        SELECT
            fk.urun,
            COALESCE(NULLIF(fk.kategori,''), '(Bilinmeyen)') AS kategori,
            SUM(CASE WHEN f.tur='Satış' THEN fk.miktar ELSE -fk.miktar END) AS miktar,
            SUM(CASE WHEN f.tur='Satış' THEN fk.toplam ELSE -fk.toplam END) AS ciro,
            SUM(CASE WHEN f.tur='Satış' THEN fk.maliyet * fk.miktar ELSE -(fk.maliyet * fk.miktar) END) AS maliyet
        FROM fatura f
        JOIN fatura_kalem fk ON fk.fatura_id=f.id
        {where_sql}
        GROUP BY fk.urun, kategori
        ORDER BY ciro DESC
        LIMIT ? OFFSET ?
        """
        rows = list(self.conn.execute(sql, tuple(params + [int(limit), int(offset)])))

        count_sql = f"""
        SELECT COUNT(*) FROM (
            SELECT fk.urun
            FROM fatura f
            JOIN fatura_kalem fk ON fk.fatura_id=f.id
            {where_sql}
            GROUP BY fk.urun, COALESCE(NULLIF(fk.kategori,''), '(Bilinmeyen)')
        ) t
        """
        total = int(self.conn.execute(count_sql, tuple(params)).fetchone()[0])

        out_rows: List[Dict[str, Any]] = []
        for r in rows:
            ciro = float(safe_float(r["ciro"]))
            maliyet = float(safe_float(r["maliyet"]))
            out_rows.append({
                "urun": r["urun"],
                "kategori": r["kategori"],
                "miktar": float(safe_float(r["miktar"])),
                "ciro": ciro,
                "maliyet": maliyet,
                "kar": ciro - maliyet,
            })

        return {"rows": out_rows, "total": total}

    def temsilci_summary(self, filters: Dict[str, Any], limit: int, offset: int) -> Dict[str, Any]:
        where_sql, params = self._base_filters(filters)
        odeme = _norm(filters.get("odeme"))
        pay_clause = "WHERE odeme=?" if odeme else ""
        pay_params = [odeme] if odeme else []

        sql = f"""
        SELECT
            COALESCE(NULLIF(f.satis_temsilcisi,''), '(Belirsiz)') AS temsilci,
            SUM(CASE WHEN f.tur='Satış' THEN f.genel_toplam ELSE 0 END) AS satis,
            SUM(CASE WHEN f.tur='İade' THEN f.genel_toplam ELSE 0 END) AS iade,
            SUM(CASE WHEN f.tur='Satış' THEN f.iskonto_toplam ELSE 0 END) AS iskonto,
            SUM(COALESCE(p.odendi,0)) AS tahsilat
        FROM fatura f
        LEFT JOIN (
            SELECT fatura_id, SUM(tutar) AS odendi
            FROM fatura_odeme
            {pay_clause}
            GROUP BY fatura_id
        ) p ON p.fatura_id=f.id
        {where_sql}
        GROUP BY temsilci
        ORDER BY satis DESC
        LIMIT ? OFFSET ?
        """
        rows = list(self.conn.execute(sql, tuple(pay_params + params + [int(limit), int(offset)])))

        count_sql = f"""
        SELECT COUNT(*) FROM (
            SELECT COALESCE(NULLIF(f.satis_temsilcisi,''), '(Belirsiz)') AS temsilci
            FROM fatura f
            {where_sql}
            GROUP BY temsilci
        ) t
        """
        total = int(self.conn.execute(count_sql, tuple(params)).fetchone()[0])

        out_rows: List[Dict[str, Any]] = []
        for r in rows:
            satis = float(safe_float(r["satis"]))
            iade = float(safe_float(r["iade"]))
            tahsilat = float(safe_float(r["tahsilat"]))
            net = satis - iade
            bakiye = net - tahsilat
            out_rows.append({
                "temsilci": r["temsilci"],
                "satis": satis,
                "iade": iade,
                "iskonto": float(safe_float(r["iskonto"])),
                "tahsilat": tahsilat,
                "net": net,
                "bakiye": bakiye,
            })

        return {"rows": out_rows, "total": total}

    def kpis(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        where_sql, params = self._base_filters(filters)
        sql = f"""
        SELECT
            SUM(CASE WHEN f.tur='Satış' THEN f.genel_toplam ELSE 0 END) AS ciro,
            SUM(CASE WHEN f.tur='İade' THEN f.genel_toplam ELSE 0 END) AS iade,
            SUM(CASE WHEN f.tur='Satış' THEN f.iskonto_toplam ELSE 0 END) AS iskonto,
            COUNT(CASE WHEN f.tur='Satış' THEN 1 END) AS satis_adet
        FROM fatura f
        {where_sql}
        """
        row = self.conn.execute(sql, tuple(params)).fetchone()
        ciro = float(safe_float(row["ciro"] if row else 0))
        iade = float(safe_float(row["iade"] if row else 0))
        iskonto = float(safe_float(row["iskonto"] if row else 0))
        satis_adet = int(row["satis_adet"] or 0) if row else 0
        net = ciro - iade
        ortalama = (ciro / satis_adet) if satis_adet else 0.0
        iade_oran = (iade / ciro) if ciro else 0.0

        top_products = self.conn.execute(
            f"""
            SELECT fk.urun, SUM(CASE WHEN f.tur='Satış' THEN fk.miktar ELSE -fk.miktar END) AS miktar,
                   SUM(CASE WHEN f.tur='Satış' THEN fk.toplam ELSE -fk.toplam END) AS ciro
            FROM fatura f
            JOIN fatura_kalem fk ON fk.fatura_id=f.id
            {where_sql}
            GROUP BY fk.urun
            ORDER BY ciro DESC
            LIMIT 20
            """,
            tuple(params),
        ).fetchall()

        top_customers = self.conn.execute(
            f"""
            SELECT COALESCE(NULLIF(f.cari_ad,''), c.ad, '(Bilinmeyen)') AS cari_ad,
                   SUM(CASE WHEN f.tur='Satış' THEN f.genel_toplam ELSE 0 END) AS satis,
                   SUM(CASE WHEN f.tur='İade' THEN f.genel_toplam ELSE 0 END) AS iade
            FROM fatura f
            LEFT JOIN cariler c ON c.id=f.cari_id
            {where_sql}
            GROUP BY f.cari_id, cari_ad
            ORDER BY (SUM(CASE WHEN f.tur='Satış' THEN f.genel_toplam ELSE 0 END) -
                      SUM(CASE WHEN f.tur='İade' THEN f.genel_toplam ELSE 0 END)) DESC
            LIMIT 20
            """,
            tuple(params),
        ).fetchall()

        return {
            "ciro": ciro,
            "net_ciro": net,
            "iade": iade,
            "iskonto": iskonto,
            "iade_oran": iade_oran,
            "ortalama_sepet": ortalama,
            "top_products": [
                {
                    "urun": r["urun"],
                    "miktar": float(safe_float(r["miktar"])),
                    "ciro": float(safe_float(r["ciro"])),
                }
                for r in top_products
            ],
            "top_customers": [
                {
                    "cari_ad": r["cari_ad"],
                    "net": float(safe_float(r["satis"])) - float(safe_float(r["iade"])),
                }
                for r in top_customers
            ],
        }

    def data_warnings(self) -> List[str]:
        warnings: List[str] = []

        # Ödeme > toplam
        overpay = self.conn.execute(
            """
            SELECT COUNT(*) AS adet
            FROM (
                SELECT f.id, f.genel_toplam, COALESCE(SUM(o.tutar),0) AS odendi
                FROM fatura f
                LEFT JOIN fatura_odeme o ON o.fatura_id=f.id
                WHERE f.tur IN ('Satış','İade') AND f.durum<>'İptal'
                GROUP BY f.id
                HAVING odendi > f.genel_toplam + 0.01
            ) t
            """
        ).fetchone()
        if overpay and int(overpay["adet"] or 0) > 0:
            warnings.append(f"Toplamı aşan tahsilat/ödeme: {int(overpay['adet'])} fatura.")

        # Kalem toplamı eşleşmiyor
        mismatch = self.conn.execute(
            """
            SELECT COUNT(*) AS adet
            FROM (
                SELECT f.id, f.genel_toplam, COALESCE(SUM(k.toplam),0) AS kalem_toplam
                FROM fatura f
                LEFT JOIN fatura_kalem k ON k.fatura_id=f.id
                WHERE f.tur IN ('Satış','İade') AND f.durum<>'İptal'
                GROUP BY f.id
                HAVING ABS(COALESCE(SUM(k.toplam),0) - f.genel_toplam) > 0.01
            ) t
            """
        ).fetchone()
        if mismatch and int(mismatch["adet"] or 0) > 0:
            warnings.append(f"Kalem toplamı ile genel toplam uyuşmayan: {int(mismatch['adet'])} fatura.")

        # Cari bilgisi eksik
        missing_cari = self.conn.execute(
            """
            SELECT COUNT(*) AS adet
            FROM fatura
            WHERE tur IN ('Satış','İade') AND durum<>'İptal' AND (cari_id IS NULL OR cari_id=0) AND COALESCE(cari_ad,'')=''
            """
        ).fetchone()
        if missing_cari and int(missing_cari["adet"] or 0) > 0:
            warnings.append(f"Cari bilgisi eksik: {int(missing_cari['adet'])} fatura.")

        # Sevkiyat bağlantısı
        sevk_count = self.conn.execute(
            "SELECT COUNT(*) AS adet FROM stok_hareket WHERE COALESCE(referans_tipi,'') LIKE '%Fatura%'"
        ).fetchone()
        if not sevk_count or int(sevk_count["adet"] or 0) == 0:
            warnings.append("Sevkiyat verisi fatura ile ilişkilendirilmemiş görünüyor.")

        return warnings
