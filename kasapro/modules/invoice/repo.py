# -*- coding: utf-8 -*-
"""Advanced invoice repository with accounting side effects."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from ...utils import parse_date_smart, safe_float
from .calculator import calculate_totals

logger = logging.getLogger(__name__)


DOC_TYPES = {
    "sales": {"label": "Satış", "sign": 1, "direction": "OUT"},
    "purchase": {"label": "Alış", "sign": 1, "direction": "IN"},
    "sales_return": {"label": "Satış İade", "sign": -1, "direction": "IN"},
    "purchase_return": {"label": "Alış İade", "sign": -1, "direction": "OUT"},
    "void": {"label": "İptal", "sign": -1, "direction": "REV"},
}


class AdvancedInvoiceRepo:
    def __init__(self, conn):
        self.conn = conn

    def _today_year(self) -> int:
        try:
            return int(date.today().year)
        except Exception:
            return 0

    def _reserve_doc_no(self, cur, company_id: int, series: str, year: int) -> str:
        cur.execute(
            "SELECT last_no, padding, format FROM series_counters WHERE company_id=? AND series=? AND year=?",
            (int(company_id), str(series), int(year)),
        )
        row = cur.fetchone()
        if not row:
            cur.execute(
                """INSERT INTO series_counters(company_id, series, year, last_no, padding, format)
                   VALUES(?,?,?,?,?,?)""",
                (int(company_id), str(series), int(year), 0, 6, "{series}-{year}-{no_pad}"),
            )
            cur.execute(
                "SELECT last_no, padding, format FROM series_counters WHERE company_id=? AND series=? AND year=?",
                (int(company_id), str(series), int(year)),
            )
            row = cur.fetchone()

        last_no = int(row["last_no"] or 0)
        padding = int(row["padding"] or 6)
        fmt = str(row["format"] or "{series}-{year}-{no_pad}")

        new_no = last_no + 1
        no_pad = str(new_no).zfill(max(1, padding))
        try:
            doc_no = fmt.format(series=series, year=year, no=new_no, no_pad=no_pad)
        except Exception:
            doc_no = f"{series}-{year}-{no_pad}"

        cur.execute(
            "UPDATE series_counters SET last_no=?, updated_at=CURRENT_TIMESTAMP WHERE company_id=? AND series=? AND year=?",
            (int(new_no), int(company_id), str(series), int(year)),
        )
        return doc_no

    def _doc_type_sign(self, doc_type: str) -> int:
        return DOC_TYPES.get(doc_type, {}).get("sign", 1)

    def _invert_tip(self, tip: str) -> str:
        return "Borç" if tip == "Alacak" else "Alacak"

    def _cari_tip_for_doc(self, doc_type: str, header: Dict[str, Any]) -> str:
        mapping = {
            "sales": "Alacak",
            "purchase": "Borç",
            "sales_return": "Borç",
            "purchase_return": "Alacak",
        }
        if doc_type == "void":
            original_type = str(header.get("reversal_of_type") or "")
            if original_type in mapping:
                return self._invert_tip(mapping[original_type])
        return mapping.get(doc_type, "Alacak")

    def _cari_tip_for_payment(self, doc_type: str) -> str:
        return "Borç" if doc_type in ("sales", "sales_return") else "Alacak"

    def list_docs(
        self,
        company_id: int,
        doc_type: Optional[str] = None,
        status: Optional[str] = None,
        query: str = "",
        date_from: str = "",
        date_to: str = "",
        customer_id: Optional[int] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[Any], int]:
        clauses = ["company_id=?"]
        params: List[Any] = [int(company_id)]

        if doc_type:
            clauses.append("doc_type=?")
            params.append(str(doc_type))
        if status:
            clauses.append("status=?")
            params.append(str(status))
        if query:
            like = f"%{query.strip()}%"
            clauses.append("(doc_no LIKE ? OR customer_name LIKE ? OR notes LIKE ?)")
            params.extend([like, like, like])
        if date_from:
            clauses.append("doc_date>=?")
            params.append(parse_date_smart(date_from))
        if date_to:
            clauses.append("doc_date<=?")
            params.append(parse_date_smart(date_to))
        if customer_id:
            clauses.append("customer_id=?")
            params.append(int(customer_id))

        where = " AND ".join(clauses)
        count_sql = f"SELECT COUNT(1) FROM docs WHERE {where}"
        total = int(self.conn.execute(count_sql, tuple(params)).fetchone()[0])

        sql = f"""
            SELECT d.*,
                   COALESCE(p.paid, 0) AS paid,
                   (COALESCE(d.grand_total,0) - COALESCE(p.paid,0)) AS remaining
            FROM docs d
            LEFT JOIN (
                SELECT doc_id, SUM(amount) AS paid
                FROM payments
                GROUP BY doc_id
            ) p ON p.doc_id = d.id
            WHERE {where}
            ORDER BY d.doc_date DESC, d.id DESC
            LIMIT ? OFFSET ?
        """
        rows = list(self.conn.execute(sql, tuple(params + [int(limit), int(offset)])))
        return rows, total

    def get_doc(self, doc_id: int) -> Optional[Dict[str, Any]]:
        header = self.conn.execute("SELECT * FROM docs WHERE id=?", (int(doc_id),)).fetchone()
        if not header:
            return None
        lines = list(self.conn.execute("SELECT * FROM doc_lines WHERE doc_id=? ORDER BY line_no ASC", (int(doc_id),)))
        payments = list(self.conn.execute("SELECT * FROM payments WHERE doc_id=? ORDER BY pay_date DESC, id DESC", (int(doc_id),)))
        return {"header": header, "lines": lines, "payments": payments}

    def create_doc(
        self,
        header: Dict[str, Any],
        lines: List[Dict[str, Any]],
        user_id: Optional[int] = None,
        username: str = "",
    ) -> int:
        company_id = int(header.get("company_id") or 1)
        doc_type = str(header.get("doc_type") or "sales")
        vat_included = int(bool(header.get("vat_included")))
        series = str(header.get("series") or "A")
        doc_date = parse_date_smart(header.get("doc_date") or "")
        year = int(str(doc_date or "")[:4] or self._today_year())
        status = str(header.get("status") or "POSTED")
        is_proforma = int(bool(header.get("is_proforma")))

        sign = self._doc_type_sign(doc_type)
        totals = calculate_totals(
            lines,
            invoice_discount_value=header.get("invoice_discount_value", 0),
            invoice_discount_type=str(header.get("invoice_discount_type") or "amount"),
            vat_included=bool(vat_included),
            sign=sign,
        )

        cur = self.conn.cursor()
        try:
            cur.execute("BEGIN IMMEDIATE")
            doc_no = self._reserve_doc_no(cur, company_id, series, year)

            payment_status = "PAID" if abs(totals.grand_total) < 0.01 else "UNPAID"
            cur.execute(
                """
                INSERT INTO docs(
                    company_id, doc_no, series, year, doc_date, due_date, doc_type, status,
                    is_proforma, customer_id, customer_name, currency, vat_included,
                    invoice_discount_type, invoice_discount_value,
                    subtotal, discount_total, vat_total, grand_total, notes, warehouse_id,
                    payment_status, created_by, created_by_name
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    company_id,
                    doc_no,
                    series,
                    year,
                    doc_date,
                    parse_date_smart(header.get("due_date") or ""),
                    doc_type,
                    status,
                    is_proforma,
                    header.get("customer_id"),
                    str(header.get("customer_name") or ""),
                    str(header.get("currency") or "TL"),
                    vat_included,
                    str(header.get("invoice_discount_type") or "amount"),
                    float(safe_float(header.get("invoice_discount_value") or 0)),
                    totals.subtotal,
                    totals.discount_total,
                    totals.vat_total,
                    totals.grand_total,
                    str(header.get("notes") or ""),
                    header.get("warehouse_id"),
                    payment_status,
                    int(user_id) if user_id is not None else None,
                    str(username or ""),
                ),
            )
            doc_id = int(cur.lastrowid or 0)

            for line in totals.lines:
                cur.execute(
                    """
                    INSERT INTO doc_lines(
                        doc_id, line_no, item_id, description, qty, unit, unit_price,
                        vat_rate, line_discount_type, line_discount_value,
                        line_subtotal, line_discount, line_vat, line_total
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        doc_id,
                        int(line.get("line_no") or 1),
                        line.get("item_id"),
                        str(line.get("description") or ""),
                        float(safe_float(line.get("qty") or 0)),
                        str(line.get("unit") or ""),
                        float(safe_float(line.get("unit_price") or 0)),
                        float(safe_float(line.get("vat_rate") or 0)),
                        str(line.get("line_discount_type") or "amount"),
                        float(safe_float(line.get("line_discount_value") or 0)),
                        float(safe_float(line.get("line_subtotal") or 0)),
                        float(safe_float(line.get("line_discount") or 0)),
                        float(safe_float(line.get("line_vat") or 0)),
                        float(safe_float(line.get("line_total") or 0)),
                    ),
                )

                if status == "POSTED" and not is_proforma:
                    self._create_stock_move(
                        cur,
                        doc_id,
                        line,
                        doc_type,
                        doc_no,
                        doc_date,
                        header.get("warehouse_id"),
                    )

            if status == "POSTED" and not is_proforma:
                header_for_ledger = dict(header)
                if "reversal_of_type" in header:
                    header_for_ledger["reversal_of_type"] = header["reversal_of_type"]
                self._create_cari_hareket(cur, header_for_ledger, totals.grand_total, doc_no, doc_type, doc_date)

            self._audit(cur, company_id, user_id, username, "create", "doc", doc_id, f"{doc_type} #{doc_no}")
            self.conn.commit()
            return doc_id
        except Exception:
            logger.exception("Failed to create invoice")
            try:
                self.conn.rollback()
            except Exception:
                pass
            raise

    def _create_cari_hareket(self, cur, header: Dict[str, Any], amount: float, doc_no: str, doc_type: str, doc_date: str) -> None:
        if not header.get("customer_id"):
            return
        amount_value = abs(float(safe_float(amount)))
        tip = self._cari_tip_for_doc(doc_type, header)
        aciklama = str(header.get("notes") or "").strip() or DOC_TYPES.get(doc_type, {}).get("label", "Fatura")
        cur.execute(
            """
            INSERT INTO cari_hareket(tarih, cari_id, tip, tutar, para, aciklama, belge, etiket)
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                doc_date,
                int(header.get("customer_id")),
                tip,
                amount_value,
                str(header.get("currency") or "TL"),
                aciklama,
                doc_no,
                "invoice",
            ),
        )

    def _create_stock_move(
        self,
        cur,
        doc_id: int,
        line: Dict[str, Any],
        doc_type: str,
        doc_no: str,
        doc_date: str,
        warehouse_id: Any,
    ) -> None:
        item_id = line.get("item_id")
        if not item_id:
            return
        direction = line.get("move_direction") or DOC_TYPES.get(doc_type, {}).get("direction", "OUT")
        cur.execute(
            """
            INSERT INTO stock_moves(
                doc_id, line_id, item_id, qty, unit, direction, move_date,
                warehouse_id, doc_type, doc_no
            ) VALUES(?,?,?,?,?,?,?,?,?,?)
            """,
            (
                int(doc_id),
                None,
                int(item_id),
                float(safe_float(line.get("qty") or 0)),
                str(line.get("unit") or ""),
                str(direction or ""),
                doc_date,
                warehouse_id,
                str(doc_type or ""),
                str(doc_no or ""),
            ),
        )

    def add_payment(
        self,
        doc_id: int,
        pay_date: Any,
        amount: float,
        currency: str,
        method: str,
        description: str = "",
        ref: str = "",
        user_id: Optional[int] = None,
        username: str = "",
    ) -> int:
        cur = self.conn.cursor()
        try:
            cur.execute("BEGIN")
            header = self.conn.execute("SELECT * FROM docs WHERE id=?", (int(doc_id),)).fetchone()
            if not header:
                raise ValueError("Belge bulunamadı")
            if header["status"] == "VOID":
                raise ValueError("İptal edilen belgeye ödeme eklenemez")
            remaining = self.remaining_balance(int(doc_id))
            amount_value = float(safe_float(amount))
            if remaining <= 0 and amount_value > 0:
                raise ValueError("Ödeme tutarı kalan bakiyeyi aşamaz")
            if remaining > 0 and amount_value - remaining > 0.009:
                raise ValueError("Ödeme tutarı kalan bakiyeyi aşamaz")
            cur.execute(
                """
                INSERT INTO payments(doc_id, pay_date, amount, currency, method, description, ref)
                VALUES(?,?,?,?,?,?,?)
                """,
                (
                    int(doc_id),
                    parse_date_smart(pay_date),
                    float(safe_float(amount)),
                    str(currency or "TL"),
                    str(method or ""),
                    str(description or ""),
                    str(ref or ""),
                ),
            )
            payment_id = int(cur.lastrowid or 0)
            if header and header["customer_id"]:
                tip = self._cari_tip_for_payment(str(header["doc_type"] or ""))
                payment_label = "Tahsilat" if header["doc_type"] in ("sales", "sales_return") else "Ödeme"
                cur.execute(
                    """
                    INSERT INTO cari_hareket(tarih, cari_id, tip, tutar, para, aciklama, odeme, belge, etiket)
                    VALUES(?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        parse_date_smart(pay_date),
                        int(header["customer_id"]),
                        tip,
                        float(safe_float(amount)),
                        str(currency or header["currency"] or "TL"),
                        str(description or "").strip() or payment_label,
                        str(method or ""),
                        str(header["doc_no"] or ""),
                        "invoice_payment",
                    ),
                )

            total_due = abs(float(safe_float(header["grand_total"]))) if header else 0.0
            paid_total = float(
                safe_float(
                    self.conn.execute(
                        "SELECT COALESCE(SUM(amount),0) FROM payments WHERE doc_id=?",
                        (int(doc_id),),
                    ).fetchone()[0]
                )
            )
            if total_due <= 0.01:
                payment_status = "PAID"
            elif paid_total <= 0.01:
                payment_status = "UNPAID"
            elif paid_total + 0.009 < total_due:
                payment_status = "PART_PAID"
            else:
                payment_status = "PAID"
            cur.execute("UPDATE docs SET payment_status=? WHERE id=?", (payment_status, int(doc_id)))

            self._audit(cur, int(header["company_id"]) if header else 1, user_id, username, "payment", "doc", doc_id, f"{amount}")
            self.conn.commit()
            return payment_id
        except Exception:
            logger.exception("Failed to add payment")
            try:
                self.conn.rollback()
            except Exception:
                pass
            raise

    def void_doc(self, doc_id: int, user_id: Optional[int] = None, username: str = "") -> int:
        try:
            header = self.conn.execute("SELECT * FROM docs WHERE id=?", (int(doc_id),)).fetchone()
            if not header:
                raise ValueError("Belge bulunamadı")
            if header["status"] == "VOID":
                return int(header["reversed_doc_id"] or 0)

            cur = self.conn.cursor()
            cur.execute("BEGIN IMMEDIATE")
            cur.execute(
                "UPDATE docs SET status='VOID', payment_status='VOID', voided_at=CURRENT_TIMESTAMP WHERE id=?",
                (int(doc_id),),
            )
            self._audit(cur, int(header["company_id"]), user_id, username, "void", "doc", doc_id, "voided")
            self.conn.commit()

            lines = list(self.conn.execute("SELECT * FROM doc_lines WHERE doc_id=?", (int(doc_id),)))
            reverse_lines = []
            direction = "IN" if DOC_TYPES.get(header["doc_type"], {}).get("direction") == "OUT" else "OUT"
            for line in lines:
                reverse_lines.append(
                    {
                        "line_no": line["line_no"],
                        "item_id": line["item_id"],
                        "description": line["description"],
                        "qty": abs(float(safe_float(line["qty"] or 0))),
                        "unit": line["unit"],
                        "unit_price": float(safe_float(line["unit_price"] or 0)),
                        "vat_rate": float(safe_float(line["vat_rate"] or 0)),
                        "line_discount_type": line["line_discount_type"],
                        "line_discount_value": float(safe_float(line["line_discount_value"] or 0)),
                        "move_direction": direction,
                    }
                )

            reverse_header = {
                "company_id": header["company_id"],
                "doc_type": "void",
                "doc_date": header["doc_date"],
                "due_date": header["due_date"],
                "customer_id": header["customer_id"],
                "customer_name": header["customer_name"],
                "currency": header["currency"],
                "vat_included": int(header["vat_included"]),
                "invoice_discount_type": header["invoice_discount_type"],
                "invoice_discount_value": header["invoice_discount_value"],
                "series": "V",
                "status": "POSTED",
                "is_proforma": 0,
                "notes": f"{header['doc_no']} iptali",
                "warehouse_id": header["warehouse_id"],
                "reversal_of_type": header["doc_type"],
            }

            reverse_id = self.create_doc(reverse_header, reverse_lines, user_id=user_id, username=username)
            self.conn.execute("UPDATE docs SET reversed_doc_id=? WHERE id=?", (int(reverse_id), int(doc_id)))
            self.conn.commit()
            return reverse_id
        except Exception:
            logger.exception("Failed to void invoice")
            try:
                self.conn.rollback()
            except Exception:
                pass
            raise

    def remaining_balance(self, doc_id: int) -> float:
        header = self.conn.execute("SELECT grand_total, status FROM docs WHERE id=?", (int(doc_id),)).fetchone()
        if not header or header["status"] == "VOID":
            return 0.0
        paid = self.conn.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE doc_id=?", (int(doc_id),)).fetchone()
        paid_amount = float(safe_float(paid[0] if paid else 0))
        total_due = abs(float(safe_float(header["grand_total"])))
        return max(0.0, total_due - paid_amount)

    def _audit(
        self,
        cur,
        company_id: int,
        user_id: Optional[int],
        username: str,
        action: str,
        entity: str,
        entity_id: int,
        message: str,
    ) -> None:
        cur.execute(
            """
            INSERT INTO audit_log(
                company_id, entity_type, entity_id, module, ref_id,
                action, user_id, username, details, message
            )
            VALUES(?,?,?,?,?,?,?,?,?,?)
            """,
            (
                int(company_id),
                str(entity),
                int(entity_id),
                "invoice",
                int(entity_id),
                str(action),
                int(user_id) if user_id is not None else None,
                str(username or ""),
                str(message or ""),
                str(message or ""),
            ),
        )
