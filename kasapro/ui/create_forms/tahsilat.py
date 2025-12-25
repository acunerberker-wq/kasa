# -*- coding: utf-8 -*-
"""Create Center form: Tahsilat."""

from __future__ import annotations

from typing import Any, Dict, Optional

import tkinter as tk
from tkinter import ttk, messagebox

from ...config import APP_TITLE
from ...utils import today_iso, safe_float, fmt_amount
from ...modules.trade.service import TradeService, TradeUserContext
from ..widgets import LabeledEntry, LabeledCombo, MoneyEntry
from .base import BaseCreateForm


class TahsilatCreateForm(BaseCreateForm):
    def __init__(self, master: tk.Misc, app: Any) -> None:
        self._docs: Dict[str, int] = {}
        self._pending_doc_id: Optional[int] = None
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
        form = ttk.LabelFrame(self, text="Tahsilat")
        form.pack(fill=tk.X, padx=10, pady=10)

        row1 = ttk.Frame(form)
        row1.pack(fill=tk.X, padx=8, pady=(8, 4))
        self.search_q = LabeledEntry(row1, "Fatura Ara:", 24)
        self.search_q.pack(side=tk.LEFT, padx=4)
        ttk.Button(row1, text="Listele", command=self._refresh_docs).pack(side=tk.LEFT, padx=4)

        row2 = ttk.Frame(form)
        row2.pack(fill=tk.X, padx=8, pady=4)
        self.doc_combo = LabeledCombo(row2, "Belge:", [], width=48, state="readonly")
        self.doc_combo.pack(side=tk.LEFT, padx=4)

        row3 = ttk.Frame(form)
        row3.pack(fill=tk.X, padx=8, pady=4)
        self.amount = MoneyEntry(row3, "Tutar:", 12)
        self.amount.pack(side=tk.LEFT, padx=4)
        self.pay_date = LabeledEntry(row3, "Tarih:", 12)
        self.pay_date.pack(side=tk.LEFT, padx=4)
        self.method = LabeledCombo(row3, "Yöntem:", ["Nakit", "Banka", "Kredi Kartı"], width=14)
        self.method.pack(side=tk.LEFT, padx=4)
        self.use_bank_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row3, text="Banka", variable=self.use_bank_var).pack(side=tk.LEFT, padx=6)

        row4 = ttk.Frame(form)
        row4.pack(fill=tk.X, padx=8, pady=(4, 8))
        self.reference = LabeledEntry(row4, "Referans:", 28)
        self.reference.pack(side=tk.LEFT, padx=4)

        self.pay_date.set(today_iso())
        self.method.set("Nakit")
        self._refresh_docs()

    def focus_first(self) -> None:
        try:
            self.search_q.ent.focus_set()
        except Exception:
            pass

    def set_context(self, ctx: Optional[Dict[str, Any]] = None) -> None:
        super().set_context(ctx)
        doc_id = None if not ctx else ctx.get("doc_id")
        try:
            self._pending_doc_id = int(doc_id) if doc_id is not None else None
        except Exception:
            self._pending_doc_id = None

    def _refresh_docs(self) -> None:
        q = (self.search_q.get() or "").strip()

        def task() -> list[tuple[str, int]]:
            rows = self._service.repo.list_docs(
                self._service.company_id,
                doc_type="sales_invoice",
                q=q,
                limit=100,
            )
            options = []
            for r in rows:
                label = f"{r['doc_no']} | {r['cari_name']} | {fmt_amount(r['total'])}"
                options.append((label, int(r["id"])))
            return options

        def on_done(payload: list[tuple[str, int]]) -> None:
            self._docs = {label: doc_id for label, doc_id in payload}
            labels = list(self._docs.keys())
            self.doc_combo.cmb.configure(values=labels)
            if labels:
                self.doc_combo.set(labels[0])
            if self._pending_doc_id is not None:
                for label, doc_id in self._docs.items():
                    if doc_id == self._pending_doc_id:
                        self.doc_combo.set(label)
                        break
                self._pending_doc_id = None

        self.run_in_background(task, on_done)

    def validate_form(self) -> bool:
        self.clear_errors()
        if not (self.doc_combo.get() or "").strip():
            self.mark_error(self.doc_combo.cmb, "Belge seçilmelidir.")
            return False
        amount = self.amount.get_float()
        if amount <= 0:
            self.mark_error(self.amount.ent, "Tutar 0'dan büyük olmalıdır.")
            return False
        return True

    def perform_save(self) -> bool:
        label = self.doc_combo.get()
        doc_id = self._docs.get(label)
        if not doc_id:
            messagebox.showwarning(APP_TITLE, "Belge seçimi bulunamadı.")
            return False
        amount = self.amount.get_float()
        try:
            self._service.record_payment(
                int(doc_id),
                float(amount),
                self.pay_date.get().strip(),
                self.method.get() or "Nakit",
                use_bank=bool(self.use_bank_var.get()),
                reference=(self.reference.get() or "").strip(),
            )
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Tahsilat kaydedilemedi: {exc}")
            return False
        return True

    def reset_form(self) -> None:
        self.amount.set("0")
        self.pay_date.set(today_iso())
        self.method.set("Nakit")
        self.reference.set("")
        self.use_bank_var.set(False)
        self._refresh_docs()
