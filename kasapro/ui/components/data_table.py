# -*- coding: utf-8 -*-
"""Data table component with state handling."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class DataTable(ttk.Frame):
    def __init__(self, master: tk.Misc, columns: list[str], height: int = 12) -> None:
        super().__init__(master, style="Panel.TFrame")
        self.state_label = ttk.Label(self, text="", style="Muted.TLabel")
        self.state_label.pack(anchor="w", pady=(0, 6))

        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=height)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="w")
        self.tree.pack(fill=tk.BOTH, expand=True)

    def set_state(self, state: str, message: str) -> None:
        self.state_label.config(text=f"{state.upper()}: {message}")
