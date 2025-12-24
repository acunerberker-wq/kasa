# -*- coding: utf-8 -*-

from __future__ import annotations

import sqlite3
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from ...utils import parse_date_smart, safe_float


class PurchaseReportRepo:
    """Satın alma hareketleri raporu için sorgular."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def list_suppliers(self) -> List[sqlite3.Row]:
        return list(self.conn.execute("SELECT id, ad FROM cariler WHERE aktif=1 ORDER BY ad"))

    def list_products(self) -> List[str]:
        out: List[str] = []
        try:
            rows = self.conn.execute(
                "SELECT DISTINCT urun FROM fatura_kalem WHERE COALESCE(urun,'')<>'' ORDER BY urun"
            ).fetchall()
            out.extend([str(r[0]) for r in rows if r and r[0]])
        except Exception:
            pass
        try:
            rows = self.conn.execute(
                "SELECT DISTINCT ad FROM stok_urun WHERE COALESCE(ad,'')<>'' ORDER BY ad"
            ).fetchall()
            for r in rows:
                v = str(r[0]) if r and r[0] else ""
                if v and v not in out:
                    out.append(v)
        except Exception:
            pass
        return out

    def list_categories(self) -> List[str]:
        rows = self.conn.execute(
            "SELECT DISTINCT kategori FROM stok_urun WHERE COALESCE(kategori,'')<>'' ORDER BY kategori"
        ).fetchall()
        return [str(r[0]) for r in rows if r and r[0]]

    def list_locations(self) -> List[sqlite3.Row]:
        return list(self.conn.execute("SELECT id, ad FROM stok_lokasyon WHERE aktif=1 ORDER BY ad"))

    def list_users(self) -> List[sqlite3.Row]:
        return list(self.conn.execute("SELECT id, username FROM users ORDER BY username"))

    def fetch_report(
        self,
        *,
        date_from: str = "",
        date_to: str = "",
        supplier_id: Optional[int] = None,
        product_name: str = "",
        category: str = "",
        payment_type: str = "",
        location_id: Optional[int] = None,
        include_stock_entries: bool = True,
    ) -> Dict[str, Any]:
        """Rapor datasını getirir."""
        df = parse_date_smart(date_from) if date_from else ""
        dt = parse_date_smart(date_to) if date_to else ""

        movements: List[Dict[str, Any]] = []
        movements.extend(
            self._fetch_invoice_items(df, dt, supplier_id, product_name, category)
        )
        movements.extend(
            self._fetch_expenses(df, dt, supplier_id, category, payment_type)
        )
        movements.extend(
            self._fetch_payments(df, dt, supplier_id, payment_type)
        )
        if include_stock_entries:
            movements.extend(
                self._fetch_stock_entries(df, dt, supplier_id, product_name, category, location_id)
            )

        movements.sort(key=lambda r: (r.get("tarih") or "", r.get("kaynak") or ""))

        summary = self._build_summary(movements)
        kpis = self._build_kpis(df, dt, supplier_id, product_name, category)

        return {
            "filters": {
                "date_from": df,
                "date_to": dt,
                "supplier_id": supplier_id,
                "product_name": product_name,
                "category": category,
                "payment_type": payment_type,
                "location_id": location_id,
                "include_stock_entries": include_stock_entries,
            },
            "summary": summary,
            "movements": movements,
            "kpis": kpis,
        }

    def _date_clause(self, col: str, df: str, dt: str, params: List[Any]) -> str:
        clauses: List[str] = []
        if df:
            clauses.append(f"{col}>=?")
            params.append(df)
        if dt:
            clauses.append(f"{col}<=?")
            params.append(dt)
        return (" AND " + " AND ".join(clauses)) if clauses else ""

    def _fetch_invoice_items(
        self,
        df: str,
        dt: str,
        supplier_id: Optional[int],
        product_name: str,
        category: str,
    ) -> List[Dict[str, Any]]:
        params: List[Any] = []
        where = "WHERE f.tur IN ('Alış','İade') AND f.durum!='İptal'"
        where += self._date_clause("f.tarih", df, dt, params)
        if supplier_id:
            where += " AND f.cari_id=?"
            params.append(int(supplier_id))
        if product_name:
            where += " AND k.urun=?"
            params.append(product_name)
        if category:
            where += " AND su.kategori=?"
            params.append(category)

        sql = f"""
            SELECT
                f.id AS fatura_id,
                f.tarih,
                f.tur,
                f.fatura_no,
                f.cari_id,
                f.cari_ad,
                f.para,
                k.urun,
                k.miktar,
                k.birim,
                k.birim_fiyat,
                k.iskonto_tutar,
                k.kdv_tutar,
                k.toplam,
                su.kategori
            FROM fatura f
            JOIN fatura_kalem k ON k.fatura_id=f.id
            LEFT JOIN stok_urun su ON su.ad=k.urun
            {where}
            ORDER BY f.tarih DESC, f.id DESC
        """
        out: List[Dict[str, Any]] = []
        for r in self.conn.execute(sql, tuple(params)):
            sign = -1 if str(r["tur"]) == "İade" else 1
            out.append(
                {
                    "kaynak": "Fatura",
                    "hareket": str(r["tur"]),
                    "tarih": r["tarih"],
                    "belge": r["fatura_no"],
                    "tedarikci_id": r["cari_id"],
                    "tedarikci": r["cari_ad"],
                    "urun": r["urun"],
                    "kategori": r["kategori"],
                    "odeme": "",
                    "depo": "",
                    "miktar": safe_float(r["miktar"]) * sign,
                    "birim": r["birim"],
                    "tutar": safe_float(r["toplam"]) * sign,
                    "kdv": safe_float(r["kdv_tutar"]) * sign,
                    "iskonto": safe_float(r["iskonto_tutar"]) * sign,
                    "para": r["para"],
                }
            )
        return out

    def _fetch_expenses(
        self,
        df: str,
        dt: str,
        supplier_id: Optional[int],
        category: str,
        payment_type: str,
    ) -> List[Dict[str, Any]]:
        params: List[Any] = []
        where = "WHERE k.tip='Gider'"
        where += self._date_clause("k.tarih", df, dt, params)
        if supplier_id:
            where += " AND k.cari_id=?"
            params.append(int(supplier_id))
        if category:
            where += " AND k.kategori=?"
            params.append(category)
        if payment_type:
            where += " AND k.odeme=?"
            params.append(payment_type)

        sql = f"""
            SELECT
                k.id,
                k.tarih,
                k.tutar,
                k.para,
                k.odeme,
                k.kategori,
                k.belge,
                c.id AS cari_id,
                c.ad AS cari_ad
            FROM kasa_hareket k
            LEFT JOIN cariler c ON c.id=k.cari_id
            {where}
            ORDER BY k.tarih DESC, k.id DESC
        """
        out: List[Dict[str, Any]] = []
        for r in self.conn.execute(sql, tuple(params)):
            out.append(
                {
                    "kaynak": "Kasa",
                    "hareket": "Gider",
                    "tarih": r["tarih"],
                    "belge": r["belge"],
                    "tedarikci_id": r["cari_id"],
                    "tedarikci": r["cari_ad"],
                    "urun": "",
                    "kategori": r["kategori"],
                    "odeme": r["odeme"],
                    "depo": "",
                    "miktar": 0,
                    "birim": "",
                    "tutar": safe_float(r["tutar"]),
                    "kdv": 0.0,
                    "iskonto": 0.0,
                    "para": r["para"],
                }
            )
        return out

    def _fetch_payments(
        self,
        df: str,
        dt: str,
        supplier_id: Optional[int],
        payment_type: str,
    ) -> List[Dict[str, Any]]:
        params: List[Any] = []
        where = "WHERE f.tur IN ('Alış','İade') AND f.durum!='İptal'"
        where += self._date_clause("o.tarih", df, dt, params)
        if supplier_id:
            where += " AND f.cari_id=?"
            params.append(int(supplier_id))
        if payment_type:
            where += " AND o.odeme=?"
            params.append(payment_type)

        sql = f"""
            SELECT
                o.id,
                o.tarih,
                o.tutar,
                o.para,
                o.odeme,
                f.tur,
                f.fatura_no,
                f.cari_id,
                f.cari_ad
            FROM fatura_odeme o
            JOIN fatura f ON f.id=o.fatura_id
            {where}
            ORDER BY o.tarih DESC, o.id DESC
        """
        out: List[Dict[str, Any]] = []
        for r in self.conn.execute(sql, tuple(params)):
            sign = -1 if str(r["tur"]) == "İade" else 1
            out.append(
                {
                    "kaynak": "Ödeme",
                    "hareket": "Ödeme",
                    "tarih": r["tarih"],
                    "belge": r["fatura_no"],
                    "tedarikci_id": r["cari_id"],
                    "tedarikci": r["cari_ad"],
                    "urun": "",
                    "kategori": "",
                    "odeme": r["odeme"],
                    "depo": "",
                    "miktar": 0,
                    "birim": "",
                    "tutar": safe_float(r["tutar"]) * sign,
                    "kdv": 0.0,
                    "iskonto": 0.0,
                    "para": r["para"],
                }
            )
        return out

    def _fetch_stock_entries(
        self,
        df: str,
        dt: str,
        supplier_id: Optional[int],
        product_name: str,
        category: str,
        location_id: Optional[int],
    ) -> List[Dict[str, Any]]:
        params: List[Any] = []
        where = "WHERE h.tip='Giris'"
        where += self._date_clause("h.tarih", df, dt, params)
        if supplier_id:
            where += " AND u.tedarikci_id=?"
            params.append(int(supplier_id))
        if product_name:
            where += " AND u.ad=?"
            params.append(product_name)
        if category:
            where += " AND u.kategori=?"
            params.append(category)
        if location_id:
            where += " AND h.hedef_lokasyon_id=?"
            params.append(int(location_id))

        sql = f"""
            SELECT
                h.id,
                h.tarih,
                h.miktar,
                h.birim,
                h.maliyet,
                u.ad AS urun,
                u.kategori,
                u.tedarikci_id,
                c.ad AS tedarikci_ad,
                l.ad AS depo
            FROM stok_hareket h
            JOIN stok_urun u ON u.id=h.urun_id
            LEFT JOIN cariler c ON c.id=u.tedarikci_id
            LEFT JOIN stok_lokasyon l ON l.id=h.hedef_lokasyon_id
            {where}
            ORDER BY h.tarih DESC, h.id DESC
        """
        out: List[Dict[str, Any]] = []
        for r in self.conn.execute(sql, tuple(params)):
            miktar = safe_float(r["miktar"])
            maliyet = safe_float(r["maliyet"])
            out.append(
                {
                    "kaynak": "Stok",
                    "hareket": "Stok Girişi",
                    "tarih": r["tarih"],
                    "belge": "",
                    "tedarikci_id": r["tedarikci_id"],
                    "tedarikci": r["tedarikci_ad"],
                    "urun": r["urun"],
                    "kategori": r["kategori"],
                    "odeme": "",
                    "depo": r["depo"],
                    "miktar": miktar,
                    "birim": r["birim"],
                    "tutar": miktar * maliyet if maliyet else 0.0,
                    "kdv": 0.0,
                    "iskonto": 0.0,
                    "para": "",
                }
            )
        return out

    def _build_summary(self, movements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        def period_key(dt_str: str, period: str) -> str:
            try:
                d = date.fromisoformat(dt_str)
            except Exception:
                return dt_str
            if period == "haftalik":
                return f"{d.isocalendar().year}-W{d.isocalendar().week:02d}"
            if period == "aylik":
                return f"{d.year}-{d.month:02d}"
            return d.strftime("%Y-%m-%d")

        summary: Dict[str, Dict[str, float]] = {}
        for m in movements:
            for period in ("gunluk", "haftalik", "aylik"):
                key = (period, period_key(str(m.get("tarih") or ""), period))
                bucket = summary.setdefault(key, {"alis": 0.0, "iade": 0.0, "gider": 0.0, "odeme": 0.0})
                hareket = str(m.get("hareket") or "")
                tutar = safe_float(m.get("tutar"))
                if hareket == "Alış":
                    bucket["alis"] += tutar
                elif hareket == "İade":
                    bucket["iade"] += abs(tutar)
                elif hareket == "Gider":
                    bucket["gider"] += tutar
                elif hareket == "Ödeme":
                    bucket["odeme"] += tutar
                elif hareket == "Stok Girişi":
                    bucket["alis"] += tutar

        out: List[Dict[str, Any]] = []
        for (period, key), totals in summary.items():
            net = totals["alis"] - totals["iade"] + totals["gider"]
            out.append(
                {
                    "period": period,
                    "key": key,
                    "alis": totals["alis"],
                    "iade": totals["iade"],
                    "gider": totals["gider"],
                    "odeme": totals["odeme"],
                    "net": net,
                }
            )
        return out

    def _build_kpis(
        self,
        df: str,
        dt: str,
        supplier_id: Optional[int],
        product_name: str,
        category: str,
    ) -> Dict[str, Any]:
        params: List[Any] = []
        where = "WHERE f.tur IN ('Alış','İade') AND f.durum!='İptal'"
        where += self._date_clause("f.tarih", df, dt, params)
        if supplier_id:
            where += " AND f.cari_id=?"
            params.append(int(supplier_id))

        sql = f"""
            SELECT
                SUM(CASE WHEN f.tur='İade' THEN -f.genel_toplam ELSE f.genel_toplam END) AS toplam,
                SUM(CASE WHEN f.tur='İade' THEN -f.kdv_toplam ELSE f.kdv_toplam END) AS kdv,
                SUM(CASE WHEN f.tur='İade' THEN -f.iskonto_toplam ELSE f.iskonto_toplam END) AS iskonto
            FROM fatura f
            {where}
        """
        row = self.conn.execute(sql, tuple(params)).fetchone()
        toplam = safe_float(row["toplam"] if row else 0.0)
        kdv = safe_float(row["kdv"] if row else 0.0)
        iskonto = safe_float(row["iskonto"] if row else 0.0)

        avg_cost, qty = self._avg_unit_cost(df, dt, supplier_id, product_name, category)
        top_products = self._top_products(df, dt, supplier_id, product_name, category)
        top_suppliers = self._top_suppliers(df, dt, supplier_id, product_name, category)

        return {
            "toplam": toplam,
            "kdv": kdv,
            "iskonto": iskonto,
            "avg_birim_maliyet": avg_cost,
            "top_products": top_products,
            "top_suppliers": top_suppliers,
            "qty": qty,
        }

    def _avg_unit_cost(
        self,
        df: str,
        dt: str,
        supplier_id: Optional[int],
        product_name: str,
        category: str,
    ) -> Tuple[float, float]:
        params: List[Any] = []
        where = "WHERE f.tur IN ('Alış','İade') AND f.durum!='İptal'"
        where += self._date_clause("f.tarih", df, dt, params)
        if supplier_id:
            where += " AND f.cari_id=?"
            params.append(int(supplier_id))
        if product_name:
            where += " AND k.urun=?"
            params.append(product_name)
        if category:
            where += " AND su.kategori=?"
            params.append(category)

        sql = f"""
            SELECT
                SUM(CASE WHEN f.tur='İade' THEN -k.miktar ELSE k.miktar END) AS qty,
                SUM(CASE WHEN f.tur='İade' THEN -(k.ara_tutar - k.iskonto_tutar) ELSE (k.ara_tutar - k.iskonto_tutar) END) AS total
            FROM fatura f
            JOIN fatura_kalem k ON k.fatura_id=f.id
            LEFT JOIN stok_urun su ON su.ad=k.urun
            {where}
        """
        row = self.conn.execute(sql, tuple(params)).fetchone()
        qty = safe_float(row["qty"] if row else 0.0)
        total = safe_float(row["total"] if row else 0.0)
        avg = (total / qty) if qty else 0.0
        return avg, qty

    def _top_products(
        self,
        df: str,
        dt: str,
        supplier_id: Optional[int],
        product_name: str,
        category: str,
    ) -> List[Dict[str, Any]]:
        params: List[Any] = []
        where = "WHERE f.tur IN ('Alış','İade') AND f.durum!='İptal'"
        where += self._date_clause("f.tarih", df, dt, params)
        if supplier_id:
            where += " AND f.cari_id=?"
            params.append(int(supplier_id))
        if product_name:
            where += " AND k.urun=?"
            params.append(product_name)
        if category:
            where += " AND su.kategori=?"
            params.append(category)

        sql = f"""
            SELECT
                k.urun AS urun,
                SUM(CASE WHEN f.tur='İade' THEN -k.miktar ELSE k.miktar END) AS qty,
                SUM(CASE WHEN f.tur='İade' THEN -k.toplam ELSE k.toplam END) AS total
            FROM fatura f
            JOIN fatura_kalem k ON k.fatura_id=f.id
            LEFT JOIN stok_urun su ON su.ad=k.urun
            {where}
            GROUP BY k.urun
            ORDER BY total DESC
            LIMIT 20
        """
        out: List[Dict[str, Any]] = []
        for r in self.conn.execute(sql, tuple(params)):
            out.append({"urun": r["urun"], "qty": safe_float(r["qty"]), "total": safe_float(r["total"])})
        return out

    def _top_suppliers(
        self,
        df: str,
        dt: str,
        supplier_id: Optional[int],
        product_name: str,
        category: str,
    ) -> List[Dict[str, Any]]:
        params: List[Any] = []
        where = "WHERE f.tur IN ('Alış','İade') AND f.durum!='İptal'"
        where += self._date_clause("f.tarih", df, dt, params)
        if supplier_id:
            where += " AND f.cari_id=?"
            params.append(int(supplier_id))

        join = ""
        if product_name or category:
            join = "JOIN fatura_kalem k ON k.fatura_id=f.id LEFT JOIN stok_urun su ON su.ad=k.urun"
            if product_name:
                where += " AND k.urun=?"
                params.append(product_name)
            if category:
                where += " AND su.kategori=?"
                params.append(category)
        sql = f"""
            SELECT
                f.cari_ad AS tedarikci,
                SUM(CASE WHEN f.tur='İade' THEN -f.genel_toplam ELSE f.genel_toplam END) AS total
            FROM fatura f
            {join}
            {where}
            GROUP BY f.cari_ad
            ORDER BY total DESC
            LIMIT 20
        """
        out: List[Dict[str, Any]] = []
        for r in self.conn.execute(sql, tuple(params)):
            out.append({"tedarikci": r["tedarikci"], "total": safe_float(r["total"])})
        return out
