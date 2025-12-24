# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import tempfile
import unittest

from kasapro.db.main_db import DB
from modules.hr.service import HRService, HRContext


class HRModuleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "hr.db")
        self.db = DB(self.db_path)
        self.admin = self._service("admin", "admin")
        self.admin.set_user_role("hr_user", "HR_USER")
        self.admin.set_user_role("manager", "MANAGER")
        self.admin.set_user_role("accounting", "ACCOUNTING")
        self.admin.set_user_role("viewer", "VIEWER")

    def tearDown(self) -> None:
        self.db.close()
        self.tmpdir.cleanup()

    def _service(self, username: str, role: str) -> HRService:
        ctx = HRContext(company_id=1, actor_username=username, actor_role=role)
        return HRService(self.db, lambda: ctx)

    def _seed_employee(self) -> int:
        dept_id = self.admin.department_create("IT")
        pos_id = self.admin.position_create("Developer", dept_id)
        return self.admin.employee_create(
            {
                "employee_no": "EMP-001",
                "first_name": "Ada",
                "last_name": "Lovelace",
                "department_id": dept_id,
                "position_id": pos_id,
                "status": "aktif",
                "tckn": "12345678901",
                "iban": "TR000000000000000000000001",
            }
        )

    def test_employee_crud_and_passive(self) -> None:
        emp_id = self._seed_employee()
        rows = self.admin.employee_list()
        self.assertTrue(any(int(r["id"]) == emp_id for r in rows))
        self.admin.employee_update(emp_id, {
            "employee_no": "EMP-001",
            "first_name": "Ada",
            "last_name": "Byron",
            "status": "aktif",
        })
        self.admin.employee_set_status(emp_id, "pasif")
        updated = [r for r in self.admin.employee_list() if int(r["id"]) == emp_id][0]
        self.assertEqual(updated["status"], "pasif")

    def test_department_and_position_crud(self) -> None:
        dept_id = self.admin.department_create("Satış")
        self.admin.department_update(dept_id, "Satış & Pazarlama")
        pos_id = self.admin.position_create("Satış Uzmanı", dept_id)
        self.admin.position_update(pos_id, "Kıdemli Satış", dept_id)
        self.admin.position_delete(pos_id)
        self.admin.department_delete(dept_id)
        self.assertFalse(self.admin.department_list())

    def test_leave_flow_manager_and_hr_approval(self) -> None:
        emp_id = self._seed_employee()
        lt_id = self.admin.leave_type_create("Yıllık", 14)
        hr_user = self._service("hr_user", "user")
        manager = self._service("manager", "user")
        req_id = hr_user.leave_request_create(emp_id, lt_id, "2024-01-10", "2024-01-12")
        manager.leave_request_manager_approve(req_id)
        hr_user.leave_request_hr_approve(req_id)
        rows = hr_user.leave_request_list()
        status = [r for r in rows if int(r["id"]) == req_id][0]["status"]
        self.assertEqual(status, "approved")

    def test_leave_overlap_check(self) -> None:
        emp_id = self._seed_employee()
        lt_id = self.admin.leave_type_create("Yıllık", 14)
        hr_user = self._service("hr_user", "user")
        hr_user.leave_request_create(emp_id, lt_id, "2024-02-01", "2024-02-03")
        with self.assertRaises(ValueError):
            hr_user.leave_request_create(emp_id, lt_id, "2024-02-02", "2024-02-04")

    def test_leave_balance_updates(self) -> None:
        emp_id = self._seed_employee()
        lt_id = self.admin.leave_type_create("Yıllık", 14)
        hr_user = self._service("hr_user", "user")
        manager = self._service("manager", "user")
        req_id = hr_user.leave_request_create(emp_id, lt_id, "2024-03-01", "2024-03-05")
        manager.leave_request_manager_approve(req_id)
        hr_user.leave_request_hr_approve(req_id)
        balances = hr_user.leave_balance_list(2024)
        self.assertTrue(balances)
        self.assertEqual(float(balances[0]["used_days"]), 5.0)

    def test_timesheet_and_report(self) -> None:
        emp_id = self._seed_employee()
        self.admin.timesheet_upsert(emp_id, "2024-04-01", "calisti", None)
        report = self.admin.report_timesheet_summary("2024-04-01", "2024-04-30")
        self.assertTrue(report)
        self.assertEqual(int(report[0]["calisti"]), 1)

    def test_overtime_flow(self) -> None:
        emp_id = self._seed_employee()
        hr_user = self._service("hr_user", "user")
        manager = self._service("manager", "user")
        req_id = hr_user.overtime_request_create(emp_id, "2024-05-10", 3)
        manager.overtime_request_approve(req_id)
        rows = manager.overtime_request_list()
        status = [r for r in rows if int(r["id"]) == req_id][0]["status"]
        self.assertEqual(status, "approved")

    def test_payroll_period_and_report(self) -> None:
        emp_id = self._seed_employee()
        accounting = self._service("accounting", "user")
        period_id = accounting.payroll_period_create(2024, 6)
        accounting.payroll_item_add(period_id, emp_id, "maaş", "Haziran", 10000, "TL")
        report = accounting.report_payroll_summary(period_id)
        self.assertTrue(report)
        self.assertEqual(float(report[0]["total_amount"]), 10000.0)

    def test_payroll_lock_prevents_change(self) -> None:
        emp_id = self._seed_employee()
        accounting = self._service("accounting", "user")
        period_id = accounting.payroll_period_create(2024, 7)
        accounting.payroll_period_lock(period_id, 1)
        with self.assertRaises(ValueError):
            accounting.payroll_item_add(period_id, emp_id, "maaş", "Temmuz", 9000, "TL")

    def test_unauthorized_action_audit_logged(self) -> None:
        viewer = self._service("viewer", "user")
        with self.assertRaises(PermissionError):
            viewer.department_create("Gizli")
        audits = viewer.report_audit(50)
        self.assertTrue(any(a["action"] == "unauthorized" for a in audits))


if __name__ == "__main__":
    unittest.main()
