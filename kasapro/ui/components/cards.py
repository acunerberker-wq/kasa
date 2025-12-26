# -*- coding: utf-8 -*-
"""Card components."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class StatCard(ttk.Frame):
    def __init__(self, master: tk.Misc, title: str, value: str, subtitle: str | None = None) -> None:
        super().__init__(master, style="Panel.TFrame")
        self.pack_propagate(False)

        ttk.Label(self, text=title, style="Muted.TLabel").pack(anchor="w")
        ttk.Label(self, text=value, style="H2.TLabel").pack(anchor="w", pady=(4, 0))
        if subtitle:
            ttk.Label(self, text=subtitle, style="SidebarSub.TLabel").pack(anchor="w", pady=(4, 0))


class ChartCard(ttk.Frame):
    def __init__(self, master: tk.Misc, title: str) -> None:
        super().__init__(master, style="Panel.TFrame")
        ttk.Label(self, text=title, style="H2.TLabel").pack(anchor="w")
        ttk.Label(self, text="(Grafik alanı)", style="Muted.TLabel").pack(anchor="w", pady=(8, 0))


class WidgetCard(ttk.Frame):
    def __init__(self, master: tk.Misc, title: str) -> None:
        super().__init__(master, style="Panel.TFrame")
        ttk.Label(self, text=title, style="H2.TLabel").pack(anchor="w")
