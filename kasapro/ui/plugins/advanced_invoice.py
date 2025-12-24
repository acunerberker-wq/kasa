# -*- coding: utf-8 -*-
"""UI plugin: Advanced Invoice Module."""

from __future__ import annotations

from ...modules.invoice.ui import InvoiceModuleFrame

PLUGIN_META = {
    "key": "advanced_invoice",
    "nav_text": "🧾 Faturalar",
    "page_title": "Faturalar",
    "order": 22,
}


def build(master, app):
    return InvoiceModuleFrame(master, app)
