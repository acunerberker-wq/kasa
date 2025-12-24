# -*- coding: utf-8 -*-
from __future__ import annotations

from tkinter import ttk

from ...modules.dms.ui.hub import DmsHubFrame

PLUGIN_META = {
    "key": "dms",
    "nav_text": "📄 Dokümanlar",
    "page_title": "Dokümanlar",
    "order": 40,
}


def build(master: ttk.Frame, app: object) -> ttk.Frame:
    return DmsHubFrame(master, app)
