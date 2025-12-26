# -*- coding: utf-8 -*-
"""Banka screen wrapper."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from ..components import PageHeader, FilterBar
from ..plugins.banka_hareketleri import BankaHareketleriFrame


class BankaScreen(ttk.Frame):
    def __init__(self, master: tk.Misc, app) -> None:
        super().__init__(master)
        self.app = app
        self._build()

    def _build(self) -> None:
        header = PageHeader(self, title="Banka")
        FilterBar(header.actions)
        ttk.Button(
            header.actions,
            text="Ekstre İçe Aktar",
            style="Primary.TButton",
            command=self._import_statement,
        ).pack(side=tk.LEFT, padx=4)
        ttk.Button(
            header.actions,
            text="Otomatik Eşleştir",
            style="Secondary.TButton",
            command=self._auto_match,
        ).pack(side=tk.LEFT, padx=4)
        ttk.Button(
            header.actions,
            text="Kural Oluştur",
            style="Secondary.TButton",
            command=self._create_rule,
        ).pack(side=tk.LEFT, padx=4)

        self.bank_frame = BankaHareketleriFrame(self, self.app)
        self.bank_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

    def _import_statement(self) -> None:
        self.app.import_excel()

    def _auto_match(self) -> None:
        messagebox.showinfo("Banka", "Otomatik eşleştirme başlatıldı (demo).")

    def _create_rule(self) -> None:
        messagebox.showinfo("Banka", "Kural oluşturma ekranı yakında.")
