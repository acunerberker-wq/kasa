# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple


@dataclass
class ReportRow:
    key: str
    label: str
    value: float


class HakedisRepo:
    def __init__(self, conn: sqlite3.Connection, log_fn=None, **kwargs):
        self.conn = conn
        if log_fn is None:
            log_fn = kwargs.get("log_fn")
        self.log_fn = log_fn

    def _now(self) -> str:
        # Use timezone-aware UTC to avoid deprecation warnings
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def _audit(
        self,
        company_id: Optional[int],
        module: str,
        ref_id: Optional[int],
        action: str,
        user_id: Optional[int] = None,
        username: str = "",
        detail: str = "",
    ) -> None:
        try:
            self.conn.execute(
                """
                INSERT INTO audit_log(company_id, entity_type, entity_id, module, ref_id, action, user_id, username, details, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    company_id,
                    module,
                    ref_id,
                    module,
                    ref_id,
                    action,
                    user_id,
                    username,
                    detail,
                    self._now(),
                ),
            )
            self.conn.commit()
        except Exception:
            pass

    def _log(self, msg: str) -> None:
        if not self.log_fn:
            return
        try:
            self.log_fn("Hakediş", msg)
        except Exception:
            pass

    # -----------------
    # Proje / Şantiye
    # -----------------
    def project_create(
        self,
        company_id: int,
        name: str,
        code: str,
        status: str = "active",
        notes: str = "",
        user_id: Optional[int] = None,
        username: str = "",
    ) -> int:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO projects(company_id, name, code, status, notes, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?)
            """,
            (company_id, name, code, status, notes, self._now(), self._now()),
        )
        self.conn.commit()
        pid = int(cur.lastrowid)
        self._audit(company_id, "projects", pid, "create", user_id, username, name)
        self._log(f"Proje oluşturuldu: {name} (id={pid})")
        return pid

    def project_list(self, company_id: int, only_active: bool = True) -> List[sqlite3.Row]:
        cur = self.conn.cursor()
        if only_active:
            rows = cur.execute(
                "SELECT * FROM projects WHERE company_id=? AND status='active' ORDER BY id DESC",
                (company_id,),
            ).fetchall()
        else:
            rows = cur.execute(
                "SELECT * FROM projects WHERE company_id=? ORDER BY id DESC",
                (company_id,),
            ).fetchall()
        return rows

    def site_create(
        self,
        company_id: int,
        project_id: int,
        name: str,
        location: str = "",
        status: str = "active",
        user_id: Optional[int] = None,
        username: str = "",
    ) -> int:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO sites(company_id, project_id, name, location, status, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?)
            """,
            (company_id, project_id, name, location, status, self._now(), self._now()),
        )
        self.conn.commit()
        sid = int(cur.lastrowid)
        self._audit(company_id, "sites", sid, "create", user_id, username, name)
        self._log(f"Şantiye oluşturuldu: {name} (id={sid})")
        return sid

    # -----------------
    # Sözleşme
    # -----------------
    def contract_create(
        self,
        company_id: int,
        project_id: int,
        site_id: Optional[int],
        contract_no: str,
        contract_type: str,
        currency: str = "TL",
        advance_rate: float = 0.0,
        retention_rate: float = 0.0,
        advance_deduction_rate: float = 0.0,
        penalty_rate: float = 0.0,
        price_diff_enabled: int = 0,
        formula_template: str = "",
        formula_params: Optional[Dict[str, Any]] = None,
        status: str = "active",
        user_id: Optional[int] = None,
        username: str = "",
    ) -> int:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO contracts(
                company_id, project_id, site_id, contract_no, contract_type, currency,
                advance_rate, retention_rate, advance_deduction_rate, penalty_rate,
                price_diff_enabled, formula_template, formula_params, status, created_at, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                company_id,
                project_id,
                site_id,
                contract_no,
                contract_type,
                currency,
                advance_rate,
                retention_rate,
                advance_deduction_rate,
                penalty_rate,
                price_diff_enabled,
                formula_template,
                json.dumps(formula_params or {}, ensure_ascii=False),
                status,
                self._now(),
                self._now(),
            ),
        )
        self.conn.commit()
        cid = int(cur.lastrowid)
        self._audit(company_id, "contracts", cid, "create", user_id, username, contract_no)
        self._log(f"Sözleşme oluşturuldu: {contract_no} (id={cid})")
        return cid

    def contract_get(self, contract_id: int, company_id: int) -> Optional[sqlite3.Row]:
        cur = self.conn.cursor()
        row = cur.execute(
            "SELECT * FROM contracts WHERE id=? AND company_id=?",
            (contract_id, company_id),
        ).fetchone()
        return row

    def contract_list(self, company_id: int, project_id: Optional[int] = None) -> List[sqlite3.Row]:
        cur = self.conn.cursor()
        if project_id:
            rows = cur.execute(
                """
                SELECT * FROM contracts
                WHERE company_id=? AND project_id=? AND status='active'
                ORDER BY id DESC
                """,
                (company_id, project_id),
            ).fetchall()
        else:
            rows = cur.execute(
                "SELECT * FROM contracts WHERE company_id=? AND status='active' ORDER BY id DESC",
                (company_id,),
            ).fetchall()
        return rows

    # -----------------
    # Poz (BOQ)
    # -----------------
    def boq_add(
        self,
        company_id: int,
        project_id: int,
        contract_id: int,
        poz_code: str,
        name: str,
        unit: str,
        qty_contract: float,
        unit_price: float,
        group_name: str = "",
        mahal: str = "",
        budget: float = 0.0,
        status: str = "active",
        rev_note: str = "",
        user_id: Optional[int] = None,
        username: str = "",
    ) -> int:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO boq_items(
                company_id, project_id, contract_id, poz_code, name, unit,
                qty_contract, unit_price, group_name, mahal, budget, status, created_at, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                company_id,
                project_id,
                contract_id,
                poz_code,
                name,
                unit,
                qty_contract,
                unit_price,
                group_name,
                mahal,
                budget,
                status,
                self._now(),
                self._now(),
            ),
        )
        self.conn.commit()
        bid = int(cur.lastrowid)
        self._boq_revision(company_id, bid, rev_note or "İlk kayıt")
        self._audit(company_id, "boq_items", bid, "create", user_id, username, poz_code)
        return bid

    def _boq_revision(self, company_id: int, boq_item_id: int, note: str) -> None:
        row = self.conn.execute("SELECT * FROM boq_items WHERE id=?", (boq_item_id,)).fetchone()
        if not row:
            return
        rev_no = 1
        rev_row = self.conn.execute(
            "SELECT MAX(rev_no) FROM boq_revisions WHERE boq_item_id=?",
            (boq_item_id,),
        ).fetchone()
        if rev_row and rev_row[0]:
            rev_no = int(rev_row[0]) + 1
        snapshot = json.dumps({k: row[k] for k in row.keys()}, ensure_ascii=False)
        self.conn.execute(
            """
            INSERT INTO boq_revisions(company_id, boq_item_id, rev_no, note, snapshot_json, created_at)
            VALUES (?,?,?,?,?,?)
            """,
            (company_id, boq_item_id, rev_no, note, snapshot, self._now()),
        )
        self.conn.commit()

    def boq_list(self, company_id: int, contract_id: int) -> List[sqlite3.Row]:
        cur = self.conn.cursor()
        return cur.execute(
            """
            SELECT * FROM boq_items
            WHERE company_id=? AND contract_id=? AND status='active'
            ORDER BY poz_code
            """,
            (company_id, contract_id),
        ).fetchall()

    def boq_import_csv(
        self,
        path: str,
        company_id: int,
        project_id: int,
        contract_id: int,
        encoding: str = "utf-8",
        user_id: Optional[int] = None,
        username: str = "",
    ) -> Tuple[int, float]:
        import csv

        total = 0.0
        count = 0
        with open(path, "r", encoding=encoding, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                poz_code = str(row.get("poz_code") or row.get("poz") or row.get("code") or "").strip()
                if not poz_code:
                    continue
                name = str(row.get("name") or row.get("ad") or "").strip()
                unit = str(row.get("unit") or row.get("birim") or "").strip() or "Adet"
                qty_contract = float(row.get("qty_contract") or row.get("miktar") or 0)
                unit_price = float(row.get("unit_price") or row.get("birim_fiyat") or 0)
                group_name = str(row.get("group") or row.get("grup") or "").strip()
                mahal = str(row.get("mahal") or "").strip()
                budget = float(row.get("budget") or 0)
                self.boq_add(
                    company_id,
                    project_id,
                    contract_id,
                    poz_code,
                    name,
                    unit,
                    qty_contract,
                    unit_price,
                    group_name=group_name,
                    mahal=mahal,
                    budget=budget,
                    rev_note="CSV İçe Aktarım",
                    user_id=user_id,
                    username=username,
                )
                total += qty_contract * unit_price
                count += 1
        self._log(f"BOQ içe aktarıldı: {count} satır, toplam={total:.2f}")
        return count, total

    # -----------------
    # Metraj
    # -----------------
    def measurement_add(
        self,
        company_id: int,
        project_id: int,
        contract_id: int,
        period_id: int,
        boq_item_id: int,
        qty: float,
        tarih: str,
        mahal: str = "",
        note: str = "",
        attachment_id: Optional[int] = None,
        user_id: Optional[int] = None,
        username: str = "",
    ) -> int:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO measurements(
                company_id, project_id, contract_id, period_id, boq_item_id,
                qty, tarih, mahal, note, attachment_id, status, created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                company_id,
                project_id,
                contract_id,
                period_id,
                boq_item_id,
                qty,
                tarih,
                mahal,
                note,
                attachment_id,
                "active",
                self._now(),
            ),
        )
        self.conn.commit()
        mid = int(cur.lastrowid)
        self._audit(company_id, "measurements", mid, "create", user_id, username, f"qty={qty}")
        return mid

    # -----------------
    # Dönem / Hakediş
    # -----------------
    def period_create(
        self,
        company_id: int,
        project_id: int,
        contract_id: int,
        period_no: int,
        start_date: str,
        end_date: str,
        status: str = "Taslak",
        user_id: Optional[int] = None,
        username: str = "",
    ) -> int:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO pay_estimates(
                company_id, project_id, contract_id, period_no,
                start_date, end_date, status, created_at, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (
                company_id,
                project_id,
                contract_id,
                period_no,
                start_date,
                end_date,
                status,
                self._now(),
                self._now(),
            ),
        )
        self.conn.commit()
        pid = int(cur.lastrowid)
        self._audit(company_id, "pay_estimates", pid, "create", user_id, username, f"no={period_no}")
        return pid

    def period_get(self, company_id: int, period_id: int) -> Optional[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM pay_estimates WHERE id=? AND company_id=?",
            (period_id, company_id),
        ).fetchone()

    def period_list(self, company_id: int, contract_id: int) -> List[sqlite3.Row]:
        return self.conn.execute(
            """
            SELECT * FROM pay_estimates
            WHERE company_id=? AND contract_id=?
            ORDER BY period_no
            """,
            (company_id, contract_id),
        ).fetchall()

    def pay_estimate_calculate(self, company_id: int, period_id: int) -> Dict[str, float]:
        period = self.period_get(company_id, period_id)
        if not period:
            raise ValueError("Hakediş dönemi bulunamadı.")
        contract_id = int(period["contract_id"])
        start_date = str(period["start_date"])
        end_date = str(period["end_date"])

        lines = []
        boq_rows = self.boq_list(company_id, contract_id)
        for row in boq_rows:
            boq_id = int(row["id"])
            unit_price = float(row["unit_price"] or 0)
            prev_qty = self._sum_measurement_qty(company_id, boq_id, None, start_date)
            current_qty = self._sum_measurement_qty(company_id, boq_id, start_date, end_date)
            cum_qty = prev_qty + current_qty
            prev_amount = prev_qty * unit_price
            current_amount = current_qty * unit_price
            cum_amount = cum_qty * unit_price
            lines.append(
                (
                    period_id,
                    boq_id,
                    prev_qty,
                    current_qty,
                    cum_qty,
                    unit_price,
                    prev_amount,
                    current_amount,
                    cum_amount,
                    "active",
                    self._now(),
                )
            )

        self.conn.execute(
            "UPDATE pay_estimate_lines SET status='passive' WHERE company_id=? AND pay_estimate_id=?",
            (company_id, period_id),
        )
        self.conn.executemany(
            """
            INSERT INTO pay_estimate_lines(
                company_id, pay_estimate_id, boq_item_id,
                prev_qty, current_qty, cum_qty, unit_price,
                prev_amount, current_amount, cum_amount, status, created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            [(company_id, *line) for line in lines],
        )
        self.conn.commit()
        totals = self._sum_pay_estimate_totals(company_id, period_id)
        deductions = self._calculate_deductions(company_id, period_id, contract_id, totals["current_total"])
        net = totals["current_total"] - deductions
        self.conn.execute(
            "UPDATE pay_estimates SET updated_at=? WHERE id=?",
            (self._now(), period_id),
        )
        self.conn.commit()
        self._audit(company_id, "pay_estimates", period_id, "calculate", detail=f"net={net:.2f}")
        return {"net": net, **totals}

    def _sum_measurement_qty(
        self,
        company_id: int,
        boq_item_id: int,
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> float:
        base_sql = """
            SELECT COALESCE(SUM(qty),0) FROM measurements
            WHERE company_id=? AND boq_item_id=? AND status='active'
        """
        params: List[Any] = [company_id, boq_item_id]
        if start_date and end_date:
            base_sql += " AND tarih>=? AND tarih<=?"
            params.extend([start_date, end_date])
        elif end_date and not start_date:
            base_sql += " AND tarih<?"
            params.append(end_date)
        row = self.conn.execute(base_sql, params).fetchone()
        return float(row[0] or 0)

    def _sum_pay_estimate_totals(self, company_id: int, period_id: int) -> Dict[str, float]:
        row = self.conn.execute(
            """
            SELECT
                COALESCE(SUM(prev_amount),0),
                COALESCE(SUM(current_amount),0),
                COALESCE(SUM(cum_amount),0)
            FROM pay_estimate_lines
            WHERE company_id=? AND pay_estimate_id=? AND status='active'
            """,
            (company_id, period_id),
        ).fetchone()
        return {
            "prev_total": float(row[0] or 0),
            "current_total": float(row[1] or 0),
            "cum_total": float(row[2] or 0),
        }

    def _calculate_deductions(
        self, company_id: int, period_id: int, contract_id: int, base_amount: float
    ) -> float:
        contract = self.contract_get(contract_id, company_id)
        if not contract:
            return 0.0
        retention_rate = float(contract["retention_rate"] or 0)
        advance_rate = float(contract["advance_deduction_rate"] or 0)
        penalty_rate = float(contract["penalty_rate"] or 0)

        self.conn.execute(
            "UPDATE deductions SET status='passive' WHERE company_id=? AND pay_estimate_id=?",
            (company_id, period_id),
        )
        total = 0.0
        def add_deduction(dtype: str, rate: float):
            nonlocal total
            amount = round(base_amount * rate, 2)
            if amount <= 0:
                return
            total += amount
            self.conn.execute(
                """
                INSERT INTO deductions(company_id, pay_estimate_id, type, rate, amount, status, created_at)
                VALUES (?,?,?,?,?,?,?)
                """,
                (company_id, period_id, dtype, rate, amount, "active", self._now()),
            )

        add_deduction("retention", retention_rate)
        add_deduction("advance", advance_rate)
        add_deduction("penalty", penalty_rate)
        self.conn.commit()
        return total

    def pay_estimate_lines(self, company_id: int, period_id: int) -> List[sqlite3.Row]:
        return self.conn.execute(
            """
            SELECT l.*, b.poz_code, b.name
            FROM pay_estimate_lines l
            JOIN boq_items b ON b.id=l.boq_item_id
            WHERE l.company_id=? AND l.pay_estimate_id=? AND l.status='active'
            ORDER BY b.poz_code
            """,
            (company_id, period_id),
        ).fetchall()

    def deductions_list(self, company_id: int, period_id: int) -> List[sqlite3.Row]:
        return self.conn.execute(
            """
            SELECT * FROM deductions
            WHERE company_id=? AND pay_estimate_id=? AND status='active'
            ORDER BY id
            """,
            (company_id, period_id),
        ).fetchall()

    # -----------------
    # Onay Akışı
    # -----------------
    def approval_add(
        self,
        company_id: int,
        module: str,
        ref_id: int,
        status: str,
        user_id: Optional[int],
        username: str,
        comment: str = "",
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO approvals(company_id, module, ref_id, status, user_id, username, comment, created_at)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (company_id, module, ref_id, status, user_id, username, comment, self._now()),
        )
        if module == "pay_estimates":
            self.conn.execute(
                "UPDATE pay_estimates SET status=?, updated_at=? WHERE id=? AND company_id=?",
                (status, self._now(), ref_id, company_id),
            )
        self.conn.commit()
        self._audit(company_id, module, ref_id, "approval", user_id, username, status)

    def approvals_list(self, company_id: int, module: str, ref_id: int) -> List[sqlite3.Row]:
        return self.conn.execute(
            """
            SELECT * FROM approvals
            WHERE company_id=? AND module=? AND ref_id=?
            ORDER BY id
            """,
            (company_id, module, ref_id),
        ).fetchall()

    # -----------------
    # Endeks / Fiyat Farkı
    # -----------------
    def indices_cache_set(
        self,
        company_id: int,
        provider: str,
        index_code: str,
        index_value: float,
        period: str,
        raw_json: str,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO indices_cache(company_id, provider, index_code, index_value, period, fetched_at, raw_json)
            VALUES (?,?,?,?,?,?,?)
            """,
            (company_id, provider, index_code, index_value, period, self._now(), raw_json),
        )
        self.conn.commit()

    def indices_cache_get(
        self,
        company_id: int,
        provider: str,
        index_code: str,
        period: str,
    ) -> Optional[float]:
        row = self.conn.execute(
            """
            SELECT index_value FROM indices_cache
            WHERE company_id=? AND provider=? AND index_code=? AND period=?
            ORDER BY id DESC LIMIT 1
            """,
            (company_id, provider, index_code, period),
        ).fetchone()
        if not row:
            return None
        return float(row[0])

    def price_diff_rule_set(
        self,
        company_id: int,
        contract_id: int,
        formula_name: str,
        formula_params: Dict[str, Any],
        base_period: str,
    ) -> int:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO price_diff_rules(company_id, contract_id, formula_name, formula_params, base_period, created_at)
            VALUES (?,?,?,?,?,?)
            """,
            (
                company_id,
                contract_id,
                formula_name,
                json.dumps(formula_params or {}, ensure_ascii=False),
                base_period,
                self._now(),
            ),
        )
        self.conn.commit()
        rid = int(cur.lastrowid)
        self._audit(company_id, "price_diff_rules", rid, "create", detail=formula_name)
        return rid

    def price_diff_rule_get(self, company_id: int, contract_id: int) -> Optional[sqlite3.Row]:
        return self.conn.execute(
            """
            SELECT * FROM price_diff_rules
            WHERE company_id=? AND contract_id=?
            ORDER BY id DESC LIMIT 1
            """,
            (company_id, contract_id),
        ).fetchone()

    # -----------------
    # Raporlar
    # -----------------
    def report_remaining_by_poz(self, company_id: int, contract_id: int) -> List[sqlite3.Row]:
        return self.conn.execute(
            """
            SELECT b.poz_code, b.name, b.qty_contract,
                   COALESCE(SUM(m.qty),0) AS qty_done,
                   (b.qty_contract - COALESCE(SUM(m.qty),0)) AS qty_remaining
            FROM boq_items b
            LEFT JOIN measurements m ON m.boq_item_id=b.id AND m.status='active'
            WHERE b.company_id=? AND b.contract_id=? AND b.status='active'
            GROUP BY b.id
            ORDER BY b.poz_code
            """,
            (company_id, contract_id),
        ).fetchall()

    def report_budget_variance(self, company_id: int, contract_id: int) -> List[sqlite3.Row]:
        return self.conn.execute(
            """
            SELECT b.poz_code, b.name, b.budget,
                   COALESCE(SUM(m.qty * b.unit_price),0) AS actual,
                   (b.budget - COALESCE(SUM(m.qty * b.unit_price),0)) AS variance
            FROM boq_items b
            LEFT JOIN measurements m ON m.boq_item_id=b.id AND m.status='active'
            WHERE b.company_id=? AND b.contract_id=? AND b.status='active'
            GROUP BY b.id
            ORDER BY b.poz_code
            """,
            (company_id, contract_id),
        ).fetchall()

    def report_pay_estimate_summary(self, company_id: int, period_id: int) -> Dict[str, float]:
        totals = self._sum_pay_estimate_totals(company_id, period_id)
        deductions = self.deductions_list(company_id, period_id)
        total_ded = sum(float(d["amount"] or 0) for d in deductions)
        return {
            **totals,
            "deductions_total": total_ded,
            "net": totals["current_total"] - total_ded,
        }

    def audit_list(self, company_id: int, module: str) -> List[sqlite3.Row]:
        return self.conn.execute(
            """
            SELECT * FROM audit_log WHERE company_id=? AND module=? ORDER BY id DESC
            """,
            (company_id, module),
        ).fetchall()
