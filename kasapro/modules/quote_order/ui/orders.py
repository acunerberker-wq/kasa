# -*- coding: utf-8 -*-

from __future__ import annotations

import queue
import threading
from typing import Any, Dict, List, Optional

import tkinter as tk
from tkinter import ttk, messagebox

from ..constants import ORDER_STATUSES
from ..service import QuoteOrderService


class OrdersFrame(ttk.Frame):
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
        status_values = [""] + ORDER_STATUSES
        ttk.Combobox(filters, textvariable=self.status_var, values=status_values, width=22, state="readonly").pack(
            side=tk.LEFT, padx=6
        )
        ttk.Button(filters, text="Ara", command=self._on_search).pack(side=tk.LEFT, padx=6)
        ttk.Button(filters, text="Yenile", command=self.refresh).pack(side=tk.LEFT)

        btns = ttk.Frame(self)
        btns.pack(fill=tk.X, padx=12, pady=(0, 6))
        ttk.Button(btns, text="Durum Güncelle", command=self._update_status).pack(side=tk.LEFT)

        columns = ("order_no", "status", "quote_id", "cari_ad", "genel_toplam", "para")
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
            messagebox.showerror("Siparişler", msg[1])
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
                    row.get("order_no"),
                    row.get("status"),
                    row.get("quote_id") or "",
                    row.get("cari_ad"),
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
                rows, total = self.service.list_orders(q=q, status=status, limit=limit, offset=offset)
                self._queue.put(("data", rows, total))
            except Exception as exc:
                self._queue.put(("error", str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _selected_id(self) -> Optional[int]:
        sel = self.tree.selection()
        if not sel:
            return None
        return int(sel[0])

    def _update_status(self):
        order_id = self._selected_id()
        if not order_id:
            return
        win = tk.Toplevel(self)
        win.title("Durum Güncelle")
        win.geometry("280x160")
        win.grab_set()

        ttk.Label(win, text="Durum").pack(pady=(12, 6))
        var = tk.StringVar(value=ORDER_STATUSES[0])
        ttk.Combobox(win, textvariable=var, values=ORDER_STATUSES, state="readonly").pack()

        def _ok():
            try:
                self.service.update_order_status(order_id, var.get(), actor=self._actor())
                self.refresh()
            finally:
                win.destroy()

        ttk.Button(win, text="Kaydet", command=_ok).pack(pady=12)
        ttk.Button(win, text="İptal", command=win.destroy).pack()

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
