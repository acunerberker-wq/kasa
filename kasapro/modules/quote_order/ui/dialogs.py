# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import Any, Dict, List, Optional

import tkinter as tk
from tkinter import ttk

from ....utils import center_window


class LineEditorDialog:
    def __init__(self, parent: tk.Widget, line: Optional[Dict[str, Any]] = None):
        self.parent = parent
        self.line = line or {}
        self.result: Optional[Dict[str, Any]] = None

        self.win = tk.Toplevel(parent)
        self.win.title("Kalem")
        self.win.geometry("420x360")
        self.win.resizable(False, False)
        self.win.grab_set()

        self._build()
        center_window(self.win, parent)
        parent.wait_window(self.win)

    def _build(self):
        frm = ttk.Frame(self.win)
        frm.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        self.vars = {
            "urun": tk.StringVar(value=self.line.get("urun", "")),
            "aciklama": tk.StringVar(value=self.line.get("aciklama", "")),
            "miktar": tk.StringVar(value=str(self.line.get("miktar", 1))),
            "birim": tk.StringVar(value=self.line.get("birim", "Adet")),
            "birim_fiyat": tk.StringVar(value=str(self.line.get("birim_fiyat", 0))),
            "iskonto_oran": tk.StringVar(value=str(self.line.get("iskonto_oran", 0))),
            "kdv_oran": tk.StringVar(value=str(self.line.get("kdv_oran", 20))),
        }

        labels = [
            ("Ürün", "urun"),
            ("Açıklama", "aciklama"),
            ("Miktar", "miktar"),
            ("Birim", "birim"),
            ("Birim Fiyat", "birim_fiyat"),
            ("İskonto %", "iskonto_oran"),
            ("KDV %", "kdv_oran"),
        ]

        for idx, (label, key) in enumerate(labels):
            ttk.Label(frm, text=label).grid(row=idx, column=0, sticky="w", pady=4)
            ttk.Entry(frm, textvariable=self.vars[key]).grid(row=idx, column=1, sticky="ew", pady=4)

        frm.columnconfigure(1, weight=1)

        btns = ttk.Frame(frm)
        btns.grid(row=len(labels), column=0, columnspan=2, pady=12, sticky="ew")
        ttk.Button(btns, text="Kaydet", command=self._ok).pack(side=tk.LEFT)
        ttk.Button(btns, text="İptal", command=self._cancel).pack(side=tk.RIGHT)

    def _ok(self):
        def _float(key: str, default: float = 0.0) -> float:
            try:
                return float(self.vars[key].get())
            except Exception:
                return default

        self.result = {
            "urun": self.vars["urun"].get(),
            "aciklama": self.vars["aciklama"].get(),
            "miktar": _float("miktar", 1.0),
            "birim": self.vars["birim"].get() or "Adet",
            "birim_fiyat": _float("birim_fiyat"),
            "iskonto_oran": _float("iskonto_oran"),
            "kdv_oran": _float("kdv_oran", 20.0),
        }
        self.win.destroy()

    def _cancel(self):
        self.result = None
        self.win.destroy()


class QuoteEditorDialog:
    def __init__(self, parent: tk.Widget, title: str, data: Optional[Dict[str, Any]] = None):
        self.parent = parent
        self.data = data or {}
        self.result: Optional[Dict[str, Any]] = None
        self.lines: List[Dict[str, Any]] = list(self.data.get("lines", []))

        self.win = tk.Toplevel(parent)
        self.win.title(title)
        self.win.geometry("760x560")
        self.win.grab_set()

        self._build()
        center_window(self.win, parent)
        parent.wait_window(self.win)

    def _build(self):
        top = ttk.Frame(self.win)
        top.pack(fill=tk.X, padx=12, pady=12)

        self.vars = {
            "cari_ad": tk.StringVar(value=self.data.get("cari_ad", "")),
            "valid_until": tk.StringVar(value=self.data.get("valid_until", "")),
            "para": tk.StringVar(value=self.data.get("para", "TL")),
            "kur": tk.StringVar(value=str(self.data.get("kur", 1))),
            "genel_iskonto_oran": tk.StringVar(value=str(self.data.get("genel_iskonto_oran", 0))),
            "notlar": tk.StringVar(value=self.data.get("notlar", "")),
        }

        labels = [
            ("Müşteri", "cari_ad"),
            ("Geçerlilik", "valid_until"),
            ("Para Birimi", "para"),
            ("Kur", "kur"),
            ("Genel İskonto %", "genel_iskonto_oran"),
            ("Notlar", "notlar"),
        ]
        for idx, (label, key) in enumerate(labels):
            ttk.Label(top, text=label).grid(row=idx, column=0, sticky="w", pady=4)
            ttk.Entry(top, textvariable=self.vars[key]).grid(row=idx, column=1, sticky="ew", pady=4)
        top.columnconfigure(1, weight=1)

        line_frame = ttk.LabelFrame(self.win, text="Kalemler")
        line_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        cols = ("urun", "aciklama", "miktar", "birim", "birim_fiyat", "iskonto_oran", "kdv_oran")
        self.tree = ttk.Treeview(line_frame, columns=cols, show="headings", height=10)
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=90, anchor="center")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        btns = ttk.Frame(line_frame)
        btns.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Button(btns, text="Ekle", command=self._add_line).pack(side=tk.LEFT)
        ttk.Button(btns, text="Düzenle", command=self._edit_line).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Sil", command=self._remove_line).pack(side=tk.LEFT)

        self._reload_lines()

        bottom = ttk.Frame(self.win)
        bottom.pack(fill=tk.X, padx=12, pady=12)
        ttk.Button(bottom, text="Kaydet", command=self._ok).pack(side=tk.LEFT)
        ttk.Button(bottom, text="İptal", command=self._cancel).pack(side=tk.RIGHT)

    def _reload_lines(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for line in self.lines:
            self.tree.insert(
                "",
                tk.END,
                values=(
                    line.get("urun", ""),
                    line.get("aciklama", ""),
                    line.get("miktar", 0),
                    line.get("birim", ""),
                    line.get("birim_fiyat", 0),
                    line.get("iskonto_oran", 0),
                    line.get("kdv_oran", 0),
                ),
            )

    def _add_line(self):
        dialog = LineEditorDialog(self.win)
        if dialog.result:
            self.lines.append(dialog.result)
            self._reload_lines()

    def _edit_line(self):
        selected = self.tree.selection()
        if not selected:
            return
        idx = self.tree.index(selected[0])
        dialog = LineEditorDialog(self.win, self.lines[idx])
        if dialog.result:
            self.lines[idx] = dialog.result
            self._reload_lines()

    def _remove_line(self):
        selected = self.tree.selection()
        if not selected:
            return
        idx = self.tree.index(selected[0])
        self.lines.pop(idx)
        self._reload_lines()

    def _ok(self):
        def _float(key: str, default: float = 0.0) -> float:
            try:
                return float(self.vars[key].get())
            except Exception:
                return default

        self.result = {
            "cari_ad": self.vars["cari_ad"].get(),
            "valid_until": self.vars["valid_until"].get(),
            "para": self.vars["para"].get() or "TL",
            "kur": _float("kur", 1.0),
            "genel_iskonto_oran": _float("genel_iskonto_oran"),
            "notlar": self.vars["notlar"].get(),
            "lines": self.lines,
        }
        self.win.destroy()

    def _cancel(self):
        self.result = None
        self.win.destroy()
