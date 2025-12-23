# -*- coding: utf-8 -*-
"""KasaPro v3 - Ana ekran frame'leri"""

from __future__ import annotations

import os
import re
from datetime import datetime, timedelta
from typing import Any, Optional, List, Dict, Tuple

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog

from ...config import APP_TITLE, HAS_OPENPYXL, HAS_REPORTLAB
from ...utils import (
    center_window,
    today_iso,
    now_iso,
    fmt_tr_date,
    parse_date_smart,
    parse_number_smart,
    safe_float,
    fmt_amount,
)
from ..widgets import SimpleField, LabeledEntry, LabeledCombo, MoneyEntry
from ..windows import ImportWizard, CariEkstreWindow

class GlobalSearchFrame(ttk.Frame):
    def __init__(self, master, app:"App"):
        super().__init__(master)
        self.app = app
        self._build()

    def _build(self):
        top = ttk.LabelFrame(self, text="Global Arama (Cari + Gelir + Hareket)")
        top.pack(fill=tk.X, padx=10, pady=10)

        r = ttk.Frame(top); r.pack(fill=tk.X, pady=6)
        self.q = LabeledEntry(r, "Ara:", 30); self.q.pack(side=tk.LEFT, padx=6)
        ttk.Button(r, text="Ara", command=self.search).pack(side=tk.LEFT, padx=6)

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


