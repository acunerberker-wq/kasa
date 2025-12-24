# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import tempfile
import unittest

from kasapro.db.main_db import DB
from kasapro.modules.hakedis.engine import HakedisEngine
from kasapro.modules.hakedis.indices import HakedisOrgProvider


class HakedisModuleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "hakedis.db")
        self.db = DB(self.db_path)
        self.company_id = 1
        self.repo = self.db.hakedis

    def tearDown(self) -> None:
        self.db.close()
        self.tmpdir.cleanup()

    def _setup_contract(self):
        project_id = self.repo.project_create(self.company_id, "Test Proje", "PRJ-1")
        contract_id = self.repo.contract_create(
            self.company_id,
            project_id,
            None,
            "CNT-1",
            "birim_fiyat",
            retention_rate=0.1,
            advance_deduction_rate=0.05,
            penalty_rate=0.02,
        )
        return project_id, contract_id

    def test_boq_import_and_total(self) -> None:
        project_id, contract_id = self._setup_contract()
        csv_path = os.path.join(self.tmpdir.name, "boq.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("poz_code,name,unit,qty_contract,unit_price,group,mahal,budget\n")
            f.write("PZ-1,Kalem 1,Adet,10,100,Grup A,M1,1000\n")
            f.write("PZ-2,Kalem 2,Adet,5,200,Grup B,M2,1000\n")
        count, total = self.repo.boq_import_csv(csv_path, self.company_id, project_id, contract_id)
        self.assertEqual(count, 2)
        self.assertAlmostEqual(total, 10 * 100 + 5 * 200)

    def test_measurement_to_pay_lines_and_cumulative(self) -> None:
        project_id, contract_id = self._setup_contract()
        boq1 = self.repo.boq_add(self.company_id, project_id, contract_id, "PZ-1", "Kalem 1", "Adet", 100, 100)
        boq2 = self.repo.boq_add(self.company_id, project_id, contract_id, "PZ-2", "Kalem 2", "Adet", 50, 200)
        p1 = self.repo.period_create(self.company_id, project_id, contract_id, 1, "2024-01-01", "2024-01-31")
        p2 = self.repo.period_create(self.company_id, project_id, contract_id, 2, "2024-02-01", "2024-02-28")
        self.repo.measurement_add(self.company_id, project_id, contract_id, p1, boq1, 10, "2024-01-10")
        self.repo.measurement_add(self.company_id, project_id, contract_id, p1, boq2, 5, "2024-01-12")
        self.repo.measurement_add(self.company_id, project_id, contract_id, p2, boq1, 6, "2024-02-10")
        totals = self.repo.pay_estimate_calculate(self.company_id, p2)
        lines = self.repo.pay_estimate_lines(self.company_id, p2)
        line_pz1 = next(l for l in lines if l["boq_item_id"] == boq1)
        self.assertAlmostEqual(line_pz1["prev_qty"], 10)
        self.assertAlmostEqual(line_pz1["current_qty"], 6)
        self.assertAlmostEqual(line_pz1["cum_qty"], 16)
        self.assertAlmostEqual(totals["current_total"], 6 * 100)

    def test_deductions_and_net_amount(self) -> None:
        project_id, contract_id = self._setup_contract()
        boq1 = self.repo.boq_add(self.company_id, project_id, contract_id, "PZ-1", "Kalem 1", "Adet", 100, 100)
        p1 = self.repo.period_create(self.company_id, project_id, contract_id, 1, "2024-02-01", "2024-02-28")
        self.repo.measurement_add(self.company_id, project_id, contract_id, p1, boq1, 6, "2024-02-10")
        totals = self.repo.pay_estimate_calculate(self.company_id, p1)
        self.assertAlmostEqual(totals["current_total"], 600)
        deductions = self.repo.deductions_list(self.company_id, p1)
        total_ded = sum(float(d["amount"]) for d in deductions)
        self.assertAlmostEqual(total_ded, 60 + 30 + 12)
        self.assertAlmostEqual(totals["net"], 600 - total_ded)

    def test_approval_flow_and_revision(self) -> None:
        project_id, contract_id = self._setup_contract()
        p1 = self.repo.period_create(self.company_id, project_id, contract_id, 1, "2024-01-01", "2024-01-31")
        self.repo.approval_add(self.company_id, "pay_estimates", p1, "Şantiye Onayı", 1, "user")
        self.repo.approval_add(self.company_id, "pay_estimates", p1, "Revizyon", 1, "user")
        approvals = self.repo.approvals_list(self.company_id, "pay_estimates", p1)
        self.assertEqual(len(approvals), 2)
        period = self.repo.period_get(self.company_id, p1)
        self.assertEqual(period["status"], "Revizyon")

    def test_attachment_safe_path(self) -> None:
        from kasapro.modules.hakedis.service import HakedisService

        service = HakedisService(self.db)
        file_path = os.path.join(self.tmpdir.name, "..", "safe.txt")
        file_path = os.path.abspath(file_path)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("data")
        original, stored, stored_path, _size = service.save_attachment(file_path, self.company_id)
        root = service._attachments_root()
        stored_abs = os.path.abspath(os.path.join(root, stored))
        self.assertTrue(os.path.commonpath([root, stored_abs]) == os.path.abspath(root))
        self.assertTrue(original.endswith("safe.txt"))
        self.assertIn(stored_path, stored_abs)

    def test_index_provider_parse(self) -> None:
        html = """
        <table>
            <tr><td>IDX-1</td><td>123.45</td></tr>
            <tr><td>IDX-2</td><td>210,5</td></tr>
        </table>
        """
        parsed = HakedisOrgProvider.parse_indices_html(html, ["IDX-1", "IDX-2", "IDX-3"])
        self.assertAlmostEqual(parsed["IDX-1"], 123.45)
        self.assertAlmostEqual(parsed["IDX-2"], 210.5)

    def test_index_cache_fallback(self) -> None:
        self.repo.indices_cache_set(self.company_id, "hakedis_org", "IDX-1", 150.0, "2024-01", "{}")
        from kasapro.modules.hakedis.service import HakedisService
        service = HakedisService(self.db)
        indices = service.index_fetch_with_cache(self.company_id, ["IDX-1"], "2024-01", refresh=False)
        self.assertAlmostEqual(indices["IDX-1"], 150.0)

    def test_price_diff_report(self) -> None:
        project_id, contract_id = self._setup_contract()
        self.repo.price_diff_rule_set(
            self.company_id,
            contract_id,
            "standart",
            {
                "weights": {"labor": 0.4, "material": 0.6},
                "base_indices": {"labor": 100, "material": 100},
            },
            "2023-12",
        )
        engine = HakedisEngine(self.repo)
        row = engine.calculate_price_diff(
            self.company_id,
            contract_id,
            "2024-01",
            1000,
            {"labor": 110, "material": 120},
        )
        self.assertGreater(row.diff_amount, 0)
        self.assertAlmostEqual(row.base_amount, 1000)

    def test_remaining_work_report(self) -> None:
        project_id, contract_id = self._setup_contract()
        boq1 = self.repo.boq_add(self.company_id, project_id, contract_id, "PZ-1", "Kalem 1", "Adet", 10, 100)
        p1 = self.repo.period_create(self.company_id, project_id, contract_id, 1, "2024-01-01", "2024-01-31")
        self.repo.measurement_add(self.company_id, project_id, contract_id, p1, boq1, 4, "2024-01-10")
        rows = self.repo.report_remaining_by_poz(self.company_id, contract_id)
        row = rows[0]
        self.assertAlmostEqual(row["qty_remaining"], 6)

    def test_budget_variance_report(self) -> None:
        project_id, contract_id = self._setup_contract()
        boq1 = self.repo.boq_add(self.company_id, project_id, contract_id, "PZ-1", "Kalem 1", "Adet", 10, 100, budget=1500)
        p1 = self.repo.period_create(self.company_id, project_id, contract_id, 1, "2024-01-01", "2024-01-31")
        self.repo.measurement_add(self.company_id, project_id, contract_id, p1, boq1, 5, "2024-01-10")
        rows = self.repo.report_budget_variance(self.company_id, contract_id)
        row = rows[0]
        self.assertAlmostEqual(row["actual"], 500)
        self.assertAlmostEqual(row["variance"], 1000)

    def test_audit_log_written(self) -> None:
        project_id, _contract_id = self._setup_contract()
        audits = self.repo.audit_list(self.company_id, "projects")
        self.assertTrue(any(int(row["ref_id"]) == project_id for row in audits))


if __name__ == "__main__":
    unittest.main()
