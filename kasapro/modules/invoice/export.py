# -*- coding: utf-8 -*-
"""Export helpers for invoices."""

from __future__ import annotations

import csv
import logging
from typing import Any, Dict, List

from ...config import HAS_REPORTLAB
from ...utils import ensure_pdf_fonts

logger = logging.getLogger(__name__)


def export_csv(path: str, header: Dict[str, Any], lines: List[Dict[str, Any]], totals: Dict[str, Any]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Fatura No", header.get("doc_no", "")])
        writer.writerow(["Tarih", header.get("doc_date", "")])
        writer.writerow(["Cari", header.get("customer_name", "")])
        writer.writerow([])
        writer.writerow(["Açıklama", "Miktar", "Birim", "Birim Fiyat", "KDV", "Toplam"])
        for line in lines:
            writer.writerow(
                [
                    line.get("description", ""),
                    line.get("qty", 0),
                    line.get("unit", ""),
                    line.get("unit_price", 0),
                    line.get("vat_rate", 0),
                    line.get("line_total", 0),
                ]
            )
        writer.writerow([])
        writer.writerow(["Ara Toplam", totals.get("subtotal", 0)])
        writer.writerow(["İskonto", totals.get("discount_total", 0)])
        writer.writerow(["KDV", totals.get("vat_total", 0)])
        writer.writerow(["Genel Toplam", totals.get("grand_total", 0)])


def export_pdf(path: str, header: Dict[str, Any], lines: List[Dict[str, Any]], totals: Dict[str, Any], company: Dict[str, str]) -> None:
    if not HAS_REPORTLAB:
        raise RuntimeError("ReportLab kurulu değil")
    ensure_pdf_fonts()
    from reportlab.pdfgen import canvas
    from .templates.invoice_template import draw_invoice

    c = canvas.Canvas(path)
    draw_invoice(c, header, lines, totals, company)
    c.showPage()
    c.save()
