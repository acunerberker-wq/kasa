# -*- coding: utf-8 -*-
"""KasaPro v3 - Küçük modal diyalog yardımcıları"""

from __future__ import annotations

from typing import Optional, List

import tkinter as tk
from tkinter import ttk

from ..utils import center_window

def simple_input(parent, title, prompt, password=False) -> Optional[str]:
    w = tk.Toplevel(parent)
    w.title(title)
    w.geometry("360x160")
    w.resizable(False, False)
    w.grab_set()

    ttk.Label(w, text=prompt).pack(pady=(14,6))
    e = ttk.Entry(w, width=30)
    if password:
        e.config(show="*")
    e.pack(pady=6)
    res = {"v": None}

    def ok():
        res["v"] = e.get()
        w.destroy()

    def cancel():
        res["v"] = None
        w.destroy()

    b = ttk.Frame(w)
    b.pack(fill=tk.X, padx=14, pady=12)
    ttk.Button(b, text="OK", command=ok).pack(side=tk.LEFT)
    ttk.Button(b, text="İptal", command=cancel).pack(side=tk.RIGHT)

    w.bind("<Return>", lambda _e: ok())
    center_window(w, parent)
    parent.wait_window(w)
    return res["v"]

def simple_choice(parent, title, prompt, options: List[str], default: str="") -> Optional[str]:
    w = tk.Toplevel(parent)
    w.title(title)
    w.geometry("360x190")
    w.resizable(False, False)
    w.grab_set()

    ttk.Label(w, text=prompt).pack(pady=(14,6))
    var = tk.StringVar(value=default or (options[0] if options else ""))
    cmb = ttk.Combobox(w, textvariable=var, values=options, state="readonly")
    cmb.pack(pady=6)
    res = {"v": None}

    def ok():
        res["v"] = var.get()
        w.destroy()

    def cancel():
        res["v"] = None
        w.destroy()

    b = ttk.Frame(w)
    b.pack(fill=tk.X, padx=14, pady=12)
    ttk.Button(b, text="OK", command=ok).pack(side=tk.LEFT)
    ttk.Button(b, text="İptal", command=cancel).pack(side=tk.RIGHT)

    center_window(w, parent)
    parent.wait_window(w)
    return res["v"]
