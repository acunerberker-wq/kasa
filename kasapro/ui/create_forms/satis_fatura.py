# -*- coding: utf-8 -*-
"""Create Center form: Satış Faturası."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import tkinter as tk
from tkinter import ttk, messagebox

from ...config import APP_TITLE
from ...utils import today_iso, safe_float
from ...modules.trade.service import TradeService, TradeUserContext
from ..widgets import LabeledEntry, LabeledCombo, MoneyEntry
from .base import BaseCreateForm


class SatisFaturaCreateForm(BaseCreateForm):
    def __init__(self, master: tk.Misc, app: Any) -> None:
        self._lines: List[Dict[str, Any]] = []
        self._cari_map: Dict[str, Optional[int]] = {}
        self._service = TradeService(
            app.db,
            TradeUserContext(
                user_id=getattr(app, "data_owner_user_id", None),
                username=str(getattr(app, "data_owner_username", "")),
                app_role=str(getattr(app, "user", {}).get("role", "")),
            ),
            company_id=getattr(app, "active_company_id", None),
        )
        super().__init__(master, app)

    def build_ui(self) -> None:
        form = ttk.LabelFrame(self, text="Satış Faturası")
        form.pack(fill=tk.X, padx=10, pady=10)

        row1 = ttk.Frame(form)
        row1.pack(fill=tk.X, padx=8, pady=(8, 4))
        self.doc_no = LabeledEntry(row1, "Belge No:", 18)
        self.doc_no.pack(side=tk.LEFT, padx=4)
        self.doc_date = LabeledEntry(row1, "Tarih:", 12)
        self.doc_date.pack(side=tk.LEFT, padx=4)
        ttk.Button(row1, text="No Üret", command=self._next_no).pack(side=tk.LEFT, padx=4)

        row2 = ttk.Frame(form)
        row2.pack(fill=tk.X, padx=8, pady=4)
        self.cari = LabeledCombo(row2, "Cari:", [], width=26)
        self.cari.pack(side=tk.LEFT, padx=4)
        self.recent_cari = LabeledCombo(row2, "Son Cari:", [], width=20)
        self.recent_cari.pack(side=tk.LEFT, padx=4)
        self.recent_cari.cmb.bind("<<ComboboxSelected>>", lambda _e: self._apply_recent_cari())

        row3 = ttk.Frame(form)
        row3.pack(fill=tk.X, padx=8, pady=4)
        self.item = LabeledEntry(row3, "Ürün:", 24)
        self.item.pack(side=tk.LEFT, padx=4)
        self.qty = LabeledEntry(row3, "Miktar:", 8)
        self.qty.pack(side=tk.LEFT, padx=4)
        self.unit = LabeledCombo(row3, "Birim:", ["Adet", "Kg", "m", "m²", "m³", "Hizmet"], width=8)
        self.unit.pack(side=tk.LEFT, padx=4)
        self.unit_price = MoneyEntry(row3, "Birim Fiyat:", 10)
        self.unit_price.pack(side=tk.LEFT, padx=4)
        self.tax = LabeledEntry(row3, "KDV %:", 6)
        self.tax.pack(side=tk.LEFT, padx=4)
        ttk.Button(row3, text="Satır Ekle", command=self._add_line).pack(side=tk.LEFT, padx=4)

        self.lines_tree = ttk.Treeview(form, columns=("item", "qty", "unit", "price", "tax"), show="headings", height=4)
        for col, label, width in (
            ("item", "Ürün", 240),
            ("qty", "Miktar", 80),
            ("unit", "Birim", 70),
            ("price", "Birim Fiyat", 110),
            ("tax", "KDV %", 60),
        ):
            self.lines_tree.heading(col, text=label)
            self.lines_tree.column(col, width=width, anchor="center")
        self.lines_tree.pack(fill=tk.X, padx=8, pady=(6, 8))

        self._refresh_cari()
        self.doc_date.set(today_iso())
        self.tax.set("20")
        self.unit.set("Adet")
        self._next_no()

    def focus_first(self) -> None:
        try:
            self.doc_no.ent.focus_set()
        except Exception:
            pass

    def _refresh_cari(self) -> None:
        def task() -> list[tuple[str, int]]:
            rows = self.app.db.cari_list(only_active=True)
            return [(r["ad"], int(r["id"])) for r in rows]

        def on_done(payload: list[tuple[str, int]]) -> None:
            names = [name for name, _cid in payload]
            self._cari_map = {name: cid for name, cid in payload}
            self.cari.cmb.configure(values=names)
            if names and not self.cari.get():
                self.cari.set(names[0])
            self._refresh_recent_cari()

        self.run_in_background(task, on_done)

    def _refresh_recent_cari(self) -> None:
        recent = self.get_recent_entities("cari")
        self.recent_cari.cmb.configure(values=recent)

    def _apply_recent_cari(self) -> None:
        val = self.recent_cari.get()
        if val:
            self.cari.set(val)

    def _next_no(self) -> None:
        self.doc_no.set(self._service.next_doc_no("TRD-S"))

    def _add_line(self) -> None:
        item = (self.item.get() or "").strip()
        if not item:
            return
        qty = safe_float(self.qty.get())
        if qty <= 0:
            return
        unit = self.unit.get() or "Adet"
        unit_price = self.unit_price.get_float()
        tax = safe_float(self.tax.get())
        line = {
            "item": item,
            "qty": qty,
            "unit": unit,
            "unit_price": unit_price,
            "tax_rate": tax,
        }
        self._lines.append(line)
        self.lines_tree.insert("", tk.END, values=(item, qty, unit, unit_price, tax))
        self.item.set("")
        self.qty.set("")
        self.unit_price.set("")

    def validate_form(self) -> bool:
        self.clear_errors()
        if not (self.doc_no.get() or "").strip():
            self.mark_error(self.doc_no.ent, "Belge no zorunlu.")
            return False
        if not (self.doc_date.get() or "").strip():
            self.mark_error(self.doc_date.ent, "Tarih zorunlu.")
            return False
        if not (self.cari.get() or "").strip():
            self.mark_error(self.cari.cmb, "Cari seçilmelidir.")
            return False
        if not self._lines:
            self._set_message("En az 1 satır ekleyin.")
            return False
        return True

    def perform_save(self) -> bool:
        cari_name = (self.cari.get() or "").strip()
        cari_id = self._cari_map.get(cari_name)
        try:
            self._service.create_sales_invoice(
                self.doc_no.get().strip(),
                self.doc_date.get().strip(),
                cari_id,
                cari_name,
                self._lines,
                currency="TL",
            )
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Satış faturası kaydedilemedi: {exc}")
            return False
        self.add_recent_entity("cari", cari_name)
        for line in self._lines:
            self.add_recent_entity("urun", str(line.get("item") or ""))
        return True

    def reset_form(self) -> None:
        self.doc_date.set(today_iso())
        self._next_no()
        try:
            if self.cari.get() == "":
                self._refresh_cari()
        except Exception:
            pass
        self.item.set("")
        self.qty.set("")
        self.unit_price.set("")
        self.tax.set("20")
        self._lines = []
        for child in self.lines_tree.get_children():
            self.lines_tree.delete(child)
