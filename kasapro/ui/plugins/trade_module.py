# -*- coding: utf-8 -*-

from __future__ import annotations

from tkinter import ttk

from ...modules.trade.ui import TradeModuleFrame

PLUGIN_META = {
    "key": "trade_module",
    "nav_text": "🏭 Ticari",
    "page_title": "Gelişmiş Alış/Satış (Ticari) Modülü",
    "order": 25,
}


def build(master: ttk.Frame, app) -> ttk.Frame:
    return TradeModuleFrame(master, app)
