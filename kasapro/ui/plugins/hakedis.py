# -*- coding: utf-8 -*-

from __future__ import annotations

from tkinter import ttk

from ...modules.hakedis.ui import HakedisFrame

PLUGIN_META = {
    "key": "hakedis",
    "nav_text": "🏗️ Hakediş Merkezi",
    "page_title": "Proje/Şantiye > Hakediş Merkezi",
    "order": 45,
}


def build(master: ttk.Frame, app) -> ttk.Frame:
    return HakedisFrame(master, app)
