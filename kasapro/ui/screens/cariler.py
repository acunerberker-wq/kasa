# -*- coding: utf-8 -*-
"""Cariler screen wrapper."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..components import PageHeader
from ..frames.cariler import CarilerFrame


class CarilerScreen(ttk.Frame):
    def __init__(self, master: tk.Misc, app) -> None:
        super().__init__(master)
        self.app = app
        self._build()

    def _build(self) -> None:
        header = PageHeader(self, title="Cariler")
        ttk.Button(
            header.actions,
            text="Yeni Cari",
            style="Primary.TButton",
            command=lambda: self.app.open_create_center("cari"),
        ).pack(side=tk.LEFT, padx=4)

        self.cariler_frame = CarilerFrame(self, self.app)
        self.cariler_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
