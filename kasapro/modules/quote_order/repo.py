# -*- coding: utf-8 -*-

from __future__ import annotations

import sqlite3
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ...utils import now_iso


class QuoteOrderRepo:
    def __init__(self, conn: sqlite3.Connection, log_fn=None):
        self.conn = conn
        self.log_fn = log_fn

    def _log(self, islem: str, detay: str = "") -> None:
        if not self.log_fn:
            return
        try:
            self.log_fn(islem, detay)
        except Exception:
            pass

    def next_series_no(
        self,
        name: str,
        prefix: str,
        padding: int = 6,
        fmt: str = "{prefix}{no_pad}",
    ) -> str:
        try:
            self.conn.execute("BEGIN IMMEDIATE")
            self.conn.execute(
                "INSERT OR IGNORE INTO series_counters(name,prefix,last_no,padding,format) VALUES(?,?,?,?,?)",
                (name, prefix, 0, int(padding), fmt),
            )
            row = self.conn.execute(
                "SELECT last_no,prefix,padding,format FROM series_counters WHERE name=?",
                (name,),
            ).fetchone()
            last_no = int(row["last_no"] if row else 0) + 1
            self.conn.execute(
                "UPDATE series_counters SET last_no=? WHERE name=?",
                (last_no, name),
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        no_pad = str(last_no).zfill(int(row["padding"]))
        return str(row["format"]).format(prefix=row["prefix"], no=last_no, no_pad=no_pad)

    def insert_quote(self, payload: Dict[str, Any]) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO quotes(
                quote_no, version, status, quote_group_id, cari_id, cari_ad, valid_until,
                para, kur, ara_toplam, iskonto_toplam, genel_iskonto_oran,
                genel_iskonto_tutar, kdv_toplam, genel_toplam, notlar, locked,
                created_at, updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                payload["quote_no"],
                int(payload.get("version", 1)),
                payload.get("status", "DRAFT"),
                payload.get("quote_group_id"),
                payload.get("cari_id"),
                payload.get("cari_ad", ""),
                payload.get("valid_until", ""),
                payload.get("para", "TL"),
                float(payload.get("kur", 1)),
                float(payload.get("ara_toplam", 0)),
                float(payload.get("iskonto_toplam", 0)),
                float(payload.get("genel_iskonto_oran", 0)),
                float(payload.get("genel_iskonto_tutar", 0)),
                float(payload.get("kdv_toplam", 0)),
                float(payload.get("genel_toplam", 0)),
                payload.get("notlar", ""),
                int(payload.get("locked", 0)),
                payload.get("created_at", now_iso()),
                payload.get("updated_at", now_iso()),
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def update_quote(self, quote_id: int, payload: Dict[str, Any]) -> None:
        current = self.get_quote(quote_id)
        if not current:
            raise ValueError("quote bulunamadı")

        fields = [
            "status",
            "quote_group_id",
            "cari_id",
            "cari_ad",
            "valid_until",
            "para",
            "kur",
            "ara_toplam",
            "iskonto_toplam",
            "genel_iskonto_oran",
            "genel_iskonto_tutar",
            "kdv_toplam",
            "genel_toplam",
            "notlar",
            "locked",
            "updated_at",
        ]
        values = [
            payload.get("status", current["status"]),
            payload.get("quote_group_id", current["quote_group_id"]),
            payload.get("cari_id", current["cari_id"]),
            payload.get("cari_ad", current["cari_ad"]),
            payload.get("valid_until", current["valid_until"]),
            payload.get("para", current["para"]),
            payload.get("kur", current["kur"]),
            payload.get("ara_toplam", current["ara_toplam"]),
            payload.get("iskonto_toplam", current["iskonto_toplam"]),
            payload.get("genel_iskonto_oran", current["genel_iskonto_oran"]),
            payload.get("genel_iskonto_tutar", current["genel_iskonto_tutar"]),
            payload.get("kdv_toplam", current["kdv_toplam"]),
            payload.get("genel_toplam", current["genel_toplam"]),
            payload.get("notlar", current["notlar"]),
            payload.get("locked", current["locked"]),
            payload.get("updated_at", now_iso()),
            int(quote_id),
        ]
        sql = "UPDATE quotes SET " + ",".join(f"{f}=?" for f in fields) + " WHERE id=?"
        self.conn.execute(sql, values)
        self.conn.commit()

    def insert_quote_lines(self, quote_id: int, lines: Iterable[Dict[str, Any]]) -> None:
        rows = []
        for idx, line in enumerate(lines, start=1):
            rows.append(
                (
                    int(quote_id),
                    int(line.get("line_no", idx)),
                    line.get("urun", ""),
                    line.get("aciklama", ""),
                    float(line.get("miktar", 0)),
                    line.get("birim", "Adet"),
                    float(line.get("birim_fiyat", 0)),
                    float(line.get("iskonto_oran", 0)),
                    float(line.get("iskonto_tutar", 0)),
                    float(line.get("kdv_oran", 0)),
                    float(line.get("kdv_tutar", 0)),
                    float(line.get("toplam", 0)),
                )
            )
        if not rows:
            return
        self.conn.executemany(
            """
            INSERT INTO quote_lines(
                quote_id, line_no, urun, aciklama, miktar, birim, birim_fiyat,
                iskonto_oran, iskonto_tutar, kdv_oran, kdv_tutar, toplam
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            rows,
        )
        self.conn.commit()

    def replace_quote_lines(self, quote_id: int, lines: Iterable[Dict[str, Any]]) -> None:
        self.conn.execute("DELETE FROM quote_lines WHERE quote_id=?", (int(quote_id),))
        self.conn.commit()
        self.insert_quote_lines(quote_id, lines)

    def get_quote(self, quote_id: int) -> Optional[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM quotes WHERE id=?", (int(quote_id),)).fetchone()

    def get_quote_lines(self, quote_id: int) -> List[sqlite3.Row]:
        cur = self.conn.execute(
            "SELECT * FROM quote_lines WHERE quote_id=? ORDER BY line_no", (int(quote_id),)
        )
        return list(cur.fetchall())

    def get_quote_versions(self, quote_no: str) -> List[sqlite3.Row]:
        cur = self.conn.execute(
            "SELECT * FROM quotes WHERE quote_no=? ORDER BY version", (quote_no,)
        )
        return list(cur.fetchall())

    def list_quotes(self, q: str = "", status: str = "", limit: int = 50, offset: int = 0) -> List[sqlite3.Row]:
        sql = "SELECT * FROM quotes WHERE 1=1"
        args: List[Any] = []
        if q:
            sql += " AND (quote_no LIKE ? OR cari_ad LIKE ?)"
            like = f"%{q}%"
            args.extend([like, like])
        if status:
            sql += " AND status=?"
            args.append(status)
        sql += " ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?"
        args.extend([int(limit), int(offset)])
        cur = self.conn.execute(sql, args)
        return list(cur.fetchall())

    def count_quotes(self, q: str = "", status: str = "") -> int:
        sql = "SELECT COUNT(*) FROM quotes WHERE 1=1"
        args: List[Any] = []
        if q:
            sql += " AND (quote_no LIKE ? OR cari_ad LIKE ?)"
            like = f"%{q}%"
            args.extend([like, like])
        if status:
            sql += " AND status=?"
            args.append(status)
        cur = self.conn.execute(sql, args)
        row = cur.fetchone()
        return int(row[0]) if row else 0

    def update_quote_status(self, quote_id: int, status: str, locked: Optional[int] = None) -> None:
        if locked is None:
            self.conn.execute(
                "UPDATE quotes SET status=?, updated_at=? WHERE id=?",
                (status, now_iso(), int(quote_id)),
            )
        else:
            self.conn.execute(
                "UPDATE quotes SET status=?, locked=?, updated_at=? WHERE id=?",
                (status, int(locked), now_iso(), int(quote_id)),
            )
        self.conn.commit()

    def expire_quotes(self, today: str) -> int:
        cur = self.conn.execute(
            """
            UPDATE quotes
            SET status='EXPIRED', updated_at=?
            WHERE valid_until <> ''
              AND valid_until < ?
              AND status NOT IN ('CONVERTED','REJECTED','EXPIRED')
            """,
            (now_iso(), today),
        )
        self.conn.commit()
        return int(cur.rowcount or 0)

    def insert_order(self, payload: Dict[str, Any]) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO sales_orders(
                order_no, quote_id, status, cari_id, cari_ad, para, kur,
                ara_toplam, iskonto_toplam, kdv_toplam, genel_toplam, notlar,
                created_at, updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                payload["order_no"],
                payload.get("quote_id"),
                payload.get("status", "DRAFT"),
                payload.get("cari_id"),
                payload.get("cari_ad", ""),
                payload.get("para", "TL"),
                float(payload.get("kur", 1)),
                float(payload.get("ara_toplam", 0)),
                float(payload.get("iskonto_toplam", 0)),
                float(payload.get("kdv_toplam", 0)),
                float(payload.get("genel_toplam", 0)),
                payload.get("notlar", ""),
                payload.get("created_at", now_iso()),
                payload.get("updated_at", now_iso()),
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def insert_order_lines(self, order_id: int, lines: Iterable[Dict[str, Any]]) -> None:
        rows = []
        for idx, line in enumerate(lines, start=1):
            rows.append(
                (
                    int(order_id),
                    int(line.get("line_no", idx)),
                    line.get("urun", ""),
                    line.get("aciklama", ""),
                    float(line.get("miktar_siparis", line.get("miktar", 0))),
                    float(line.get("miktar_sevk", 0)),
                    float(line.get("miktar_fatura", 0)),
                    line.get("birim", "Adet"),
                    float(line.get("birim_fiyat", 0)),
                    float(line.get("iskonto_oran", 0)),
                    float(line.get("iskonto_tutar", 0)),
                    float(line.get("kdv_oran", 0)),
                    float(line.get("kdv_tutar", 0)),
                    float(line.get("toplam", 0)),
                )
            )
        if not rows:
            return
        self.conn.executemany(
            """
            INSERT INTO sales_order_lines(
                order_id, line_no, urun, aciklama, miktar_siparis, miktar_sevk,
                miktar_fatura, birim, birim_fiyat, iskonto_oran, iskonto_tutar,
                kdv_oran, kdv_tutar, toplam
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            rows,
        )
        self.conn.commit()

    def get_order(self, order_id: int) -> Optional[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM sales_orders WHERE id=?", (int(order_id),)
        ).fetchone()

    def get_order_lines(self, order_id: int) -> List[sqlite3.Row]:
        cur = self.conn.execute(
            "SELECT * FROM sales_order_lines WHERE order_id=? ORDER BY line_no",
            (int(order_id),),
        )
        return list(cur.fetchall())

    def list_orders(self, q: str = "", status: str = "", limit: int = 50, offset: int = 0) -> List[sqlite3.Row]:
        sql = "SELECT * FROM sales_orders WHERE 1=1"
        args: List[Any] = []
        if q:
            sql += " AND (order_no LIKE ? OR cari_ad LIKE ?)"
            like = f"%{q}%"
            args.extend([like, like])
        if status:
            sql += " AND status=?"
            args.append(status)
        sql += " ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?"
        args.extend([int(limit), int(offset)])
        cur = self.conn.execute(sql, args)
        return list(cur.fetchall())

    def count_orders(self, q: str = "", status: str = "") -> int:
        sql = "SELECT COUNT(*) FROM sales_orders WHERE 1=1"
        args: List[Any] = []
        if q:
            sql += " AND (order_no LIKE ? OR cari_ad LIKE ?)"
            like = f"%{q}%"
            args.extend([like, like])
        if status:
            sql += " AND status=?"
            args.append(status)
        cur = self.conn.execute(sql, args)
        row = cur.fetchone()
        return int(row[0]) if row else 0

    def update_order_status(self, order_id: int, status: str) -> None:
        self.conn.execute(
            "UPDATE sales_orders SET status=?, updated_at=? WHERE id=?",
            (status, now_iso(), int(order_id)),
        )
        self.conn.commit()

    def add_audit(
        self,
        entity_type: str,
        entity_id: int,
        action: str,
        user_id: Optional[int],
        username: str,
        role: str,
        note: str = "",
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO audit_log(entity_type, entity_id, action, user_id, username, role, note)
            VALUES(?,?,?,?,?,?,?)
            """,
            (entity_type, int(entity_id), action, user_id, username, role, note),
        )
        self.conn.commit()

    def list_audit(self, entity_type: str, entity_id: int) -> List[sqlite3.Row]:
        cur = self.conn.execute(
            "SELECT * FROM audit_log WHERE entity_type=? AND entity_id=? ORDER BY ts",
            (entity_type, int(entity_id)),
        )
        return list(cur.fetchall())
