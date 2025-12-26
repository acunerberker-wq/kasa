# -*- coding: utf-8 -*-
"""Right detail panel component."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class RightDetailPanel(ttk.Frame):
    def __init__(self, master: tk.Misc, title: str) -> None:
        super().__init__(master, style="Panel.TFrame")
        ttk.Label(self, text=title, style="H2.TLabel").pack(anchor="w")
        self.body = ttk.Frame(self, style="Panel.TFrame")
        self.body.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
