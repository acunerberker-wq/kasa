# -*- coding: utf-8 -*-

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from ...config import APP_TITLE
from ...utils import today_iso, fmt_amount
from ...ui.widgets import LabeledEntry, LabeledCombo, MoneyEntry
from .permissions import ROLE_PERMISSIONS, has_permission
from .service import TradeService, TradeUserContext


@dataclass
class _LineItem:
    item: str
    qty: float
    unit: str
    unit_price: float
    tax_rate: float

    def as_dict(self) -> Dict[str, Any]:
        return {
            "item": self.item,
            "qty": self.qty,
            "unit": self.unit,
            "unit_price": self.unit_price,
            "tax_rate": self.tax_rate,
        }


class TradeModuleFrame(ttk.Frame):
    def __init__(self, master: tk.Misc, app: Any):
        super().__init__(master)
        self.app = app
        self._report_queue: queue.Queue = queue.Queue()
        user_ctx = TradeUserContext(
            user_id=getattr(app, "data_owner_user_id", None),
            username=str(getattr(app, "data_owner_username", "")),
            app_role=str(getattr(app, "user", {}).get("role", "")),
        )
        company_id = getattr(app, "active_company_id", None)
        self.service = TradeService(app.db, user_ctx, company_id=company_id)
        self.service.repo.ensure_default_warehouse(self.service.company_id)
        self._build_ui()
        self._load_sales_list()
        self._load_purchase_list()
        self._load_order_list()
        self._load_stock_list()
        self._load_roles()
        self._refresh_settings()

    def _build_ui(self) -> None:
        header = ttk.Frame(self)
        header.pack(fill=tk.X, padx=12, pady=8)
        ttk.Label(header, text="🏭 Gelişmiş Alış/Satış (Ticari) Modülü", style="PageTitle.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text=f"Şirket: {getattr(self.app, 'active_company_name', '')}",
            style="SidebarSub.TLabel",
        ).pack(anchor="w", pady=(2, 0))

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        self.sales_tab = ttk.Frame(self.nb)
        self.purchase_tab = ttk.Frame(self.nb)
        self.orders_tab = ttk.Frame(self.nb)
        self.stock_tab = ttk.Frame(self.nb)
        self.reports_tab = ttk.Frame(self.nb)
        self.settings_tab = ttk.Frame(self.nb)

        self.nb.add(self.sales_tab, text="Ticari > Satış")
        self.nb.add(self.purchase_tab, text="Ticari > Alış")
        self.nb.add(self.orders_tab, text="Sipariş Yönetimi")
        self.nb.add(self.stock_tab, text="Stok")
        self.nb.add(self.reports_tab, text="Raporlar")
        self.nb.add(self.settings_tab, text="Ayarlar")

        self._build_sales_tab()
        self._build_purchase_tab()
        self._build_orders_tab()
        self._build_stock_tab()
        self._build_reports_tab()
        self._build_settings_tab()
        
        # Refresh cari after all tabs are built
        self._refresh_cari()

    def _ensure_permission(self, permission: str) -> bool:
        role = self.service._role()
        if not has_permission(role, permission):
            messagebox.showwarning(APP_TITLE, f"Bu ekran için yetkiniz yok. (Rol: {role})")
            return False
        return True

    def _build_sales_tab(self) -> None:
        form = ttk.LabelFrame(self.sales_tab, text="Fatura Oluştur")
        form.pack(fill=tk.X, padx=8, pady=8)

        row1 = ttk.Frame(form)
        row1.pack(fill=tk.X, padx=8, pady=4)
        self.sales_doc_no = LabeledEntry(row1, "Belge No:")
        self.sales_doc_no.pack(side=tk.LEFT, padx=4)
        self.sales_doc_date = LabeledEntry(row1, "Tarih:")
        self.sales_doc_date.pack(side=tk.LEFT, padx=4)
        ttk.Button(row1, text="No Üret", command=self._sales_next_no).pack(side=tk.LEFT, padx=4)

        row2 = ttk.Frame(form)
        row2.pack(fill=tk.X, padx=8, pady=4)
        self.sales_cari = LabeledCombo(row2, "Cari:", [], width=26)
        self.sales_cari.pack(side=tk.LEFT, padx=4)
        ttk.Button(row2, text="Yenile", command=self._refresh_cari).pack(side=tk.LEFT, padx=4)

        row3 = ttk.Frame(form)
        row3.pack(fill=tk.X, padx=8, pady=4)
        self.sales_item = LabeledEntry(row3, "Ürün:")
        self.sales_item.pack(side=tk.LEFT, padx=4)
        self.sales_qty = LabeledEntry(row3, "Miktar:", width=8)
        self.sales_qty.pack(side=tk.LEFT, padx=4)
        self.sales_unit_price = MoneyEntry(row3, "Birim Fiyat:")
        self.sales_unit_price.pack(side=tk.LEFT, padx=4)
        self.sales_tax = LabeledEntry(row3, "KDV %:", width=6)
        self.sales_tax.pack(side=tk.LEFT, padx=4)
        ttk.Button(row3, text="Satır Ekle", command=self._sales_add_line).pack(side=tk.LEFT, padx=4)

        self.sales_lines: List[_LineItem] = []
        self.sales_lines_tree = ttk.Treeview(form, columns=("item", "qty", "unit", "price", "tax"), show="headings", height=4)
        for col, label, width in (
            ("item", "Ürün", 240),
            ("qty", "Miktar", 80),
            ("unit", "Birim", 70),
            ("price", "Birim Fiyat", 100),
            ("tax", "KDV %", 60),
        ):
            self.sales_lines_tree.heading(col, text=label)
            self.sales_lines_tree.column(col, width=width, anchor="center")
        self.sales_lines_tree.pack(fill=tk.X, padx=8, pady=6)

        ttk.Button(form, text="Kaydet", command=self._sales_save).pack(anchor="e", padx=8, pady=(0, 8))

        list_frame = ttk.LabelFrame(self.sales_tab, text="Fatura Listesi")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.sales_tree = ttk.Treeview(list_frame, columns=("no", "date", "cari", "total", "status"), show="headings")
        for col, label, width in (
            ("no", "Belge No", 140),
            ("date", "Tarih", 100),
            ("cari", "Cari", 180),
            ("total", "Toplam", 120),
            ("status", "Durum", 90),
        ):
            self.sales_tree.heading(col, text=label)
            self.sales_tree.column(col, width=width)
        self.sales_tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        btns = ttk.Frame(list_frame)
        btns.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Button(btns, text="Detay", command=self._sales_detail).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="İade", command=self._sales_return).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Tahsilat", command=self._sales_payment).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="İptal", command=self._sales_void).pack(side=tk.LEFT, padx=4)

        self.sales_doc_date.set(today_iso())
        self.sales_tax.set("20")
        self._sales_next_no()

    def _build_purchase_tab(self) -> None:
        form = ttk.LabelFrame(self.purchase_tab, text="Alış Faturası Oluştur")
        form.pack(fill=tk.X, padx=8, pady=8)

        row1 = ttk.Frame(form)
        row1.pack(fill=tk.X, padx=8, pady=4)
        self.purchase_doc_no = LabeledEntry(row1, "Belge No:")
        self.purchase_doc_no.pack(side=tk.LEFT, padx=4)
        self.purchase_doc_date = LabeledEntry(row1, "Tarih:")
        self.purchase_doc_date.pack(side=tk.LEFT, padx=4)
        ttk.Button(row1, text="No Üret", command=self._purchase_next_no).pack(side=tk.LEFT, padx=4)

        row2 = ttk.Frame(form)
        row2.pack(fill=tk.X, padx=8, pady=4)
        self.purchase_cari = LabeledCombo(row2, "Cari:", [], width=26)
        self.purchase_cari.pack(side=tk.LEFT, padx=4)
        ttk.Button(row2, text="Yenile", command=self._refresh_cari).pack(side=tk.LEFT, padx=4)

        row3 = ttk.Frame(form)
        row3.pack(fill=tk.X, padx=8, pady=4)
        self.purchase_item = LabeledEntry(row3, "Ürün:")
        self.purchase_item.pack(side=tk.LEFT, padx=4)
        self.purchase_qty = LabeledEntry(row3, "Miktar:", width=8)
        self.purchase_qty.pack(side=tk.LEFT, padx=4)
        self.purchase_unit_price = MoneyEntry(row3, "Birim Fiyat:")
        self.purchase_unit_price.pack(side=tk.LEFT, padx=4)
        self.purchase_tax = LabeledEntry(row3, "KDV %:", width=6)
        self.purchase_tax.pack(side=tk.LEFT, padx=4)
        ttk.Button(row3, text="Satır Ekle", command=self._purchase_add_line).pack(side=tk.LEFT, padx=4)

        self.purchase_lines: List[_LineItem] = []
        self.purchase_lines_tree = ttk.Treeview(form, columns=("item", "qty", "unit", "price", "tax"), show="headings", height=4)
        for col, label, width in (
            ("item", "Ürün", 240),
            ("qty", "Miktar", 80),
            ("unit", "Birim", 70),
            ("price", "Birim Fiyat", 100),
            ("tax", "KDV %", 60),
        ):
            self.purchase_lines_tree.heading(col, text=label)
            self.purchase_lines_tree.column(col, width=width, anchor="center")
        self.purchase_lines_tree.pack(fill=tk.X, padx=8, pady=6)

        ttk.Button(form, text="Kaydet", command=self._purchase_save).pack(anchor="e", padx=8, pady=(0, 8))

        list_frame = ttk.LabelFrame(self.purchase_tab, text="Alış Faturası Listesi")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.purchase_tree = ttk.Treeview(list_frame, columns=("no", "date", "cari", "total", "status"), show="headings")
        for col, label, width in (
            ("no", "Belge No", 140),
            ("date", "Tarih", 100),
            ("cari", "Cari", 180),
            ("total", "Toplam", 120),
            ("status", "Durum", 90),
        ):
            self.purchase_tree.heading(col, text=label)
            self.purchase_tree.column(col, width=width)
        self.purchase_tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        btns = ttk.Frame(list_frame)
        btns.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Button(btns, text="Detay", command=self._purchase_detail).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="İade", command=self._purchase_return).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Ödeme", command=self._purchase_payment).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="İptal", command=self._purchase_void).pack(side=tk.LEFT, padx=4)

        self.purchase_doc_date.set(today_iso())
        self.purchase_tax.set("20")
        self._purchase_next_no()

    def _build_orders_tab(self) -> None:
        form = ttk.LabelFrame(self.orders_tab, text="Sipariş Oluştur")
        form.pack(fill=tk.X, padx=8, pady=8)

        row1 = ttk.Frame(form)
        row1.pack(fill=tk.X, padx=8, pady=4)
        self.order_type = LabeledCombo(row1, "Tür:", ["sales", "purchase"], width=12)
        self.order_type.pack(side=tk.LEFT, padx=4)
        self.order_no = LabeledEntry(row1, "Sipariş No:")
        self.order_no.pack(side=tk.LEFT, padx=4)
        self.order_date = LabeledEntry(row1, "Tarih:")
        self.order_date.pack(side=tk.LEFT, padx=4)
        ttk.Button(row1, text="No Üret", command=self._order_next_no).pack(side=tk.LEFT, padx=4)

        row2 = ttk.Frame(form)
        row2.pack(fill=tk.X, padx=8, pady=4)
        self.order_cari = LabeledCombo(row2, "Cari:", [], width=26)
        self.order_cari.pack(side=tk.LEFT, padx=4)
        ttk.Button(row2, text="Yenile", command=self._refresh_cari).pack(side=tk.LEFT, padx=4)

        row3 = ttk.Frame(form)
        row3.pack(fill=tk.X, padx=8, pady=4)
        self.order_item = LabeledEntry(row3, "Ürün:")
        self.order_item.pack(side=tk.LEFT, padx=4)
        self.order_qty = LabeledEntry(row3, "Miktar:", width=8)
        self.order_qty.pack(side=tk.LEFT, padx=4)
        self.order_unit_price = MoneyEntry(row3, "Birim Fiyat:")
        self.order_unit_price.pack(side=tk.LEFT, padx=4)
        ttk.Button(row3, text="Satır Ekle", command=self._order_add_line).pack(side=tk.LEFT, padx=4)

        self.order_lines: List[_LineItem] = []
        self.order_lines_tree = ttk.Treeview(form, columns=("item", "qty", "unit", "price"), show="headings", height=4)
        for col, label, width in (
            ("item", "Ürün", 240),
            ("qty", "Miktar", 80),
            ("unit", "Birim", 70),
            ("price", "Birim Fiyat", 100),
        ):
            self.order_lines_tree.heading(col, text=label)
            self.order_lines_tree.column(col, width=width, anchor="center")
        self.order_lines_tree.pack(fill=tk.X, padx=8, pady=6)

        ttk.Button(form, text="Kaydet", command=self._order_save).pack(anchor="e", padx=8, pady=(0, 8))

        list_frame = ttk.LabelFrame(self.orders_tab, text="Sipariş Listesi")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.orders_tree = ttk.Treeview(list_frame, columns=("no", "date", "cari", "total", "status"), show="headings")
        for col, label, width in (
            ("no", "Sipariş No", 140),
            ("date", "Tarih", 100),
            ("cari", "Cari", 180),
            ("total", "Toplam", 120),
            ("status", "Durum", 90),
        ):
            self.orders_tree.heading(col, text=label)
            self.orders_tree.column(col, width=width)
        self.orders_tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        btns = ttk.Frame(list_frame)
        btns.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Button(btns, text="Kısmi Sevk", command=self._order_partial).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Fatura Oluştur", command=self._order_invoice).pack(side=tk.LEFT, padx=4)

        self.order_type.set("sales")
        self.order_date.set(today_iso())
        self._order_next_no()

    def _build_stock_tab(self) -> None:
        top = ttk.Frame(self.stock_tab)
        top.pack(fill=tk.X, padx=8, pady=8)

        ttk.Label(top, text="Stok Hareketleri & Transfer", style="SidebarSub.TLabel").pack(side=tk.LEFT)
        ttk.Button(top, text="Transfer", command=self._stock_transfer).pack(side=tk.RIGHT, padx=4)
        ttk.Button(top, text="Sayım Farkı", command=self._stock_adjust).pack(side=tk.RIGHT, padx=4)

        self.stock_tree = ttk.Treeview(self.stock_tab, columns=("item", "balance"), show="headings")
        self.stock_tree.heading("item", text="Ürün")
        self.stock_tree.heading("balance", text="Bakiye")
        self.stock_tree.column("item", width=240)
        self.stock_tree.column("balance", width=120, anchor="center")
        self.stock_tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

    def _build_reports_tab(self) -> None:
        top = ttk.Frame(self.reports_tab)
        top.pack(fill=tk.X, padx=8, pady=8)
        ttk.Label(top, text="Raporlar", style="SidebarSub.TLabel").pack(side=tk.LEFT)
        ttk.Button(top, text="Raporları Yenile", command=self._run_reports).pack(side=tk.RIGHT)

        self.report_tree = ttk.Treeview(self.reports_tab, columns=("type", "name", "value"), show="headings")
        for col, label, width in (
            ("type", "Rapor", 160),
            ("name", "Başlık", 240),
            ("value", "Değer", 140),
        ):
            self.report_tree.heading(col, text=label)
            self.report_tree.column(col, width=width)
        self.report_tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

    def _build_settings_tab(self) -> None:
        role_frame = ttk.LabelFrame(self.settings_tab, text="Roller & Yetkiler")
        role_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.roles_tree = ttk.Treeview(role_frame, columns=("username", "role"), show="headings")
        self.roles_tree.heading("username", text="Kullanıcı")
        self.roles_tree.heading("role", text="Rol")
        self.roles_tree.column("username", width=180)
        self.roles_tree.column("role", width=120, anchor="center")
        self.roles_tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        controls = ttk.Frame(role_frame)
        controls.pack(fill=tk.X, padx=6, pady=(0, 6))
        self.role_select = LabeledCombo(controls, "Rol:", list(ROLE_PERMISSIONS.keys()), width=16)
        self.role_select.pack(side=tk.LEFT, padx=4)
        ttk.Button(controls, text="Kaydet", command=self._role_save).pack(side=tk.LEFT, padx=4)

        settings = ttk.LabelFrame(self.settings_tab, text="Ticari Ayarlar")
        settings.pack(fill=tk.X, padx=8, pady=8)
        row = ttk.Frame(settings)
        row.pack(fill=tk.X, padx=8, pady=4)
        self.kdv_rates = LabeledEntry(row, "KDV Oranları:")
        self.kdv_rates.pack(side=tk.LEFT, padx=4)
        self.price_lists = LabeledEntry(row, "Fiyat Listeleri:")
        self.price_lists.pack(side=tk.LEFT, padx=4)
        self.currency = LabeledEntry(row, "Para Birimi:")
        self.currency.pack(side=tk.LEFT, padx=4)
        ttk.Button(settings, text="Kaydet", command=self._settings_save).pack(anchor="e", padx=8, pady=(0, 8))

    def _refresh_cari(self) -> None:
        rows = self.app.db.cari_list()
        names = [r["ad"] for r in rows]
        for cmb in (self.sales_cari, self.purchase_cari, self.order_cari):
            cmb.cmb.configure(values=names)
            if names:
                cmb.set(names[0])

    def _sales_next_no(self) -> None:
        self.sales_doc_no.set(self.service.next_doc_no("TRD-S"))

    def _purchase_next_no(self) -> None:
        self.purchase_doc_no.set(self.service.next_doc_no("TRD-A"))

    def _order_next_no(self) -> None:
        self.order_no.set(self.service.next_doc_no("TRD-SIP"))

    def _sales_add_line(self) -> None:
        item = self.sales_item.get().strip()
        if not item:
            return
        line = _LineItem(
            item=item,
            qty=float(self.sales_qty.get() or 0),
            unit="Adet",
            unit_price=float(self.sales_unit_price.get() or 0),
            tax_rate=float(self.sales_tax.get() or 0),
        )
        self.sales_lines.append(line)
        self.sales_lines_tree.insert("", tk.END, values=(line.item, line.qty, line.unit, line.unit_price, line.tax_rate))
        self.sales_item.set("")
        self.sales_qty.set("")
        self.sales_unit_price.set("")

    def _purchase_add_line(self) -> None:
        item = self.purchase_item.get().strip()
        if not item:
            return
        line = _LineItem(
            item=item,
            qty=float(self.purchase_qty.get() or 0),
            unit="Adet",
            unit_price=float(self.purchase_unit_price.get() or 0),
            tax_rate=float(self.purchase_tax.get() or 0),
        )
        self.purchase_lines.append(line)
        self.purchase_lines_tree.insert("", tk.END, values=(line.item, line.qty, line.unit, line.unit_price, line.tax_rate))
        self.purchase_item.set("")
        self.purchase_qty.set("")
        self.purchase_unit_price.set("")

    def _order_add_line(self) -> None:
        item = self.order_item.get().strip()
        if not item:
            return
        line = _LineItem(
            item=item,
            qty=float(self.order_qty.get() or 0),
            unit="Adet",
            unit_price=float(self.order_unit_price.get() or 0),
            tax_rate=0,
        )
        self.order_lines.append(line)
        self.order_lines_tree.insert("", tk.END, values=(line.item, line.qty, line.unit, line.unit_price))
        self.order_item.set("")
        self.order_qty.set("")
        self.order_unit_price.set("")

    def _sales_save(self) -> None:
        if not self._ensure_permission("sales"):
            return
        if not self.sales_lines:
            messagebox.showwarning(APP_TITLE, "En az 1 satır ekleyin.")
            return
        name = self.sales_cari.get()
        cari_id = self._cari_id_by_name(name)
        try:
            self.service.create_sales_invoice(
                self.sales_doc_no.get(),
                self.sales_doc_date.get(),
                cari_id,
                name,
                [l.as_dict() for l in self.sales_lines],
            )
        except Exception as exc:
            messagebox.showerror(APP_TITLE, str(exc))
            return
        self.sales_lines.clear()
        for item in self.sales_lines_tree.get_children():
            self.sales_lines_tree.delete(item)
        self._sales_next_no()
        self._load_sales_list()
        self._load_stock_list()

    def _purchase_save(self) -> None:
        if not self._ensure_permission("purchase"):
            return
        if not self.purchase_lines:
            messagebox.showwarning(APP_TITLE, "En az 1 satır ekleyin.")
            return
        name = self.purchase_cari.get()
        cari_id = self._cari_id_by_name(name)
        try:
            self.service.create_purchase_invoice(
                self.purchase_doc_no.get(),
                self.purchase_doc_date.get(),
                cari_id,
                name,
                [l.as_dict() for l in self.purchase_lines],
            )
        except Exception as exc:
            messagebox.showerror(APP_TITLE, str(exc))
            return
        self.purchase_lines.clear()
        for item in self.purchase_lines_tree.get_children():
            self.purchase_lines_tree.delete(item)
        self._purchase_next_no()
        self._load_purchase_list()
        self._load_stock_list()

    def _order_save(self) -> None:
        if not self._ensure_permission("orders"):
            return
        if not self.order_lines:
            messagebox.showwarning(APP_TITLE, "En az 1 satır ekleyin.")
            return
        name = self.order_cari.get()
        cari_id = self._cari_id_by_name(name)
        order_type = self.order_type.get() or "sales"
        lines = [
            {
                "item": l.item,
                "qty": l.qty,
                "unit": l.unit,
                "unit_price": l.unit_price,
                "line_total": l.qty * l.unit_price,
                "fulfilled_qty": 0,
            }
            for l in self.order_lines
        ]
        try:
            self.service.create_order(
                order_type,
                self.order_no.get(),
                self.order_date.get(),
                cari_id,
                name,
                lines,
            )
        except Exception as exc:
            messagebox.showerror(APP_TITLE, str(exc))
            return
        self.order_lines.clear()
        for item in self.order_lines_tree.get_children():
            self.order_lines_tree.delete(item)
        self._order_next_no()
        self._load_order_list()

    def _load_sales_list(self) -> None:
        for item in self.sales_tree.get_children():
            self.sales_tree.delete(item)
        for row in self.service.list_docs("sales_invoice", limit=200):
            self.sales_tree.insert(
                "",
                tk.END,
                iid=str(row["id"]),
                values=(row["doc_no"], row["doc_date"], row["cari_name"], fmt_amount(row["total"]), row["status"]),
            )

    def _load_purchase_list(self) -> None:
        for item in self.purchase_tree.get_children():
            self.purchase_tree.delete(item)
        for row in self.service.list_docs("purchase_invoice", limit=200):
            self.purchase_tree.insert(
                "",
                tk.END,
                iid=str(row["id"]),
                values=(row["doc_no"], row["doc_date"], row["cari_name"], fmt_amount(row["total"]), row["status"]),
            )

    def _load_order_list(self) -> None:
        for item in self.orders_tree.get_children():
            self.orders_tree.delete(item)
        for row in self.service.list_orders():
            self.orders_tree.insert(
                "",
                tk.END,
                iid=str(row["id"]),
                values=(row["order_no"], row["order_date"], row["cari_name"], fmt_amount(row["total"]), row["status"]),
            )

    def _load_stock_list(self) -> None:
        for item in self.stock_tree.get_children():
            self.stock_tree.delete(item)
        for row in self.service.list_stock(limit=200):
            self.stock_tree.insert("", tk.END, values=(row["item"], fmt_amount(row["balance"])))

    def _load_roles(self) -> None:
        for item in self.roles_tree.get_children():
            self.roles_tree.delete(item)
        rows = self.service.list_roles()
        roles_map = {r["user_id"]: r for r in rows}
        for user in self.app.usersdb.list_users():
            assigned = roles_map.get(int(user["id"]))
            role = assigned["role"] if assigned else "read-only"
            self.roles_tree.insert("", tk.END, iid=str(user["id"]), values=(user["username"], role))

    def _sales_detail(self) -> None:
        doc_id = self._selected_id(self.sales_tree)
        if not doc_id:
            return
        lines = self.service.list_doc_lines(int(doc_id))
        detail = "\n".join(
            f"{l['item']} x{l['qty']} = {fmt_amount(l['line_total'])}" for l in lines
        )
        messagebox.showinfo(APP_TITLE, detail or "Satır yok")

    def _purchase_detail(self) -> None:
        doc_id = self._selected_id(self.purchase_tree)
        if not doc_id:
            return
        lines = self.service.list_doc_lines(int(doc_id))
        detail = "\n".join(
            f"{l['item']} x{l['qty']} = {fmt_amount(l['line_total'])}" for l in lines
        )
        messagebox.showinfo(APP_TITLE, detail or "Satır yok")

    def _sales_return(self) -> None:
        if not self._ensure_permission("sales"):
            return
        doc_id = self._selected_id(self.sales_tree)
        if not doc_id:
            return
        try:
            self.service.create_sales_return(int(doc_id), self.service.next_doc_no("TRD-SR"), today_iso())
        except Exception as exc:
            messagebox.showerror(APP_TITLE, str(exc))
            return
        self._load_sales_list()
        self._load_stock_list()

    def _purchase_return(self) -> None:
        if not self._ensure_permission("purchase"):
            return
        doc_id = self._selected_id(self.purchase_tree)
        if not doc_id:
            return
        try:
            self.service.create_purchase_return(int(doc_id), self.service.next_doc_no("TRD-AR"), today_iso())
        except Exception as exc:
            messagebox.showerror(APP_TITLE, str(exc))
            return
        self._load_purchase_list()
        self._load_stock_list()

    def _sales_payment(self) -> None:
        if not self._ensure_permission("payments"):
            return
        doc_id = self._selected_id(self.sales_tree)
        if not doc_id:
            return
        try:
            self.app.open_create_center("tahsilat", {"doc_id": int(doc_id)})
        except Exception:
            pass

    def _purchase_payment(self) -> None:
        if not self._ensure_permission("payments"):
            return
        doc_id = self._selected_id(self.purchase_tree)
        if not doc_id:
            return
        amount = simpledialog.askfloat(APP_TITLE, "Ödeme tutarı")
        if not amount:
            return
        try:
            self.service.record_payment(int(doc_id), amount, today_iso(), "Nakit", use_bank=False)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, str(exc))
            return
        self._load_purchase_list()

    def _sales_void(self) -> None:
        doc_id = self._selected_id(self.sales_tree)
        if not doc_id:
            return
        self.service.void_doc(int(doc_id), "UI void")
        self._load_sales_list()

    def _purchase_void(self) -> None:
        doc_id = self._selected_id(self.purchase_tree)
        if not doc_id:
            return
        self.service.void_doc(int(doc_id), "UI void")
        self._load_purchase_list()

    def _order_partial(self) -> None:
        if not self._ensure_permission("orders"):
            return
        order_id = self._selected_id(self.orders_tree)
        if not order_id:
            return
        qty = simpledialog.askfloat(APP_TITLE, "Sevk edilecek miktar")
        if not qty or qty <= 0:
            return
        lines = self.service.repo.list_order_line_summary(int(order_id))
        if not lines:
            return
        fulfill_map = {int(lines[0]["id"]): float(qty)}
        try:
            self.service.fulfill_order_to_invoice(int(order_id), self.service.next_doc_no("TRD-S"), today_iso(), fulfill_map)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, str(exc))
            return
        self._load_order_list()
        self._load_sales_list()
        self._load_stock_list()

    def _order_invoice(self) -> None:
        if not self._ensure_permission("orders"):
            return
        order_id = self._selected_id(self.orders_tree)
        if not order_id:
            return
        try:
            self.service.fulfill_order_to_invoice(int(order_id), self.service.next_doc_no("TRD-S"), today_iso())
        except Exception as exc:
            messagebox.showerror(APP_TITLE, str(exc))
            return
        self._load_order_list()
        self._load_sales_list()
        self._load_stock_list()

    def _stock_transfer(self) -> None:
        if not self._ensure_permission("stock"):
            return
        item = simpledialog.askstring(APP_TITLE, "Ürün adı")
        if not item:
            return
        qty = simpledialog.askfloat(APP_TITLE, "Miktar")
        if not qty:
            return
        warehouses = self.service.list_warehouses()
        names = [w["name"] for w in warehouses]
        if len(names) < 2:
            messagebox.showwarning(APP_TITLE, "Transfer için en az 2 depo gerekiyor.")
            return
        src = simpledialog.askstring(APP_TITLE, f"Kaynak depo ({', '.join(names)})")
        dst = simpledialog.askstring(APP_TITLE, f"Hedef depo ({', '.join(names)})")
        wh_map = {w["name"]: int(w["id"]) for w in warehouses}
        if src not in wh_map or dst not in wh_map:
            return
        self.service.repo.create_stock_move(
            self.service.company_id,
            None,
            None,
            item,
            float(qty),
            "Adet",
            "OUT",
            wh_map[src],
            "transfer",
            note=f"Transfer -> {dst}",
        )
        self.service.repo.create_stock_move(
            self.service.company_id,
            None,
            None,
            item,
            float(qty),
            "Adet",
            "IN",
            wh_map[dst],
            "transfer",
            note=f"Transfer <- {src}",
        )
        self._load_stock_list()

    def _stock_adjust(self) -> None:
        if not self._ensure_permission("stock"):
            return
        item = simpledialog.askstring(APP_TITLE, "Ürün adı")
        if not item:
            return
        qty = simpledialog.askfloat(APP_TITLE, "Fark miktarı (+/-)")
        if qty is None:
            return
        direction = "IN" if qty >= 0 else "OUT"
        self.service.repo.create_stock_move(
            self.service.company_id,
            None,
            None,
            item,
            abs(float(qty)),
            "Adet",
            direction,
            None,
            "count_adjustment",
        )
        self._load_stock_list()

    def _run_reports(self) -> None:
        if not self._ensure_permission("reports"):
            return
        self.report_tree.delete(*self.report_tree.get_children())

        def worker():
            try:
                data = self.service.report_summary()
                risk = self.service.cari_risk()
                self._report_queue.put((data, risk))
            except Exception as exc:
                self._report_queue.put(exc)

        threading.Thread(target=worker, daemon=True).start()
        self.after(120, self._poll_reports)

    def _poll_reports(self) -> None:
        try:
            result = self._report_queue.get_nowait()
        except queue.Empty:
            self.after(120, self._poll_reports)
            return
        if isinstance(result, Exception):
            messagebox.showerror(APP_TITLE, str(result))
            return
        data, risk = result
        for row in data.get("daily_sales", []):
            self.report_tree.insert("", tk.END, values=("Günlük Satış", row["doc_date"], fmt_amount(row["total"])))
        for row in data.get("daily_purchase", []):
            self.report_tree.insert("", tk.END, values=("Günlük Alış", row["doc_date"], fmt_amount(row["total"])))
        for row in data.get("monthly_sales", []):
            self.report_tree.insert("", tk.END, values=("Aylık Satış", row["ym"], fmt_amount(row["total"])))
        for row in data.get("monthly_purchase", []):
            self.report_tree.insert("", tk.END, values=("Aylık Alış", row["ym"], fmt_amount(row["total"])))
        for row in data.get("top_sellers", []):
            self.report_tree.insert("", tk.END, values=("Top Satış", row["item"], fmt_amount(row["total"])))
        for row in data.get("top_buyers", []):
            self.report_tree.insert("", tk.END, values=("Top Alış", row["item"], fmt_amount(row["total"])))
        for row in risk[:10]:
            self.report_tree.insert("", tk.END, values=("Cari Risk", row["cari"], fmt_amount(row["bakiye"])))

    def _role_save(self) -> None:
        if not self._ensure_permission("settings"):
            return
        user_id = self._selected_id(self.roles_tree)
        if not user_id:
            return
        role = self.role_select.get()
        if not role:
            return
        user = self.app.usersdb.conn.execute("SELECT username FROM users WHERE id=?", (int(user_id),)).fetchone()
        if not user:
            return
        try:
            self.service.set_user_role(int(user_id), user["username"], role)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, str(exc))
            return
        self._load_roles()

    def _refresh_settings(self) -> None:
        settings = self.service.load_settings()
        self.kdv_rates.set(settings["kdv_rates"])
        self.price_lists.set(settings["price_lists"])
        self.currency.set(settings["currency"])

    def _settings_save(self) -> None:
        if not self._ensure_permission("settings"):
            return
        self.service.save_settings(self.kdv_rates.get(), self.price_lists.get(), self.currency.get())
        messagebox.showinfo(APP_TITLE, "Kaydedildi")

    @staticmethod
    def _selected_id(tree: ttk.Treeview) -> Optional[str]:
        sel = tree.selection()
        if not sel:
            return None
        return sel[0]

    def _cari_id_by_name(self, name: str) -> Optional[int]:
        row = self.app.db.cari_get_by_name(name)
        if row:
            return int(row["id"])
        return None
