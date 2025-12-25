# -*- coding: utf-8 -*-
"""Create Center form: Sipariş."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import tkinter as tk
from tkinter import ttk, messagebox

from ...config import APP_TITLE
from ...utils import today_iso, safe_float
from ...modules.trade.service import TradeService, TradeUserContext
from ..widgets import LabeledEntry, LabeledCombo, MoneyEntry
from .base import BaseCreateForm


class SiparisCreateForm(BaseCreateForm):
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
        form = ttk.LabelFrame(self, text="Sipariş")
        form.pack(fill=tk.X, padx=10, pady=10)

        row1 = ttk.Frame(form)
        row1.pack(fill=tk.X, padx=8, pady=(8, 4))
        self.order_type = LabeledCombo(row1, "Tür:", ["sales", "purchase"], width=12)
        self.order_type.pack(side=tk.LEFT, padx=4)
        self.order_no = LabeledEntry(row1, "Sipariş No:", 18)
        self.order_no.pack(side=tk.LEFT, padx=4)
        self.order_date = LabeledEntry(row1, "Tarih:", 12)
        self.order_date.pack(side=tk.LEFT, padx=4)
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
        ttk.Button(row3, text="Satır Ekle", command=self._add_line).pack(side=tk.LEFT, padx=4)

        self.lines_tree = ttk.Treeview(form, columns=("item", "qty", "unit", "price"), show="headings", height=4)
        for col, label, width in (
            ("item", "Ürün", 240),
            ("qty", "Miktar", 80),
            ("unit", "Birim", 70),
            ("price", "Birim Fiyat", 110),
        ):
            self.lines_tree.heading(col, text=label)
            self.lines_tree.column(col, width=width, anchor="center")
        self.lines_tree.pack(fill=tk.X, padx=8, pady=(6, 8))

        self.order_type.set("sales")
        self.order_date.set(today_iso())
        self.unit.set("Adet")
        self._next_no()
        self._refresh_cari()

    def focus_first(self) -> None:
        try:
            self.order_no.ent.focus_set()
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
        self.order_no.set(self._service.next_doc_no("TRD-SIP"))

    def _add_line(self) -> None:
        item = (self.item.get() or "").strip()
        if not item:
            return
        qty = safe_float(self.qty.get())
        if qty <= 0:
            return
        unit = self.unit.get() or "Adet"
        unit_price = self.unit_price.get_float()
        line_total = qty * unit_price
        line = {
            "item": item,
            "description": "",
            "qty": qty,
            "unit": unit,
            "unit_price": unit_price,
            "line_total": line_total,
        }
        self._lines.append(line)
        self.lines_tree.insert("", tk.END, values=(item, qty, unit, unit_price))
        self.item.set("")
        self.qty.set("")
        self.unit_price.set("")

    def validate_form(self) -> bool:
        self.clear_errors()
        if not (self.order_no.get() or "").strip():
            self.mark_error(self.order_no.ent, "Sipariş no zorunlu.")
            return False
        if not (self.order_date.get() or "").strip():
            self.mark_error(self.order_date.ent, "Tarih zorunlu.")
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
            self._service.create_order(
                self.order_type.get() or "sales",
                self.order_no.get().strip(),
                self.order_date.get().strip(),
                cari_id,
                cari_name,
                self._lines,
                currency="TL",
            )
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Sipariş kaydedilemedi: {exc}")
            return False
        self.add_recent_entity("cari", cari_name)
        for line in self._lines:
            self.add_recent_entity("urun", str(line.get("item") or ""))
        return True

    def reset_form(self) -> None:
        self.order_date.set(today_iso())
        self._next_no()
        self.item.set("")
        self.qty.set("")
        self.unit_price.set("")
        self._lines = []
        for child in self.lines_tree.get_children():
            self.lines_tree.delete(child)
