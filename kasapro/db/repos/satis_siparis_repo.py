# -*- coding: utf-8 -*-

from __future__ import annotations

import sqlite3
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ...utils import parse_date_smart, safe_float


class SatisSiparisRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def _has_table(self, name: str) -> bool:
        try:
            row = self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (name,),
            ).fetchone()
            return row is not None
        except Exception:
            return False

    def _build_filters(
        self,
        customer: str = "",
        representative: str = "",
        depot_id: Optional[int] = None,
        status: str = "",
        date_from: str = "",
        date_to: str = "",
        statuses: Optional[Iterable[str]] = None,
    ) -> Tuple[str, List[Any]]:
        clauses: List[str] = []
        params: List[Any] = []
        if statuses:
            statuses = list(statuses)
            placeholders = ",".join(["?"] * len(statuses))
            clauses.append(f"s.durum IN ({placeholders})")
            params.extend(statuses)
        if (status or "").strip() and status != "(Tümü)":
            clauses.append("s.durum=?")
            params.append(status)
        if (customer or "").strip():
            clauses.append("(c.ad LIKE ? OR s.cari_ad LIKE ?)")
            params.append(f"%{customer.strip()}%")
            params.append(f"%{customer.strip()}%")
        if (representative or "").strip():
            clauses.append("s.temsilci LIKE ?")
            params.append(f"%{representative.strip()}%")
        if depot_id:
            clauses.append("s.depo_id=?")
            params.append(int(depot_id))
        if (date_from or "").strip():
            clauses.append("s.tarih>=?")
            params.append(parse_date_smart(date_from))
        if (date_to or "").strip():
            clauses.append("s.tarih<=?")
            params.append(parse_date_smart(date_to))
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        return where, params

    def _list_orders(
        self,
        customer: str = "",
        representative: str = "",
        depot_id: Optional[int] = None,
        status: str = "",
        date_from: str = "",
        date_to: str = "",
        statuses: Optional[Iterable[str]] = None,
    ) -> List[sqlite3.Row]:
        where, params = self._build_filters(
            customer=customer,
            representative=representative,
            depot_id=depot_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
            statuses=statuses,
        )
        sql = f"""
        SELECT s.*,
               COALESCE(c.ad, s.cari_ad) cari_ad,
               l.ad depo_ad
        FROM satis_siparis s
        LEFT JOIN cariler c ON c.id=s.cari_id
        LEFT JOIN stok_lokasyon l ON l.id=s.depo_id
        {where}
        ORDER BY s.tarih DESC, s.id DESC
        """
        return list(self.conn.execute(sql, tuple(params)))

    def _list_items_for_orders(self, order_ids: List[int]) -> List[sqlite3.Row]:
        if not order_ids:
            return []
        placeholders = ",".join(["?"] * len(order_ids))
        sql = f"""
        SELECT k.*
        FROM satis_siparis_kalem k
        WHERE k.siparis_id IN ({placeholders})
        ORDER BY k.siparis_id, k.id
        """
        return list(self.conn.execute(sql, tuple(order_ids)))

    def _stock_totals(self, urun_ids: List[int]) -> Dict[int, float]:
        if not urun_ids:
            return {}
        placeholders = ",".join(["?"] * len(urun_ids))
        sql = f"""
        SELECT urun_id,
               SUM(CASE
                   WHEN tip IN ('Giris','Uretim') THEN miktar
                   WHEN tip IN ('Cikis','Fire') THEN -miktar
                   WHEN tip IN ('Sayim','Duzeltme') THEN miktar
                   ELSE 0
               END) toplam
        FROM stok_hareket
        WHERE urun_id IN ({placeholders})
        GROUP BY urun_id
        """
        out: Dict[int, float] = {}
        for r in self.conn.execute(sql, tuple(urun_ids)):
            try:
                out[int(r["urun_id"])] = safe_float(r["toplam"])
            except Exception:
                continue
        return out

    def rapor_acik_siparisler(self, filters: Dict[str, Any], open_statuses: List[str]) -> Dict[str, Any]:
        rows = self._list_orders(statuses=open_statuses, **filters)
        grouped: Dict[str, Dict[str, Any]] = {}
        total = 0.0
        for r in rows:
            cari = str(r["cari_ad"] or "(Belirtilmemiş)")
            tutar = safe_float(r["toplam"])
            total += tutar
            if cari not in grouped:
                grouped[cari] = {"cari": cari, "adet": 0, "toplam": 0.0}
            grouped[cari]["adet"] += 1
            grouped[cari]["toplam"] += tutar
        grouped_rows = sorted(grouped.values(), key=lambda x: x["toplam"], reverse=True)
        return {"rows": grouped_rows, "order_count": len(rows), "total": total}

    def rapor_sevkiyata_hazir(self, filters: Dict[str, Any], status_pool: List[str]) -> Dict[str, Any]:
        orders = self._list_orders(statuses=status_pool, **filters)
        order_ids = [int(r["id"]) for r in orders]
        items = self._list_items_for_orders(order_ids)
        item_map: Dict[int, List[sqlite3.Row]] = {}
        urun_ids: List[int] = []
        for item in items:
            oid = int(item["siparis_id"])
            item_map.setdefault(oid, []).append(item)
            try:
                if item["urun_id"]:
                    urun_ids.append(int(item["urun_id"]))
            except Exception:
                continue
        has_stock = self._has_table("stok_urun") and self._has_table("stok_hareket")
        stock_totals = self._stock_totals(sorted(set(urun_ids))) if has_stock else {}

        report_rows: List[Dict[str, Any]] = []
        for order in orders:
            oid = int(order["id"])
            order_items = item_map.get(oid, [])
            remaining = 0.0
            status = "Bilinmiyor"
            if not has_stock:
                status = "Kontrol Yok"
            else:
                status = "Yeterli"
            for item in order_items:
                miktar = safe_float(item["miktar"])
                sevk_miktar = safe_float(item["sevk_miktar"])
                kalan = max(0.0, miktar - sevk_miktar)
                remaining += kalan
                urun_id = item["urun_id"]
                if not has_stock:
                    continue
                if not urun_id:
                    status = "Kısmi Kontrol"
                    continue
                mevcut = stock_totals.get(int(urun_id), 0.0)
                if mevcut < kalan:
                    status = "Yetersiz"
            if status in ("Yeterli", "Kısmi Kontrol", "Kontrol Yok"):
                report_rows.append({
                    "siparis_no": order["siparis_no"],
                    "tarih": order["tarih"],
                    "cari": order["cari_ad"] or "",
                    "temsilci": order["temsilci"] or "",
                    "depo": order["depo_ad"] or "",
                    "durum": order["durum"] or "",
                    "kalan": remaining,
                    "para": order["para"] or "TL",
                    "toplam": safe_float(order["toplam"]),
                    "stok_durum": status,
                })
        return {"rows": report_rows, "order_count": len(report_rows)}

    def rapor_kismi_sevk(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        orders = self._list_orders(**filters)
        order_ids = [int(r["id"]) for r in orders]
        items = self._list_items_for_orders(order_ids)
        order_map = {int(r["id"]): r for r in orders}
        report_rows: List[Dict[str, Any]] = []
        for item in items:
            miktar = safe_float(item["miktar"])
            sevk_miktar = safe_float(item["sevk_miktar"])
            kalan = max(0.0, miktar - sevk_miktar)
            if sevk_miktar <= 0 or kalan <= 0:
                continue
            order = order_map.get(int(item["siparis_id"]))
            if not order:
                continue
            report_rows.append({
                "siparis_no": order["siparis_no"],
                "tarih": order["tarih"],
                "cari": order["cari_ad"] or "",
                "urun": item["urun_ad"] or "",
                "miktar": miktar,
                "sevk": sevk_miktar,
                "kalan": kalan,
                "birim": item["birim"] or "",
                "durum": order["durum"] or "",
            })
        return {"rows": report_rows, "order_count": len(report_rows)}

    def rapor_donusum(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        where, params = self._build_filters(**filters)
        sql = f"""
        SELECT s.*,
               COALESCE(c.ad, s.cari_ad) cari_ad,
               l.ad depo_ad,
               f.fatura_no fatura_no,
               f.tarih fatura_tarih
        FROM satis_siparis s
        LEFT JOIN cariler c ON c.id=s.cari_id
        LEFT JOIN stok_lokasyon l ON l.id=s.depo_id
        LEFT JOIN fatura f ON f.id=s.fatura_id
        {where}
        ORDER BY s.tarih DESC, s.id DESC
        """
        rows = []
        for r in self.conn.execute(sql, tuple(params)):
            rows.append({
                "siparis_no": r["siparis_no"],
                "tarih": r["tarih"],
                "cari": r["cari_ad"] or "",
                "temsilci": r["temsilci"] or "",
                "depo": r["depo_ad"] or "",
                "durum": r["durum"] or "",
                "sevk_no": r["sevk_no"] or "",
                "sevk_tarih": r["sevk_tarih"] or "",
                "fatura_no": r["fatura_no"] or "",
                "fatura_tarih": r["fatura_tarih"] or "",
                "toplam": safe_float(r["toplam"]),
                "para": r["para"] or "TL",
            })
        return {"rows": rows, "order_count": len(rows)}

    def acik_siparis_ozet(self, open_statuses: List[str]) -> Dict[str, Any]:
        rows = self._list_orders(statuses=open_statuses)
        total = sum(safe_float(r["toplam"]) for r in rows)
        return {"adet": len(rows), "toplam": total}
