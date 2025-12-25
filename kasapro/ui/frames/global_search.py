# -*- coding: utf-8 -*-
"""KasaPro v3 - Ana ekran frame'leri"""

from __future__ import annotations

from typing import TYPE_CHECKING
import tkinter as tk
from tkinter import ttk

from ...utils import (
    fmt_tr_date,
)
from ..base import BaseView
from ..ui_logging import wrap_callback
from ..widgets import LabeledEntry

if TYPE_CHECKING:
    from ...app import App

class GlobalSearchFrame(BaseView):
    def __init__(self, master, app: "App"):
        self.app = app
        super().__init__(master, app)
        self.build_ui()

    def build_ui(self) -> None:
        self._build()

    def _build(self):
        top = ttk.LabelFrame(self, text="Global Arama (Cari + Kasa + Stok)")
        top.pack(fill=tk.X, padx=10, pady=10)

        r = ttk.Frame(top)
        r.pack(fill=tk.X, pady=6)
        self.q = LabeledEntry(r, "Ara:", 30)
        self.q.pack(side=tk.LEFT, padx=6)
        ttk.Button(r, text="Ara", command=wrap_callback("global_search", self.search)).pack(side=tk.LEFT, padx=6)

        self.txt = tk.Text(self)
        self.txt.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,10))

    def search(self):
        q = self.q.get().strip()
        self.txt.delete("1.0", tk.END)
        res = self.app.db.global_search(q)
        self.txt.insert(tk.END, f"CARİLER ({len(res['cariler'])})\n" + "-"*80 + "\n")
        for r in res["cariler"]:
            self.txt.insert(tk.END, f"{r['id']} | {r['ad']} | tel={r['telefon']} | açılış={r['acilis_bakiye']}\n")
        self.txt.insert(tk.END, f"\nCARİ HAREKET ({len(res['cari_hareket'])})\n" + "-"*80 + "\n")
        for r in res["cari_hareket"]:
            self.txt.insert(tk.END, f"{r['id']} | {fmt_tr_date(r['tarih'])} | {r['cari_ad']} | {r['tip']} | {r['tutar']}\n")
        self.txt.insert(tk.END, f"\nKASA ({len(res['kasa'])})\n" + "-"*80 + "\n")
        for r in res["kasa"]:
            self.txt.insert(tk.END, f"{r['id']} | {fmt_tr_date(r['tarih'])} | {r['tip']} | {r['tutar']} | {r['kategori']} | {r['cari_ad'] or ''}\n")

        self.txt.insert(tk.END, f"\nSTOK ÜRÜN ({len(res['stok_urun'])})\n" + "-"*80 + "\n")
        for r in res["stok_urun"]:
            self.txt.insert(tk.END, f"{r['id']} | {r['kod']} | {r['ad']} | {r['kategori']} | {r['birim']}\n")

        self.txt.insert(tk.END, f"\nSTOK HAREKET ({len(res['stok_hareket'])})\n" + "-"*80 + "\n")
        for r in res["stok_hareket"]:
            self.txt.insert(tk.END, f"{r['id']} | {fmt_tr_date(r['tarih'])} | {r['urun_kod']} | {r['urun_ad']} | {r['tip']} | {r['miktar']}\n")

        self.txt.insert(tk.END, f"\nSTOK HAREKET ({len(res['stok_hareket'])})\n" + "-"*80 + "\n")
        for r in res["stok_hareket"]:
            self.txt.insert(tk.END, f"{r['id']} | {fmt_tr_date(r['tarih'])} | {r['urun_kod']} | {r['urun_ad']} | {r['tip']} | {r['miktar']}\n")
