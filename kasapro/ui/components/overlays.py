# -*- coding: utf-8 -*-
"""Overlay components."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class Toast(ttk.Frame):
    def __init__(self, master: tk.Misc, title: str, message: str | None = None) -> None:
        super().__init__(master, style="Panel.TFrame")
        ttk.Label(self, text=title, style="H2.TLabel").pack(anchor="w")
        if message:
            ttk.Label(self, text=message, style="Body.TLabel").pack(anchor="w", pady=(4, 0))


class Modal(tk.Toplevel):
    def __init__(self, master: tk.Misc, title: str) -> None:
        super().__init__(master)
        self.title(title)
        self.body = ttk.Frame(self)
        self.body.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)


class InlineProgressChip(ttk.Frame):
    def __init__(self, master: tk.Misc, label: str) -> None:
        super().__init__(master, style="Panel.TFrame")
        ttk.Label(self, text=label, style="Muted.TLabel").pack(side=tk.LEFT, padx=6, pady=2)
        ttk.Label(self, text="⏳", style="Muted.TLabel").pack(side=tk.LEFT)
