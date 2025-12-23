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

class LogsFrame(ttk.Frame):
    def __init__(self, master, app:"App"):
        super().__init__(master)
        self.app = app
        self._build()

    def _build(self):
        top = ttk.Frame(self); top.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(top, text="Yenile", command=self.refresh).pack(side=tk.LEFT)
        ttk.Button(top, text="Logu TXT Dışa Aktar", command=self.export_txt).pack(side=tk.LEFT, padx=6)
        self.txt = tk.Text(self, height=25)
        self.txt.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,10))
        self.refresh()

    def refresh(self):
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

