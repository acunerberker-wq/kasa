# -*- coding: utf-8 -*-
"""Page header component."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class PageHeader(ttk.Frame):
    def __init__(self, master: tk.Misc, title: str, subtitle: str | None = None) -> None:
        super().__init__(master, style="Panel.TFrame")
        self.pack(fill=tk.X)

        title_row = ttk.Frame(self, style="Panel.TFrame")
        title_row.pack(fill=tk.X)

        self.title_label = ttk.Label(title_row, text=title, style="H2.TLabel")
        self.title_label.pack(side=tk.LEFT)

        if subtitle:
            self.subtitle_label = ttk.Label(title_row, text=subtitle, style="Muted.TLabel")
            self.subtitle_label.pack(side=tk.LEFT, padx=(8, 0))
        else:
            self.subtitle_label = None

        self.actions = ttk.Frame(title_row, style="Panel.TFrame")
        self.actions.pack(side=tk.RIGHT)
