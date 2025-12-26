# -*- coding: utf-8 -*-

from __future__ import annotations

from tkinter import ttk

from ...modules.quote_order.ui import QuotesFrame


PLUGIN_META = {
    "key": "quote_orders_quotes",
    "nav_text": "Satış > Teklifler",
    "page_title": "Teklif Yönetimi",
    "order": 45,
}


def build(master: ttk.Frame, app):
    return QuotesFrame(master, app)
