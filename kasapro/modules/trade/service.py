# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from ...db.main_db import DB
from ...utils import parse_date_smart, today_iso
from .permissions import has_permission
from .repo import TradeRepo


@dataclass
class TradeUserContext:
    user_id: Optional[int]
    username: str
    app_role: str


class TradeService:
    def __init__(self, db: DB, user_ctx: TradeUserContext, company_id: Optional[int] = None):
        self.db = db
        self.user_ctx = user_ctx
        self.company_id = int(company_id or 0)
        self.repo = TradeRepo(db.conn)

    def _role(self) -> str:
        if (self.user_ctx.app_role or "").strip().lower() == "admin":
            return "admin"
        if self.user_ctx.user_id is None:
            return "read-only"
        role = self.repo.get_user_role(self.company_id, int(self.user_ctx.user_id))
        return role or "read-only"

    def require(self, permission: str) -> None:
        role = self._role()
        if not has_permission(role, permission):
            raise PermissionError(f"{role} rolü için yetki yok: {permission}")

    def set_user_role(self, user_id: int, username: str, role: str) -> None:
        self.require("settings")
        self.repo.set_user_role(self.company_id, int(user_id), username, role)
        self.repo.add_audit_log(
            self.company_id,
            self.user_ctx.user_id,
            self.user_ctx.username,
            "update",
            "trade_user_roles",
            None,
            f"{username} -> {role}",
        )

    def list_roles(self) -> List[Dict[str, Any]]:
        return [dict(r) for r in self.repo.list_user_roles(self.company_id)]

    def list_warehouses(self) -> List[Dict[str, Any]]:
        self.repo.ensure_default_warehouse(self.company_id)
        return [dict(r) for r in self.repo.list_warehouses(self.company_id)]

    def create_sales_invoice(
        self,
        doc_no: str,
        doc_date: Any,
        cari_id: Optional[int],
        cari_name: str,
        lines: Iterable[Dict[str, Any]],
        currency: str = "TL",
        notes: str = "",
    ) -> int:
        self.require("sales")
        subtotal, tax_total, total = self._calc_totals(lines)
        doc_id = self.repo.create_doc(
            self.company_id,
            "sales_invoice",
            doc_no,
            doc_date,
            "posted",
            cari_id,
            cari_name,
            currency,
            subtotal,
            tax_total,
            0.0,
            total,
            notes,
        )
        self.repo.add_doc_lines(doc_id, lines)
        warehouse_id = self.repo.ensure_default_warehouse(self.company_id)
        for line in lines:
            self.repo.create_stock_move(
                self.company_id,
                doc_id,
                None,
                str(line.get("item") or ""),
                float(line.get("qty") or 0),
                str(line.get("unit") or "Adet"),
                "OUT",
                warehouse_id,
                "sales_invoice",
            )
        if cari_id:
            self.db.cari_hareket_add(
                parse_date_smart(doc_date),
                int(cari_id),
                "Alacak",
                total,
                currency,
                f"Satış Faturası {doc_no}",
                "",
                doc_no,
                "trade",
            )
        self.repo.add_audit_log(
            self.company_id,
            self.user_ctx.user_id,
            self.user_ctx.username,
            "create",
            "trade_doc",
            doc_id,
            f"sales_invoice {doc_no}",
        )
        return doc_id

    def create_sales_return(self, original_doc_id: int, doc_no: str, doc_date: Any) -> int:
        self.require("sales")
        original = self.repo.get_doc(original_doc_id)
        if not original:
            raise ValueError("Orijinal fatura bulunamadı")
        lines = [dict(l) for l in self.repo.list_doc_lines(original_doc_id)]
        subtotal, tax_total, total = self._calc_totals(lines)
        doc_id = self.repo.create_doc(
            self.company_id,
            "sales_return",
            doc_no,
            doc_date,
            "posted",
            original["cari_id"],
            original["cari_name"],
            original["currency"],
            subtotal,
            tax_total,
            0.0,
            total,
            f"Satış iade (ref #{original_doc_id})",
            related_doc_id=original_doc_id,
        )
        self.repo.add_doc_lines(doc_id, lines)
        warehouse_id = self.repo.ensure_default_warehouse(self.company_id)
        for line in lines:
            self.repo.create_stock_move(
                self.company_id,
                doc_id,
                None,
                str(line.get("item") or ""),
                float(line.get("qty") or 0),
                str(line.get("unit") or "Adet"),
                "IN",
                warehouse_id,
                "sales_return",
            )
        if original["cari_id"]:
            self.db.cari_hareket_add(
                parse_date_smart(doc_date),
                int(original["cari_id"]),
                "Borç",
                total,
                original["currency"],
                f"Satış İade {doc_no}",
                "",
                doc_no,
                "trade",
            )
        self.repo.add_audit_log(
            self.company_id,
            self.user_ctx.user_id,
            self.user_ctx.username,
            "create",
            "trade_doc",
            doc_id,
            f"sales_return {doc_no}",
        )
        return doc_id

    def create_purchase_invoice(
        self,
        doc_no: str,
        doc_date: Any,
        cari_id: Optional[int],
        cari_name: str,
        lines: Iterable[Dict[str, Any]],
        currency: str = "TL",
        notes: str = "",
    ) -> int:
        self.require("purchase")
        subtotal, tax_total, total = self._calc_totals(lines)
        doc_id = self.repo.create_doc(
            self.company_id,
            "purchase_invoice",
            doc_no,
            doc_date,
            "posted",
            cari_id,
            cari_name,
            currency,
            subtotal,
            tax_total,
            0.0,
            total,
            notes,
        )
        self.repo.add_doc_lines(doc_id, lines)
        warehouse_id = self.repo.ensure_default_warehouse(self.company_id)
        for line in lines:
            self.repo.create_stock_move(
                self.company_id,
                doc_id,
                None,
                str(line.get("item") or ""),
                float(line.get("qty") or 0),
                str(line.get("unit") or "Adet"),
                "IN",
                warehouse_id,
                "purchase_invoice",
            )
        if cari_id:
            self.db.cari_hareket_add(
                parse_date_smart(doc_date),
                int(cari_id),
                "Borç",
                total,
                currency,
                f"Alış Faturası {doc_no}",
                "",
                doc_no,
                "trade",
            )
        self.repo.add_audit_log(
            self.company_id,
            self.user_ctx.user_id,
            self.user_ctx.username,
            "create",
            "trade_doc",
            doc_id,
            f"purchase_invoice {doc_no}",
        )
        return doc_id

    def create_purchase_return(self, original_doc_id: int, doc_no: str, doc_date: Any) -> int:
        self.require("purchase")
        original = self.repo.get_doc(original_doc_id)
        if not original:
            raise ValueError("Orijinal fatura bulunamadı")
        lines = [dict(l) for l in self.repo.list_doc_lines(original_doc_id)]
        subtotal, tax_total, total = self._calc_totals(lines)
        doc_id = self.repo.create_doc(
            self.company_id,
            "purchase_return",
            doc_no,
            doc_date,
            "posted",
            original["cari_id"],
            original["cari_name"],
            original["currency"],
            subtotal,
            tax_total,
            0.0,
            total,
            f"Alış iade (ref #{original_doc_id})",
            related_doc_id=original_doc_id,
        )
        self.repo.add_doc_lines(doc_id, lines)
        warehouse_id = self.repo.ensure_default_warehouse(self.company_id)
        for line in lines:
            self.repo.create_stock_move(
                self.company_id,
                doc_id,
                None,
                str(line.get("item") or ""),
                float(line.get("qty") or 0),
                str(line.get("unit") or "Adet"),
                "OUT",
                warehouse_id,
                "purchase_return",
            )
        if original["cari_id"]:
            self.db.cari_hareket_add(
                parse_date_smart(doc_date),
                int(original["cari_id"]),
                "Alacak",
                total,
                original["currency"],
                f"Alış İade {doc_no}",
                "",
                doc_no,
                "trade",
            )
        self.repo.add_audit_log(
            self.company_id,
            self.user_ctx.user_id,
            self.user_ctx.username,
            "create",
            "trade_doc",
            doc_id,
            f"purchase_return {doc_no}",
        )
        return doc_id

    def record_payment(
        self,
        doc_id: int,
        amount: float,
        pay_date: Any,
        method: str,
        use_bank: bool = False,
        reference: str = "",
    ) -> int:
        self.require("payments")
        doc = self.repo.get_doc(doc_id)
        if not doc:
            raise ValueError("Belge bulunamadı")
        direction = "in" if doc["doc_type"].startswith("sales") else "out"
        currency = doc["currency"]
        kasa_hareket_id = None
        banka_hareket_id = None
        if use_bank:
            tip = "Giriş" if direction == "in" else "Çıkış"
            banka_hareket_id = self.db.banka_add(
                parse_date_smart(pay_date),
                method or "Banka",
                "",
                tip,
                float(amount),
                currency,
                f"{doc['doc_no']} ödeme",
                reference,
                doc["doc_no"],
                "trade",
            )
        else:
            tip = "Gelir" if direction == "in" else "Gider"
            kasa_hareket_id = self.db.kasa_add(
                parse_date_smart(pay_date),
                tip,
                float(amount),
                currency,
                method,
                "Ticari",
                doc["cari_id"],
                f"{doc['doc_no']} ödeme",
                doc["doc_no"],
                "trade",
            )
        if doc["cari_id"]:
            cari_tip = "Borç" if direction == "in" else "Alacak"
            self.db.cari_hareket_add(
                parse_date_smart(pay_date),
                int(doc["cari_id"]),
                cari_tip,
                float(amount),
                currency,
                f"Ödeme {doc['doc_no']}",
                method,
                doc["doc_no"],
                "trade",
            )
        pay_id = self.repo.create_payment(
            self.company_id,
            doc_id,
            pay_date,
            direction,
            float(amount),
            currency,
            method,
            reference,
            kasa_hareket_id,
            banka_hareket_id,
            "",
        )
        self.repo.add_audit_log(
            self.company_id,
            self.user_ctx.user_id,
            self.user_ctx.username,
            "create",
            "trade_payment",
            pay_id,
            f"{doc['doc_no']} {amount}",
        )
        return pay_id

    def create_order(
        self,
        order_type: str,
        order_no: str,
        order_date: Any,
        cari_id: Optional[int],
        cari_name: str,
        lines: Iterable[Dict[str, Any]],
        currency: str = "TL",
        notes: str = "",
    ) -> int:
        self.require("orders")
        total = sum(float(l.get("line_total") or 0) for l in lines)
        order_id = self.repo.create_order(
            self.company_id,
            order_type,
            order_no,
            order_date,
            "Açık",
            cari_id,
            cari_name,
            currency,
            total,
            notes,
        )
        self.repo.add_order_lines(order_id, lines)
        self.repo.add_audit_log(
            self.company_id,
            self.user_ctx.user_id,
            self.user_ctx.username,
            "create",
            "trade_order",
            order_id,
            f"{order_type} {order_no}",
        )
        return order_id

    def fulfill_order_to_invoice(
        self,
        order_id: int,
        doc_no: str,
        doc_date: Any,
        fulfill_map: Optional[Dict[int, float]] = None,
    ) -> int:
        self.require("orders")
        order = self.repo.get_order(order_id)
        if not order:
            raise ValueError("Sipariş bulunamadı")
        lines = []
        has_partial = False
        for line in self.repo.list_order_line_summary(order_id):
            remaining = float(line["qty"]) - float(line["fulfilled_qty"])
            qty = remaining
            if fulfill_map and int(line["id"]) in fulfill_map:
                qty = min(remaining, float(fulfill_map[int(line["id"])]) or 0)
            if qty <= 0:
                continue
            if qty < remaining:
                has_partial = True
            line_total = qty * float(line["unit_price"])
            lines.append(
                {
                    "item": line["item"],
                    "description": "",
                    "qty": qty,
                    "unit": line["unit"],
                    "unit_price": float(line["unit_price"]),
                    "tax_rate": 20,
                    "line_total": line_total,
                    "tax_total": line_total * 0.2,
                }
            )
            self.repo.update_order_line_fulfilled(int(line["id"]), float(line["fulfilled_qty"]) + qty)
        if not lines:
            raise ValueError("Sevk edilecek satır yok")
        if order["order_type"] == "sales":
            doc_id = self.create_sales_invoice(
                doc_no,
                doc_date,
                order["cari_id"],
                order["cari_name"],
                lines,
                order["currency"],
                notes=f"Sipariş dönüşümü #{order_id}",
            )
        else:
            doc_id = self.create_purchase_invoice(
                doc_no,
                doc_date,
                order["cari_id"],
                order["cari_name"],
                lines,
                order["currency"],
                notes=f"Sipariş dönüşümü #{order_id}",
            )
        new_status = "Kısmi" if has_partial else "Kapalı"
        if has_partial:
            remaining_any = False
            for line in self.repo.list_order_line_summary(order_id):
                if float(line["qty"]) > float(line["fulfilled_qty"]):
                    remaining_any = True
            if not remaining_any:
                new_status = "Kapalı"
        self.repo.update_order_status(order_id, new_status)
        self.repo.add_audit_log(
            self.company_id,
            self.user_ctx.user_id,
            self.user_ctx.username,
            "update",
            "trade_order",
            order_id,
            f"{order['order_no']} -> {new_status}",
        )
        return doc_id

    def void_doc(self, doc_id: int, reason: str = "") -> None:
        doc = self.repo.get_doc(doc_id)
        if not doc:
            raise ValueError("Belge bulunamadı")
        if doc["doc_type"].startswith("purchase"):
            self.require("purchase")
        else:
            self.require("sales")
        self.repo.update_doc_status(doc_id, "void")
        self.repo.add_audit_log(
            self.company_id,
            self.user_ctx.user_id,
            self.user_ctx.username,
            "void",
            "trade_doc",
            doc_id,
            reason or "void",
        )

    def stock_balance(self, item: str) -> float:
        rows = self.repo.list_stock_summary(self.company_id, q=item, limit=1, offset=0)
        if not rows:
            return 0.0
        return float(rows[0]["balance"] or 0)

    def list_docs(self, doc_type: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        return [dict(r) for r in self.repo.list_docs(self.company_id, doc_type=doc_type, limit=limit, offset=offset)]

    def list_orders(self, order_type: Optional[str] = None) -> List[Dict[str, Any]]:
        return [dict(r) for r in self.repo.list_orders(self.company_id, order_type=order_type)]

    def list_doc_lines(self, doc_id: int) -> List[Dict[str, Any]]:
        return [dict(r) for r in self.repo.list_doc_lines(doc_id)]

    def list_stock(self, q: str = "", limit: int = 200, offset: int = 0) -> List[Dict[str, Any]]:
        return [dict(r) for r in self.repo.list_stock_summary(self.company_id, q=q, limit=limit, offset=offset)]

    def report_summary(self) -> Dict[str, List[Dict[str, Any]]]:
        self.require("reports")
        return {
            "daily_sales": [dict(r) for r in self.repo.report_daily_totals(self.company_id, "sales_invoice")],
            "daily_purchase": [dict(r) for r in self.repo.report_daily_totals(self.company_id, "purchase_invoice")],
            "monthly_sales": [dict(r) for r in self.repo.report_monthly_totals(self.company_id, "sales_invoice")],
            "monthly_purchase": [dict(r) for r in self.repo.report_monthly_totals(self.company_id, "purchase_invoice")],
            "top_sellers": [dict(r) for r in self.repo.report_top_items(self.company_id, "sales_invoice")],
            "top_buyers": [dict(r) for r in self.repo.report_top_items(self.company_id, "purchase_invoice")],
        }

    def cari_risk(self) -> List[Dict[str, Any]]:
        self.require("reports")
        rows = []
        for cari in self.db.cari_list():
            bakiye = self.db.cari_bakiye(int(cari["id"]))
            rows.append({"cari": cari["ad"], "bakiye": bakiye["bakiye"]})
        rows.sort(key=lambda x: x["bakiye"], reverse=True)
        return rows

    def save_settings(self, kdv_rates: str, price_lists: str, currency: str) -> None:
        self.require("settings")
        self.db.set_setting("trade_kdv_rates", kdv_rates)
        self.db.set_setting("trade_price_lists", price_lists)
        self.db.set_setting("trade_currency", currency)

    def load_settings(self) -> Dict[str, str]:
        return {
            "kdv_rates": self.db.get_setting("trade_kdv_rates") or "20",
            "price_lists": self.db.get_setting("trade_price_lists") or "Standart",
            "currency": self.db.get_setting("trade_currency") or "TL",
        }

    @staticmethod
    def _calc_totals(lines: Iterable[Dict[str, Any]]) -> tuple[float, float, float]:
        subtotal = 0.0
        tax_total = 0.0
        for line in lines:
            qty = float(line.get("qty") or 0)
            unit_price = float(line.get("unit_price") or 0)
            tax_rate = float(line.get("tax_rate") or 0)
            line_total = qty * unit_price
            line_tax = line_total * (tax_rate / 100)
            line["line_total"] = line_total
            line["tax_total"] = line_tax
            subtotal += line_total
            tax_total += line_tax
        total = subtotal + tax_total
        return subtotal, tax_total, total

    def next_doc_no(self, prefix: str) -> str:
        try:
            return self.db.next_belge_no(prefix=prefix)
        except Exception:
            return f"{prefix}-{today_iso()}"
