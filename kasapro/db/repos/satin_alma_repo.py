# -*- coding: utf-8 -*-

from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional

from ...utils import parse_date_smart


class SatinAlmaRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def siparis_list(
        self,
        tedarikci_id: Optional[int] = None,
        durum: str = "",
        date_from: str = "",
        date_to: str = "",
        depo_id: Optional[int] = None,
        urun_id: Optional[int] = None,
        limit: int = 20000,
    ) -> List[sqlite3.Row]:
        clauses: List[str] = []
        params: List[Any] = []
        join_kalem = ""

        if tedarikci_id:
            clauses.append("s.tedarikci_id=?")
            params.append(int(tedarikci_id))
        if (durum or "").strip() and durum != "(Tümü)":
            clauses.append("s.durum=?")
            params.append(str(durum))
        if depo_id:
            clauses.append("s.depo_id=?")
            params.append(int(depo_id))
        if (date_from or "").strip():
            clauses.append("s.tarih>=?")
            params.append(parse_date_smart(date_from))
        if (date_to or "").strip():
            clauses.append("s.tarih<=?")
            params.append(parse_date_smart(date_to))
        if urun_id:
            join_kalem = "JOIN satin_alma_siparis_kalem k ON k.siparis_id=s.id"
            clauses.append("k.urun_id=?")
            params.append(int(urun_id))

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"""
        SELECT DISTINCT s.*, c.ad tedarikci_ad, d.ad depo_ad
        FROM satin_alma_siparis s
        LEFT JOIN cariler c ON c.id=s.tedarikci_id
        LEFT JOIN stok_lokasyon d ON d.id=s.depo_id
        {join_kalem}
        {where}
        ORDER BY s.tarih DESC, s.id DESC
        LIMIT ?
        """
        params.append(int(limit))
        return list(self.conn.execute(sql, tuple(params)))

    def siparis_kalem_totals(self, siparis_ids: List[int]) -> Dict[int, Dict[str, float]]:
        if not siparis_ids:
            return {}
        placeholders = ",".join(["?"] * len(siparis_ids))
        sql = f"""
        SELECT siparis_id,
               SUM(miktar) miktar,
               SUM(toplam) toplam,
               SUM(iskonto_tutar) iskonto
        FROM satin_alma_siparis_kalem
        WHERE siparis_id IN ({placeholders})
        GROUP BY siparis_id
        """
        out: Dict[int, Dict[str, float]] = {}
        for r in self.conn.execute(sql, tuple(int(x) for x in siparis_ids)):
            out[int(r["siparis_id"])] = {
                "miktar": float(r["miktar"] or 0),
                "toplam": float(r["toplam"] or 0),
                "iskonto": float(r["iskonto"] or 0),
            }
        return out

    def teslim_summary_by_siparis(self, siparis_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        if not siparis_ids:
            return {}
        placeholders = ",".join(["?"] * len(siparis_ids))
        sql = f"""
        SELECT t.siparis_id,
               MAX(t.tarih) last_tarih,
               SUM(k.miktar) miktar,
               SUM(k.toplam) toplam
        FROM satin_alma_teslim t
        LEFT JOIN satin_alma_teslim_kalem k ON k.teslim_id=t.id
        WHERE t.siparis_id IN ({placeholders})
        GROUP BY t.siparis_id
        """
        out: Dict[int, Dict[str, Any]] = {}
        for r in self.conn.execute(sql, tuple(int(x) for x in siparis_ids)):
            out[int(r["siparis_id"])] = {
                "last_tarih": str(r["last_tarih"] or ""),
                "miktar": float(r["miktar"] or 0),
                "toplam": float(r["toplam"] or 0),
            }
        return out

    def teslim_list(
        self,
        tedarikci_id: Optional[int] = None,
        date_from: str = "",
        date_to: str = "",
        depo_id: Optional[int] = None,
        limit: int = 20000,
    ) -> List[sqlite3.Row]:
        clauses: List[str] = []
        params: List[Any] = []

        if tedarikci_id:
            clauses.append("s.tedarikci_id=?")
            params.append(int(tedarikci_id))
        if depo_id:
            clauses.append("t.depo_id=?")
            params.append(int(depo_id))
        if (date_from or "").strip():
            clauses.append("t.tarih>=?")
            params.append(parse_date_smart(date_from))
        if (date_to or "").strip():
            clauses.append("t.tarih<=?")
            params.append(parse_date_smart(date_to))

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"""
        SELECT t.*, s.siparis_no, s.tedarikci_id, c.ad tedarikci_ad,
               f.fatura_no, f.durum fatura_durum, d.ad depo_ad
        FROM satin_alma_teslim t
        LEFT JOIN satin_alma_siparis s ON s.id=t.siparis_id
        LEFT JOIN cariler c ON c.id=s.tedarikci_id
        LEFT JOIN fatura f ON f.id=t.fatura_id
        LEFT JOIN stok_lokasyon d ON d.id=t.depo_id
        {where}
        ORDER BY t.tarih DESC, t.id DESC
        LIMIT ?
        """
        params.append(int(limit))
        return list(self.conn.execute(sql, tuple(params)))
