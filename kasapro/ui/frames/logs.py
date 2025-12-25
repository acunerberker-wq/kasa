# -*- coding: utf-8 -*-
"""KasaPro v3 - Ana ekran frame'leri"""

from __future__ import annotations

from typing import TYPE_CHECKING
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from ..base import BaseView
from ..ui_logging import wrap_callback
from ...config import APP_TITLE

if TYPE_CHECKING:
    from ...app import App

class LogsFrame(BaseView):
    def __init__(self, master, app: "App"):
        self.app = app
        super().__init__(master, app)
        self.build_ui()

    def build_ui(self) -> None:
        self._build()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(top, text="Yenile", command=wrap_callback("logs_refresh", self.refresh)).pack(side=tk.LEFT)
        ttk.Button(
            top,
            text="Logu TXT Dışa Aktar",
            command=wrap_callback("logs_export_txt", self.export_txt),
        ).pack(side=tk.LEFT, padx=6)
        self.txt = tk.Text(self, height=25)
        self.txt.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,10))
        self.refresh()

    def refresh(self, data=None):
        self.txt.delete("1.0", tk.END)
        for r in self.app.db.logs_list(800):
            self.txt.insert(tk.END, f"{r['ts']} | {r['islem']} | {r['detay']}\n")

    def export_txt(self):
        p = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text", "*.txt")], title="Log Kaydet")
        if not p:
            return
        with open(p, "w", encoding="utf-8") as f:
            f.write(self.txt.get("1.0", tk.END))
        messagebox.showinfo(APP_TITLE, "Kaydedildi.")


# =========================
# APP
# =========================


# =========================
# KULLANICILAR (Admin)
# =========================
