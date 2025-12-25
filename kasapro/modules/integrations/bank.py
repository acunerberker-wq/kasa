# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from kasapro.utils import parse_date_smart

from .repo import IntegrationRepo


@dataclass
class BankTransactionRow:
    transaction_date: str
    amount: float
    description: str


class BankStatementService:
    def __init__(self, repo: IntegrationRepo):
        self.repo = repo

    def parse_csv(self, csv_path: Path) -> List[BankTransactionRow]:
        rows: List[BankTransactionRow] = []
        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                date_val = parse_date_smart(row.get("tarih") or row.get("date") or "")
                amount = float(str(row.get("tutar") or row.get("amount") or 0).replace(",", "."))
                desc = str(row.get("aciklama") or row.get("description") or "")
                rows.append(BankTransactionRow(date_val, amount, desc))
        return rows

    def import_statement(
        self,
        company_id: int,
        source_name: str,
        period_start: str,
        period_end: str,
        transactions: List[BankTransactionRow],
    ) -> Tuple[int, int, int]:
        statement_id = self.repo.bank_statement_add(company_id, source_name, period_start, period_end)
        inserted = 0
        skipped = 0
        for tx in transactions:
            unique_hash = self._unique_hash(company_id, tx.transaction_date, tx.amount, tx.description)
            ok = self.repo.bank_transaction_add(
                company_id,
                statement_id,
                tx.transaction_date,
                tx.amount,
                tx.description,
                unique_hash,
            )
            if ok:
                inserted += 1
            else:
                skipped += 1
        return statement_id, inserted, skipped

    def auto_reconcile(self, company_id: int, conn, window_days: int = 3) -> int:
        unmatched = self.repo.bank_transactions_list(company_id, matched=0)
        if not unmatched:
            return 0
        matched_count = 0
        for tx in unmatched:
            amount = float(tx["amount"])
            tx_date = tx["transaction_date"]
            candidates = conn.execute(
                """
                SELECT id, tarih, tutar FROM fatura_odeme
                WHERE ABS(tutar - ?) < 0.01
                """,
                (amount,),
            ).fetchall()
            for c in candidates:
                if self._date_close(tx_date, c["tarih"], window_days):
                    self.repo.bank_transaction_mark_matched(int(tx["id"]), f"payment:{c['id']}")
                    matched_count += 1
                    break
        return matched_count

    def manual_reconcile(self, tx_id: int, reference: str) -> None:
        self.repo.bank_transaction_mark_matched(tx_id, reference)

    def _unique_hash(self, company_id: int, date_val: str, amount: float, description: str) -> str:
        raw = f"{company_id}|{date_val}|{amount:.2f}|{description.strip().lower()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _date_close(self, d1: str, d2: str, window_days: int) -> bool:
        try:
            dt1 = datetime.strptime(d1, "%Y-%m-%d")
            dt2 = datetime.strptime(d2, "%Y-%m-%d")
            return abs((dt1 - dt2).days) <= window_days
        except Exception:
            return False
