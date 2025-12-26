# -*- coding: utf-8 -*-
"""Application shell layout."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .top_bar import TopBar
from .side_bar import SideBar


class AppShell(ttk.Frame):
    def __init__(self, master: tk.Misc, sidebar_width: int = 240) -> None:
        super().__init__(master, style="TFrame")
        self.pack(fill=tk.BOTH, expand=True)

        self.container = ttk.Frame(self, style="TFrame")
        self.container.pack(fill=tk.BOTH, expand=True)

        self.sidebar = SideBar(self.container, width=sidebar_width)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)

        self.content = ttk.Frame(self.container, style="TFrame")
        self.content.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.topbar = TopBar(self.content)
        self.topbar.pack(fill=tk.X, padx=12, pady=(12, 8))

        self.body = ttk.Frame(self.content, style="TFrame")
        self.body.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        self.status_var = tk.StringVar(value="")
        self.status = ttk.Label(self.content, textvariable=self.status_var, style="Status.TLabel")
        self.status.pack(fill=tk.X, side=tk.BOTTOM)
