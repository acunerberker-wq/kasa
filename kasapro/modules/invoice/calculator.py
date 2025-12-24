# -*- coding: utf-8 -*-
"""Invoice calculation engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from ...utils import parse_number_smart


@dataclass
class LineResult:
    line_subtotal: float
    line_discount: float
    line_vat: float
    line_total: float


@dataclass
class TotalsResult:
    subtotal: float
    discount_total: float
    vat_total: float
    grand_total: float
    lines: List[Dict[str, Any]]


def _as_float(value: Any) -> float:
    try:
        return float(parse_number_smart(value))
    except Exception:
        return 0.0


def _discount_amount(base: float, discount_value: Any, discount_type: str) -> float:
    value = _as_float(discount_value)
    if discount_type == "percent":
        return max(0.0, base * value / 100.0)
    return max(0.0, value)


def _line_calc(
    qty: Any,
    unit_price: Any,
    vat_rate: Any,
    vat_included: bool,
    line_discount_value: Any,
    line_discount_type: str,
) -> LineResult:
    qty_val = _as_float(qty)
    unit_price_val = _as_float(unit_price)
    vat_rate_val = _as_float(vat_rate)

    if qty_val == 0:
        return LineResult(0.0, 0.0, 0.0, 0.0)

    gross = qty_val * unit_price_val
    if vat_included:
        divisor = 1.0 + vat_rate_val / 100.0
        line_subtotal = gross / divisor if divisor else gross
    else:
        line_subtotal = gross

    discount = min(line_subtotal, _discount_amount(line_subtotal, line_discount_value, line_discount_type))
    net_base = max(0.0, line_subtotal - discount)

    vat_amount = net_base * vat_rate_val / 100.0
    line_total = net_base + vat_amount

    return LineResult(line_subtotal=line_subtotal, line_discount=discount, line_vat=vat_amount, line_total=line_total)


def calculate_totals(
    lines: List[Dict[str, Any]],
    invoice_discount_value: Any = 0,
    invoice_discount_type: str = "amount",
    vat_included: bool = False,
    sign: int = 1,
) -> TotalsResult:
    prepared_lines: List[Dict[str, Any]] = []
    subtotal = 0.0
    line_discount_total = 0.0
    vat_total = 0.0
    grand_total = 0.0

    for idx, line in enumerate(lines, start=1):
        result = _line_calc(
            qty=line.get("qty", 0),
            unit_price=line.get("unit_price", 0),
            vat_rate=line.get("vat_rate", 0),
            vat_included=vat_included,
            line_discount_value=line.get("line_discount_value", 0),
            line_discount_type=line.get("line_discount_type", "amount"),
        )
        subtotal += result.line_subtotal
        line_discount_total += result.line_discount
        vat_total += result.line_vat
        grand_total += result.line_total

        prepared_lines.append(
            {
                **line,
                "line_no": int(line.get("line_no") or idx),
                "line_subtotal": result.line_subtotal,
                "line_discount": result.line_discount,
                "line_vat": result.line_vat,
                "line_total": result.line_total,
            }
        )

    net_subtotal = max(0.0, subtotal - line_discount_total)
    inv_discount = min(net_subtotal, _discount_amount(net_subtotal, invoice_discount_value, invoice_discount_type))
    discount_total = line_discount_total + inv_discount

    if net_subtotal > 0:
        discount_ratio = inv_discount / net_subtotal
    else:
        discount_ratio = 0.0

    if discount_ratio:
        vat_total = vat_total * (1.0 - discount_ratio)
        grand_total = (net_subtotal - inv_discount) + vat_total

    return TotalsResult(
        subtotal=round(subtotal * sign, 2),
        discount_total=round(discount_total * sign, 2),
        vat_total=round(vat_total * sign, 2),
        grand_total=round(grand_total * sign, 2),
        lines=prepared_lines,
    )
