# -*- coding: utf-8 -*-

from __future__ import annotations

import sqlite3
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from ...utils import now_iso, parse_date_smart


class TradeRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def ensure_default_warehouse(self, company_id: int) -> int:
        row = self.conn.execute(
            "SELECT id FROM trade_warehouses WHERE company_id=? ORDER BY id LIMIT 1",
            (int(company_id),),
        ).fetchone()
        if row:
            return int(row[0])
        self.conn.execute(
            "INSERT INTO trade_warehouses(company_id, name, created_at) VALUES(?,?,?)",
            (int(company_id), "Ana Depo", now_iso()),
        )
        self.conn.commit()
        return int(
            self.conn.execute(
                "SELECT id FROM trade_warehouses WHERE company_id=? ORDER BY id LIMIT 1",
                (int(company_id),),
            ).fetchone()[0]
        )

    def list_warehouses(self, company_id: int) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT * FROM trade_warehouses WHERE company_id=? ORDER BY name",
                (int(company_id),),
            )
        )

    def create_doc(
        self,
        company_id: int,
        doc_type: str,
        doc_no: str,
        doc_date: Any,
        status: str,
        cari_id: Optional[int],
        cari_name: str,
        currency: str,
        subtotal: float,
        tax_total: float,
        discount_total: float,
        total: float,
        notes: str = "",
        related_doc_id: Optional[int] = None,
        order_id: Optional[int] = None,
    ) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO trade_docs(
                company_id, doc_type, doc_no, doc_date, status,
                cari_id, cari_name, currency, subtotal, tax_total, discount_total, total,
                notes, related_doc_id, order_id, created_at, updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                int(company_id),
                doc_type,
                doc_no,
                parse_date_smart(doc_date),
                status,
                None if cari_id is None else int(cari_id),
                cari_name,
                currency,
                float(subtotal),
                float(tax_total),
                float(discount_total),
                float(total),
                notes,
                None if related_doc_id is None else int(related_doc_id),
                None if order_id is None else int(order_id),
                now_iso(),
                now_iso(),
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def add_doc_lines(self, doc_id: int, lines: Iterable[Dict[str, Any]]) -> None:
        payload = []
        for line in lines:
            payload.append(
                (
                    int(doc_id),
                    str(line.get("item") or ""),
                    str(line.get("description") or ""),
                    float(line.get("qty") or 0),
                    str(line.get("unit") or "Adet"),
                    float(line.get("unit_price") or 0),
                    float(line.get("tax_rate") or 0),
                    float(line.get("line_total") or 0),
                    float(line.get("tax_total") or 0),
                )
            )
        self.conn.executemany(
            """
            INSERT INTO trade_doc_lines(
                doc_id, item, description, qty, unit, unit_price, tax_rate, line_total, tax_total
            ) VALUES(?,?,?,?,?,?,?,?,?)
            """,
            payload,
        )
        self.conn.commit()

    def list_docs(
        self,
        company_id: int,
        doc_type: Optional[str] = None,
        status: Optional[str] = None,
        q: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> List[sqlite3.Row]:
        clauses = ["company_id=?"]
        params: List[Any] = [int(company_id)]
        if doc_type:
            clauses.append("doc_type=?")
            params.append(doc_type)
        if status:
            clauses.append("status=?")
            params.append(status)
        if (q or "").strip():
            clauses.append("(doc_no LIKE ? OR cari_name LIKE ?)")
            like = f"%{q.strip()}%"
            params.extend([like, like])
        where = " AND ".join(clauses)
        sql = f"""
            SELECT * FROM trade_docs
            WHERE {where}
            ORDER BY doc_date DESC, id DESC
            LIMIT ? OFFSET ?
        """
        params.extend([int(limit), int(offset)])
        return list(self.conn.execute(sql, tuple(params)))

    def get_doc(self, doc_id: int) -> Optional[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM trade_docs WHERE id=?", (int(doc_id),)).fetchone()

    def list_doc_lines(self, doc_id: int) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT * FROM trade_doc_lines WHERE doc_id=? ORDER BY id", (int(doc_id),)
            )
        )

    def update_doc_status(self, doc_id: int, status: str) -> None:
        self.conn.execute(
            "UPDATE trade_docs SET status=?, updated_at=? WHERE id=?",
            (status, now_iso(), int(doc_id)),
        )
        self.conn.commit()

    def create_stock_move(
        self,
        company_id: int,
        doc_id: Optional[int],
        line_id: Optional[int],
        item: str,
        qty: float,
        unit: str,
        direction: str,
        warehouse_id: Optional[int],
        move_type: str,
        note: str = "",
    ) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO trade_stock_moves(
                company_id, doc_id, line_id, item, qty, unit, direction,
                warehouse_id, move_type, note, created_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                int(company_id),
                None if doc_id is None else int(doc_id),
                None if line_id is None else int(line_id),
                item,
                float(qty),
                unit,
                direction,
                None if warehouse_id is None else int(warehouse_id),
                move_type,
                note,
                now_iso(),
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def list_stock_summary(
        self,
        company_id: int,
        q: str = "",
        limit: int = 200,
        offset: int = 0,
    ) -> List[sqlite3.Row]:
        clauses = ["company_id=?"]
        params: List[Any] = [int(company_id)]
        if (q or "").strip():
            clauses.append("item LIKE ?")
            params.append(f"%{q.strip()}%")
        where = " AND ".join(clauses)
        sql = f"""
            SELECT item,
                   SUM(CASE WHEN direction='IN' THEN qty ELSE -qty END) AS balance
            FROM trade_stock_moves
            WHERE {where}
            GROUP BY item
            ORDER BY item
            LIMIT ? OFFSET ?
        """
        params.extend([int(limit), int(offset)])
        return list(self.conn.execute(sql, tuple(params)))

    def create_payment(
        self,
        company_id: int,
        doc_id: Optional[int],
        date: Any,
        direction: str,
        amount: float,
        currency: str,
        method: str,
        reference: str,
        kasa_hareket_id: Optional[int],
        banka_hareket_id: Optional[int],
        notes: str,
    ) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO trade_payments(
                company_id, doc_id, pay_date, direction, amount, currency, method,
                reference, kasa_hareket_id, banka_hareket_id, notes, created_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                int(company_id),
                None if doc_id is None else int(doc_id),
                parse_date_smart(date),
                direction,
                float(amount),
                currency,
                method,
                reference,
                None if kasa_hareket_id is None else int(kasa_hareket_id),
                None if banka_hareket_id is None else int(banka_hareket_id),
                notes,
                now_iso(),
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def list_payments(self, doc_id: int) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT * FROM trade_payments WHERE doc_id=? ORDER BY pay_date DESC",
                (int(doc_id),),
            )
        )

    def create_order(
        self,
        company_id: int,
        order_type: str,
        order_no: str,
        order_date: Any,
        status: str,
        cari_id: Optional[int],
        cari_name: str,
        currency: str,
        total: float,
        notes: str = "",
    ) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO trade_orders(
                company_id, order_type, order_no, order_date, status,
                cari_id, cari_name, currency, total, notes, created_at, updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                int(company_id),
                order_type,
                order_no,
                parse_date_smart(order_date),
                status,
                None if cari_id is None else int(cari_id),
                cari_name,
                currency,
                float(total),
                notes,
                now_iso(),
                now_iso(),
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def add_order_lines(self, order_id: int, lines: Iterable[Dict[str, Any]]) -> None:
        payload = []
        for line in lines:
            payload.append(
                (
                    int(order_id),
                    str(line.get("item") or ""),
                    float(line.get("qty") or 0),
                    float(line.get("fulfilled_qty") or 0),
                    str(line.get("unit") or "Adet"),
                    float(line.get("unit_price") or 0),
                    float(line.get("line_total") or 0),
                )
            )
        self.conn.executemany(
            """
            INSERT INTO trade_order_lines(
                order_id, item, qty, fulfilled_qty, unit, unit_price, line_total
            ) VALUES(?,?,?,?,?,?,?)
            """,
            payload,
        )
        self.conn.commit()

    def list_orders(
        self,
        company_id: int,
        order_type: Optional[str] = None,
        status: Optional[str] = None,
        q: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> List[sqlite3.Row]:
        clauses = ["company_id=?"]
        params: List[Any] = [int(company_id)]
        if order_type:
            clauses.append("order_type=?")
            params.append(order_type)
        if status:
            clauses.append("status=?")
            params.append(status)
        if (q or "").strip():
            clauses.append("(order_no LIKE ? OR cari_name LIKE ?)")
            like = f"%{q.strip()}%"
            params.extend([like, like])
        where = " AND ".join(clauses)
        sql = f"""
            SELECT * FROM trade_orders
            WHERE {where}
            ORDER BY order_date DESC, id DESC
            LIMIT ? OFFSET ?
        """
        params.extend([int(limit), int(offset)])
        return list(self.conn.execute(sql, tuple(params)))

    def get_order(self, order_id: int) -> Optional[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM trade_orders WHERE id=?", (int(order_id),)).fetchone()

    def list_order_lines(self, order_id: int) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT * FROM trade_order_lines WHERE order_id=? ORDER BY id",
                (int(order_id),),
            )
        )

    def update_order_status(self, order_id: int, status: str) -> None:
        self.conn.execute(
            "UPDATE trade_orders SET status=?, updated_at=? WHERE id=?",
            (status, now_iso(), int(order_id)),
        )
        self.conn.commit()

    def update_order_line_fulfilled(self, line_id: int, fulfilled_qty: float) -> None:
        self.conn.execute(
            "UPDATE trade_order_lines SET fulfilled_qty=? WHERE id=?",
            (float(fulfilled_qty), int(line_id)),
        )
        self.conn.commit()

    def add_audit_log(
        self,
        company_id: int,
        user_id: Optional[int],
        username: str,
        action: str,
        entity: str,
        entity_id: Optional[int],
        detail: str,
    ) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO trade_audit_log(
                company_id, user_id, username, action, entity, entity_id, detail, created_at
            ) VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                int(company_id),
                None if user_id is None else int(user_id),
                username,
                action,
                entity,
                None if entity_id is None else int(entity_id),
                detail,
                now_iso(),
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def list_audit_logs(self, company_id: int, limit: int = 200) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT * FROM trade_audit_log WHERE company_id=? ORDER BY id DESC LIMIT ?",
                (int(company_id), int(limit)),
            )
        )

    def set_user_role(self, company_id: int, user_id: int, username: str, role: str) -> None:
        self.conn.execute(
            """
            INSERT INTO trade_user_roles(company_id, user_id, username, role)
            VALUES(?,?,?,?)
            ON CONFLICT(company_id, user_id) DO UPDATE SET
                username=excluded.username,
                role=excluded.role
            """,
            (int(company_id), int(user_id), username, role),
        )
        self.conn.commit()

    def get_user_role(self, company_id: int, user_id: int) -> Optional[str]:
        row = self.conn.execute(
            "SELECT role FROM trade_user_roles WHERE company_id=? AND user_id=?",
            (int(company_id), int(user_id)),
        ).fetchone()
        if not row:
            return None
        return str(row[0])

    def list_user_roles(self, company_id: int) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT * FROM trade_user_roles WHERE company_id=? ORDER BY username",
                (int(company_id),),
            )
        )

    def list_order_line_summary(self, order_id: int) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                """
                SELECT id, item, qty, fulfilled_qty, unit, unit_price
                FROM trade_order_lines
                WHERE order_id=?
                ORDER BY id
                """,
                (int(order_id),),
            )
        )

    def report_daily_totals(self, company_id: int, doc_type: str) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                """
                SELECT doc_date, SUM(total) AS total
                FROM trade_docs
                WHERE company_id=? AND doc_type=? AND status!='void'
                GROUP BY doc_date
                ORDER BY doc_date DESC
                """,
                (int(company_id), doc_type),
            )
        )

    def report_monthly_totals(self, company_id: int, doc_type: str) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                """
                SELECT SUBSTR(doc_date,1,7) AS ym, SUM(total) AS total
                FROM trade_docs
                WHERE company_id=? AND doc_type=? AND status!='void'
                GROUP BY SUBSTR(doc_date,1,7)
                ORDER BY ym DESC
                """,
                (int(company_id), doc_type),
            )
        )

    def report_top_items(self, company_id: int, doc_type: str, limit: int = 10) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                """
                SELECT l.item, SUM(l.qty) AS qty, SUM(l.line_total + l.tax_total) AS total
                FROM trade_doc_lines l
                JOIN trade_docs d ON d.id=l.doc_id
                WHERE d.company_id=? AND d.doc_type=? AND d.status!='void'
                GROUP BY l.item
                ORDER BY total DESC
                LIMIT ?
                """,
                (int(company_id), doc_type, int(limit)),
            )
        )
