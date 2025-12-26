# -*- coding: utf-8 -*-

from __future__ import annotations

import queue
import threading
from typing import Callable, Dict, Optional

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from kasapro.config import APP_TITLE
from kasapro.utils import today_iso

PLUGIN_META = {
    "key": "hr",
    "nav_text": "🧑‍💼 İK",
    "page_title": "İK Modülü",
    "order": 30,
}


class HRFrame(ttk.Frame):
    def __init__(self, master: ttk.Frame, app):
        super().__init__(master)
        self.app = app
        self.hr = app.services.hr
        self._init_ui()

    def _init_ui(self) -> None:
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=tk.BOTH, expand=True)

        self.tabs: Dict[str, ttk.Frame] = {}
        self.tabs["personel"] = self._build_personnel_tab()
        self.tabs["izinler"] = self._build_leave_tab()
        self.tabs["puantaj"] = self._build_timesheet_tab()
        self.tabs["bordro"] = self._build_payroll_tab()
        self.tabs["raporlar"] = self._build_reports_tab()
        self.tabs["tanimlar"] = self._build_definitions_tab()

        for title, key in (
            ("Personel", "personel"),
            ("İzinler", "izinler"),
            ("Puantaj", "puantaj"),
            ("Bordro", "bordro"),
            ("Raporlar", "raporlar"),
            ("Tanımlar", "tanimlar"),
        ):
            self.nb.add(self.tabs[key], text=title)

        self._apply_role_visibility()

    def _run_bg(self, worker: Callable[[], object], on_done: Callable[[object], None]) -> None:
        q: "queue.Queue[object]" = queue.Queue()

        def _task():
            try:
                q.put(worker())
            except Exception as exc:  # noqa: BLE001
                q.put(exc)

        def _poll():
            try:
                item = q.get_nowait()
            except queue.Empty:
                self.after(80, _poll)
                return
            if isinstance(item, Exception):
                messagebox.showerror(APP_TITLE, str(item))
                return
            on_done(item)

        threading.Thread(target=_task, daemon=True).start()
        self.after(80, _poll)

    def _apply_role_visibility(self) -> None:
        role = self.hr.get_user_role()
        allowed = {
            "HR_ADMIN": {"personel", "izinler", "puantaj", "bordro", "raporlar", "tanimlar"},
            "HR_USER": {"personel", "izinler", "puantaj", "raporlar", "tanimlar"},
            "MANAGER": {"personel", "izinler", "puantaj", "raporlar"},
            "ACCOUNTING": {"bordro", "raporlar"},
            "VIEWER": {"raporlar"},
        }
        allowed_tabs = allowed.get(role, {"raporlar"})
        for key, frame in self.tabs.items():
            try:
                self.nb.tab(frame, state="normal" if key in allowed_tabs else "disabled")
            except Exception:
                pass

    # -----------------
    # Personel
    # -----------------
    def _build_personnel_tab(self) -> ttk.Frame:
        frame = ttk.Frame(self.nb)

        top = ttk.Frame(frame)
        top.pack(fill=tk.X, padx=8, pady=8)

        ttk.Label(top, text="Personel Kartı").grid(row=0, column=0, sticky="w")

        form = ttk.Frame(frame)
        form.pack(fill=tk.X, padx=8)

        self.emp_fields: Dict[str, tk.Widget] = {}
        labels = [
            ("employee_no", "Personel No"),
            ("first_name", "Ad"),
            ("last_name", "Soyad"),
            ("phone", "Telefon"),
            ("email", "E-posta"),
            ("start_date", "Giriş"),
            ("end_date", "Çıkış"),
            ("status", "Durum"),
            ("tckn", "TCKN"),
            ("iban", "IBAN"),
        ]
        for idx, (key, label) in enumerate(labels):
            ttk.Label(form, text=label).grid(row=idx // 2, column=(idx % 2) * 2, sticky="w", padx=4, pady=2)
            entry = ttk.Entry(form, width=32)
            entry.grid(row=idx // 2, column=(idx % 2) * 2 + 1, sticky="w", padx=4, pady=2)
            self.emp_fields[key] = entry

        try:
            self.emp_fields["status"].insert(0, "aktif")
        except Exception:
            pass

        ttk.Label(form, text="Departman").grid(row=5, column=0, sticky="w", padx=4, pady=2)
        self.cmb_department = ttk.Combobox(form, state="readonly", width=30)
        self.cmb_department.grid(row=5, column=1, sticky="w", padx=4, pady=2)

        ttk.Label(form, text="Pozisyon").grid(row=5, column=2, sticky="w", padx=4, pady=2)
        self.cmb_position = ttk.Combobox(form, state="readonly", width=30)
        self.cmb_position.grid(row=5, column=3, sticky="w", padx=4, pady=2)

        ttk.Label(form, text="Adres").grid(row=6, column=0, sticky="w", padx=4, pady=2)
        self.txt_address = tk.Text(form, width=62, height=3)
        self.txt_address.grid(row=6, column=1, columnspan=3, sticky="w", padx=4, pady=2)

        btns = ttk.Frame(frame)
        btns.pack(fill=tk.X, padx=8, pady=6)

        ttk.Button(btns, text="Kaydet", command=self._employee_save).pack(side=tk.LEFT)
        ttk.Button(btns, text="Pasife Al", command=self._employee_passive).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Yenile", command=self._employees_refresh).pack(side=tk.LEFT, padx=6)

        extra = ttk.Frame(frame)
        extra.pack(fill=tk.X, padx=8, pady=(0, 6))

        salary = ttk.LabelFrame(extra, text="Ücret Geçmişi")
        salary.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        ttk.Label(salary, text="Tutar").grid(row=0, column=0, sticky="w", padx=4, pady=2)
        self.ent_salary_amount = ttk.Entry(salary, width=12)
        self.ent_salary_amount.grid(row=0, column=1, sticky="w", padx=4, pady=2)
        ttk.Label(salary, text="Para").grid(row=0, column=2, sticky="w", padx=4, pady=2)
        self.ent_salary_currency = ttk.Entry(salary, width=8)
        self.ent_salary_currency.grid(row=0, column=3, sticky="w", padx=4, pady=2)
        self.ent_salary_currency.insert(0, "TL")
        ttk.Label(salary, text="Tarih").grid(row=0, column=4, sticky="w", padx=4, pady=2)
        self.ent_salary_date = ttk.Entry(salary, width=12)
        self.ent_salary_date.grid(row=0, column=5, sticky="w", padx=4, pady=2)
        self.ent_salary_date.insert(0, today_iso())
        ttk.Button(salary, text="Ekle", command=self._salary_add).grid(row=0, column=6, padx=4, pady=2)

        docs = ttk.LabelFrame(extra, text="Dokümanlar")
        docs.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(docs, text="Tür").grid(row=0, column=0, sticky="w", padx=4, pady=2)
        self.ent_doc_type = ttk.Entry(docs, width=16)
        self.ent_doc_type.grid(row=0, column=1, sticky="w", padx=4, pady=2)
        ttk.Button(docs, text="Yükle", command=self._document_upload).grid(row=0, column=2, padx=4, pady=2)
        self.doc_list = tk.Listbox(docs, height=3)
        self.doc_list.grid(row=1, column=0, columnspan=3, sticky="we", padx=4, pady=2)

        self.employee_tree = ttk.Treeview(
            frame,
            columns=("id", "employee_no", "name", "department", "position", "status", "tckn", "iban"),
            show="headings",
            height=12,
        )
        for col, title in (
            ("id", "ID"),
            ("employee_no", "No"),
            ("name", "Ad Soyad"),
            ("department", "Departman"),
            ("position", "Pozisyon"),
            ("status", "Durum"),
            ("tckn", "TCKN"),
            ("iban", "IBAN"),
        ):
            self.employee_tree.heading(col, text=title)
        self.employee_tree.column("id", width=40, anchor="center")
        self.employee_tree.column("employee_no", width=90)
        self.employee_tree.column("name", width=160)
        self.employee_tree.column("department", width=120)
        self.employee_tree.column("position", width=120)
        self.employee_tree.column("status", width=80, anchor="center")
        self.employee_tree.column("tckn", width=140)
        self.employee_tree.column("iban", width=160)
        self.employee_tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 6))
        self.employee_tree.bind("<<TreeviewSelect>>", self._employee_select)

        self._reload_departments_positions()
        self._employees_refresh()
        return frame

    def _reload_departments_positions(self) -> None:
        depts = self.hr.department_list()
        positions = self.hr.position_list()
        self.dept_map = {f"{d['name']}#{d['id']}": int(d["id"]) for d in depts}
        self.pos_map = {f"{p['name']}#{p['id']}": int(p["id"]) for p in positions}
        self.cmb_department["values"] = list(self.dept_map.keys())
        self.cmb_position["values"] = list(self.pos_map.keys())

    def _employee_payload(self) -> Dict[str, object]:
        data = {}
        for key, widget in self.emp_fields.items():
            data[key] = widget.get().strip()
        data["department_id"] = self.dept_map.get(self.cmb_department.get())
        data["position_id"] = self.pos_map.get(self.cmb_position.get())
        data["address"] = self.txt_address.get("1.0", tk.END).strip()
        return data

    def _employee_save(self) -> None:
        data = self._employee_payload()
        if not data.get("employee_no"):
            messagebox.showerror(APP_TITLE, "Personel No zorunlu.")
            return
        if not data.get("first_name") or not data.get("last_name"):
            messagebox.showerror(APP_TITLE, "Ad/Soyad zorunlu.")
            return
        try:
            selected = self._selected_employee_id()
            if selected:
                self.hr.employee_update(selected, data)
            else:
                self.hr.employee_create(data)
            self._employees_refresh()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, str(exc))

    def _employee_passive(self) -> None:
        emp_id = self._selected_employee_id()
        if not emp_id:
            return
        try:
            self.hr.employee_set_status(emp_id, "pasif")
            self._employees_refresh()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, str(exc))

    def _salary_add(self) -> None:
        emp_id = self._selected_employee_id()
        if not emp_id:
            messagebox.showerror(APP_TITLE, "Personel seçmelisiniz.")
            return
        try:
            amount = float(self.ent_salary_amount.get().strip() or 0)
            currency = self.ent_salary_currency.get().strip() or "TL"
            date = self.ent_salary_date.get().strip() or today_iso()
            self.hr.salary_history_add(emp_id, amount, currency, date)
            messagebox.showinfo(APP_TITLE, "Ücret geçmişi eklendi.")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, str(exc))

    def _document_upload(self) -> None:
        emp_id = self._selected_employee_id()
        if not emp_id:
            messagebox.showerror(APP_TITLE, "Personel seçmelisiniz.")
            return
        doc_type = self.ent_doc_type.get().strip() or "Doküman"
        path = filedialog.askopenfilename(title="Doküman Seç")
        if not path:
            return
        try:
            self.hr.document_add(emp_id, doc_type, path)
            self._documents_refresh(emp_id)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, str(exc))

    def _documents_refresh(self, emp_id: int) -> None:
        self.doc_list.delete(0, tk.END)
        try:
            for doc in self.hr.documents_list(emp_id):
                self.doc_list.insert(tk.END, f"{doc.get('doc_type')} - {doc.get('filename')}")
        except Exception:
            return

    def _selected_employee_id(self) -> Optional[int]:
        sel = self.employee_tree.selection()
        if not sel:
            return None
        return int(self.employee_tree.item(sel[0], "values")[0])

    def _employee_select(self, _event) -> None:
        emp_id = self._selected_employee_id()
        if not emp_id:
            return
        rows = self.hr.employee_list()
        selected = next((r for r in rows if int(r["id"]) == emp_id), None)
        if not selected:
            return
        for key, widget in self.emp_fields.items():
            try:
                widget.delete(0, tk.END)
                widget.insert(0, selected.get(key, ""))
            except Exception:
                pass
        self.cmb_department.set(self._find_key_by_id(self.dept_map, selected.get("department_id")))
        self.cmb_position.set(self._find_key_by_id(self.pos_map, selected.get("position_id")))
        self.txt_address.delete("1.0", tk.END)
        self.txt_address.insert("1.0", selected.get("address", ""))
        self._documents_refresh(emp_id)

    def _find_key_by_id(self, mapping: Dict[str, int], value: Optional[int]) -> str:
        for k, v in mapping.items():
            if value is not None and int(v) == int(value):
                return k
        return ""

    def _employees_refresh(self) -> None:
        def worker():
            return self.hr.employee_list()

        def done(rows):
            for item in self.employee_tree.get_children():
                self.employee_tree.delete(item)
            for r in rows:
                role = self.hr.get_user_role()
                tckn = self.hr.mask_sensitive(str(r.get("tckn", "")), role)
                iban = self.hr.mask_sensitive(str(r.get("iban", "")), role)
                name = f"{r.get('first_name', '')} {r.get('last_name', '')}".strip()
                self.employee_tree.insert(
                    "",
                    tk.END,
                    values=(
                        r.get("id"),
                        r.get("employee_no"),
                        name,
                        r.get("department_name", ""),
                        r.get("position_name", ""),
                        r.get("status"),
                        tckn,
                        iban,
                    ),
                )

        self._run_bg(worker, done)

    # -----------------
    # İzin
    # -----------------
    def _build_leave_tab(self) -> ttk.Frame:
        frame = ttk.Frame(self.nb)

        form = ttk.Frame(frame)
        form.pack(fill=tk.X, padx=8, pady=8)

        ttk.Label(form, text="Personel").grid(row=0, column=0, sticky="w")
        self.cmb_leave_employee = ttk.Combobox(form, state="readonly", width=30)
        self.cmb_leave_employee.grid(row=0, column=1, sticky="w", padx=4)

        ttk.Label(form, text="İzin Türü").grid(row=0, column=2, sticky="w")
        self.cmb_leave_type = ttk.Combobox(form, state="readonly", width=24)
        self.cmb_leave_type.grid(row=0, column=3, sticky="w", padx=4)

        ttk.Label(form, text="Başlangıç").grid(row=1, column=0, sticky="w")
        self.ent_leave_start = ttk.Entry(form, width=16)
        self.ent_leave_start.grid(row=1, column=1, sticky="w", padx=4)
        self.ent_leave_start.insert(0, today_iso())

        ttk.Label(form, text="Bitiş").grid(row=1, column=2, sticky="w")
        self.ent_leave_end = ttk.Entry(form, width=16)
        self.ent_leave_end.grid(row=1, column=3, sticky="w", padx=4)
        self.ent_leave_end.insert(0, today_iso())

        ttk.Label(form, text="Not").grid(row=2, column=0, sticky="w")
        self.ent_leave_note = ttk.Entry(form, width=60)
        self.ent_leave_note.grid(row=2, column=1, columnspan=3, sticky="w", padx=4, pady=2)

        btns = ttk.Frame(frame)
        btns.pack(fill=tk.X, padx=8, pady=6)
        ttk.Button(btns, text="Talep Oluştur", command=self._leave_request_create).pack(side=tk.LEFT)
        ttk.Button(btns, text="Yönetici Onayı", command=self._leave_manager_approve).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="İK Onayı", command=self._leave_hr_approve).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Reddet", command=self._leave_reject).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Yenile", command=self._leave_refresh).pack(side=tk.LEFT, padx=6)

        filter_row = ttk.Frame(frame)
        filter_row.pack(fill=tk.X, padx=8, pady=(0, 6))
        ttk.Label(filter_row, text="Filtre Başlangıç").pack(side=tk.LEFT)
        self.ent_leave_filter_start = ttk.Entry(filter_row, width=16)
        self.ent_leave_filter_start.pack(side=tk.LEFT, padx=4)
        ttk.Label(filter_row, text="Filtre Bitiş").pack(side=tk.LEFT)
        self.ent_leave_filter_end = ttk.Entry(filter_row, width=16)
        self.ent_leave_filter_end.pack(side=tk.LEFT, padx=4)
        ttk.Button(filter_row, text="Filtrele", command=self._leave_refresh).pack(side=tk.LEFT, padx=4)

        self.leave_tree = ttk.Treeview(
            frame,
            columns=("id", "employee", "type", "start", "end", "days", "status"),
            show="headings",
            height=12,
        )
        for col, title in (
            ("id", "ID"),
            ("employee", "Personel"),
            ("type", "Tür"),
            ("start", "Başlangıç"),
            ("end", "Bitiş"),
            ("days", "Gün"),
            ("status", "Durum"),
        ):
            self.leave_tree.heading(col, text=title)
        self.leave_tree.column("id", width=50, anchor="center")
        self.leave_tree.column("employee", width=160)
        self.leave_tree.column("type", width=120)
        self.leave_tree.column("start", width=100)
        self.leave_tree.column("end", width=100)
        self.leave_tree.column("days", width=60, anchor="center")
        self.leave_tree.column("status", width=140)
        self.leave_tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 6))

        self._leave_reload_sources()
        self._leave_refresh()
        return frame

    def _leave_reload_sources(self) -> None:
        employees = self.hr.employee_list()
        self.leave_emp_map = {f"{e['first_name']} {e['last_name']}#{e['id']}": int(e["id"]) for e in employees}
        types = self.hr.leave_type_list()
        self.leave_type_map = {f"{t['name']}#{t['id']}": int(t["id"]) for t in types}
        self.cmb_leave_employee["values"] = list(self.leave_emp_map.keys())
        self.cmb_leave_type["values"] = list(self.leave_type_map.keys())

    def _selected_leave_id(self) -> Optional[int]:
        sel = self.leave_tree.selection()
        if not sel:
            return None
        return int(self.leave_tree.item(sel[0], "values")[0])

    def _leave_request_create(self) -> None:
        emp_id = self.leave_emp_map.get(self.cmb_leave_employee.get())
        leave_type_id = self.leave_type_map.get(self.cmb_leave_type.get())
        if not emp_id or not leave_type_id:
            messagebox.showerror(APP_TITLE, "Personel ve izin türü seçmelisiniz.")
            return
        try:
            self.hr.leave_request_create(
                emp_id,
                leave_type_id,
                self.ent_leave_start.get().strip(),
                self.ent_leave_end.get().strip(),
                self.ent_leave_note.get().strip(),
            )
            self._leave_refresh()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, str(exc))

    def _leave_manager_approve(self) -> None:
        req_id = self._selected_leave_id()
        if not req_id:
            return
        try:
            self.hr.leave_request_manager_approve(req_id)
            self._leave_refresh()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, str(exc))

    def _leave_hr_approve(self) -> None:
        req_id = self._selected_leave_id()
        if not req_id:
            return
        try:
            self.hr.leave_request_hr_approve(req_id)
            self._leave_refresh()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, str(exc))

    def _leave_reject(self) -> None:
        req_id = self._selected_leave_id()
        if not req_id:
            return
        reason = self.ent_leave_note.get().strip()
        try:
            self.hr.leave_request_reject(req_id, reason)
            self._leave_refresh()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, str(exc))

    def _leave_refresh(self) -> None:
        start_date = self.ent_leave_filter_start.get().strip() or None
        end_date = self.ent_leave_filter_end.get().strip() or None

        def worker():
            return self.hr.leave_request_list(start_date, end_date)

        def done(rows):
            for item in self.leave_tree.get_children():
                self.leave_tree.delete(item)
            for r in rows:
                name = f"{r.get('first_name', '')} {r.get('last_name', '')}".strip()
                self.leave_tree.insert(
                    "",
                    tk.END,
                    values=(
                        r.get("id"),
                        name,
                        r.get("leave_type", ""),
                        r.get("start_date"),
                        r.get("end_date"),
                        r.get("total_days"),
                        r.get("status"),
                    ),
                )

        self._run_bg(worker, done)

    # -----------------
    # Puantaj
    # -----------------
    def _build_timesheet_tab(self) -> ttk.Frame:
        frame = ttk.Frame(self.nb)
        form = ttk.Frame(frame)
        form.pack(fill=tk.X, padx=8, pady=8)

        ttk.Label(form, text="Personel").grid(row=0, column=0, sticky="w")
        self.cmb_ts_employee = ttk.Combobox(form, state="readonly", width=28)
        self.cmb_ts_employee.grid(row=0, column=1, sticky="w", padx=4)

        ttk.Label(form, text="Tarih").grid(row=0, column=2, sticky="w")
        self.ent_ts_date = ttk.Entry(form, width=16)
        self.ent_ts_date.grid(row=0, column=3, sticky="w", padx=4)
        self.ent_ts_date.insert(0, today_iso())

        ttk.Label(form, text="Durum").grid(row=1, column=0, sticky="w")
        self.cmb_ts_status = ttk.Combobox(form, state="readonly", width=28, values=["calisti", "izin", "rapor", "gelmedi"])
        self.cmb_ts_status.grid(row=1, column=1, sticky="w", padx=4)
        self.cmb_ts_status.set("calisti")

        ttk.Label(form, text="Vardiya").grid(row=1, column=2, sticky="w")
        self.cmb_ts_shift = ttk.Combobox(form, state="readonly", width=16)
        self.cmb_ts_shift.grid(row=1, column=3, sticky="w", padx=4)

        ttk.Label(form, text="Giriş").grid(row=2, column=0, sticky="w")
        self.ent_ts_in = ttk.Entry(form, width=12)
        self.ent_ts_in.grid(row=2, column=1, sticky="w", padx=4)

        ttk.Label(form, text="Çıkış").grid(row=2, column=2, sticky="w")
        self.ent_ts_out = ttk.Entry(form, width=12)
        self.ent_ts_out.grid(row=2, column=3, sticky="w", padx=4)

        ttk.Label(form, text="Not").grid(row=3, column=0, sticky="w")
        self.ent_ts_note = ttk.Entry(form, width=60)
        self.ent_ts_note.grid(row=3, column=1, columnspan=3, sticky="w", padx=4, pady=2)

        btns = ttk.Frame(frame)
        btns.pack(fill=tk.X, padx=8)
        ttk.Button(btns, text="Kaydet", command=self._timesheet_save).pack(side=tk.LEFT)
        ttk.Button(btns, text="Yenile", command=self._timesheet_refresh).pack(side=tk.LEFT, padx=6)

        filter_row = ttk.Frame(frame)
        filter_row.pack(fill=tk.X, padx=8, pady=(0, 6))
        ttk.Label(filter_row, text="Başlangıç").pack(side=tk.LEFT)
        self.ent_ts_filter_start = ttk.Entry(filter_row, width=16)
        self.ent_ts_filter_start.pack(side=tk.LEFT, padx=4)
        ttk.Label(filter_row, text="Bitiş").pack(side=tk.LEFT)
        self.ent_ts_filter_end = ttk.Entry(filter_row, width=16)
        self.ent_ts_filter_end.pack(side=tk.LEFT, padx=4)
        ttk.Button(filter_row, text="Filtrele", command=self._timesheet_refresh).pack(side=tk.LEFT, padx=4)

        self.timesheet_tree = ttk.Treeview(
            frame,
            columns=("id", "employee", "date", "status", "shift", "in", "out"),
            show="headings",
            height=10,
        )
        for col, title in (
            ("id", "ID"),
            ("employee", "Personel"),
            ("date", "Tarih"),
            ("status", "Durum"),
            ("shift", "Vardiya"),
            ("in", "Giriş"),
            ("out", "Çıkış"),
        ):
            self.timesheet_tree.heading(col, text=title)
        self.timesheet_tree.column("id", width=40, anchor="center")
        self.timesheet_tree.column("employee", width=160)
        self.timesheet_tree.column("date", width=100)
        self.timesheet_tree.column("status", width=100)
        self.timesheet_tree.column("shift", width=120)
        self.timesheet_tree.column("in", width=80)
        self.timesheet_tree.column("out", width=80)
        self.timesheet_tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 6))

        overtime_frame = ttk.LabelFrame(frame, text="Mesai Talepleri")
        overtime_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        ot_form = ttk.Frame(overtime_frame)
        ot_form.pack(fill=tk.X, padx=6, pady=6)
        ttk.Label(ot_form, text="Personel").grid(row=0, column=0, sticky="w")
        self.cmb_ot_employee = ttk.Combobox(ot_form, state="readonly", width=28)
        self.cmb_ot_employee.grid(row=0, column=1, sticky="w", padx=4)
        ttk.Label(ot_form, text="Tarih").grid(row=0, column=2, sticky="w")
        self.ent_ot_date = ttk.Entry(ot_form, width=16)
        self.ent_ot_date.grid(row=0, column=3, sticky="w", padx=4)
        self.ent_ot_date.insert(0, today_iso())
        ttk.Label(ot_form, text="Saat").grid(row=0, column=4, sticky="w")
        self.ent_ot_hours = ttk.Entry(ot_form, width=8)
        self.ent_ot_hours.grid(row=0, column=5, sticky="w", padx=4)

        ot_btns = ttk.Frame(overtime_frame)
        ot_btns.pack(fill=tk.X, padx=6)
        ttk.Button(ot_btns, text="Talep", command=self._overtime_create).pack(side=tk.LEFT)
        ttk.Button(ot_btns, text="Onay", command=self._overtime_approve).pack(side=tk.LEFT, padx=6)
        ttk.Button(ot_btns, text="Reddet", command=self._overtime_reject).pack(side=tk.LEFT, padx=6)
        ttk.Button(ot_btns, text="Yenile", command=self._overtime_refresh).pack(side=tk.LEFT, padx=6)

        self.overtime_tree = ttk.Treeview(
            overtime_frame,
            columns=("id", "employee", "date", "hours", "status"),
            show="headings",
            height=6,
        )
        for col, title in (
            ("id", "ID"),
            ("employee", "Personel"),
            ("date", "Tarih"),
            ("hours", "Saat"),
            ("status", "Durum"),
        ):
            self.overtime_tree.heading(col, text=title)
        self.overtime_tree.column("id", width=40, anchor="center")
        self.overtime_tree.column("employee", width=160)
        self.overtime_tree.column("date", width=100)
        self.overtime_tree.column("hours", width=80)
        self.overtime_tree.column("status", width=120)
        self.overtime_tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

        self._timesheet_reload_sources()
        self._timesheet_refresh()
        self._overtime_refresh()
        return frame

    def _timesheet_reload_sources(self) -> None:
        employees = self.hr.employee_list()
        self.ts_emp_map = {f"{e['first_name']} {e['last_name']}#{e['id']}": int(e["id"]) for e in employees}
        shifts = self.hr.shift_list()
        self.shift_map = {f"{s['name']}#{s['id']}": int(s["id"]) for s in shifts}
        self.cmb_ts_employee["values"] = list(self.ts_emp_map.keys())
        self.cmb_ts_shift["values"] = list(self.shift_map.keys())
        self.cmb_ot_employee["values"] = list(self.ts_emp_map.keys())

    def _timesheet_save(self) -> None:
        emp_id = self.ts_emp_map.get(self.cmb_ts_employee.get())
        if not emp_id:
            messagebox.showerror(APP_TITLE, "Personel seçmelisiniz.")
            return
        shift_id = self.shift_map.get(self.cmb_ts_shift.get())
        try:
            self.hr.timesheet_upsert(
                emp_id,
                self.ent_ts_date.get().strip(),
                self.cmb_ts_status.get(),
                shift_id,
                self.ent_ts_in.get().strip(),
                self.ent_ts_out.get().strip(),
                self.ent_ts_note.get().strip(),
            )
            self._timesheet_refresh()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, str(exc))

    def _timesheet_refresh(self) -> None:
        start_date = self.ent_ts_filter_start.get().strip() or None
        end_date = self.ent_ts_filter_end.get().strip() or None

        def worker():
            return self.hr.timesheet_list(start_date, end_date)

        def done(rows):
            for item in self.timesheet_tree.get_children():
                self.timesheet_tree.delete(item)
            for r in rows:
                name = f"{r.get('first_name', '')} {r.get('last_name', '')}".strip()
                self.timesheet_tree.insert(
                    "",
                    tk.END,
                    values=(
                        r.get("id"),
                        name,
                        r.get("work_date"),
                        r.get("status"),
                        r.get("shift_name", ""),
                        r.get("check_in", ""),
                        r.get("check_out", ""),
                    ),
                )

        self._run_bg(worker, done)

    def _overtime_create(self) -> None:
        emp_id = self.ts_emp_map.get(self.cmb_ot_employee.get())
        if not emp_id:
            messagebox.showerror(APP_TITLE, "Personel seçmelisiniz.")
            return
        try:
            hours = float(self.ent_ot_hours.get().strip() or 0)
            self.hr.overtime_request_create(emp_id, self.ent_ot_date.get().strip(), hours)
            self._overtime_refresh()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, str(exc))

    def _selected_overtime_id(self) -> Optional[int]:
        sel = self.overtime_tree.selection()
        if not sel:
            return None
        return int(self.overtime_tree.item(sel[0], "values")[0])

    def _overtime_approve(self) -> None:
        req_id = self._selected_overtime_id()
        if not req_id:
            return
        try:
            self.hr.overtime_request_approve(req_id)
            self._overtime_refresh()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, str(exc))

    def _overtime_reject(self) -> None:
        req_id = self._selected_overtime_id()
        if not req_id:
            return
        try:
            self.hr.overtime_request_reject(req_id)
            self._overtime_refresh()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, str(exc))

    def _overtime_refresh(self) -> None:
        def worker():
            return self.hr.overtime_request_list()

        def done(rows):
            for item in self.overtime_tree.get_children():
                self.overtime_tree.delete(item)
            for r in rows:
                name = f"{r.get('first_name', '')} {r.get('last_name', '')}".strip()
                self.overtime_tree.insert(
                    "",
                    tk.END,
                    values=(r.get("id"), name, r.get("work_date"), r.get("hours"), r.get("status")),
                )

        self._run_bg(worker, done)

    # -----------------
    # Bordro
    # -----------------
    def _build_payroll_tab(self) -> ttk.Frame:
        frame = ttk.Frame(self.nb)

        period_frame = ttk.LabelFrame(frame, text="Bordro Dönemleri")
        period_frame.pack(fill=tk.X, padx=8, pady=8)

        row = ttk.Frame(period_frame)
        row.pack(fill=tk.X, padx=6, pady=6)
        ttk.Label(row, text="Yıl").pack(side=tk.LEFT)
        self.ent_period_year = ttk.Entry(row, width=8)
        self.ent_period_year.pack(side=tk.LEFT, padx=4)
        ttk.Label(row, text="Ay").pack(side=tk.LEFT)
        self.ent_period_month = ttk.Entry(row, width=6)
        self.ent_period_month.pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="Dönem Oluştur", command=self._period_create).pack(side=tk.LEFT, padx=6)
        ttk.Button(row, text="Kilitle", command=self._period_lock).pack(side=tk.LEFT, padx=6)
        ttk.Button(row, text="Yenile", command=self._period_refresh).pack(side=tk.LEFT, padx=6)

        self.period_tree = ttk.Treeview(
            period_frame,
            columns=("id", "year", "month", "locked"),
            show="headings",
            height=5,
        )
        for col, title in (
            ("id", "ID"),
            ("year", "Yıl"),
            ("month", "Ay"),
            ("locked", "Kilit"),
        ):
            self.period_tree.heading(col, text=title)
        self.period_tree.column("id", width=50, anchor="center")
        self.period_tree.column("year", width=80, anchor="center")
        self.period_tree.column("month", width=60, anchor="center")
        self.period_tree.column("locked", width=80, anchor="center")
        self.period_tree.pack(fill=tk.X, padx=6, pady=(0, 6))
        self.period_tree.bind("<<TreeviewSelect>>", lambda _e: self._items_refresh())

        items_frame = ttk.LabelFrame(frame, text="Bordro Kalemleri")
        items_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        form = ttk.Frame(items_frame)
        form.pack(fill=tk.X, padx=6, pady=6)

        ttk.Label(form, text="Personel").grid(row=0, column=0, sticky="w")
        self.cmb_pay_employee = ttk.Combobox(form, state="readonly", width=28)
        self.cmb_pay_employee.grid(row=0, column=1, sticky="w", padx=4)

        ttk.Label(form, text="Kalem").grid(row=0, column=2, sticky="w")
        self.cmb_pay_type = ttk.Combobox(form, state="readonly", width=18, values=["maaş", "mesai", "prim", "avans", "kesinti"])
        self.cmb_pay_type.grid(row=0, column=3, sticky="w", padx=4)
        self.cmb_pay_type.set("maaş")

        ttk.Label(form, text="Açıklama").grid(row=1, column=0, sticky="w")
        self.ent_pay_desc = ttk.Entry(form, width=52)
        self.ent_pay_desc.grid(row=1, column=1, columnspan=3, sticky="w", padx=4)

        ttk.Label(form, text="Tutar").grid(row=2, column=0, sticky="w")
        self.ent_pay_amount = ttk.Entry(form, width=14)
        self.ent_pay_amount.grid(row=2, column=1, sticky="w", padx=4)

        ttk.Label(form, text="Para").grid(row=2, column=2, sticky="w")
        self.ent_pay_currency = ttk.Entry(form, width=10)
        self.ent_pay_currency.grid(row=2, column=3, sticky="w", padx=4)
        self.ent_pay_currency.insert(0, "TL")

        btns = ttk.Frame(items_frame)
        btns.pack(fill=tk.X, padx=6)
        ttk.Button(btns, text="Kalem Ekle", command=self._item_add).pack(side=tk.LEFT)
        ttk.Button(btns, text="İptal", command=self._item_void).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Yenile", command=self._items_refresh).pack(side=tk.LEFT, padx=6)

        self.items_tree = ttk.Treeview(
            items_frame,
            columns=("id", "employee", "type", "amount", "currency", "void"),
            show="headings",
            height=10,
        )
        for col, title in (
            ("id", "ID"),
            ("employee", "Personel"),
            ("type", "Kalem"),
            ("amount", "Tutar"),
            ("currency", "Para"),
            ("void", "İptal"),
        ):
            self.items_tree.heading(col, text=title)
        self.items_tree.column("id", width=50, anchor="center")
        self.items_tree.column("employee", width=160)
        self.items_tree.column("type", width=120)
        self.items_tree.column("amount", width=100, anchor="e")
        self.items_tree.column("currency", width=80)
        self.items_tree.column("void", width=60, anchor="center")
        self.items_tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

        self._payroll_reload_sources()
        self._period_refresh()
        return frame

    def _payroll_reload_sources(self) -> None:
        employees = self.hr.employee_list()
        self.pay_emp_map = {f"{e['first_name']} {e['last_name']}#{e['id']}": int(e["id"]) for e in employees}
        self.cmb_pay_employee["values"] = list(self.pay_emp_map.keys())

    def _selected_period_id(self) -> Optional[int]:
        sel = self.period_tree.selection()
        if not sel:
            return None
        return int(self.period_tree.item(sel[0], "values")[0])

    def _period_create(self) -> None:
        try:
            year = int(self.ent_period_year.get().strip())
            month = int(self.ent_period_month.get().strip())
            self.hr.payroll_period_create(year, month)
            self._period_refresh()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, str(exc))

    def _period_lock(self) -> None:
        pid = self._selected_period_id()
        if not pid:
            return
        try:
            self.hr.payroll_period_lock(pid, 1)
            self._period_refresh()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, str(exc))

    def _period_refresh(self) -> None:
        def worker():
            return self.hr.payroll_period_list()

        def done(rows):
            for item in self.period_tree.get_children():
                self.period_tree.delete(item)
            for r in rows:
                self.period_tree.insert(
                    "",
                    tk.END,
                    values=(r.get("id"), r.get("year"), r.get("month"), "Evet" if r.get("locked") else "Hayır"),
                )

        self._run_bg(worker, done)

    def _item_add(self) -> None:
        pid = self._selected_period_id()
        if not pid:
            messagebox.showerror(APP_TITLE, "Dönem seçmelisiniz.")
            return
        emp_id = self.pay_emp_map.get(self.cmb_pay_employee.get())
        if not emp_id:
            messagebox.showerror(APP_TITLE, "Personel seçmelisiniz.")
            return
        try:
            amount = float(self.ent_pay_amount.get().strip() or 0)
            self.hr.payroll_item_add(
                pid,
                emp_id,
                self.cmb_pay_type.get(),
                self.ent_pay_desc.get().strip(),
                amount,
                self.ent_pay_currency.get().strip() or "TL",
            )
            self._items_refresh()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, str(exc))

    def _selected_item_id(self) -> Optional[int]:
        sel = self.items_tree.selection()
        if not sel:
            return None
        return int(self.items_tree.item(sel[0], "values")[0])

    def _item_void(self) -> None:
        item_id = self._selected_item_id()
        if not item_id:
            return
        try:
            self.hr.payroll_item_void(item_id)
            self._items_refresh()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, str(exc))

    def _items_refresh(self) -> None:
        pid = self._selected_period_id()
        if not pid:
            return

        def worker():
            return self.hr.payroll_items_list(pid)

        def done(rows):
            for item in self.items_tree.get_children():
                self.items_tree.delete(item)
            for r in rows:
                name = f"{r.get('first_name', '')} {r.get('last_name', '')}".strip()
                self.items_tree.insert(
                    "",
                    tk.END,
                    values=(
                        r.get("id"),
                        name,
                        r.get("item_type"),
                        r.get("amount"),
                        r.get("currency"),
                        "Evet" if r.get("is_void") else "Hayır",
                    ),
                )

        self._run_bg(worker, done)

    # -----------------
    # Raporlar
    # -----------------
    def _build_reports_tab(self) -> ttk.Frame:
        frame = ttk.Frame(self.nb)
        nb = ttk.Notebook(frame)
        nb.pack(fill=tk.BOTH, expand=True)

        nb.add(self._report_personnel_tab(nb), text="Personel")
        nb.add(self._report_leave_tab(nb), text="İzin")
        nb.add(self._report_timesheet_tab(nb), text="Puantaj")
        nb.add(self._report_payroll_tab(nb), text="Bordro")
        nb.add(self._report_audit_tab(nb), text="Audit")
        return frame

    def _report_personnel_tab(self, master: ttk.Notebook) -> ttk.Frame:
        frame = ttk.Frame(master)
        filters = ttk.Frame(frame)
        filters.pack(fill=tk.X, padx=8, pady=8)

        ttk.Label(filters, text="Departman").pack(side=tk.LEFT)
        self.cmb_rpt_dept = ttk.Combobox(filters, state="readonly", width=20)
        self.cmb_rpt_dept.pack(side=tk.LEFT, padx=4)

        ttk.Label(filters, text="Pozisyon").pack(side=tk.LEFT)
        self.cmb_rpt_pos = ttk.Combobox(filters, state="readonly", width=20)
        self.cmb_rpt_pos.pack(side=tk.LEFT, padx=4)

        ttk.Label(filters, text="Durum").pack(side=tk.LEFT)
        self.cmb_rpt_status = ttk.Combobox(filters, state="readonly", width=12, values=["aktif", "pasif"])
        self.cmb_rpt_status.pack(side=tk.LEFT, padx=4)

        ttk.Button(filters, text="Rapor", command=self._report_personnel_run).pack(side=tk.LEFT, padx=6)

        self.rpt_personnel_tree = ttk.Treeview(
            frame,
            columns=("id", "name", "dept", "pos", "status"),
            show="headings",
            height=12,
        )
        for col, title in (
            ("id", "ID"),
            ("name", "Ad Soyad"),
            ("dept", "Departman"),
            ("pos", "Pozisyon"),
            ("status", "Durum"),
        ):
            self.rpt_personnel_tree.heading(col, text=title)
        self.rpt_personnel_tree.column("id", width=50, anchor="center")
        self.rpt_personnel_tree.column("name", width=180)
        self.rpt_personnel_tree.column("dept", width=140)
        self.rpt_personnel_tree.column("pos", width=140)
        self.rpt_personnel_tree.column("status", width=80, anchor="center")
        self.rpt_personnel_tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 6))

        self._reload_departments_positions()
        return frame

    def _report_personnel_run(self) -> None:
        dept_id = self.dept_map.get(self.cmb_rpt_dept.get())
        pos_id = self.pos_map.get(self.cmb_rpt_pos.get())
        status = self.cmb_rpt_status.get() or None

        def worker():
            return self.hr.report_personnel(dept_id, pos_id, status)

        def done(rows):
            for item in self.rpt_personnel_tree.get_children():
                self.rpt_personnel_tree.delete(item)
            for r in rows:
                name = f"{r.get('first_name', '')} {r.get('last_name', '')}".strip()
                self.rpt_personnel_tree.insert(
                    "",
                    tk.END,
                    values=(r.get("id"), name, r.get("department_name", ""), r.get("position_name", ""), r.get("status")),
                )

        self._run_bg(worker, done)

    def _report_leave_tab(self, master: ttk.Notebook) -> ttk.Frame:
        frame = ttk.Frame(master)
        row = ttk.Frame(frame)
        row.pack(fill=tk.X, padx=8, pady=8)
        ttk.Label(row, text="Yıl").pack(side=tk.LEFT)
        self.ent_rpt_leave_year = ttk.Entry(row, width=8)
        self.ent_rpt_leave_year.pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="Rapor", command=self._report_leave_run).pack(side=tk.LEFT, padx=6)

        self.rpt_leave_tree = ttk.Treeview(
            frame,
            columns=("employee", "total", "used", "remaining"),
            show="headings",
            height=12,
        )
        for col, title in (
            ("employee", "Personel"),
            ("total", "Toplam"),
            ("used", "Kullanılan"),
            ("remaining", "Kalan"),
        ):
            self.rpt_leave_tree.heading(col, text=title)
        self.rpt_leave_tree.column("employee", width=200)
        self.rpt_leave_tree.column("total", width=80, anchor="center")
        self.rpt_leave_tree.column("used", width=80, anchor="center")
        self.rpt_leave_tree.column("remaining", width=80, anchor="center")
        self.rpt_leave_tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 6))
        return frame

    def _report_leave_run(self) -> None:
        try:
            year = int(self.ent_rpt_leave_year.get().strip())
        except Exception:
            messagebox.showerror(APP_TITLE, "Yıl giriniz.")
            return

        def worker():
            return self.hr.report_leave_summary(year)

        def done(rows):
            for item in self.rpt_leave_tree.get_children():
                self.rpt_leave_tree.delete(item)
            for r in rows:
                name = f"{r.get('first_name', '')} {r.get('last_name', '')}".strip()
                self.rpt_leave_tree.insert(
                    "",
                    tk.END,
                    values=(name, r.get("total_days"), r.get("used_days"), r.get("remaining_days")),
                )

        self._run_bg(worker, done)

    def _report_timesheet_tab(self, master: ttk.Notebook) -> ttk.Frame:
        frame = ttk.Frame(master)
        row = ttk.Frame(frame)
        row.pack(fill=tk.X, padx=8, pady=8)
        ttk.Label(row, text="Başlangıç").pack(side=tk.LEFT)
        self.ent_rpt_ts_start = ttk.Entry(row, width=12)
        self.ent_rpt_ts_start.pack(side=tk.LEFT, padx=4)
        ttk.Label(row, text="Bitiş").pack(side=tk.LEFT)
        self.ent_rpt_ts_end = ttk.Entry(row, width=12)
        self.ent_rpt_ts_end.pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="Rapor", command=self._report_timesheet_run).pack(side=tk.LEFT, padx=6)

        self.rpt_ts_tree = ttk.Treeview(
            frame,
            columns=("employee", "calisti", "izin", "rapor", "gelmedi"),
            show="headings",
            height=12,
        )
        for col, title in (
            ("employee", "Personel"),
            ("calisti", "Çalıştı"),
            ("izin", "İzin"),
            ("rapor", "Rapor"),
            ("gelmedi", "Gelmedi"),
        ):
            self.rpt_ts_tree.heading(col, text=title)
        self.rpt_ts_tree.column("employee", width=200)
        self.rpt_ts_tree.column("calisti", width=70, anchor="center")
        self.rpt_ts_tree.column("izin", width=70, anchor="center")
        self.rpt_ts_tree.column("rapor", width=70, anchor="center")
        self.rpt_ts_tree.column("gelmedi", width=70, anchor="center")
        self.rpt_ts_tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 6))
        return frame

    def _report_timesheet_run(self) -> None:
        start_date = self.ent_rpt_ts_start.get().strip()
        end_date = self.ent_rpt_ts_end.get().strip()
        if not start_date or not end_date:
            messagebox.showerror(APP_TITLE, "Tarih aralığı giriniz.")
            return

        def worker():
            return self.hr.report_timesheet_summary(start_date, end_date)

        def done(rows):
            for item in self.rpt_ts_tree.get_children():
                self.rpt_ts_tree.delete(item)
            for r in rows:
                name = f"{r.get('first_name', '')} {r.get('last_name', '')}".strip()
                self.rpt_ts_tree.insert(
                    "",
                    tk.END,
                    values=(name, r.get("calisti"), r.get("izin"), r.get("rapor"), r.get("gelmedi")),
                )

        self._run_bg(worker, done)

    def _report_payroll_tab(self, master: ttk.Notebook) -> ttk.Frame:
        frame = ttk.Frame(master)
        row = ttk.Frame(frame)
        row.pack(fill=tk.X, padx=8, pady=8)
        ttk.Label(row, text="Dönem ID").pack(side=tk.LEFT)
        self.ent_rpt_pay_period = ttk.Entry(row, width=8)
        self.ent_rpt_pay_period.pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="Rapor", command=self._report_payroll_run).pack(side=tk.LEFT, padx=6)

        self.rpt_pay_tree = ttk.Treeview(
            frame,
            columns=("employee", "total"),
            show="headings",
            height=12,
        )
        for col, title in (
            ("employee", "Personel"),
            ("total", "Toplam"),
        ):
            self.rpt_pay_tree.heading(col, text=title)
        self.rpt_pay_tree.column("employee", width=200)
        self.rpt_pay_tree.column("total", width=100, anchor="e")
        self.rpt_pay_tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 6))
        return frame

    def _report_payroll_run(self) -> None:
        try:
            period_id = int(self.ent_rpt_pay_period.get().strip())
        except Exception:
            messagebox.showerror(APP_TITLE, "Dönem ID giriniz.")
            return

        def worker():
            return self.hr.report_payroll_summary(period_id)

        def done(rows):
            for item in self.rpt_pay_tree.get_children():
                self.rpt_pay_tree.delete(item)
            for r in rows:
                name = f"{r.get('first_name', '')} {r.get('last_name', '')}".strip()
                self.rpt_pay_tree.insert("", tk.END, values=(name, r.get("total_amount")))

        self._run_bg(worker, done)

    def _report_audit_tab(self, master: ttk.Notebook) -> ttk.Frame:
        frame = ttk.Frame(master)
        row = ttk.Frame(frame)
        row.pack(fill=tk.X, padx=8, pady=8)
        ttk.Button(row, text="Yenile", command=self._report_audit_refresh).pack(side=tk.LEFT)

        self.rpt_audit_tree = ttk.Treeview(
            frame,
            columns=("id", "entity", "action", "actor", "detail", "created"),
            show="headings",
            height=12,
        )
        for col, title in (
            ("id", "ID"),
            ("entity", "Varlık"),
            ("action", "İşlem"),
            ("actor", "Kullanıcı"),
            ("detail", "Detay"),
            ("created", "Tarih"),
        ):
            self.rpt_audit_tree.heading(col, text=title)
        self.rpt_audit_tree.column("id", width=50, anchor="center")
        self.rpt_audit_tree.column("entity", width=120)
        self.rpt_audit_tree.column("action", width=120)
        self.rpt_audit_tree.column("actor", width=120)
        self.rpt_audit_tree.column("detail", width=200)
        self.rpt_audit_tree.column("created", width=140)
        self.rpt_audit_tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 6))
        return frame

    def _report_audit_refresh(self) -> None:
        def worker():
            return self.hr.report_audit(200)

        def done(rows):
            for item in self.rpt_audit_tree.get_children():
                self.rpt_audit_tree.delete(item)
            for r in rows:
                self.rpt_audit_tree.insert(
                    "",
                    tk.END,
                    values=(
                        r.get("id"),
                        r.get("entity_type"),
                        r.get("action"),
                        r.get("actor_username"),
                        r.get("detail"),
                        r.get("created_at"),
                    ),
                )

        self._run_bg(worker, done)

    # -----------------
    # Tanımlar
    # -----------------
    def _build_definitions_tab(self) -> ttk.Frame:
        frame = ttk.Frame(self.nb)
        nb = ttk.Notebook(frame)
        nb.pack(fill=tk.BOTH, expand=True)

        nb.add(self._def_departments_tab(nb), text="Departman")
        nb.add(self._def_positions_tab(nb), text="Pozisyon")
        nb.add(self._def_leave_types_tab(nb), text="İzin Türleri")
        nb.add(self._def_shifts_tab(nb), text="Vardiyalar")
        nb.add(self._def_roles_tab(nb), text="Yetkiler")
        return frame

    def _def_departments_tab(self, master: ttk.Notebook) -> ttk.Frame:
        frame = ttk.Frame(master)
        row = ttk.Frame(frame)
        row.pack(fill=tk.X, padx=8, pady=8)
        ttk.Label(row, text="Departman").pack(side=tk.LEFT)
        self.ent_dept_name = ttk.Entry(row, width=24)
        self.ent_dept_name.pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="Ekle", command=self._dept_add).pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="Sil", command=self._dept_delete).pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="Yenile", command=self._dept_refresh).pack(side=tk.LEFT, padx=4)

        self.dept_tree = ttk.Treeview(frame, columns=("id", "name", "active"), show="headings", height=10)
        for col, title in (("id", "ID"), ("name", "Ad"), ("active", "Aktif")):
            self.dept_tree.heading(col, text=title)
        self.dept_tree.column("id", width=50, anchor="center")
        self.dept_tree.column("name", width=200)
        self.dept_tree.column("active", width=80, anchor="center")
        self.dept_tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 6))

        self._dept_refresh()
        return frame

    def _selected_dept_id(self) -> Optional[int]:
        sel = self.dept_tree.selection()
        if not sel:
            return None
        return int(self.dept_tree.item(sel[0], "values")[0])

    def _dept_add(self) -> None:
        name = self.ent_dept_name.get().strip()
        if not name:
            return
        try:
            self.hr.department_create(name)
            self._dept_refresh()
            self._reload_departments_positions()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, str(exc))

    def _dept_delete(self) -> None:
        dept_id = self._selected_dept_id()
        if not dept_id:
            return
        try:
            self.hr.department_delete(dept_id)
            self._dept_refresh()
            self._reload_departments_positions()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, str(exc))

    def _dept_refresh(self) -> None:
        def worker():
            return self.hr.department_list()

        def done(rows):
            for item in self.dept_tree.get_children():
                self.dept_tree.delete(item)
            for r in rows:
                self.dept_tree.insert(
                    "",
                    tk.END,
                    values=(r.get("id"), r.get("name"), "Evet" if r.get("active") else "Hayır"),
                )

        self._run_bg(worker, done)

    def _def_positions_tab(self, master: ttk.Notebook) -> ttk.Frame:
        frame = ttk.Frame(master)
        row = ttk.Frame(frame)
        row.pack(fill=tk.X, padx=8, pady=8)
        ttk.Label(row, text="Pozisyon").pack(side=tk.LEFT)
        self.ent_pos_name = ttk.Entry(row, width=24)
        self.ent_pos_name.pack(side=tk.LEFT, padx=4)
        ttk.Label(row, text="Departman").pack(side=tk.LEFT)
        self.cmb_pos_dept = ttk.Combobox(row, state="readonly", width=20)
        self.cmb_pos_dept.pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="Ekle", command=self._pos_add).pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="Sil", command=self._pos_delete).pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="Yenile", command=self._pos_refresh).pack(side=tk.LEFT, padx=4)

        self.pos_tree = ttk.Treeview(frame, columns=("id", "name", "department"), show="headings", height=10)
        for col, title in (("id", "ID"), ("name", "Ad"), ("department", "Departman")):
            self.pos_tree.heading(col, text=title)
        self.pos_tree.column("id", width=50, anchor="center")
        self.pos_tree.column("name", width=200)
        self.pos_tree.column("department", width=200)
        self.pos_tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 6))

        self._pos_refresh()
        return frame

    def _selected_pos_id(self) -> Optional[int]:
        sel = self.pos_tree.selection()
        if not sel:
            return None
        return int(self.pos_tree.item(sel[0], "values")[0])

    def _pos_add(self) -> None:
        name = self.ent_pos_name.get().strip()
        dept_id = self.dept_map.get(self.cmb_pos_dept.get())
        if not name:
            return
        try:
            self.hr.position_create(name, dept_id)
            self._pos_refresh()
            self._reload_departments_positions()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, str(exc))

    def _pos_delete(self) -> None:
        pos_id = self._selected_pos_id()
        if not pos_id:
            return
        try:
            self.hr.position_delete(pos_id)
            self._pos_refresh()
            self._reload_departments_positions()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, str(exc))

    def _pos_refresh(self) -> None:
        def worker():
            return self.hr.position_list()

        def done(rows):
            for item in self.pos_tree.get_children():
                self.pos_tree.delete(item)
            for r in rows:
                self.pos_tree.insert("", tk.END, values=(r.get("id"), r.get("name"), r.get("department_name", "")))
            self.cmb_pos_dept["values"] = list(self.dept_map.keys())

        self._run_bg(worker, done)

    def _def_leave_types_tab(self, master: ttk.Notebook) -> ttk.Frame:
        frame = ttk.Frame(master)
        row = ttk.Frame(frame)
        row.pack(fill=tk.X, padx=8, pady=8)
        ttk.Label(row, text="İzin Türü").pack(side=tk.LEFT)
        self.ent_leave_type_name = ttk.Entry(row, width=24)
        self.ent_leave_type_name.pack(side=tk.LEFT, padx=4)
        ttk.Label(row, text="Yıllık Gün").pack(side=tk.LEFT)
        self.ent_leave_type_days = ttk.Entry(row, width=8)
        self.ent_leave_type_days.pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="Ekle", command=self._leave_type_add).pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="Sil", command=self._leave_type_delete).pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="Yenile", command=self._leave_type_refresh).pack(side=tk.LEFT, padx=4)

        self.leave_type_tree = ttk.Treeview(frame, columns=("id", "name", "days"), show="headings", height=10)
        for col, title in (("id", "ID"), ("name", "Ad"), ("days", "Yıllık")):
            self.leave_type_tree.heading(col, text=title)
        self.leave_type_tree.column("id", width=50, anchor="center")
        self.leave_type_tree.column("name", width=200)
        self.leave_type_tree.column("days", width=80, anchor="center")
        self.leave_type_tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 6))

        self._leave_type_refresh()
        return frame

    def _selected_leave_type_id(self) -> Optional[int]:
        sel = self.leave_type_tree.selection()
        if not sel:
            return None
        return int(self.leave_type_tree.item(sel[0], "values")[0])

    def _leave_type_add(self) -> None:
        name = self.ent_leave_type_name.get().strip()
        if not name:
            return
        try:
            days = float(self.ent_leave_type_days.get().strip() or 0)
            self.hr.leave_type_create(name, days)
            self._leave_type_refresh()
            self._leave_reload_sources()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, str(exc))

    def _leave_type_delete(self) -> None:
        lt_id = self._selected_leave_type_id()
        if not lt_id:
            return
        try:
            self.hr.leave_type_delete(lt_id)
            self._leave_type_refresh()
            self._leave_reload_sources()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, str(exc))

    def _leave_type_refresh(self) -> None:
        def worker():
            return self.hr.leave_type_list()

        def done(rows):
            for item in self.leave_type_tree.get_children():
                self.leave_type_tree.delete(item)
            for r in rows:
                self.leave_type_tree.insert("", tk.END, values=(r.get("id"), r.get("name"), r.get("annual_days")))

        self._run_bg(worker, done)

    def _def_shifts_tab(self, master: ttk.Notebook) -> ttk.Frame:
        frame = ttk.Frame(master)
        row = ttk.Frame(frame)
        row.pack(fill=tk.X, padx=8, pady=8)
        ttk.Label(row, text="Vardiya").pack(side=tk.LEFT)
        self.ent_shift_name = ttk.Entry(row, width=20)
        self.ent_shift_name.pack(side=tk.LEFT, padx=4)
        ttk.Label(row, text="Başlangıç").pack(side=tk.LEFT)
        self.ent_shift_start = ttk.Entry(row, width=8)
        self.ent_shift_start.pack(side=tk.LEFT, padx=4)
        ttk.Label(row, text="Bitiş").pack(side=tk.LEFT)
        self.ent_shift_end = ttk.Entry(row, width=8)
        self.ent_shift_end.pack(side=tk.LEFT, padx=4)
        ttk.Label(row, text="Mola(dk)").pack(side=tk.LEFT)
        self.ent_shift_break = ttk.Entry(row, width=6)
        self.ent_shift_break.pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="Ekle", command=self._shift_add).pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="Sil", command=self._shift_delete).pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="Yenile", command=self._shift_refresh).pack(side=tk.LEFT, padx=4)

        self.shift_tree = ttk.Treeview(frame, columns=("id", "name", "start", "end", "break"), show="headings", height=10)
        for col, title in (("id", "ID"), ("name", "Ad"), ("start", "Baş"), ("end", "Bitiş"), ("break", "Mola")):
            self.shift_tree.heading(col, text=title)
        self.shift_tree.column("id", width=50, anchor="center")
        self.shift_tree.column("name", width=160)
        self.shift_tree.column("start", width=80)
        self.shift_tree.column("end", width=80)
        self.shift_tree.column("break", width=70, anchor="center")
        self.shift_tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 6))

        self._shift_refresh()
        return frame

    def _selected_shift_id(self) -> Optional[int]:
        sel = self.shift_tree.selection()
        if not sel:
            return None
        return int(self.shift_tree.item(sel[0], "values")[0])

    def _shift_add(self) -> None:
        name = self.ent_shift_name.get().strip()
        if not name:
            return
        try:
            self.hr.shift_create(
                name,
                self.ent_shift_start.get().strip(),
                self.ent_shift_end.get().strip(),
                int(self.ent_shift_break.get().strip() or 0),
            )
            self._shift_refresh()
            self._timesheet_reload_sources()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, str(exc))

    def _shift_delete(self) -> None:
        sid = self._selected_shift_id()
        if not sid:
            return
        try:
            self.hr.shift_delete(sid)
            self._shift_refresh()
            self._timesheet_reload_sources()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, str(exc))

    def _shift_refresh(self) -> None:
        def worker():
            return self.hr.shift_list()

        def done(rows):
            for item in self.shift_tree.get_children():
                self.shift_tree.delete(item)
            for r in rows:
                self.shift_tree.insert(
                    "",
                    tk.END,
                    values=(r.get("id"), r.get("name"), r.get("start_time"), r.get("end_time"), r.get("break_minutes")),
                )

        self._run_bg(worker, done)

    def _def_roles_tab(self, master: ttk.Notebook) -> ttk.Frame:
        frame = ttk.Frame(master)
        row = ttk.Frame(frame)
        row.pack(fill=tk.X, padx=8, pady=8)

        ttk.Label(row, text="Kullanıcı").pack(side=tk.LEFT)
        self.cmb_role_user = ttk.Combobox(row, state="readonly", width=20)
        self.cmb_role_user.pack(side=tk.LEFT, padx=4)
        ttk.Label(row, text="Rol").pack(side=tk.LEFT)
        self.cmb_role = ttk.Combobox(row, state="readonly", width=16, values=["HR_ADMIN", "HR_USER", "MANAGER", "ACCOUNTING", "VIEWER"])
        self.cmb_role.pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="Kaydet", command=self._role_save).pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="Yenile", command=self._role_refresh).pack(side=tk.LEFT, padx=4)

        self.roles_tree = ttk.Treeview(frame, columns=("user", "role"), show="headings", height=10)
        for col, title in (("user", "Kullanıcı"), ("role", "Rol")):
            self.roles_tree.heading(col, text=title)
        self.roles_tree.column("user", width=200)
        self.roles_tree.column("role", width=140)
        self.roles_tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 6))

        self._role_refresh()
        return frame

    def _role_refresh(self) -> None:
        users = [u["username"] for u in self.app.usersdb.list_users()]
        self.cmb_role_user["values"] = users

        def worker():
            return self.hr.list_user_roles()

        def done(rows):
            for item in self.roles_tree.get_children():
                self.roles_tree.delete(item)
            for r in rows:
                self.roles_tree.insert("", tk.END, values=(r.get("username"), r.get("role")))

        self._run_bg(worker, done)

    def _role_save(self) -> None:
        username = self.cmb_role_user.get().strip()
        role = self.cmb_role.get().strip()
        if not username or not role:
            return
        try:
            self.hr.set_user_role(username, role)
            self._role_refresh()
            self._apply_role_visibility()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, str(exc))


def build(master: ttk.Frame, app) -> ttk.Frame:
    return HRFrame(master, app)

