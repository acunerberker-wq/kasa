# -*- coding: utf-8 -*-
"""Top bar component."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class TopBar(ttk.Frame):
    def __init__(self, master: tk.Misc, title: str = "", subtitle: str = "") -> None:
        super().__init__(master, style="Topbar.TFrame")
        self.title_label = ttk.Label(self, text=title, style="TopTitle.TLabel")
        self.title_label.pack(side=tk.LEFT, padx=(10, 10), pady=8)

        self.subtitle_label = ttk.Label(self, text=subtitle, style="TopSub.TLabel")
        self.subtitle_label.pack(side=tk.LEFT, pady=10)

        self.actions = ttk.Frame(self, style="Topbar.TFrame")
        self.actions.pack(side=tk.RIGHT, padx=(0, 10), pady=8)

    def set_title(self, text: str) -> None:
        self.title_label.config(text=text)

    def set_subtitle(self, text: str) -> None:
        self.subtitle_label.config(text=text)
