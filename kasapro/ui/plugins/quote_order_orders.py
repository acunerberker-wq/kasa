# -*- coding: utf-8 -*-

from __future__ import annotations

from tkinter import ttk

from ...modules.quote_order.ui import OrdersFrame


PLUGIN_META = {
    "key": "quote_orders_orders",
    "nav_text": "Satış > Siparişler",
    "page_title": "Sipariş Yönetimi",
    "order": 46,
}


def build(master: ttk.Frame, app):
    return OrdersFrame(master, app)
