# -*- coding: utf-8 -*-
"""PDF template for invoice export."""

from __future__ import annotations

from typing import Any, Dict, List

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def draw_invoice(
    c: canvas.Canvas,
    header: Dict[str, Any],
    lines: List[Dict[str, Any]],
    totals: Dict[str, Any],
    company: Dict[str, str],
) -> None:
    width, height = A4
    y = height - 20 * mm

    c.setFont("Helvetica-Bold", 14)
    c.drawString(20 * mm, y, company.get("name", "Şirket"))
    c.setFont("Helvetica", 9)
    y -= 6 * mm
    c.drawString(20 * mm, y, company.get("address", ""))
    y -= 5 * mm
    c.drawString(20 * mm, y, company.get("tax", ""))

    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(width - 20 * mm, height - 20 * mm, f"FATURA {header.get('doc_no', '')}")
    c.setFont("Helvetica", 9)
    c.drawRightString(width - 20 * mm, height - 26 * mm, f"Tarih: {header.get('doc_date', '')}")

    y -= 14 * mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(20 * mm, y, "Cari Bilgileri")
    c.setFont("Helvetica", 9)
    y -= 5 * mm
    c.drawString(20 * mm, y, header.get("customer_name", ""))
    y -= 5 * mm
    c.drawString(20 * mm, y, header.get("notes", ""))

    y -= 10 * mm
    c.setFont("Helvetica-Bold", 9)
    c.drawString(20 * mm, y, "Açıklama")
    c.drawRightString(width - 60 * mm, y, "Miktar")
    c.drawRightString(width - 40 * mm, y, "Birim")
    c.drawRightString(width - 20 * mm, y, "Toplam")

    c.setFont("Helvetica", 9)
    for line in lines:
        y -= 5 * mm
        if y < 30 * mm:
            c.showPage()
            y = height - 20 * mm
        c.drawString(20 * mm, y, str(line.get("description", ""))[:60])
        c.drawRightString(width - 60 * mm, y, f"{line.get('qty', 0):.2f}")
        c.drawRightString(width - 40 * mm, y, str(line.get("unit", "")))
        c.drawRightString(width - 20 * mm, y, f"{line.get('line_total', 0):.2f}")

    y -= 10 * mm
    c.setFont("Helvetica-Bold", 9)
    c.drawRightString(width - 20 * mm, y, f"Ara Toplam: {totals.get('subtotal', 0):.2f}")
    y -= 5 * mm
    c.drawRightString(width - 20 * mm, y, f"İskonto: {totals.get('discount_total', 0):.2f}")
    y -= 5 * mm
    c.drawRightString(width - 20 * mm, y, f"KDV: {totals.get('vat_total', 0):.2f}")
    y -= 5 * mm
    c.drawRightString(width - 20 * mm, y, f"Genel Toplam: {totals.get('grand_total', 0):.2f}")
