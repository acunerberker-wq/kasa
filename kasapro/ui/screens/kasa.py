# -*- coding: utf-8 -*-
"""Kasa screen wrapper."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..components import PageHeader
from ..frames.kasa import KasaFrame


class KasaScreen(ttk.Frame):
    def __init__(self, master: tk.Misc, app) -> None:
        super().__init__(master)
        self.app = app
        self._build()

    def _build(self) -> None:
        header = PageHeader(self, title="Kasa")
        ttk.Button(
            header.actions,
            text="Gelir Ekle",
            style="Primary.TButton",
            command=lambda: self._open_form("Gelir"),
        ).pack(side=tk.LEFT, padx=4)
        ttk.Button(
            header.actions,
            text="Gider Ekle",
            style="Danger.TButton",
            command=lambda: self._open_form("Gider"),
        ).pack(side=tk.LEFT, padx=4)

        self.kasa_frame = KasaFrame(self, self.app)
        self.kasa_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

    def _open_form(self, tip: str) -> None:
        try:
            self.kasa_frame.nb.select(self.kasa_frame.tab_form)
            self.kasa_frame.in_tip.set(tip)
        except Exception:
            pass
