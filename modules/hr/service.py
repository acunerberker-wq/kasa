# -*- coding: utf-8 -*-

from __future__ import annotations

import logging
import os
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, Iterable, List, Optional

from kasapro.utils import now_iso
from kasapro.config import HR_ATTACHMENTS_DIR
from kasapro.db.main_db import DB
from kasapro.db.repos.hr_repo import HRRepo

from .constants import HR_ROLES, HR_ROLE_DEFAULTS


@dataclass(frozen=True)
class HRContext:
    company_id: int
    actor_username: str
    actor_role: str


class HRService:
    def __init__(self, db: DB, context_provider: Callable[[], HRContext], attachments_dir: Optional[str] = None):
        self.db = db
        self.repo = HRRepo(db.conn)
        self._context_provider = context_provider
        self.logger = logging.getLogger("kasapro.hr")
        self.attachments_dir = attachments_dir or HR_ATTACHMENTS_DIR
        try:
            os.makedirs(self.attachments_dir, exist_ok=True)
        except Exception:
            pass

    def _ctx(self) -> HRContext:
        return self._context_provider()

    def _company_id(self) -> int:
        ctx = self._ctx()
        return int(ctx.company_id or 1)

    def _actor(self) -> str:
        return self._ctx().actor_username

    def _actor_role(self) -> str:
        return self._ctx().actor_role

    def _default_hr_role(self) -> str:
        return HR_ROLE_DEFAULTS.get(self._actor_role(), "HR_USER")

    def get_user_role(self, username: Optional[str] = None) -> str:
        company_id = self._company_id()
        username = username or self._actor()
        row = self.repo.user_role_get(company_id, username)
        if row:
            return str(row["role"])
        if username == self._actor():
            return self._default_hr_role()
        return "HR_USER"

    def list_user_roles(self) -> List[dict]:
        company_id = self._company_id()
        rows = self.repo.user_roles_list(company_id)
        return [dict(r) for r in rows]

    def set_user_role(self, username: str, role: str) -> None:
        if role not in HR_ROLES:
            raise ValueError("Geçersiz HR rolü")
        company_id = self._company_id()
        self.repo.user_role_upsert(company_id, username.strip(), role)
        self.audit("user_role", None, "set_role", f"{username} -> {role}")

    def can_view_sensitive(self, role: Optional[str] = None) -> bool:
        role = role or self.get_user_role()
        return role in ("HR_ADMIN", "ACCOUNTING")

    def mask_sensitive(self, value: str, role: Optional[str] = None) -> str:
        value = value or ""
        if not value:
            return ""
        if self.can_view_sensitive(role):
            return value
        if len(value) <= 4:
            return "*" * len(value)
        return "*" * (len(value) - 4) + value[-4:]

    def _require_roles(self, allowed: Iterable[str]) -> None:
        role = self.get_user_role()
        if role not in allowed:
            self.repo.audit_log(
                self._company_id(),
                entity_type="auth",
                entity_id=None,
                action="unauthorized",
                actor_username=self._actor(),
                actor_role=role,
                detail=f"allowed={','.join(allowed)}",
            )
            raise PermissionError("Bu işlem için yetkiniz yok.")

    def audit(self, entity_type: str, entity_id: Optional[int], action: str, detail: str = "") -> None:
        company_id = self._company_id()
        self.repo.audit_log(
            company_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            actor_username=self._actor(),
            actor_role=self.get_user_role(),
            detail=detail,
        )
        self.logger.info("HR audit %s %s (%s)", action, entity_type, detail)

    # -----------------
    # Organizasyon
    # -----------------
    def department_list(self) -> List[dict]:
        company_id = self._company_id()
        return [dict(r) for r in self.repo.department_list(company_id)]

    def department_create(self, name: str, active: int = 1) -> int:
        self._require_roles(["HR_ADMIN"])
        company_id = self._company_id()
        dept_id = self.repo.department_create(company_id, name, active)
        self.audit("department", dept_id, "create", name)
        return dept_id

    def department_update(self, dept_id: int, name: str, active: int = 1) -> None:
        self._require_roles(["HR_ADMIN"])
        company_id = self._company_id()
        self.repo.department_update(company_id, dept_id, name, active)
        self.audit("department", dept_id, "update", name)

    def department_delete(self, dept_id: int) -> None:
        self._require_roles(["HR_ADMIN"])
        company_id = self._company_id()
        self.repo.department_delete(company_id, dept_id)
        self.audit("department", dept_id, "delete")

    def position_list(self) -> List[dict]:
        company_id = self._company_id()
        return [dict(r) for r in self.repo.position_list(company_id)]

    def position_create(self, name: str, department_id: Optional[int], active: int = 1) -> int:
        self._require_roles(["HR_ADMIN"])
        company_id = self._company_id()
        pos_id = self.repo.position_create(company_id, name, department_id, active)
        self.audit("position", pos_id, "create", name)
        return pos_id

    def position_update(self, pos_id: int, name: str, department_id: Optional[int], active: int = 1) -> None:
        self._require_roles(["HR_ADMIN"])
        company_id = self._company_id()
        self.repo.position_update(company_id, pos_id, name, department_id, active)
        self.audit("position", pos_id, "update", name)

    def position_delete(self, pos_id: int) -> None:
        self._require_roles(["HR_ADMIN"])
        company_id = self._company_id()
        self.repo.position_delete(company_id, pos_id)
        self.audit("position", pos_id, "delete")

    # -----------------
    # Özlük Yönetimi
    # -----------------
    def employee_list(self, q: str = "", status: Optional[str] = None) -> List[dict]:
        company_id = self._company_id()
        return [dict(r) for r in self.repo.employee_list(company_id, q=q, status=status)]

    def employee_create(self, data: Dict[str, object]) -> int:
        self._require_roles(["HR_ADMIN", "HR_USER"])
        company_id = self._company_id()
        if not data.get("employee_no"):
            raise ValueError("Personel numarası zorunlu.")
        if not data.get("first_name") or not data.get("last_name"):
            raise ValueError("Ad/Soyad zorunlu.")
        emp_id = self.repo.employee_create(company_id, data)
        self.audit("employee", emp_id, "create", f"{data.get('employee_no', '')}")
        return emp_id

    def employee_update(self, emp_id: int, data: Dict[str, object]) -> None:
        self._require_roles(["HR_ADMIN", "HR_USER"])
        company_id = self._company_id()
        current = self.repo.employee_get(company_id, emp_id)
        if not current:
            raise ValueError("Personel bulunamadı.")
        merged = dict(current)
        merged.update({k: v for k, v in data.items() if v is not None})
        self.repo.employee_update(company_id, emp_id, merged)
        self.audit("employee", emp_id, "update")

    def employee_set_status(self, emp_id: int, status: str) -> None:
        self._require_roles(["HR_ADMIN", "HR_USER"])
        company_id = self._company_id()
        self.repo.employee_set_status(company_id, emp_id, status)
        self.audit("employee", emp_id, "status", status)

    def salary_history_add(self, emp_id: int, amount: float, currency: str, effective_date: str) -> int:
        self._require_roles(["HR_ADMIN", "HR_USER"])
        company_id = self._company_id()
        sid = self.repo.salary_history_add(company_id, emp_id, amount, currency, effective_date)
        self.audit("salary_history", sid, "create", f"{amount} {currency}")
        return sid

    def documents_list(self, emp_id: int) -> List[dict]:
        company_id = self._company_id()
        return [dict(r) for r in self.repo.documents_list(company_id, emp_id)]

    def document_add(self, emp_id: int, doc_type: str, file_path: str) -> int:
        self._require_roles(["HR_ADMIN", "HR_USER"])
        if not os.path.isfile(file_path):
            raise ValueError("Dosya bulunamadı")
        company_id = self._company_id()
        ext = os.path.splitext(file_path)[1].lower()
        stored_name = f"{emp_id}_{uuid.uuid4().hex}{ext}"
        dest_path = os.path.join(self.attachments_dir, stored_name)
        os.makedirs(self.attachments_dir, exist_ok=True)
        shutil.copy2(file_path, dest_path)
        size_bytes = os.path.getsize(dest_path)
        doc_id = self.repo.document_add(
            company_id,
            emp_id,
            doc_type=doc_type,
            filename=os.path.basename(file_path),
            stored_name=stored_name,
            size_bytes=size_bytes,
        )
        self.audit("document", doc_id, "upload", doc_type)
        return doc_id

    # -----------------
    # İzin Yönetimi
    # -----------------
    def leave_type_list(self) -> List[dict]:
        company_id = self._company_id()
        return [dict(r) for r in self.repo.leave_type_list(company_id)]

    def leave_type_create(self, name: str, annual_days: float, active: int = 1) -> int:
        self._require_roles(["HR_ADMIN"])
        company_id = self._company_id()
        lt_id = self.repo.leave_type_create(company_id, name, annual_days, active)
        self.audit("leave_type", lt_id, "create", name)
        return lt_id

    def leave_type_update(self, lt_id: int, name: str, annual_days: float, active: int = 1) -> None:
        self._require_roles(["HR_ADMIN"])
        company_id = self._company_id()
        self.repo.leave_type_update(company_id, lt_id, name, annual_days, active)
        self.audit("leave_type", lt_id, "update", name)

    def leave_type_delete(self, lt_id: int) -> None:
        self._require_roles(["HR_ADMIN"])
        company_id = self._company_id()
        self.repo.leave_type_delete(company_id, lt_id)
        self.audit("leave_type", lt_id, "delete")

    def leave_request_list(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[dict]:
        company_id = self._company_id()
        return [dict(r) for r in self.repo.leave_request_list(company_id, start_date, end_date)]

    def leave_request_create(self, emp_id: int, leave_type_id: int, start_date: str, end_date: str, notes: str = "") -> int:
        self._require_roles(["HR_ADMIN", "HR_USER", "MANAGER"])
        company_id = self._company_id()
        if self.repo.leave_request_overlap(company_id, emp_id, start_date, end_date):
            raise ValueError("İzin tarihleri çakışıyor.")
        total_days = self._calc_days(start_date, end_date)
        req_id = self.repo.leave_request_create(
            company_id,
            emp_id,
            leave_type_id,
            start_date,
            end_date,
            total_days,
            notes,
        )
        self.audit("leave_request", req_id, "create", f"{start_date} - {end_date}")
        return req_id

    def leave_request_manager_approve(self, req_id: int) -> None:
        self._require_roles(["MANAGER", "HR_ADMIN"])
        company_id = self._company_id()
        self.repo.leave_request_set_status(company_id, req_id, "manager_approved", manager_username=self._actor())
        self.audit("leave_request", req_id, "manager_approve")

    def leave_request_hr_approve(self, req_id: int) -> None:
        self._require_roles(["HR_ADMIN", "HR_USER"])
        company_id = self._company_id()
        req_row = self.repo.leave_request_get(company_id, req_id)
        if not req_row:
            raise ValueError("İzin talebi bulunamadı")
        req = dict(req_row)
        if str(req.get("status")) != "manager_approved":
            raise ValueError("Yönetici onayı bekleniyor.")
        self.repo.leave_request_set_status(company_id, req_id, "approved", hr_username=self._actor())
        self._update_leave_balance(req)
        self.audit("leave_request", req_id, "hr_approve")

    def leave_request_reject(self, req_id: int, reason: str = "") -> None:
        self._require_roles(["MANAGER", "HR_ADMIN", "HR_USER"])
        company_id = self._company_id()
        self.repo.leave_request_set_status(company_id, req_id, "rejected", notes=reason)
        self.audit("leave_request", req_id, "reject", reason)

    def leave_balance_list(self, year: Optional[int] = None) -> List[dict]:
        company_id = self._company_id()
        return [dict(r) for r in self.repo.leave_balance_list(company_id, year)]

    def _update_leave_balance(self, req: Dict[str, object]) -> None:
        company_id = self._company_id()
        start_date = str(req["start_date"])
        year = int(start_date.split("-")[0])
        leave_type = self.repo.leave_type_get(company_id, int(req["leave_type_id"]))
        total = float(leave_type["annual_days"]) if leave_type else 0.0
        self.repo.leave_balance_upsert(
            company_id,
            int(req["employee_id"]),
            year,
            total_days=total,
            used_days_delta=float(req["total_days"]),
        )

    def _calc_days(self, start_date: str, end_date: str) -> float:
        try:
            s = datetime.strptime(start_date, "%Y-%m-%d").date()
            e = datetime.strptime(end_date, "%Y-%m-%d").date()
            return float((e - s).days + 1)
        except Exception:
            return 0.0

    # -----------------
    # Puantaj / Vardiya
    # -----------------
    def shift_list(self) -> List[dict]:
        company_id = self._company_id()
        return [dict(r) for r in self.repo.shift_list(company_id)]

    def shift_create(self, name: str, start_time: str, end_time: str, break_minutes: int, active: int = 1) -> int:
        self._require_roles(["HR_ADMIN"])
        company_id = self._company_id()
        sid = self.repo.shift_create(company_id, name, start_time, end_time, break_minutes, active)
        self.audit("shift", sid, "create", name)
        return sid

    def shift_update(self, shift_id: int, name: str, start_time: str, end_time: str, break_minutes: int, active: int = 1) -> None:
        self._require_roles(["HR_ADMIN"])
        company_id = self._company_id()
        self.repo.shift_update(company_id, shift_id, name, start_time, end_time, break_minutes, active)
        self.audit("shift", shift_id, "update", name)

    def shift_delete(self, shift_id: int) -> None:
        self._require_roles(["HR_ADMIN"])
        company_id = self._company_id()
        self.repo.shift_delete(company_id, shift_id)
        self.audit("shift", shift_id, "delete")

    def timesheet_upsert(self, emp_id: int, work_date: str, status: str, shift_id: Optional[int], check_in: str = "", check_out: str = "", notes: str = "") -> None:
        self._require_roles(["HR_ADMIN", "HR_USER"])
        company_id = self._company_id()
        self.repo.timesheet_upsert(company_id, emp_id, work_date, status, shift_id, check_in, check_out, notes)
        self.audit("timesheet", emp_id, "upsert", work_date)

    def timesheet_list(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[dict]:
        company_id = self._company_id()
        return [dict(r) for r in self.repo.timesheet_list(company_id, start_date, end_date)]

    def overtime_request_create(self, emp_id: int, work_date: str, hours: float) -> int:
        self._require_roles(["HR_ADMIN", "HR_USER", "MANAGER"])
        company_id = self._company_id()
        oid = self.repo.overtime_request_create(company_id, emp_id, work_date, hours)
        self.audit("overtime", oid, "create", f"{hours}h")
        return oid

    def overtime_request_approve(self, req_id: int) -> None:
        self._require_roles(["HR_ADMIN", "MANAGER"])
        company_id = self._company_id()
        self.repo.overtime_request_set_status(company_id, req_id, "approved", approved_by=self._actor())
        self.audit("overtime", req_id, "approve")

    def overtime_request_reject(self, req_id: int, reason: str = "") -> None:
        self._require_roles(["HR_ADMIN", "MANAGER"])
        company_id = self._company_id()
        self.repo.overtime_request_set_status(company_id, req_id, "rejected", approved_by=self._actor(), notes=reason)
        self.audit("overtime", req_id, "reject", reason)

    def overtime_request_list(self) -> List[dict]:
        company_id = self._company_id()
        return [dict(r) for r in self.repo.overtime_request_list(company_id)]

    # -----------------
    # Bordro
    # -----------------
    def payroll_period_list(self) -> List[dict]:
        company_id = self._company_id()
        return [dict(r) for r in self.repo.payroll_period_list(company_id)]

    def payroll_period_create(self, year: int, month: int) -> int:
        self._require_roles(["HR_ADMIN", "ACCOUNTING"])
        company_id = self._company_id()
        pid = self.repo.payroll_period_create(company_id, year, month)
        self.audit("payroll_period", pid, "create", f"{year}-{month}")
        return pid

    def payroll_period_lock(self, period_id: int, locked: int = 1) -> None:
        self._require_roles(["HR_ADMIN", "ACCOUNTING"])
        company_id = self._company_id()
        self.repo.payroll_period_set_locked(company_id, period_id, locked)
        self.audit("payroll_period", period_id, "lock" if locked else "unlock")

    def payroll_item_add(self, period_id: int, emp_id: int, item_type: str, description: str, amount: float, currency: str) -> int:
        self._require_roles(["HR_ADMIN", "ACCOUNTING"])
        company_id = self._company_id()
        if self.repo.payroll_period_is_locked(company_id, period_id):
            raise ValueError("Bordro dönemi kilitli.")
        item_id = self.repo.payroll_item_add(company_id, period_id, emp_id, item_type, description, amount, currency)
        self.audit("payroll_item", item_id, "create", item_type)
        return item_id

    def payroll_item_void(self, item_id: int) -> None:
        self._require_roles(["HR_ADMIN", "ACCOUNTING"])
        company_id = self._company_id()
        self.repo.payroll_item_set_void(company_id, item_id, 1)
        self.audit("payroll_item", item_id, "void")

    def payroll_items_list(self, period_id: int) -> List[dict]:
        company_id = self._company_id()
        return [dict(r) for r in self.repo.payroll_items_list(company_id, period_id)]

    # -----------------
    # Raporlar
    # -----------------
    def report_personnel(self, department_id: Optional[int] = None, position_id: Optional[int] = None, status: Optional[str] = None) -> List[dict]:
        company_id = self._company_id()
        return [dict(r) for r in self.repo.report_personnel(company_id, department_id, position_id, status)]

    def report_leave_summary(self, year: int) -> List[dict]:
        company_id = self._company_id()
        return [dict(r) for r in self.repo.report_leave_summary(company_id, year)]

    def report_timesheet_summary(self, start_date: str, end_date: str) -> List[dict]:
        company_id = self._company_id()
        return [dict(r) for r in self.repo.report_timesheet_summary(company_id, start_date, end_date)]

    def report_payroll_summary(self, period_id: int) -> List[dict]:
        company_id = self._company_id()
        return [dict(r) for r in self.repo.report_payroll_summary(company_id, period_id)]

    def report_audit(self, limit: int = 200) -> List[dict]:
        company_id = self._company_id()
        return [dict(r) for r in self.repo.audit_list(company_id, limit)]
