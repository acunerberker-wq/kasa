# -*- coding: utf-8 -*-

from __future__ import annotations

import queue
import threading
from typing import Any, Dict, List, Optional

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from ....ui.dialogs import simple_input
from ..constants import QUOTE_STATUSES
from ..service import QuoteOrderService
from .dialogs import QuoteEditorDialog


class QuotesFrame(ttk.Frame):
    def __init__(self, master: tk.Widget, app):
        super().__init__(master)
        self.app = app
        self.service = QuoteOrderService(app.db)
        self._queue: "queue.Queue[tuple]" = queue.Queue()
        self._loading = False
        self._page = 1
        self._page_size = 25
        self._total = 0
        self._rows: List[Dict[str, Any]] = []
        self._build()
        self.after(120, self._poll_queue)
        self.refresh()

    def _build(self):
        filters = ttk.Frame(self)
        filters.pack(fill=tk.X, padx=12, pady=8)

        ttk.Label(filters, text="Arama").pack(side=tk.LEFT)
        self.q_var = tk.StringVar()
        ttk.Entry(filters, textvariable=self.q_var, width=26).pack(side=tk.LEFT, padx=6)

        ttk.Label(filters, text="Durum").pack(side=tk.LEFT, padx=(12, 0))
        self.status_var = tk.StringVar()
        status_values = [""] + QUOTE_STATUSES
        ttk.Combobox(filters, textvariable=self.status_var, values=status_values, width=20, state="readonly").pack(
            side=tk.LEFT, padx=6
        )

        ttk.Button(filters, text="Ara", command=self._on_search).pack(side=tk.LEFT, padx=6)
        ttk.Button(filters, text="Yenile", command=self.refresh).pack(side=tk.LEFT)

        btns = ttk.Frame(self)
        btns.pack(fill=tk.X, padx=12, pady=(0, 6))
        ttk.Button(btns, text="Yeni Teklif", command=self._create_quote).pack(side=tk.LEFT)
        ttk.Button(btns, text="Düzenle", command=self._edit_quote).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Revize Et", command=self._revise_quote).pack(side=tk.LEFT)
        ttk.Button(btns, text="Gönder", command=self._send_quote).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Onay", command=self._approve_quote).pack(side=tk.LEFT)
        ttk.Button(btns, text="Reddet", command=self._reject_quote).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Siparişe Dönüştür", command=self._convert_quote).pack(side=tk.LEFT)
        ttk.Button(btns, text="CSV Export", command=self._export_csv).pack(side=tk.RIGHT)

        columns = ("quote_no", "version", "status", "cari_ad", "valid_until", "genel_toplam", "para")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=16)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, anchor="center")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        nav = ttk.Frame(self)
        nav.pack(fill=tk.X, padx=12, pady=(0, 12))
        ttk.Button(nav, text="Önceki", command=self._prev_page).pack(side=tk.LEFT)
        ttk.Button(nav, text="Sonraki", command=self._next_page).pack(side=tk.LEFT, padx=6)
        self.page_label = ttk.Label(nav, text="Sayfa 1")
        self.page_label.pack(side=tk.LEFT, padx=12)
        self.count_label = ttk.Label(nav, text="0 kayıt")
        self.count_label.pack(side=tk.RIGHT)

    def _actor(self) -> Dict[str, Any]:
        return {
            "id": self.app.user.get("id") if self.app.user else None,
            "username": self.app.user.get("username") if self.app.user else "user",
            "role": self.app.user.get("role") if self.app.user else "user",
        }

    def _poll_queue(self):
        try:
            msg = self._queue.get_nowait()
        except queue.Empty:
            self.after(120, self._poll_queue)
            return

        kind = msg[0]
        if kind == "data":
            rows, total = msg[1], msg[2]
            self._apply_rows(rows, total)
        elif kind == "error":
            messagebox.showerror("Teklifler", msg[1])
        self._loading = False
        self.after(120, self._poll_queue)

    def _apply_rows(self, rows: List[Dict[str, Any]], total: int) -> None:
        self._rows = rows
        self._total = total
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in rows:
            iid = str(row["id"])
            self.tree.insert(
                "",
                tk.END,
                iid=iid,
                values=(
                    row.get("quote_no"),
                    row.get("version"),
                    row.get("status"),
                    row.get("cari_ad"),
                    row.get("valid_until"),
                    f"{row.get('genel_toplam', 0):.2f}",
                    row.get("para"),
                ),
            )
        page_count = max(1, (total + self._page_size - 1) // self._page_size)
        self.page_label.config(text=f"Sayfa {self._page} / {page_count}")
        self.count_label.config(text=f"{total} kayıt")

    def _on_search(self):
        self._page = 1
        self.refresh()

    def refresh(self):
        if self._loading:
            return
        self._loading = True
        q = self.q_var.get().strip()
        status = self.status_var.get().strip()
        limit = self._page_size
        offset = (self._page - 1) * self._page_size

        def worker():
            try:
                rows, total = self.service.list_quotes(q=q, status=status, limit=limit, offset=offset)
                self._queue.put(("data", rows, total))
            except Exception as exc:
                self._queue.put(("error", str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _selected_id(self) -> Optional[int]:
        sel = self.tree.selection()
        if not sel:
            return None
        return int(sel[0])

    def _create_quote(self):
        dialog = QuoteEditorDialog(self, "Yeni Teklif")
        if not dialog.result:
            return
        data = dialog.result
        lines = data.pop("lines", [])
        self.service.create_quote(data, lines, actor=self._actor())
        self.refresh()

    def _edit_quote(self):
        quote_id = self._selected_id()
        if not quote_id:
            return
        quote = self.service.get_quote(quote_id)
        dialog = QuoteEditorDialog(self, "Teklif Düzenle", quote)
        if not dialog.result:
            return
        data = dialog.result
        lines = data.pop("lines", [])
        self.service.update_quote(quote_id, data, lines, actor=self._actor())
        self.refresh()

    def _revise_quote(self):
        quote_id = self._selected_id()
        if not quote_id:
            return
        new_id = self.service.revise_quote(quote_id, actor=self._actor())
        quote = self.service.get_quote(new_id)
        dialog = QuoteEditorDialog(self, "Revize Teklif", quote)
        if dialog.result:
            data = dialog.result
            lines = data.pop("lines", [])
            self.service.update_quote(new_id, data, lines, actor=self._actor())
        self.refresh()

    def _send_quote(self):
        quote_id = self._selected_id()
        if not quote_id:
            return
        self.service.send_quote(quote_id, actor=self._actor())
        self.refresh()

    def _approve_quote(self):
        quote_id = self._selected_id()
        if not quote_id:
            return
        self.service.approve_quote(quote_id, actor=self._actor())
        self.refresh()

    def _reject_quote(self):
        quote_id = self._selected_id()
        if not quote_id:
            return
        note = simple_input(self, "Reddet", "Reddetme notu:") or ""
        self.service.reject_quote(quote_id, actor=self._actor(), note=note)
        self.refresh()

    def _convert_quote(self):
        quote_id = self._selected_id()
        if not quote_id:
            return
        try:
            self.service.convert_to_order(quote_id, actor=self._actor())
        except Exception as exc:
            messagebox.showwarning("Dönüştürme", str(exc))
        self.refresh()

    def _export_csv(self):
        if not self._rows:
            messagebox.showinfo("CSV", "Listede veri yok")
            return
        path = filedialog.asksaveasfilename(
            title="CSV Kaydet",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
        )
        if not path:
            return
        self.service.export_quotes_csv(path, self._rows)
        messagebox.showinfo("CSV", "Export tamamlandı")

    def _prev_page(self):
        if self._page <= 1:
            return
        self._page -= 1
        self.refresh()

    def _next_page(self):
        max_page = max(1, (self._total + self._page_size - 1) // self._page_size)
        if self._page >= max_page:
            return
        self._page += 1
        self.refresh()
