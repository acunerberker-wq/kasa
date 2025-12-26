# -*- coding: utf-8 -*-
"""Filter bar component."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class FilterBar(ttk.Frame):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, style="Panel.TFrame")
        self.pack(fill=tk.X)

    def add_item(self, widget: tk.Widget, padx: int = 6) -> None:
        widget.pack(in_=self, side=tk.LEFT, padx=padx)
