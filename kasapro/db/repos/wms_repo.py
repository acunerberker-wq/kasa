# -*- coding: utf-8 -*-

from __future__ import annotations

import logging
import os
import sqlite3
from datetime import date
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ...utils import parse_date_smart, safe_float

logger = logging.getLogger(__name__)


def _ensure_app_logger() -> None:
    if any(isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", "").endswith("app.log") for h in logger.handlers):
        return
    log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "..", "logs", "app.log")
    log_path = os.path.abspath(log_path)
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    handler = logging.FileHandler(log_path)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class WmsToleranceError(RuntimeError):
    pass


DOC_DIRECTIONS = {
    "GRN": "IN",
    "SHIP": "OUT",
    "TRF": "XFER",
    "ADJ": "ADJ",
    "COUNT": "COUNT",
    "ISSUE": "OUT",
    "MO": "IN",
}


class WMSRepo:
    def __init__(self, conn: sqlite3.Connection, log_fn=None) -> None:
        self.conn = conn
        self.log_fn = log_fn

    # -----------------
    # Dönem / Kilitler
    # -----------------
    def create_period(
        self,
        company_id: int,
        branch_id: int,
        name: str,
        start_date: str,
        end_date: str,
        is_locked: int = 0,
    ) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO periods(company_id, branch_id, name, start_date, end_date, is_locked)
            VALUES(?,?,?,?,?,?)
            """,
            (
                int(company_id),
                int(branch_id),
                str(name),
                parse_date_smart(start_date),
                parse_date_smart(end_date),
                int(is_locked),
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def lock_period(self, period_id: int, user_id: Optional[int] = None) -> None:
        self.conn.execute(
            """
            UPDATE periods
            SET is_locked=1, locked_at=CURRENT_TIMESTAMP, locked_by=?
            WHERE id=?
            """,
            (int(user_id) if user_id else None, int(period_id)),
        )
        self.conn.commit()

    def is_period_locked(self, company_id: int, branch_id: int, doc_date: str) -> bool:
        row = self.conn.execute(
            """
            SELECT 1 FROM periods
            WHERE company_id=? AND branch_id=?
              AND start_date<=? AND end_date>=?
              AND is_locked=1
            LIMIT 1
            """,
            (int(company_id), int(branch_id), parse_date_smart(doc_date), parse_date_smart(doc_date)),
        ).fetchone()
        return bool(row)

    # -----------------
    # Master Data
    # -----------------
    def create_uom(self, company_id: int, code: str, name: str) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO uoms(company_id, code, name)
            VALUES(?,?,?)
            """,
            (int(company_id), str(code), str(name)),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def create_category(self, company_id: int, name: str, parent_id: Optional[int] = None) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO categories(company_id, name, parent_id)
            VALUES(?,?,?)
            """,
            (int(company_id), str(name), int(parent_id) if parent_id else None),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def create_brand(self, company_id: int, name: str) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO brands(company_id, name)
            VALUES(?,?)
            """,
            (int(company_id), str(name)),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def create_variant(self, company_id: int, name: str) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO variants(company_id, name)
            VALUES(?,?)
            """,
            (int(company_id), str(name)),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def create_item(
        self,
        company_id: int,
        item_code: str,
        name: str,
        base_uom_id: int,
        category_id: Optional[int] = None,
        brand_id: Optional[int] = None,
        variant_id: Optional[int] = None,
        track_lot: int = 0,
        track_serial: int = 0,
        negative_stock_policy: str = "forbid",
        is_active: int = 1,
    ) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO items(
                company_id, item_code, name, base_uom_id, category_id, brand_id, variant_id,
                track_lot, track_serial, negative_stock_policy, is_active
            )
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                int(company_id),
                str(item_code),
                str(name),
                int(base_uom_id),
                int(category_id) if category_id else None,
                int(brand_id) if brand_id else None,
                int(variant_id) if variant_id else None,
                int(track_lot),
                int(track_serial),
                str(negative_stock_policy),
                int(is_active),
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def add_item_barcode(self, item_id: int, barcode: str, is_primary: int = 0) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO item_barcodes(item_id, barcode, is_primary)
            VALUES(?,?,?)
            """,
            (int(item_id), str(barcode), int(is_primary)),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def add_item_uom(self, item_id: int, uom_id: int, is_base: int = 0) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO item_uoms(item_id, uom_id, is_base)
            VALUES(?,?,?)
            """,
            (int(item_id), int(uom_id), int(is_base)),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def add_uom_conversion(self, item_id: int, from_uom_id: int, to_uom_id: int, factor: float) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO uom_conversions(item_id, from_uom_id, to_uom_id, factor)
            VALUES(?,?,?,?)
            """,
            (int(item_id), int(from_uom_id), int(to_uom_id), float(factor)),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def create_warehouse(self, company_id: int, branch_id: int, code: str, name: str, is_active: int = 1) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO warehouses(company_id, branch_id, code, name, is_active)
            VALUES(?,?,?,?,?)
            """,
            (int(company_id), int(branch_id), str(code), str(name), int(is_active)),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def create_location(
        self,
        company_id: int,
        branch_id: int,
        warehouse_id: int,
        name: str,
        parent_id: Optional[int] = None,
        location_type: str = "STORAGE",
        capacity_qty: Optional[float] = None,
        capacity_weight: Optional[float] = None,
        capacity_volume: Optional[float] = None,
        is_active: int = 1,
    ) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO warehouse_locations(
                company_id, branch_id, warehouse_id, parent_id, name, location_type,
                capacity_qty, capacity_weight, capacity_volume, is_active
            )
            VALUES(?,?,?,?,?,?,?,?,?,?)
            """,
            (
                int(company_id),
                int(branch_id),
                int(warehouse_id),
                int(parent_id) if parent_id else None,
                str(name),
                str(location_type),
                float(capacity_qty) if capacity_qty is not None else None,
                float(capacity_weight) if capacity_weight is not None else None,
                float(capacity_volume) if capacity_volume is not None else None,
                int(is_active),
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def create_lot(
        self,
        company_id: int,
        item_id: int,
        lot_no: str,
        expiry_date: str = "",
        manufacture_date: str = "",
        status: str = "ACTIVE",
    ) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO lots(company_id, item_id, lot_no, expiry_date, manufacture_date, status)
            VALUES(?,?,?,?,?,?)
            """,
            (
                int(company_id),
                int(item_id),
                str(lot_no),
                str(expiry_date or ""),
                str(manufacture_date or ""),
                str(status),
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def create_serial(self, company_id: int, item_id: int, serial_no: str, status: str = "ACTIVE") -> int:
        cur = self.conn.execute(
            """
            INSERT INTO serials(company_id, item_id, serial_no, status)
            VALUES(?,?,?,?)
            """,
            (int(company_id), int(item_id), str(serial_no), str(status)),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def pick_lot_fefo(self, company_id: int, item_id: int) -> Optional[sqlite3.Row]:
        return self.conn.execute(
            """
            SELECT * FROM lots
            WHERE company_id=? AND item_id=? AND status='ACTIVE'
            ORDER BY
                CASE WHEN expiry_date='' THEN 1 ELSE 0 END,
                expiry_date ASC,
                lot_no ASC
            LIMIT 1
            """,
            (int(company_id), int(item_id)),
        ).fetchone()

    # -----------------
    # Yetkilendirme
    # -----------------
    def set_warehouse_permission(
        self,
        user_id: int,
        company_id: int,
        branch_id: int,
        warehouse_id: int,
        can_view: int = 1,
        can_post: int = 0,
    ) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO warehouse_permissions(
                user_id, company_id, branch_id, warehouse_id, can_view, can_post
            ) VALUES(?,?,?,?,?,?)
            """,
            (int(user_id), int(company_id), int(branch_id), int(warehouse_id), int(can_view), int(can_post)),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def can_post(self, user_id: int, company_id: int, branch_id: int, warehouse_id: int) -> bool:
        row = self.conn.execute(
            """
            SELECT can_post FROM warehouse_permissions
            WHERE user_id=? AND company_id=? AND branch_id=? AND warehouse_id=?
            """,
            (int(user_id), int(company_id), int(branch_id), int(warehouse_id)),
        ).fetchone()
        return bool(row and int(row["can_post"]) == 1)

    # -----------------
    # Seri numarası
    # -----------------
    def _today_year(self) -> int:
        try:
            return int(date.today().year)
        except Exception:
            return 0

    def _reserve_doc_no(self, cur: sqlite3.Cursor, company_id: int, series: str, year: int) -> str:
        cur.execute(
            "SELECT last_no, padding, format FROM series_counters WHERE company_id=? AND series=? AND year=?",
            (int(company_id), str(series), int(year)),
        )
        row = cur.fetchone()
        if not row:
            cur.execute(
                """
                INSERT INTO series_counters(company_id, series, year, last_no, padding, format)
                VALUES(?,?,?,?,?,?)
                """,
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

    # -----------------
    # Dokümanlar
    # -----------------
    def create_doc(
        self,
        header: Dict[str, Any],
        lines: List[Dict[str, Any]],
        user_id: Optional[int] = None,
        username: str = "",
    ) -> int:
        company_id = int(header.get("company_id") or 1)
        branch_id = int(header.get("branch_id") or 1)
        doc_type = str(header.get("doc_type") or "GRN")
        series = str(header.get("series") or "WMS")
        doc_date = parse_date_smart(header.get("doc_date") or "")
        year = int(str(doc_date or "")[:4] or self._today_year())
        status = str(header.get("status") or "DRAFT")

        cur = self.conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        try:
            doc_no = self._reserve_doc_no(cur, company_id, series, year)
            cur.execute(
                """
                INSERT INTO docs(
                    company_id, branch_id, doc_no, series, year, doc_date, doc_type,
                    status, warehouse_id, notes, created_by, created_by_name, module
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    company_id,
                    branch_id,
                    doc_no,
                    series,
                    year,
                    doc_date,
                    doc_type,
                    status,
                    int(header.get("warehouse_id") or 0) or None,
                    str(header.get("notes") or ""),
                    int(user_id) if user_id else None,
                    str(username or ""),
                    "stock",
                ),
            )
            doc_id = int(cur.lastrowid)

            for idx, line in enumerate(lines, start=1):
                cur.execute(
                    """
                    INSERT INTO doc_lines(
                        doc_id, line_no, item_id, description, qty, unit,
                        unit_price, vat_rate, line_discount_type, line_discount_value,
                        line_subtotal, line_discount, line_vat, line_total,
                        source_warehouse_id, target_warehouse_id,
                        source_location_id, target_location_id,
                        lot_id, serial_id, line_status, line_notes
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        doc_id,
                        int(line.get("line_no") or idx),
                        int(line.get("item_id") or 0) or None,
                        str(line.get("description") or ""),
                        float(line.get("qty") or 0),
                        str(line.get("unit") or ""),
                        float(line.get("unit_price") or 0),
                        float(line.get("vat_rate") or 0),
                        str(line.get("line_discount_type") or "amount"),
                        float(line.get("line_discount_value") or 0),
                        float(line.get("line_subtotal") or 0),
                        float(line.get("line_discount") or 0),
                        float(line.get("line_vat") or 0),
                        float(line.get("line_total") or 0),
                        int(line.get("source_warehouse_id") or 0) or None,
                        int(line.get("target_warehouse_id") or 0) or None,
                        int(line.get("source_location_id") or 0) or None,
                        int(line.get("target_location_id") or 0) or None,
                        int(line.get("lot_id") or 0) or None,
                        int(line.get("serial_id") or 0) or None,
                        str(line.get("line_status") or ""),
                        str(line.get("line_notes") or ""),
                    ),
                )

            cur.execute("COMMIT")
            self._audit(
                company_id,
                "stock_doc",
                doc_id,
                "CREATE",
                user_id,
                f"{doc_type} {doc_no}",
            )
            return doc_id
        except Exception:
            cur.execute("ROLLBACK")
            raise

    def get_doc(self, doc_id: int) -> Optional[Dict[str, Any]]:
        header = self.conn.execute(
            "SELECT * FROM docs WHERE id=? AND module='stock'",
            (int(doc_id),),
        ).fetchone()
        if not header:
            return None
        lines = list(self.conn.execute("SELECT * FROM doc_lines WHERE doc_id=? ORDER BY line_no ASC", (int(doc_id),)))
        return {"header": header, "lines": lines}

    def lock_doc(self, company_id: int, branch_id: int, doc_type: str, doc_no: str, user_id: Optional[int], reason: str = "") -> int:
        cur = self.conn.execute(
            """
            INSERT INTO doc_locks(company_id, branch_id, doc_type, doc_no, locked_by, reason)
            VALUES(?,?,?,?,?,?)
            """,
            (int(company_id), int(branch_id), str(doc_type), str(doc_no), int(user_id) if user_id else None, str(reason)),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def is_doc_locked(self, company_id: int, branch_id: int, doc_type: str, doc_no: str) -> bool:
        row = self.conn.execute(
            """
            SELECT 1 FROM doc_locks
            WHERE company_id=? AND branch_id=? AND doc_type=? AND doc_no=? AND is_active=1
            """,
            (int(company_id), int(branch_id), str(doc_type), str(doc_no)),
        ).fetchone()
        return bool(row)

    # -----------------
    # Stok İşlemleri
    # -----------------
    def post_doc(
        self,
        doc_id: int,
        user_id: Optional[int] = None,
        username: str = "",
        negative_stock_policy: str = "forbid",
    ) -> None:
        payload = self.get_doc(doc_id)
        if not payload:
            raise ValueError("Stock document not found.")

        header = payload["header"]
        lines = payload["lines"]
        status = str(header["status"] or "")
        if status == "POSTED":
            return
        if status == "VOID":
            raise ValueError("Voided document cannot be posted.")

        company_id = int(header["company_id"])
        branch_id = int(header["branch_id"] or 1)
        warehouse_id = int(header["warehouse_id"] or 0)
        doc_no = str(header["doc_no"])
        doc_type = str(header["doc_type"])
        doc_date = str(header["doc_date"])

        if self.is_doc_locked(company_id, branch_id, doc_type, doc_no):
            raise ValueError("Document is locked.")
        if self.is_period_locked(company_id, branch_id, doc_date):
            raise ValueError("Period is locked.")

        direction = DOC_DIRECTIONS.get(doc_type, "")
        if not direction:
            raise ValueError(f"Unsupported doc type: {doc_type}")

        cur = self.conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        try:
            for line in lines:
                item_id = int(line["item_id"] or 0)
                qty = safe_float(line["qty"])
                if qty == 0:
                    continue
                item = self.conn.execute(
                    "SELECT * FROM items WHERE id=? AND company_id=?",
                    (item_id, company_id),
                ).fetchone()
                if not item:
                    raise ValueError("Item not found for line.")
                if int(item["track_lot"] or 0) == 1 and not line["lot_id"]:
                    raise ValueError("Lot is required for this item.")
                if int(item["track_serial"] or 0) == 1 and not line["serial_id"]:
                    raise ValueError("Serial is required for this item.")

                if doc_type == "TRF":
                    src_wh = int(line["source_warehouse_id"] or 0)
                    tgt_wh = int(line["target_warehouse_id"] or 0)
                    src_loc = int(line["source_location_id"] or 0)
                    tgt_loc = int(line["target_location_id"] or 0)
                    if not src_wh or not tgt_wh:
                        raise ValueError("Transfer requires source and target warehouses.")
                    self._ensure_outbound_available(
                        company_id,
                        branch_id,
                        src_wh,
                        src_loc,
                        item_id,
                        qty,
                        negative_stock_policy,
                    )
                    self._insert_ledger(
                        cur,
                        company_id,
                        branch_id,
                        src_wh,
                        src_loc,
                        item_id,
                        int(line["lot_id"] or 0) or None,
                        int(line["serial_id"] or 0) or None,
                        doc_id,
                        int(line["id"]),
                        doc_date,
                        -qty,
                        "OUT",
                        float(line["unit_price"] or 0),
                    )
                    self._update_balance(cur, company_id, branch_id, src_wh, src_loc, item_id, -qty)
                    self._insert_ledger(
                        cur,
                        company_id,
                        branch_id,
                        tgt_wh,
                        tgt_loc,
                        item_id,
                        int(line["lot_id"] or 0) or None,
                        int(line["serial_id"] or 0) or None,
                        doc_id,
                        int(line["id"]),
                        doc_date,
                        qty,
                        "IN",
                        float(line["unit_price"] or 0),
                    )
                    self._update_balance(cur, company_id, branch_id, tgt_wh, tgt_loc, item_id, qty)
                    continue

                if doc_type == "COUNT":
                    location_id = int(line["source_location_id"] or line["target_location_id"] or 0)
                    on_hand = self.get_on_hand(company_id, branch_id, warehouse_id, location_id, item_id)
                    diff = qty - on_hand
                    tolerance_qty = safe_float(header["tolerance_qty"] if "tolerance_qty" in header.keys() else 0)
                    tolerance_pct = safe_float(header["tolerance_pct"] if "tolerance_pct" in header.keys() else 0)
                    if self._exceeds_tolerance(diff, tolerance_qty, tolerance_pct, on_hand):
                        raise WmsToleranceError("Count difference exceeds tolerance.")
                    if diff == 0:
                        continue
                    direction = "IN" if diff > 0 else "OUT"
                    if diff < 0:
                        self._ensure_outbound_available(
                            company_id,
                            branch_id,
                            warehouse_id,
                            location_id,
                            item_id,
                            abs(diff),
                            negative_stock_policy,
                        )
                    self._insert_ledger(
                        cur,
                        company_id,
                        branch_id,
                        warehouse_id,
                        location_id,
                        item_id,
                        int(line["lot_id"] or 0) or None,
                        int(line["serial_id"] or 0) or None,
                        doc_id,
                        int(line["id"]),
                        doc_date,
                        diff,
                        direction,
                        float(line["unit_price"] or 0),
                    )
                    self._update_balance(cur, company_id, branch_id, warehouse_id, location_id, item_id, diff)
                    continue

                location_id = int(
                    line["target_location_id"] if direction == "IN" else line["source_location_id"] or 0
                )
                if direction == "OUT":
                    self._ensure_outbound_available(
                        company_id,
                        branch_id,
                        warehouse_id,
                        location_id,
                        item_id,
                        qty,
                        negative_stock_policy,
                    )
                    qty_signed = -abs(qty)
                else:
                    qty_signed = abs(qty)
                self._insert_ledger(
                    cur,
                    company_id,
                    branch_id,
                    warehouse_id,
                    location_id,
                    item_id,
                    int(line["lot_id"] or 0) or None,
                    int(line["serial_id"] or 0) or None,
                    doc_id,
                    int(line["id"]),
                    doc_date,
                    qty_signed,
                    "IN" if qty_signed > 0 else "OUT",
                    float(line["unit_price"] or 0),
                )
                self._update_balance(cur, company_id, branch_id, warehouse_id, location_id, item_id, qty_signed)

            cur.execute("UPDATE docs SET status='POSTED' WHERE id=?", (int(doc_id),))
            cur.execute("COMMIT")
        except Exception as exc:
            cur.execute("ROLLBACK")
            if isinstance(exc, WmsToleranceError):
                self.conn.execute("UPDATE docs SET status='PENDING_APPROVAL' WHERE id=?", (int(doc_id),))
                self.conn.commit()
                raise ValueError(str(exc)) from exc
            raise

        self._audit(
            company_id,
            "stock_doc",
            doc_id,
            "POST",
            user_id,
            f"{doc_type} {doc_no}",
        )
        if self.log_fn:
            try:
                self.log_fn("Stok Fişi", f"POST {doc_type} {doc_no}")
            except Exception:
                pass

    def void_doc(self, doc_id: int, user_id: Optional[int] = None, reason: str = "") -> None:
        payload = self.get_doc(doc_id)
        if not payload:
            raise ValueError("Stock document not found.")

        header = payload["header"]
        if str(header["status"]) != "POSTED":
            raise ValueError("Only posted documents can be voided.")

        company_id = int(header["company_id"])
        branch_id = int(header["branch_id"] or 1)
        doc_no = str(header["doc_no"])
        doc_type = str(header["doc_type"])
        doc_date = str(header["doc_date"])

        cur = self.conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        try:
            rows = list(
                self.conn.execute(
                    """
                    SELECT * FROM stock_ledger
                    WHERE doc_id=? AND company_id=? AND branch_id=?
                    """,
                    (int(doc_id), int(company_id), int(branch_id)),
                )
            )
            for row in rows:
                qty = safe_float(row["qty"]) * -1
                self._insert_ledger(
                    cur,
                    company_id,
                    branch_id,
                    int(row["warehouse_id"]),
                    int(row["location_id"]) if row["location_id"] is not None else 0,
                    int(row["item_id"]),
                    int(row["lot_id"]) if row["lot_id"] is not None else None,
                    int(row["serial_id"]) if row["serial_id"] is not None else None,
                    doc_id,
                    int(row["doc_line_id"]) if row["doc_line_id"] is not None else None,
                    doc_date,
                    qty,
                    "REV",
                    float(row["cost"] or 0),
                )
                self._update_balance(
                    cur,
                    company_id,
                    branch_id,
                    int(row["warehouse_id"]),
                    int(row["location_id"]) if row["location_id"] is not None else 0,
                    int(row["item_id"]),
                    qty,
                )
            cur.execute(
                "UPDATE docs SET status='VOID', notes=notes || ? WHERE id=?",
                (f" VOID:{reason or ''}", int(doc_id)),
            )
            cur.execute("COMMIT")
        except Exception:
            cur.execute("ROLLBACK")
            raise

        self._audit(
            company_id,
            "stock_doc",
            doc_id,
            "VOID",
            user_id,
            f"{doc_type} {doc_no} {reason}",
        )

    def list_ledger(
        self,
        company_id: int,
        branch_id: int,
        warehouse_id: int,
        item_id: Optional[int] = None,
        limit: int = 200,
        offset: int = 0,
    ) -> List[sqlite3.Row]:
        clauses = ["company_id=?", "branch_id=?", "warehouse_id=?"]
        params: List[Any] = [int(company_id), int(branch_id), int(warehouse_id)]
        if item_id:
            clauses.append("item_id=?")
            params.append(int(item_id))
        where = " AND ".join(clauses)
        sql = f"""
        SELECT * FROM stock_ledger
        WHERE {where}
        ORDER BY txn_date DESC, id DESC
        LIMIT ? OFFSET ?
        """
        params.extend([int(limit), int(offset)])
        return list(self.conn.execute(sql, tuple(params)))

    def list_ledger_masked_cost(
        self,
        user_id: int,
        company_id: int,
        branch_id: int,
        warehouse_id: int,
        item_id: Optional[int] = None,
        limit: int = 200,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        rows = self.list_ledger(
            company_id,
            branch_id,
            warehouse_id,
            item_id=item_id,
            limit=limit,
            offset=offset,
        )
        can_see_cost = self.can_post(user_id, company_id, branch_id, warehouse_id)
        result: List[Dict[str, Any]] = []
        for row in rows:
            data = dict(row)
            if not can_see_cost:
                data["cost"] = None
            result.append(data)
        return result

    def get_on_hand(
        self,
        company_id: int,
        branch_id: int,
        warehouse_id: int,
        location_id: int,
        item_id: int,
    ) -> float:
        row = self.conn.execute(
            """
            SELECT qty_on_hand FROM stock_balance
            WHERE company_id=? AND branch_id=? AND warehouse_id=? AND location_id=? AND item_id=?
            """,
            (int(company_id), int(branch_id), int(warehouse_id), int(location_id), int(item_id)),
        ).fetchone()
        return safe_float(row["qty_on_hand"] if row else 0)

    def create_reservation(
        self,
        company_id: int,
        branch_id: int,
        warehouse_id: int,
        location_id: int,
        item_id: int,
        qty: float,
        ref_doc_id: Optional[int] = None,
        status: str = "ACTIVE",
    ) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO stock_reservations(
                company_id, branch_id, warehouse_id, location_id, item_id, qty, ref_doc_id, status
            ) VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                int(company_id),
                int(branch_id),
                int(warehouse_id),
                int(location_id),
                int(item_id),
                float(qty),
                int(ref_doc_id) if ref_doc_id else None,
                str(status),
            ),
        )
        self._update_balance(
            self.conn,
            company_id,
            branch_id,
            warehouse_id,
            location_id,
            item_id,
            0,
            reserved_delta=float(qty),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def release_reservation(self, reservation_id: int) -> None:
        row = self.conn.execute(
            "SELECT * FROM stock_reservations WHERE id=?",
            (int(reservation_id),),
        ).fetchone()
        if not row:
            return
        self.conn.execute(
            "UPDATE stock_reservations SET status='CLOSED' WHERE id=?",
            (int(reservation_id),),
        )
        self._update_balance(
            self.conn,
            int(row["company_id"]),
            int(row["branch_id"]),
            int(row["warehouse_id"]),
            int(row["location_id"]),
            int(row["item_id"]),
            0,
            reserved_delta=-safe_float(row["qty"]),
        )
        self.conn.commit()

    def create_block(
        self,
        company_id: int,
        branch_id: int,
        warehouse_id: int,
        location_id: int,
        item_id: int,
        qty: float,
        reason: str = "",
        status: str = "ACTIVE",
    ) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO stock_blocks(
                company_id, branch_id, warehouse_id, location_id, item_id, qty, reason, status
            ) VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                int(company_id),
                int(branch_id),
                int(warehouse_id),
                int(location_id),
                int(item_id),
                float(qty),
                str(reason),
                str(status),
            ),
        )
        self._update_balance(
            self.conn,
            company_id,
            branch_id,
            warehouse_id,
            location_id,
            item_id,
            0,
            blocked_delta=float(qty),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def release_block(self, block_id: int) -> None:
        row = self.conn.execute(
            "SELECT * FROM stock_blocks WHERE id=?",
            (int(block_id),),
        ).fetchone()
        if not row:
            return
        self.conn.execute(
            "UPDATE stock_blocks SET status='CLOSED' WHERE id=?",
            (int(block_id),),
        )
        self._update_balance(
            self.conn,
            int(row["company_id"]),
            int(row["branch_id"]),
            int(row["warehouse_id"]),
            int(row["location_id"]),
            int(row["item_id"]),
            0,
            blocked_delta=-safe_float(row["qty"]),
        )
        self.conn.commit()

    def _ensure_outbound_available(
        self,
        company_id: int,
        branch_id: int,
        warehouse_id: int,
        location_id: int,
        item_id: int,
        qty: float,
        negative_stock_policy: str,
    ) -> None:
        row = self.conn.execute(
            """
            SELECT qty_on_hand, qty_reserved, qty_blocked
            FROM stock_balance
            WHERE company_id=? AND branch_id=? AND warehouse_id=? AND location_id=? AND item_id=?
            """,
            (int(company_id), int(branch_id), int(warehouse_id), int(location_id), int(item_id)),
        ).fetchone()
        on_hand = safe_float(row["qty_on_hand"] if row else 0)
        reserved = safe_float(row["qty_reserved"] if row else 0)
        blocked = safe_float(row["qty_blocked"] if row else 0)
        available = on_hand - reserved - blocked
        if available + 1e-9 < qty:
            if negative_stock_policy == "allow":
                return
            if negative_stock_policy == "warn":
                self._audit(
                    company_id,
                    "stock_policy",
                    item_id,
                    "NEGATIVE_WARN",
                    None,
                    f"Available {available} < {qty}",
                )
                return
            raise ValueError("Insufficient stock for outbound movement.")

    def _update_balance(
        self,
        cur: sqlite3.Connection | sqlite3.Cursor,
        company_id: int,
        branch_id: int,
        warehouse_id: int,
        location_id: int,
        item_id: int,
        qty_delta: float,
        reserved_delta: float = 0,
        blocked_delta: float = 0,
    ) -> None:
        cur.execute(
            """
            INSERT INTO stock_balance(
                company_id, branch_id, warehouse_id, location_id, item_id,
                qty_on_hand, qty_reserved, qty_blocked
            ) VALUES(?,?,?,?,?,?,?,?)
            ON CONFLICT(company_id, branch_id, warehouse_id, location_id, item_id)
            DO UPDATE SET
                qty_on_hand = qty_on_hand + excluded.qty_on_hand,
                qty_reserved = qty_reserved + excluded.qty_reserved,
                qty_blocked = qty_blocked + excluded.qty_blocked,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                int(company_id),
                int(branch_id),
                int(warehouse_id),
                int(location_id),
                int(item_id),
                float(qty_delta),
                float(reserved_delta),
                float(blocked_delta),
            ),
        )

    def _insert_ledger(
        self,
        cur: sqlite3.Cursor,
        company_id: int,
        branch_id: int,
        warehouse_id: int,
        location_id: int,
        item_id: int,
        lot_id: Optional[int],
        serial_id: Optional[int],
        doc_id: int,
        doc_line_id: Optional[int],
        txn_date: str,
        qty: float,
        direction: str,
        cost: float,
    ) -> None:
        cur.execute(
            """
            INSERT INTO stock_ledger(
                company_id, branch_id, warehouse_id, location_id, item_id,
                lot_id, serial_id, doc_id, doc_line_id, txn_date,
                qty, direction, cost
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                int(company_id),
                int(branch_id),
                int(warehouse_id),
                int(location_id) if location_id else None,
                int(item_id),
                int(lot_id) if lot_id else None,
                int(serial_id) if serial_id else None,
                int(doc_id),
                int(doc_line_id) if doc_line_id else None,
                parse_date_smart(txn_date),
                float(qty),
                str(direction),
                float(cost),
            ),
        )

    def _exceeds_tolerance(self, diff_qty: float, tol_qty: float, tol_pct: float, base_qty: float) -> bool:
        diff_abs = abs(diff_qty)
        if tol_qty == 0 and tol_pct == 0:
            return diff_abs > 0
        if tol_qty and diff_abs > tol_qty:
            return True
        if tol_pct:
            base = abs(base_qty) if abs(base_qty) > 0 else 1
            if (diff_abs / base) * 100 > tol_pct:
                return True
        return False

    def _audit(
        self,
        company_id: int,
        entity_type: str,
        entity_id: int,
        action: str,
        actor_id: Optional[int],
        details: str,
    ) -> None:
        try:
            _ensure_app_logger()
            self.conn.execute(
                """
                INSERT INTO audit_log(company_id, entity_type, entity_id, action, actor_id, details)
                VALUES(?,?,?,?,?,?)
                """,
                (
                    int(company_id),
                    str(entity_type),
                    int(entity_id),
                    str(action),
                    int(actor_id) if actor_id else None,
                    str(details or ""),
                ),
            )
            self.conn.commit()
            logger.info("audit_log %s %s %s", entity_type, action, details)
        except Exception:
            logger.exception("Failed to write audit log.")

    # -----------------
    # Cost helpers
    # -----------------
    def calculate_fifo_cost(
        self,
        company_id: int,
        branch_id: int,
        warehouse_id: int,
        item_id: int,
        qty: float,
    ) -> float:
        remaining = abs(qty)
        total = 0.0
        rows = self.conn.execute(
            """
            SELECT qty, cost FROM stock_ledger
            WHERE company_id=? AND branch_id=? AND warehouse_id=? AND item_id=? AND qty>0
            ORDER BY txn_date ASC, id ASC
            """,
            (int(company_id), int(branch_id), int(warehouse_id), int(item_id)),
        ).fetchall()
        for row in rows:
            if remaining <= 0:
                break
            take = min(remaining, safe_float(row["qty"]))
            total += take * safe_float(row["cost"])
            remaining -= take
        return total

    def calculate_weighted_avg_cost(
        self,
        company_id: int,
        branch_id: int,
        warehouse_id: int,
        item_id: int,
    ) -> float:
        row = self.conn.execute(
            """
            SELECT SUM(qty) AS qty_sum, SUM(qty * cost) AS cost_sum
            FROM stock_ledger
            WHERE company_id=? AND branch_id=? AND warehouse_id=? AND item_id=? AND qty>0
            """,
            (int(company_id), int(branch_id), int(warehouse_id), int(item_id)),
        ).fetchone()
        qty_sum = safe_float(row["qty_sum"] if row else 0)
        if qty_sum <= 0:
            return 0.0
        return safe_float(row["cost_sum"] if row else 0) / qty_sum

    @staticmethod
    def allocate_landed_cost(total_cost: float, weights: Iterable[float]) -> List[float]:
        weights = [safe_float(w) for w in weights]
        total_weight = sum(weights) or 1.0
        allocated = [total_cost * (w / total_weight) for w in weights]
        diff = total_cost - sum(allocated)
        if allocated:
            allocated[-1] += diff
        return allocated
