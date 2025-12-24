# -*- coding: utf-8 -*-

from __future__ import annotations

import sqlite3
from typing import List, Optional, Sequence

from kasapro.utils import now_iso


class HRRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    # -----------------
    # Yetki + Audit
    # -----------------
    def user_role_get(self, company_id: int, username: str) -> Optional[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM hr_user_roles WHERE company_id=? AND username=?",
            (int(company_id), username),
        ).fetchone()

    def user_roles_list(self, company_id: int) -> List[sqlite3.Row]:
        return list(self.conn.execute(
            "SELECT * FROM hr_user_roles WHERE company_id=? ORDER BY username",
            (int(company_id),),
        ))

    def user_role_upsert(self, company_id: int, username: str, role: str) -> None:
        row = self.user_role_get(company_id, username)
        if row:
            self.conn.execute(
                "UPDATE hr_user_roles SET role=? WHERE id=?",
                (role, int(row["id"])),
            )
        else:
            self.conn.execute(
                "INSERT INTO hr_user_roles(company_id, username, role, created_at) VALUES(?,?,?,?)",
                (int(company_id), username, role, now_iso()),
            )
        self.conn.commit()

    def audit_log(
        self,
        company_id: int,
        entity_type: str,
        entity_id: Optional[int],
        action: str,
        actor_username: str,
        actor_role: str,
        detail: str,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO hr_audit_log(company_id, entity_type, entity_id, action, actor_username, actor_role, detail, created_at)
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                int(company_id),
                entity_type,
                int(entity_id) if entity_id is not None else None,
                action,
                actor_username,
                actor_role,
                detail,
                now_iso(),
            ),
        )
        self.conn.commit()

    def audit_list(self, company_id: int, limit: int = 200) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT * FROM hr_audit_log WHERE company_id=? ORDER BY id DESC LIMIT ?",
                (int(company_id), int(limit)),
            )
        )

    # -----------------
    # Organizasyon
    # -----------------
    def department_list(self, company_id: int) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT * FROM hr_departments WHERE company_id=? ORDER BY name",
                (int(company_id),),
            )
        )

    def department_create(self, company_id: int, name: str, active: int = 1) -> int:
        self.conn.execute(
            "INSERT INTO hr_departments(company_id, name, active, created_at) VALUES(?,?,?,?)",
            (int(company_id), name.strip(), int(active), now_iso()),
        )
        self.conn.commit()
        return int(self.conn.execute("SELECT last_insert_rowid() id").fetchone()[0])

    def department_update(self, company_id: int, dept_id: int, name: str, active: int = 1) -> None:
        self.conn.execute(
            "UPDATE hr_departments SET name=?, active=? WHERE id=? AND company_id=?",
            (name.strip(), int(active), int(dept_id), int(company_id)),
        )
        self.conn.commit()

    def department_delete(self, company_id: int, dept_id: int) -> None:
        self.conn.execute(
            "DELETE FROM hr_departments WHERE id=? AND company_id=?",
            (int(dept_id), int(company_id)),
        )
        self.conn.commit()

    def position_list(self, company_id: int) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                """
                SELECT p.*, d.name AS department_name
                FROM hr_positions p
                LEFT JOIN hr_departments d ON d.id=p.department_id
                WHERE p.company_id=?
                ORDER BY p.name
                """,
                (int(company_id),),
            )
        )

    def position_create(self, company_id: int, name: str, department_id: Optional[int], active: int = 1) -> int:
        self.conn.execute(
            "INSERT INTO hr_positions(company_id, name, department_id, active, created_at) VALUES(?,?,?,?,?)",
            (int(company_id), name.strip(), department_id, int(active), now_iso()),
        )
        self.conn.commit()
        return int(self.conn.execute("SELECT last_insert_rowid() id").fetchone()[0])

    def position_update(self, company_id: int, pos_id: int, name: str, department_id: Optional[int], active: int = 1) -> None:
        self.conn.execute(
            "UPDATE hr_positions SET name=?, department_id=?, active=? WHERE id=? AND company_id=?",
            (name.strip(), department_id, int(active), int(pos_id), int(company_id)),
        )
        self.conn.commit()

    def position_delete(self, company_id: int, pos_id: int) -> None:
        self.conn.execute(
            "DELETE FROM hr_positions WHERE id=? AND company_id=?",
            (int(pos_id), int(company_id)),
        )
        self.conn.commit()

    # -----------------
    # Özlük
    # -----------------
    def employee_list(self, company_id: int, q: str = "", status: Optional[str] = None) -> List[sqlite3.Row]:
        clauses = ["e.company_id=?"]
        params: List[object] = [int(company_id)]
        if q:
            q = q.strip()
            clauses.append("(e.employee_no LIKE ? OR e.first_name LIKE ? OR e.last_name LIKE ?)")
            like = f"%{q}%"
            params.extend([like, like, like])
        if status:
            clauses.append("e.status=?")
            params.append(status)
        where = " AND ".join(clauses)
        return list(
            self.conn.execute(
                f"""
                SELECT e.*, d.name AS department_name, p.name AS position_name
                FROM hr_employees e
                LEFT JOIN hr_departments d ON d.id=e.department_id
                LEFT JOIN hr_positions p ON p.id=e.position_id
                WHERE {where}
                ORDER BY e.last_name, e.first_name
                """,
                tuple(params),
            )
        )

    def employee_get(self, company_id: int, emp_id: int) -> Optional[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM hr_employees WHERE company_id=? AND id=?",
            (int(company_id), int(emp_id)),
        ).fetchone()

    def employee_create(self, company_id: int, data: dict) -> int:
        self.conn.execute(
            """
            INSERT INTO hr_employees(
                company_id, employee_no, first_name, last_name, phone, email,
                department_id, position_id, start_date, end_date, status,
                tckn, iban, address, created_at, updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                int(company_id),
                data.get("employee_no"),
                data.get("first_name"),
                data.get("last_name"),
                data.get("phone", ""),
                data.get("email", ""),
                data.get("department_id"),
                data.get("position_id"),
                data.get("start_date", ""),
                data.get("end_date", ""),
                data.get("status", "aktif"),
                data.get("tckn", ""),
                data.get("iban", ""),
                data.get("address", ""),
                now_iso(),
                now_iso(),
            ),
        )
        self.conn.commit()
        return int(self.conn.execute("SELECT last_insert_rowid() id").fetchone()[0])

    def employee_update(self, company_id: int, emp_id: int, data: dict) -> None:
        self.conn.execute(
            """
            UPDATE hr_employees SET
                employee_no=?, first_name=?, last_name=?, phone=?, email=?,
                department_id=?, position_id=?, start_date=?, end_date=?, status=?,
                tckn=?, iban=?, address=?, updated_at=?
            WHERE id=? AND company_id=?
            """,
            (
                data.get("employee_no"),
                data.get("first_name"),
                data.get("last_name"),
                data.get("phone", ""),
                data.get("email", ""),
                data.get("department_id"),
                data.get("position_id"),
                data.get("start_date", ""),
                data.get("end_date", ""),
                data.get("status", "aktif"),
                data.get("tckn", ""),
                data.get("iban", ""),
                data.get("address", ""),
                now_iso(),
                int(emp_id),
                int(company_id),
            ),
        )
        self.conn.commit()

    def employee_set_status(self, company_id: int, emp_id: int, status: str) -> None:
        self.conn.execute(
            "UPDATE hr_employees SET status=?, updated_at=? WHERE id=? AND company_id=?",
            (status, now_iso(), int(emp_id), int(company_id)),
        )
        self.conn.commit()

    def salary_history_add(self, company_id: int, emp_id: int, amount: float, currency: str, effective_date: str) -> int:
        self.conn.execute(
            """
            INSERT INTO hr_salary_history(company_id, employee_id, amount, currency, effective_date, created_at)
            VALUES(?,?,?,?,?,?)
            """,
            (int(company_id), int(emp_id), float(amount), currency, effective_date, now_iso()),
        )
        self.conn.commit()
        return int(self.conn.execute("SELECT last_insert_rowid() id").fetchone()[0])

    def documents_list(self, company_id: int, emp_id: int) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT * FROM hr_documents WHERE company_id=? AND employee_id=? AND active=1 ORDER BY id DESC",
                (int(company_id), int(emp_id)),
            )
        )

    def document_add(self, company_id: int, emp_id: int, doc_type: str, filename: str, stored_name: str, size_bytes: int) -> int:
        self.conn.execute(
            """
            INSERT INTO hr_documents(company_id, employee_id, doc_type, filename, stored_name, size_bytes, uploaded_at, active)
            VALUES(?,?,?,?,?,?,?,1)
            """,
            (int(company_id), int(emp_id), doc_type, filename, stored_name, int(size_bytes), now_iso()),
        )
        self.conn.commit()
        return int(self.conn.execute("SELECT last_insert_rowid() id").fetchone()[0])

    # -----------------
    # İzin
    # -----------------
    def leave_type_list(self, company_id: int) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT * FROM hr_leave_types WHERE company_id=? ORDER BY name",
                (int(company_id),),
            )
        )

    def leave_type_get(self, company_id: int, lt_id: int) -> Optional[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM hr_leave_types WHERE company_id=? AND id=?",
            (int(company_id), int(lt_id)),
        ).fetchone()

    def leave_type_create(self, company_id: int, name: str, annual_days: float, active: int = 1) -> int:
        self.conn.execute(
            "INSERT INTO hr_leave_types(company_id, name, annual_days, active, created_at) VALUES(?,?,?,?,?)",
            (int(company_id), name.strip(), float(annual_days), int(active), now_iso()),
        )
        self.conn.commit()
        return int(self.conn.execute("SELECT last_insert_rowid() id").fetchone()[0])

    def leave_type_update(self, company_id: int, lt_id: int, name: str, annual_days: float, active: int = 1) -> None:
        self.conn.execute(
            "UPDATE hr_leave_types SET name=?, annual_days=?, active=? WHERE id=? AND company_id=?",
            (name.strip(), float(annual_days), int(active), int(lt_id), int(company_id)),
        )
        self.conn.commit()

    def leave_type_delete(self, company_id: int, lt_id: int) -> None:
        self.conn.execute(
            "DELETE FROM hr_leave_types WHERE id=? AND company_id=?",
            (int(lt_id), int(company_id)),
        )
        self.conn.commit()

    def leave_request_list(self, company_id: int, start_date: Optional[str], end_date: Optional[str]) -> List[sqlite3.Row]:
        clauses = ["lr.company_id=?"]
        params: List[object] = [int(company_id)]
        if start_date:
            clauses.append("lr.start_date>=?")
            params.append(start_date)
        if end_date:
            clauses.append("lr.end_date<=?")
            params.append(end_date)
        where = " AND ".join(clauses)
        return list(
            self.conn.execute(
                f"""
                SELECT lr.*, e.first_name, e.last_name, lt.name AS leave_type
                FROM hr_leave_requests lr
                LEFT JOIN hr_employees e ON e.id=lr.employee_id
                LEFT JOIN hr_leave_types lt ON lt.id=lr.leave_type_id
                WHERE {where}
                ORDER BY lr.created_at DESC
                """,
                tuple(params),
            )
        )

    def leave_request_get(self, company_id: int, req_id: int) -> Optional[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM hr_leave_requests WHERE company_id=? AND id=?",
            (int(company_id), int(req_id)),
        ).fetchone()

    def leave_request_overlap(self, company_id: int, emp_id: int, start_date: str, end_date: str) -> bool:
        row = self.conn.execute(
            """
            SELECT 1 FROM hr_leave_requests
            WHERE company_id=? AND employee_id=? AND status!='rejected'
              AND NOT (end_date < ? OR start_date > ?)
            LIMIT 1
            """,
            (int(company_id), int(emp_id), start_date, end_date),
        ).fetchone()
        return bool(row)

    def leave_request_create(
        self,
        company_id: int,
        emp_id: int,
        leave_type_id: int,
        start_date: str,
        end_date: str,
        total_days: float,
        notes: str,
    ) -> int:
        self.conn.execute(
            """
            INSERT INTO hr_leave_requests(
                company_id, employee_id, leave_type_id, start_date, end_date,
                total_days, status, notes, created_at, updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?)
            """,
            (
                int(company_id),
                int(emp_id),
                int(leave_type_id),
                start_date,
                end_date,
                float(total_days),
                "pending_manager",
                notes,
                now_iso(),
                now_iso(),
            ),
        )
        self.conn.commit()
        return int(self.conn.execute("SELECT last_insert_rowid() id").fetchone()[0])

    def leave_request_set_status(
        self,
        company_id: int,
        req_id: int,
        status: str,
        manager_username: Optional[str] = None,
        hr_username: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> None:
        self.conn.execute(
            """
            UPDATE hr_leave_requests
            SET status=?, manager_username=COALESCE(?, manager_username),
                hr_username=COALESCE(?, hr_username),
                notes=COALESCE(?, notes),
                updated_at=?
            WHERE id=? AND company_id=?
            """,
            (
                status,
                manager_username,
                hr_username,
                notes,
                now_iso(),
                int(req_id),
                int(company_id),
            ),
        )
        self.conn.commit()

    def leave_balance_list(self, company_id: int, year: Optional[int] = None) -> List[sqlite3.Row]:
        clauses = ["lb.company_id=?"]
        params: List[object] = [int(company_id)]
        if year is not None:
            clauses.append("lb.year=?")
            params.append(int(year))
        where = " AND ".join(clauses)
        return list(
            self.conn.execute(
                f"""
                SELECT lb.*, e.first_name, e.last_name
                FROM hr_leave_balances lb
                LEFT JOIN hr_employees e ON e.id=lb.employee_id
                WHERE {where}
                ORDER BY lb.year DESC
                """,
                tuple(params),
            )
        )

    def leave_balance_upsert(self, company_id: int, emp_id: int, year: int, total_days: float, used_days_delta: float) -> None:
        row = self.conn.execute(
            "SELECT id, total_days, used_days FROM hr_leave_balances WHERE company_id=? AND employee_id=? AND year=?",
            (int(company_id), int(emp_id), int(year)),
        ).fetchone()
        if row:
            new_total = float(total_days) if float(total_days) > 0 else float(row["total_days"])
            used = float(row["used_days"]) + float(used_days_delta)
            self.conn.execute(
                "UPDATE hr_leave_balances SET total_days=?, used_days=?, updated_at=? WHERE id=?",
                (new_total, used, now_iso(), int(row["id"])),
            )
        else:
            self.conn.execute(
                "INSERT INTO hr_leave_balances(company_id, employee_id, year, total_days, used_days, updated_at) VALUES(?,?,?,?,?,?)",
                (int(company_id), int(emp_id), int(year), float(total_days), float(used_days_delta), now_iso()),
            )
        self.conn.commit()

    # -----------------
    # Vardiya / Puantaj
    # -----------------
    def shift_list(self, company_id: int) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT * FROM hr_shifts WHERE company_id=? ORDER BY name",
                (int(company_id),),
            )
        )

    def shift_create(self, company_id: int, name: str, start_time: str, end_time: str, break_minutes: int, active: int = 1) -> int:
        self.conn.execute(
            "INSERT INTO hr_shifts(company_id, name, start_time, end_time, break_minutes, active, created_at) VALUES(?,?,?,?,?,?,?)",
            (int(company_id), name.strip(), start_time, end_time, int(break_minutes), int(active), now_iso()),
        )
        self.conn.commit()
        return int(self.conn.execute("SELECT last_insert_rowid() id").fetchone()[0])

    def shift_update(self, company_id: int, shift_id: int, name: str, start_time: str, end_time: str, break_minutes: int, active: int = 1) -> None:
        self.conn.execute(
            "UPDATE hr_shifts SET name=?, start_time=?, end_time=?, break_minutes=?, active=? WHERE id=? AND company_id=?",
            (name.strip(), start_time, end_time, int(break_minutes), int(active), int(shift_id), int(company_id)),
        )
        self.conn.commit()

    def shift_delete(self, company_id: int, shift_id: int) -> None:
        self.conn.execute(
            "DELETE FROM hr_shifts WHERE id=? AND company_id=?",
            (int(shift_id), int(company_id)),
        )
        self.conn.commit()

    def timesheet_upsert(
        self,
        company_id: int,
        emp_id: int,
        work_date: str,
        status: str,
        shift_id: Optional[int],
        check_in: str,
        check_out: str,
        notes: str,
    ) -> None:
        row = self.conn.execute(
            "SELECT id FROM hr_timesheets WHERE company_id=? AND employee_id=? AND work_date=?",
            (int(company_id), int(emp_id), work_date),
        ).fetchone()
        if row:
            self.conn.execute(
                """
                UPDATE hr_timesheets
                SET status=?, shift_id=?, check_in=?, check_out=?, notes=?, updated_at=?
                WHERE id=?
                """,
                (status, shift_id, check_in, check_out, notes, now_iso(), int(row["id"])),
            )
        else:
            self.conn.execute(
                """
                INSERT INTO hr_timesheets(
                    company_id, employee_id, work_date, status, shift_id, check_in, check_out, notes, created_at, updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    int(company_id),
                    int(emp_id),
                    work_date,
                    status,
                    shift_id,
                    check_in,
                    check_out,
                    notes,
                    now_iso(),
                    now_iso(),
                ),
            )
        self.conn.commit()

    def timesheet_list(self, company_id: int, start_date: Optional[str], end_date: Optional[str]) -> List[sqlite3.Row]:
        clauses = ["t.company_id=?"]
        params: List[object] = [int(company_id)]
        if start_date:
            clauses.append("t.work_date>=?")
            params.append(start_date)
        if end_date:
            clauses.append("t.work_date<=?")
            params.append(end_date)
        where = " AND ".join(clauses)
        return list(
            self.conn.execute(
                f"""
                SELECT t.*, e.first_name, e.last_name, s.name AS shift_name
                FROM hr_timesheets t
                LEFT JOIN hr_employees e ON e.id=t.employee_id
                LEFT JOIN hr_shifts s ON s.id=t.shift_id
                WHERE {where}
                ORDER BY t.work_date DESC
                """,
                tuple(params),
            )
        )

    def overtime_request_create(self, company_id: int, emp_id: int, work_date: str, hours: float) -> int:
        self.conn.execute(
            """
            INSERT INTO hr_overtime_requests(company_id, employee_id, work_date, hours, status, created_at, updated_at)
            VALUES(?,?,?,?,?,?,?)
            """,
            (int(company_id), int(emp_id), work_date, float(hours), "pending", now_iso(), now_iso()),
        )
        self.conn.commit()
        return int(self.conn.execute("SELECT last_insert_rowid() id").fetchone()[0])

    def overtime_request_set_status(self, company_id: int, req_id: int, status: str, approved_by: str, notes: Optional[str] = None) -> None:
        self.conn.execute(
            """
            UPDATE hr_overtime_requests
            SET status=?, approved_by=?, notes=COALESCE(?, notes), updated_at=?
            WHERE id=? AND company_id=?
            """,
            (status, approved_by, notes, now_iso(), int(req_id), int(company_id)),
        )
        self.conn.commit()

    def overtime_request_list(self, company_id: int) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                """
                SELECT o.*, e.first_name, e.last_name
                FROM hr_overtime_requests o
                LEFT JOIN hr_employees e ON e.id=o.employee_id
                WHERE o.company_id=?
                ORDER BY o.created_at DESC
                """,
                (int(company_id),),
            )
        )

    # -----------------
    # Bordro
    # -----------------
    def payroll_period_list(self, company_id: int) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT * FROM hr_payroll_periods WHERE company_id=? ORDER BY year DESC, month DESC",
                (int(company_id),),
            )
        )

    def payroll_period_create(self, company_id: int, year: int, month: int) -> int:
        self.conn.execute(
            "INSERT INTO hr_payroll_periods(company_id, year, month, locked, created_at, updated_at) VALUES(?,?,?,?,?,?)",
            (int(company_id), int(year), int(month), 0, now_iso(), now_iso()),
        )
        self.conn.commit()
        return int(self.conn.execute("SELECT last_insert_rowid() id").fetchone()[0])

    def payroll_period_is_locked(self, company_id: int, period_id: int) -> bool:
        row = self.conn.execute(
            "SELECT locked FROM hr_payroll_periods WHERE company_id=? AND id=?",
            (int(company_id), int(period_id)),
        ).fetchone()
        return bool(row and int(row["locked"]) == 1)

    def payroll_period_set_locked(self, company_id: int, period_id: int, locked: int) -> None:
        self.conn.execute(
            "UPDATE hr_payroll_periods SET locked=?, updated_at=? WHERE id=? AND company_id=?",
            (int(locked), now_iso(), int(period_id), int(company_id)),
        )
        self.conn.commit()

    def payroll_item_add(self, company_id: int, period_id: int, emp_id: int, item_type: str, description: str, amount: float, currency: str) -> int:
        self.conn.execute(
            """
            INSERT INTO hr_payroll_items(company_id, period_id, employee_id, item_type, description, amount, currency, is_void, created_at)
            VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (int(company_id), int(period_id), int(emp_id), item_type, description, float(amount), currency, 0, now_iso()),
        )
        self.conn.commit()
        return int(self.conn.execute("SELECT last_insert_rowid() id").fetchone()[0])

    def payroll_item_set_void(self, company_id: int, item_id: int, is_void: int) -> None:
        self.conn.execute(
            "UPDATE hr_payroll_items SET is_void=? WHERE id=? AND company_id=?",
            (int(is_void), int(item_id), int(company_id)),
        )
        self.conn.commit()

    def payroll_items_list(self, company_id: int, period_id: int) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                """
                SELECT pi.*, e.first_name, e.last_name
                FROM hr_payroll_items pi
                LEFT JOIN hr_employees e ON e.id=pi.employee_id
                WHERE pi.company_id=? AND pi.period_id=?
                ORDER BY pi.created_at DESC
                """,
                (int(company_id), int(period_id)),
            )
        )

    # -----------------
    # Raporlar
    # -----------------
    def report_personnel(
        self,
        company_id: int,
        department_id: Optional[int] = None,
        position_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[sqlite3.Row]:
        clauses = ["e.company_id=?"]
        params: List[object] = [int(company_id)]
        if department_id:
            clauses.append("e.department_id=?")
            params.append(int(department_id))
        if position_id:
            clauses.append("e.position_id=?")
            params.append(int(position_id))
        if status:
            clauses.append("e.status=?")
            params.append(status)
        where = " AND ".join(clauses)
        return list(
            self.conn.execute(
                f"""
                SELECT e.*, d.name AS department_name, p.name AS position_name
                FROM hr_employees e
                LEFT JOIN hr_departments d ON d.id=e.department_id
                LEFT JOIN hr_positions p ON p.id=e.position_id
                WHERE {where}
                ORDER BY e.last_name, e.first_name
                """,
                tuple(params),
            )
        )

    def report_leave_summary(self, company_id: int, year: int) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                """
                SELECT lb.*, e.first_name, e.last_name,
                       (lb.total_days - lb.used_days) AS remaining_days
                FROM hr_leave_balances lb
                LEFT JOIN hr_employees e ON e.id=lb.employee_id
                WHERE lb.company_id=? AND lb.year=?
                ORDER BY e.last_name, e.first_name
                """,
                (int(company_id), int(year)),
            )
        )

    def report_timesheet_summary(self, company_id: int, start_date: str, end_date: str) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                """
                SELECT e.id AS employee_id, e.first_name, e.last_name,
                       SUM(CASE WHEN t.status='calisti' THEN 1 ELSE 0 END) AS calisti,
                       SUM(CASE WHEN t.status='izin' THEN 1 ELSE 0 END) AS izin,
                       SUM(CASE WHEN t.status='rapor' THEN 1 ELSE 0 END) AS rapor,
                       SUM(CASE WHEN t.status='gelmedi' THEN 1 ELSE 0 END) AS gelmedi
                FROM hr_timesheets t
                LEFT JOIN hr_employees e ON e.id=t.employee_id
                WHERE t.company_id=? AND t.work_date BETWEEN ? AND ?
                GROUP BY e.id
                ORDER BY e.last_name, e.first_name
                """,
                (int(company_id), start_date, end_date),
            )
        )

    def report_payroll_summary(self, company_id: int, period_id: int) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                """
                SELECT e.id AS employee_id, e.first_name, e.last_name,
                       SUM(pi.amount) AS total_amount
                FROM hr_payroll_items pi
                LEFT JOIN hr_employees e ON e.id=pi.employee_id
                WHERE pi.company_id=? AND pi.period_id=? AND pi.is_void=0
                GROUP BY e.id
                ORDER BY e.last_name, e.first_name
                """,
                (int(company_id), int(period_id)),
            )
        )
