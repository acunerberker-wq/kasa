# -*- coding: utf-8 -*-
"""Fatura screen wrapper."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..components import PageHeader
from ..plugins.fatura import FaturaFrame


class FaturaScreen(ttk.Frame):
    def __init__(self, master: tk.Misc, app) -> None:
        super().__init__(master)
        self.app = app
        self._build()

    def _build(self) -> None:
        header = PageHeader(self, title="Fatura")
        ttk.Button(
            header.actions,
            text="Fatura Oluştur",
            style="Primary.TButton",
            command=lambda: self.app.open_create_center("satis_fatura"),
        ).pack(side=tk.LEFT, padx=4)

        self.fatura_frame = FaturaFrame(self, self.app)
        self.fatura_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
