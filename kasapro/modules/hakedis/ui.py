# -*- coding: utf-8 -*-

from __future__ import annotations

import csv
import os
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Optional

from .engine import HakedisEngine


class HakedisFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.repo = app.db.hakedis
        self.service = app.services.hakedis
        self.engine = HakedisEngine(self.repo)
        self._queue: "queue.Queue[tuple]" = queue.Queue()
        self._build()
        self.after(200, self._poll_queue)

    def _build(self) -> None:
        title = ttk.Label(self, text="Proje/Şantiye > Hakediş Merkezi", style="Header.TLabel")
        title.pack(anchor="w", padx=12, pady=(10, 6))

        tabs = ttk.Notebook(self)
        tabs.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.tab_projects = ttk.Frame(tabs)
        self.tab_contracts = ttk.Frame(tabs)
        self.tab_boq = ttk.Frame(tabs)
        self.tab_measure = ttk.Frame(tabs)
        self.tab_pay = ttk.Frame(tabs)
        self.tab_reports = ttk.Frame(tabs)
        self.tab_indices = ttk.Frame(tabs)
        self.tab_approvals = ttk.Frame(tabs)

        tabs.add(self.tab_projects, text="Projeler")
        tabs.add(self.tab_contracts, text="Sözleşmeler")
        tabs.add(self.tab_boq, text="Poz (BOQ)")
        tabs.add(self.tab_measure, text="Metraj")
        tabs.add(self.tab_pay, text="Hakediş")
        tabs.add(self.tab_reports, text="Raporlar")
        tabs.add(self.tab_indices, text="Endeks")
        tabs.add(self.tab_approvals, text="Onay")

        self._build_projects()
        self._build_contracts()
        self._build_boq()
        self._build_measure()
        self._build_pay()
        self._build_reports()
        self._build_indices()
        self._build_approvals()

    def _build_projects(self) -> None:
        frame = self.tab_projects
        form = ttk.LabelFrame(frame, text="Yeni Proje")
        form.pack(fill=tk.X, padx=8, pady=6)
        ttk.Label(form, text="Proje Adı").grid(row=0, column=0, padx=6, pady=6, sticky="w")
        ttk.Label(form, text="Kod").grid(row=0, column=2, padx=6, pady=6, sticky="w")
        self.ent_project_name = ttk.Entry(form, width=30)
        self.ent_project_code = ttk.Entry(form, width=12)
        self.ent_project_name.grid(row=0, column=1, padx=6, pady=6)
        self.ent_project_code.grid(row=0, column=3, padx=6, pady=6)
        ttk.Button(form, text="Kaydet", command=self._project_save).grid(row=0, column=4, padx=6)

        self.lst_projects = tk.Listbox(frame, height=8)
        self.lst_projects.pack(fill=tk.X, padx=8, pady=6)
        ttk.Button(frame, text="Listeyi Yenile", command=self._projects_refresh).pack(anchor="e", padx=8)
        self._projects_refresh()

    def _project_save(self) -> None:
        name = self.ent_project_name.get().strip()
        code = self.ent_project_code.get().strip()
        if not name:
            messagebox.showwarning("Hakediş", "Proje adı gerekli.")
            return
        try:
            cid = int(self.app.active_company_id or 0)
        except Exception:
            cid = 0
        pid = self.repo.project_create(cid, name, code, user_id=self.app.data_owner_user_id, username=self.app.user["username"])
        self.repo.site_create(cid, pid, name=f"{name} Şantiye")
        self.ent_project_name.delete(0, tk.END)
        self.ent_project_code.delete(0, tk.END)
        self._projects_refresh()

    def _projects_refresh(self) -> None:
        self.lst_projects.delete(0, tk.END)
        cid = int(self.app.active_company_id or 0)
        for row in self.repo.project_list(cid, only_active=False):
            self.lst_projects.insert(tk.END, f"#{row['id']} {row['name']} ({row['code']})")

    def _build_contracts(self) -> None:
        frame = self.tab_contracts
        form = ttk.LabelFrame(frame, text="Yeni Sözleşme")
        form.pack(fill=tk.X, padx=8, pady=6)
        ttk.Label(form, text="Proje ID").grid(row=0, column=0, padx=6, pady=6, sticky="w")
        ttk.Label(form, text="Sözleşme No").grid(row=0, column=2, padx=6, pady=6, sticky="w")
        self.ent_contract_project = ttk.Entry(form, width=8)
        self.ent_contract_no = ttk.Entry(form, width=20)
        self.ent_contract_project.grid(row=0, column=1, padx=6, pady=6)
        self.ent_contract_no.grid(row=0, column=3, padx=6, pady=6)
        ttk.Label(form, text="Tip").grid(row=0, column=4, padx=6, pady=6, sticky="w")
        self.cmb_contract_type = ttk.Combobox(form, values=["birim_fiyat", "goturu"], width=12)
        self.cmb_contract_type.set("birim_fiyat")
        self.cmb_contract_type.grid(row=0, column=5, padx=6, pady=6)
        ttk.Button(form, text="Kaydet", command=self._contract_save).grid(row=0, column=6, padx=6)

        self.lst_contracts = tk.Listbox(frame, height=8)
        self.lst_contracts.pack(fill=tk.X, padx=8, pady=6)
        ttk.Button(frame, text="Listeyi Yenile", command=self._contracts_refresh).pack(anchor="e", padx=8)
        self._contracts_refresh()

    def _contract_save(self) -> None:
        try:
            project_id = int(self.ent_contract_project.get().strip())
        except Exception:
            messagebox.showwarning("Hakediş", "Proje ID gerekli.")
            return
        contract_no = self.ent_contract_no.get().strip()
        if not contract_no:
            messagebox.showwarning("Hakediş", "Sözleşme numarası gerekli.")
            return
        contract_type = self.cmb_contract_type.get().strip() or "birim_fiyat"
        cid = int(self.app.active_company_id or 0)
        self.repo.contract_create(cid, project_id, None, contract_no, contract_type)
        self.ent_contract_no.delete(0, tk.END)
        self._contracts_refresh()

    def _contracts_refresh(self) -> None:
        self.lst_contracts.delete(0, tk.END)
        cid = int(self.app.active_company_id or 0)
        for row in self.repo.contract_list(cid):
            self.lst_contracts.insert(tk.END, f"#{row['id']} {row['contract_no']} ({row['contract_type']})")

    def _build_boq(self) -> None:
        frame = self.tab_boq
        form = ttk.LabelFrame(frame, text="BOQ İçe Aktar")
        form.pack(fill=tk.X, padx=8, pady=6)
        ttk.Label(form, text="Proje ID").grid(row=0, column=0, padx=6, pady=6, sticky="w")
        ttk.Label(form, text="Sözleşme ID").grid(row=0, column=2, padx=6, pady=6, sticky="w")
        self.ent_boq_project = ttk.Entry(form, width=8)
        self.ent_boq_contract = ttk.Entry(form, width=8)
        self.ent_boq_project.grid(row=0, column=1, padx=6, pady=6)
        self.ent_boq_contract.grid(row=0, column=3, padx=6, pady=6)
        ttk.Button(form, text="CSV Seç", command=self._boq_import).grid(row=0, column=4, padx=6)

        self.lbl_boq_status = ttk.Label(frame, text="")
        self.lbl_boq_status.pack(anchor="w", padx=8, pady=(6, 0))

    def _boq_import(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if not path:
            return
        try:
            project_id = int(self.ent_boq_project.get().strip())
            contract_id = int(self.ent_boq_contract.get().strip())
        except Exception:
            messagebox.showwarning("Hakediş", "Proje/Sözleşme ID gerekli.")
            return
        cid = int(self.app.active_company_id or 0)
        count, total = self.repo.boq_import_csv(path, cid, project_id, contract_id)
        self.lbl_boq_status.config(text=f"{count} satır içe aktarıldı • Toplam {total:.2f}")

    def _build_measure(self) -> None:
        frame = self.tab_measure
        form = ttk.LabelFrame(frame, text="Metraj Girişi")
        form.pack(fill=tk.X, padx=8, pady=6)
        labels = [
            ("Dönem ID", 0),
            ("Poz ID", 2),
            ("Miktar", 4),
            ("Tarih", 6),
        ]
        for text, col in labels:
            ttk.Label(form, text=text).grid(row=0, column=col, padx=6, pady=6, sticky="w")
        self.ent_measure_period = ttk.Entry(form, width=8)
        self.ent_measure_poz = ttk.Entry(form, width=8)
        self.ent_measure_qty = ttk.Entry(form, width=8)
        self.ent_measure_date = ttk.Entry(form, width=12)
        self.ent_measure_period.grid(row=0, column=1, padx=6, pady=6)
        self.ent_measure_poz.grid(row=0, column=3, padx=6, pady=6)
        self.ent_measure_qty.grid(row=0, column=5, padx=6, pady=6)
        self.ent_measure_date.grid(row=0, column=7, padx=6, pady=6)

        ttk.Button(form, text="Ek Dosya", command=self._select_measure_attachment).grid(row=0, column=8, padx=6)
        ttk.Button(form, text="Kaydet", command=self._measure_save).grid(row=0, column=9, padx=6)

        self.lbl_measure_attachment = ttk.Label(frame, text="")
        self.lbl_measure_attachment.pack(anchor="w", padx=8, pady=(4, 0))
        self._selected_attachment: Optional[str] = None

    def _select_measure_attachment(self) -> None:
        path = filedialog.askopenfilename()
        if not path:
            return
        self._selected_attachment = path
        self.lbl_measure_attachment.config(text=os.path.basename(path))

    def _measure_save(self) -> None:
        try:
            period_id = int(self.ent_measure_period.get().strip())
            boq_id = int(self.ent_measure_poz.get().strip())
            qty = float(self.ent_measure_qty.get().strip())
        except Exception:
            messagebox.showwarning("Hakediş", "Dönem, Poz ve miktar zorunlu.")
            return
        tarih = self.ent_measure_date.get().strip() or ""
        if not tarih:
            messagebox.showwarning("Hakediş", "Tarih gerekli.")
            return
        cid = int(self.app.active_company_id or 0)
        attachment_id = None
        if self._selected_attachment:
            original, stored, stored_path, size = self.service.save_attachment(self._selected_attachment, cid)
            attachment_id = self.repo.conn.execute(
                """
                INSERT INTO attachments(company_id, module, filename, stored_name, stored_path, size_bytes, created_at)
                VALUES (?,?,?,?,?,?,?)
                """,
                (cid, "hakedis", original, stored, stored_path, size, self.repo._now()),
            ).lastrowid
            self.repo.conn.commit()
        period = self.repo.period_get(cid, period_id)
        if not period:
            messagebox.showwarning("Hakediş", "Dönem bulunamadı.")
            return
        contract_id = int(period["contract_id"])
        project_id = int(period["project_id"])
        self.repo.measurement_add(cid, project_id, contract_id, period_id, boq_id, qty, tarih, attachment_id=attachment_id)
        messagebox.showinfo("Hakediş", "Metraj kaydedildi.")

    def _build_pay(self) -> None:
        frame = self.tab_pay
        form = ttk.LabelFrame(frame, text="Dönem Oluştur")
        form.pack(fill=tk.X, padx=8, pady=6)
        ttk.Label(form, text="Proje ID").grid(row=0, column=0, padx=6, pady=6, sticky="w")
        ttk.Label(form, text="Sözleşme ID").grid(row=0, column=2, padx=6, pady=6, sticky="w")
        ttk.Label(form, text="No").grid(row=0, column=4, padx=6, pady=6, sticky="w")
        ttk.Label(form, text="Başlangıç").grid(row=0, column=6, padx=6, pady=6, sticky="w")
        ttk.Label(form, text="Bitiş").grid(row=0, column=8, padx=6, pady=6, sticky="w")
        self.ent_pay_project = ttk.Entry(form, width=8)
        self.ent_pay_contract = ttk.Entry(form, width=8)
        self.ent_pay_no = ttk.Entry(form, width=6)
        self.ent_pay_start = ttk.Entry(form, width=10)
        self.ent_pay_end = ttk.Entry(form, width=10)
        self.ent_pay_project.grid(row=0, column=1, padx=6, pady=6)
        self.ent_pay_contract.grid(row=0, column=3, padx=6, pady=6)
        self.ent_pay_no.grid(row=0, column=5, padx=6, pady=6)
        self.ent_pay_start.grid(row=0, column=7, padx=6, pady=6)
        self.ent_pay_end.grid(row=0, column=9, padx=6, pady=6)
        ttk.Button(form, text="Oluştur", command=self._pay_create).grid(row=0, column=10, padx=6)

        calc = ttk.LabelFrame(frame, text="Hakediş Hesapla")
        calc.pack(fill=tk.X, padx=8, pady=6)
        ttk.Label(calc, text="Dönem ID").grid(row=0, column=0, padx=6, pady=6)
        self.ent_pay_period = ttk.Entry(calc, width=8)
        self.ent_pay_period.grid(row=0, column=1, padx=6, pady=6)
        ttk.Button(calc, text="Hesapla", command=self._pay_calculate).grid(row=0, column=2, padx=6)
        self.lbl_pay_status = ttk.Label(calc, text="")
        self.lbl_pay_status.grid(row=0, column=3, padx=6)

    def _pay_create(self) -> None:
        try:
            project_id = int(self.ent_pay_project.get().strip())
            contract_id = int(self.ent_pay_contract.get().strip())
            period_no = int(self.ent_pay_no.get().strip())
        except Exception:
            messagebox.showwarning("Hakediş", "Proje, sözleşme ve dönem no gerekli.")
            return
        start = self.ent_pay_start.get().strip()
        end = self.ent_pay_end.get().strip()
        if not start or not end:
            messagebox.showwarning("Hakediş", "Tarih aralığı gerekli.")
            return
        cid = int(self.app.active_company_id or 0)
        pid = self.repo.period_create(cid, project_id, contract_id, period_no, start, end)
        self.lbl_pay_status.config(text=f"Dönem oluşturuldu (id={pid})")

    def _pay_calculate(self) -> None:
        try:
            period_id = int(self.ent_pay_period.get().strip())
        except Exception:
            messagebox.showwarning("Hakediş", "Dönem ID gerekli.")
            return
        cid = int(self.app.active_company_id or 0)
        totals = self.repo.pay_estimate_calculate(cid, period_id)
        self.lbl_pay_status.config(text=f"Net: {totals['net']:.2f}")

    def _build_reports(self) -> None:
        frame = self.tab_reports
        form = ttk.LabelFrame(frame, text="Rapor Oluştur")
        form.pack(fill=tk.X, padx=8, pady=6)
        ttk.Label(form, text="Dönem ID").grid(row=0, column=0, padx=6, pady=6)
        self.ent_report_period = ttk.Entry(form, width=8)
        self.ent_report_period.grid(row=0, column=1, padx=6, pady=6)
        ttk.Button(form, text="CSV Üret", command=self._report_csv).grid(row=0, column=2, padx=6)
        self.lbl_report_status = ttk.Label(form, text="")
        self.lbl_report_status.grid(row=0, column=3, padx=6)

    def _report_csv(self) -> None:
        try:
            period_id = int(self.ent_report_period.get().strip())
        except Exception:
            messagebox.showwarning("Hakediş", "Dönem ID gerekli.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        cid = int(self.app.active_company_id or 0)
        def worker():
            try:
                lines = self.repo.pay_estimate_lines(cid, period_id)
                with open(path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Poz", "Ad", "Önceki", "Bu Dönem", "Kümülatif", "Tutar"])
                    for line in lines:
                        writer.writerow([
                            line["poz_code"],
                            line["name"],
                            line["prev_qty"],
                            line["current_qty"],
                            line["cum_qty"],
                            line["current_amount"],
                        ])
                self._queue.put(("report", f"CSV üretildi: {os.path.basename(path)}"))
            except Exception as exc:
                self._queue.put(("report", f"Hata: {exc}"))
        threading.Thread(target=worker, daemon=True).start()

    def _build_indices(self) -> None:
        frame = self.tab_indices
        form = ttk.LabelFrame(frame, text="Endeks Çek")
        form.pack(fill=tk.X, padx=8, pady=6)
        ttk.Label(form, text="Kodlar (virgül)").grid(row=0, column=0, padx=6, pady=6)
        ttk.Label(form, text="Dönem").grid(row=0, column=2, padx=6, pady=6)
        self.ent_index_codes = ttk.Entry(form, width=30)
        self.ent_index_period = ttk.Entry(form, width=10)
        self.ent_index_codes.grid(row=0, column=1, padx=6, pady=6)
        self.ent_index_period.grid(row=0, column=3, padx=6, pady=6)
        ttk.Button(form, text="Çek", command=self._index_fetch).grid(row=0, column=4, padx=6)
        self.lbl_index_status = ttk.Label(frame, text="")
        self.lbl_index_status.pack(anchor="w", padx=8, pady=(4, 0))

    def _index_fetch(self) -> None:
        codes = [c.strip() for c in self.ent_index_codes.get().split(",") if c.strip()]
        period = self.ent_index_period.get().strip()
        if not codes or not period:
            messagebox.showwarning("Hakediş", "Kod ve dönem gerekli.")
            return
        cid = int(self.app.active_company_id or 0)
        def worker():
            try:
                indices = self.service.index_fetch_with_cache(cid, codes, period, refresh=True)
                msg = ", ".join(f"{k}:{v}" for k, v in indices.items())
                self._queue.put(("index", msg or "Veri yok"))
            except Exception as exc:
                self._queue.put(("index", f"Hata: {exc}"))
        threading.Thread(target=worker, daemon=True).start()

    def _build_approvals(self) -> None:
        frame = self.tab_approvals
        form = ttk.LabelFrame(frame, text="Onay")
        form.pack(fill=tk.X, padx=8, pady=6)
        ttk.Label(form, text="Dönem ID").grid(row=0, column=0, padx=6, pady=6)
        ttk.Label(form, text="Durum").grid(row=0, column=2, padx=6, pady=6)
        self.ent_approval_period = ttk.Entry(form, width=8)
        self.ent_approval_period.grid(row=0, column=1, padx=6, pady=6)
        self.cmb_approval_status = ttk.Combobox(
            form,
            values=["Taslak", "Şantiye Onayı", "Kontrol Onayı", "Merkez Onayı", "Çıktı", "Revizyon"],
            width=16,
        )
        self.cmb_approval_status.set("Taslak")
        self.cmb_approval_status.grid(row=0, column=3, padx=6, pady=6)
        ttk.Button(form, text="Kaydet", command=self._approval_save).grid(row=0, column=4, padx=6)

    def _approval_save(self) -> None:
        try:
            period_id = int(self.ent_approval_period.get().strip())
        except Exception:
            messagebox.showwarning("Hakediş", "Dönem ID gerekli.")
            return
        status = self.cmb_approval_status.get().strip() or "Taslak"
        cid = int(self.app.active_company_id or 0)
        self.repo.approval_add(
            cid,
            "pay_estimates",
            period_id,
            status,
            self.app.data_owner_user_id,
            self.app.user["username"],
            "",
        )
        messagebox.showinfo("Hakediş", "Onay kaydedildi.")

    def _poll_queue(self) -> None:
        try:
            while True:
                key, msg = self._queue.get_nowait()
                if key == "report":
                    self.lbl_report_status.config(text=msg)
                elif key == "index":
                    self.lbl_index_status.config(text=msg)
        except queue.Empty:
            pass
        self.after(200, self._poll_queue)
