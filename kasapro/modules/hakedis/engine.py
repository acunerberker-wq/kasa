# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, List, Optional

from .repo import HakedisRepo


@dataclass
class PriceDiffRow:
    period: str
    base_amount: float
    factor: float
    diff_amount: float


class HakedisEngine:
    def __init__(self, repo: HakedisRepo):
        self.repo = repo

    def calculate_price_diff(
        self,
        company_id: int,
        contract_id: int,
        period: str,
        amount: float,
        index_values: Dict[str, float],
    ) -> PriceDiffRow:
        rule = self.repo.price_diff_rule_get(company_id, contract_id)
        if not rule:
            return PriceDiffRow(period=period, base_amount=amount, factor=0.0, diff_amount=0.0)
        params = {}
        try:
            params = json.loads(rule["formula_params"] or "{}")
        except Exception:
            params = {}
        weights = params.get("weights", {})
        base_indices = params.get("base_indices", {})
        factor = 0.0
        for key, weight in weights.items():
            try:
                w = float(weight)
            except Exception:
                continue
            period_value = float(index_values.get(key) or 0)
            base_value = float(base_indices.get(key) or 0)
            if base_value <= 0:
                continue
            factor += w * ((period_value / base_value) - 1)
        diff_amount = amount * factor
        return PriceDiffRow(period=period, base_amount=amount, factor=factor, diff_amount=diff_amount)

    def price_diff_report(
        self,
        company_id: int,
        contract_id: int,
        periods: List[str],
        amounts: List[float],
        index_lookup: Dict[str, Dict[str, float]],
    ) -> List[PriceDiffRow]:
        rows: List[PriceDiffRow] = []
        for period, amount in zip(periods, amounts):
            indices = index_lookup.get(period, {})
            rows.append(self.calculate_price_diff(company_id, contract_id, period, amount, indices))
        return rows
