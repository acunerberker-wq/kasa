# -*- coding: utf-8 -*-
"""Sidebar component."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class SideBar(ttk.Frame):
    def __init__(self, master: tk.Misc, width: int = 240) -> None:
        super().__init__(master, style="Sidebar.TFrame", width=width)
        self.pack_propagate(False)

        self.header = ttk.Frame(self, style="Sidebar.TFrame")
        self.header.pack(fill=tk.X, padx=14, pady=(14, 10))

        self.menu = ttk.Frame(self, style="Sidebar.TFrame")
        self.menu.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        self.footer = ttk.Frame(self, style="Sidebar.TFrame")
        self.footer.pack(fill=tk.X, padx=8, pady=(0, 12), side=tk.BOTTOM)
