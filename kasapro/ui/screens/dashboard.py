# -*- coding: utf-8 -*-
"""Dashboard screen."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..components import StatCard, ChartCard, WidgetCard, DataTable, InlineProgressChip


class DashboardScreen(ttk.Frame):
    def __init__(self, master: tk.Misc, app) -> None:
        super().__init__(master)
        self.app = app
        self._build()

    def _build(self) -> None:
        header_row = ttk.Frame(self)
        header_row.pack(fill=tk.X, pady=(0, 10))

        stat_grid = ttk.Frame(header_row)
        stat_grid.pack(side=tk.LEFT, fill=tk.X, expand=True)

        cards = [
            ("Günlük Ciro", "₺12.450"),
            ("Tahsilat", "₺8.950"),
            ("Borç / Alacak", "₺15.200"),
            ("Kasa Bakiyesi", "₺32.450"),
        ]
        for title, value in cards:
            card = StatCard(stat_grid, title=title, value=value)
            card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6)

        main_row = ttk.Frame(self)
        main_row.pack(fill=tk.BOTH, expand=True)

        chart_col = ttk.Frame(main_row)
        chart_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        chart = ChartCard(chart_col, title="Son 30 Gün Nakit Akışı")
        chart.pack(fill=tk.BOTH, expand=True)
        chip = InlineProgressChip(chart, "Senkronize ediliyor…")
        chip.pack(anchor="ne", pady=(8, 0))

        right_col = ttk.Frame(main_row)
        right_col.pack(side=tk.RIGHT, fill=tk.Y)
        for title in ("Kritik Stok", "Ödenmemiş Faturalar", "Hatırlatmalar"):
            widget = WidgetCard(right_col, title=title)
            widget.pack(fill=tk.X, pady=6)

        table = DataTable(self, columns=["Tarih", "Tür", "Açıklama", "Tutar", "Durum"], height=8)
        table.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        table.set_state("empty", "Son işlemler yükleniyor")
