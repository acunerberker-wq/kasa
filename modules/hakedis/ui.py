# -*- coding: utf-8 -*-

from __future__ import annotations

import threading
from typing import Dict, Optional

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from kasapro.config import HAS_OPENPYXL
from kasapro.utils import fmt_amount

from .service import HakedisService


DEFAULT_INDEX_SETS = [
    "Yapım işleri endeksleri",
    "Yİ-ÜFE",
    "EPDK akaryakıt",
]


class HakedisFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.service = HakedisService(app.db, app.services.exporter)
        self._build_ui()
        self.refresh_all()

    def _build_ui(self):
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.tab_project = ttk.Frame(self.nb)
        self.tab_positions = ttk.Frame(self.nb)
        self.tab_periods = ttk.Frame(self.nb)
        self.tab_indices = ttk.Frame(self.nb)
        self.tab_reports = ttk.Frame(self.nb)

        self.nb.add(self.tab_project, text="📁 Proje/Sözleşme")
        self.nb.add(self.tab_positions, text="📌 Poz/Birim Fiyat")
        self.nb.add(self.tab_periods, text="🧾 Hakediş Dönemi")
        self.nb.add(self.tab_indices, text="📈 Endeks & Fiyat Farkı")
        self.nb.add(self.tab_reports, text="📄 Rapor/Döküm")

        self._build_project_tab()
        self._build_positions_tab()
        self._build_periods_tab()
        self._build_indices_tab()
        self._build_reports_tab()

    # -----------------
    # Proje
    # -----------------
    def _build_project_tab(self):
        frm = ttk.Frame(self.tab_project)
        frm.pack(fill=tk.X, padx=8, pady=8)

        self.project_fields: Dict[str, tk.Entry] = {}
        fields = [
            ("idare", "İdare"),
            ("yuklenici", "Yüklenici"),
            ("isin_adi", "İşin Adı"),
            ("sozlesme_bedeli", "Sözleşme Bedeli"),
            ("baslangic", "Başlangıç"),
            ("bitis", "Bitiş"),
            ("sure_gun", "Süre (gün)"),
            ("artis_eksilis", "Artış/Eksiliş"),
            ("avans", "Avans"),
        ]
        for i, (key, label) in enumerate(fields):
            ttk.Label(frm, text=label).grid(row=i // 3, column=(i % 3) * 2, sticky="w", padx=4, pady=4)
            ent = ttk.Entry(frm, width=24)
            ent.grid(row=i // 3, column=(i % 3) * 2 + 1, sticky="w", padx=4, pady=4)
            self.project_fields[key] = ent

        ttk.Button(frm, text="➕ Proje Kaydet", command=self._on_project_save).grid(
            row=3, column=0, padx=4, pady=10, sticky="w"
        )

        self.project_list = tk.Listbox(self.tab_project, height=8)
        self.project_list.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.project_list.bind("<<ListboxSelect>>", lambda _e: self._on_project_select())

        role_frame = ttk.LabelFrame(self.tab_project, text="Rol / Yetki Atama")
        role_frame.pack(fill=tk.X, padx=8, pady=8)
        ttk.Label(role_frame, text="Kullanıcı ID").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.ent_role_user = ttk.Entry(role_frame, width=10)
        self.ent_role_user.grid(row=0, column=1, padx=4, pady=4)
        ttk.Label(role_frame, text="Rol").grid(row=0, column=2, sticky="w", padx=4, pady=4)
        self.cmb_role = ttk.Combobox(role_frame, values=["hazirlayan", "kontrol", "idare", "goruntuleme"], width=16)
        self.cmb_role.grid(row=0, column=3, padx=4, pady=4)
        ttk.Button(role_frame, text="💾 Rol Kaydet", command=self._on_role_save).grid(
            row=0, column=4, padx=4, pady=4
        )

    def _on_project_save(self):
        try:
            data = {k: v.get().strip() for k, v in self.project_fields.items()}
            project_id = self.service.create_project(
                self._user_id(),
                idare=data["idare"],
                yuklenici=data["yuklenici"],
                isin_adi=data["isin_adi"],
                sozlesme_bedeli=float(data["sozlesme_bedeli"] or 0),
                baslangic=data["baslangic"],
                bitis=data["bitis"],
                sure_gun=int(data["sure_gun"] or 0),
                artis_eksilis=float(data["artis_eksilis"] or 0),
                avans=float(data["avans"] or 0),
            )
            messagebox.showinfo("Hakediş", f"Proje kaydedildi (id={project_id}).")
            self.refresh_projects()
        except Exception as exc:
            messagebox.showerror("Hakediş", f"Proje kaydedilemedi: {exc}")

    def _on_project_select(self):
        self.refresh_positions()
        self.refresh_periods()
        self._load_index_selections()

    def _on_role_save(self):
        project_id = self._selected_project_id()
        if not project_id:
            messagebox.showwarning("Hakediş", "Önce proje seçin.")
            return
        try:
            user_id = int(self.ent_role_user.get().strip())
            role = self.cmb_role.get().strip()
            if role not in {"hazirlayan", "kontrol", "idare", "goruntuleme"}:
                raise ValueError("Geçerli rol seçin.")
            self.service.repo.set_user_role(project_id, user_id, role)
            messagebox.showinfo("Hakediş", "Rol kaydedildi.")
        except Exception as exc:
            messagebox.showerror("Hakediş", f"Rol kaydedilemedi: {exc}")

    # -----------------
    # Poz tab
    # -----------------
    def _build_positions_tab(self):
        frm = ttk.Frame(self.tab_positions)
        frm.pack(fill=tk.X, padx=8, pady=8)

        ttk.Label(frm, text="Poz Kodu").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.ent_poz_kod = ttk.Entry(frm, width=16)
        self.ent_poz_kod.grid(row=0, column=1, padx=4, pady=4)

        ttk.Label(frm, text="Açıklama").grid(row=0, column=2, sticky="w", padx=4, pady=4)
        self.ent_poz_aciklama = ttk.Entry(frm, width=28)
        self.ent_poz_aciklama.grid(row=0, column=3, padx=4, pady=4)

        ttk.Label(frm, text="Birim").grid(row=1, column=0, sticky="w", padx=4, pady=4)
        self.ent_poz_birim = ttk.Entry(frm, width=10)
        self.ent_poz_birim.grid(row=1, column=1, padx=4, pady=4)

        ttk.Label(frm, text="Sözleşme Miktarı").grid(row=1, column=2, sticky="w", padx=4, pady=4)
        self.ent_poz_miktar = ttk.Entry(frm, width=12)
        self.ent_poz_miktar.grid(row=1, column=3, padx=4, pady=4)

        ttk.Label(frm, text="Birim Fiyat").grid(row=2, column=0, sticky="w", padx=4, pady=4)
        self.ent_poz_fiyat = ttk.Entry(frm, width=12)
        self.ent_poz_fiyat.grid(row=2, column=1, padx=4, pady=4)

        ttk.Button(frm, text="➕ Poz Ekle", command=self._on_poz_add).grid(row=2, column=3, sticky="e", padx=4, pady=4)

        self.positions_list = tk.Listbox(self.tab_positions, height=12)
        self.positions_list.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

    def _on_poz_add(self):
        project_id = self._selected_project_id()
        if not project_id:
            messagebox.showwarning("Hakediş", "Önce proje seçin.")
            return
        try:
            self.service.add_position(
                self._user_id(),
                project_id=project_id,
                kod=self.ent_poz_kod.get().strip(),
                aciklama=self.ent_poz_aciklama.get().strip(),
                birim=self.ent_poz_birim.get().strip(),
                sozlesme_miktar=float(self.ent_poz_miktar.get().strip() or 0),
                birim_fiyat=float(self.ent_poz_fiyat.get().strip() or 0),
            )
            self.refresh_positions()
        except Exception as exc:
            messagebox.showerror("Hakediş", f"Poz eklenemedi: {exc}")

    # -----------------
    # Dönem tab
    # -----------------
    def _build_periods_tab(self):
        frm = ttk.Frame(self.tab_periods)
        frm.pack(fill=tk.X, padx=8, pady=8)

        ttk.Label(frm, text="Hakediş No").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.ent_period_no = ttk.Entry(frm, width=12)
        self.ent_period_no.grid(row=0, column=1, padx=4, pady=4)

        ttk.Label(frm, text="Ay/Yıl").grid(row=0, column=2, sticky="w", padx=4, pady=4)
        self.ent_period_ay = ttk.Entry(frm, width=6)
        self.ent_period_ay.grid(row=0, column=3, padx=4, pady=4)
        self.ent_period_yil = ttk.Entry(frm, width=8)
        self.ent_period_yil.grid(row=0, column=4, padx=4, pady=4)

        ttk.Label(frm, text="Tarih Aralığı").grid(row=1, column=0, sticky="w", padx=4, pady=4)
        self.ent_period_bas = ttk.Entry(frm, width=12)
        self.ent_period_bas.grid(row=1, column=1, padx=4, pady=4)
        self.ent_period_bit = ttk.Entry(frm, width=12)
        self.ent_period_bit.grid(row=1, column=2, padx=4, pady=4)

        ttk.Button(frm, text="➕ Dönem Ekle", command=self._on_period_add).grid(row=1, column=4, sticky="e", padx=4, pady=4)

        self.periods_list = tk.Listbox(self.tab_periods, height=8)
        self.periods_list.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.periods_list.bind("<<ListboxSelect>>", lambda _e: self._on_period_select())

        metraj = ttk.LabelFrame(self.tab_periods, text="Metraj & Ataşman")
        metraj.pack(fill=tk.X, padx=8, pady=8)

        ttk.Label(metraj, text="Poz ID").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.ent_metraj_pos = ttk.Entry(metraj, width=10)
        self.ent_metraj_pos.grid(row=0, column=1, padx=4, pady=4)

        ttk.Label(metraj, text="Bu Dönem Miktar").grid(row=0, column=2, sticky="w", padx=4, pady=4)
        self.ent_metraj_miktar = ttk.Entry(metraj, width=10)
        self.ent_metraj_miktar.grid(row=0, column=3, padx=4, pady=4)

        ttk.Button(metraj, text="💾 Metraj Kaydet", command=self._on_metraj_save).grid(
            row=0, column=4, padx=4, pady=4
        )
        ttk.Button(metraj, text="📎 Ataşman Ekle", command=self._on_attachment_add).grid(
            row=0, column=5, padx=4, pady=4
        )

        self.lbl_period_summary = ttk.Label(self.tab_periods, text="Toplam: -")
        self.lbl_period_summary.pack(anchor="w", padx=10, pady=4)

    def _on_period_add(self):
        project_id = self._selected_project_id()
        if not project_id:
            messagebox.showwarning("Hakediş", "Önce proje seçin.")
            return
        try:
            self.service.add_period(
                self._user_id(),
                project_id=project_id,
                hakedis_no=self.ent_period_no.get().strip(),
                ay=int(self.ent_period_ay.get().strip() or 1),
                yil=int(self.ent_period_yil.get().strip() or 2024),
                tarih_bas=self.ent_period_bas.get().strip(),
                tarih_bit=self.ent_period_bit.get().strip(),
                status="Taslak",
            )
            self.refresh_periods()
        except Exception as exc:
            messagebox.showerror("Hakediş", f"Dönem eklenemedi: {exc}")

    def _on_period_select(self):
        pid = self._selected_period_id()
        if pid:
            summary = self.service.period_summary(pid)
            self.lbl_period_summary.config(
                text=f"Bu Dönem: {fmt_amount(summary['this_total'])} | Önceki: {fmt_amount(summary['previous_total'])}"
            )

    def _on_metraj_save(self):
        period_id = self._selected_period_id()
        if not period_id:
            messagebox.showwarning("Hakediş", "Önce hakediş dönemi seçin.")
            return
        try:
            pos_id = int(self.ent_metraj_pos.get().strip())
            miktar = float(self.ent_metraj_miktar.get().strip() or 0)
            self.service.record_measurement(self._user_id(), period_id, pos_id, miktar)
            self._on_period_select()
        except Exception as exc:
            messagebox.showerror("Hakediş", f"Metraj kaydedilemedi: {exc}")

    def _on_attachment_add(self):
        period_id = self._selected_period_id()
        if not period_id:
            messagebox.showwarning("Hakediş", "Önce hakediş dönemi seçin.")
            return
        paths = filedialog.askopenfilenames(title="Ataşman seç")
        if not paths:
            return
        try:
            for path in paths:
                self.service.save_attachment(period_id, path)
            messagebox.showinfo("Hakediş", "Ataşman(lar) kaydedildi.")
        except Exception as exc:
            messagebox.showerror("Hakediş", f"Ataşman eklenemedi: {exc}")

    # -----------------
    # Endeks tab
    # -----------------
    def _build_indices_tab(self):
        frm = ttk.Frame(self.tab_indices)
        frm.pack(fill=tk.X, padx=8, pady=8)

        ttk.Label(frm, text="Endeks Setleri").pack(anchor="w")
        self.index_vars: Dict[str, tk.IntVar] = {}
        for key in DEFAULT_INDEX_SETS:
            var = tk.IntVar(value=0)
            chk = ttk.Checkbutton(frm, text=key, variable=var)
            chk.pack(anchor="w", padx=6)
            self.index_vars[key] = var

        btns = ttk.Frame(frm)
        btns.pack(anchor="w", pady=8)
        ttk.Button(btns, text="💾 Seçimleri Kaydet", command=self._on_index_save).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="🔄 Endeksleri Çek (Arka Plan)", command=self._on_indices_fetch).pack(
            side=tk.LEFT, padx=4
        )

        self.lbl_indices_status = ttk.Label(frm, text="Durum: -")
        self.lbl_indices_status.pack(anchor="w", pady=4)

        self.indices_list = tk.Listbox(self.tab_indices, height=8)
        self.indices_list.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

    def _on_index_save(self):
        project_id = self._selected_project_id()
        if not project_id:
            messagebox.showwarning("Hakediş", "Önce proje seçin.")
            return
        selections = {k: bool(v.get()) for k, v in self.index_vars.items()}
        self.service.set_index_selections(project_id, selections)
        self.lbl_indices_status.config(text="Durum: Seçimler kaydedildi")

    def _on_indices_fetch(self):
        project_id = self._selected_project_id()
        if not project_id:
            messagebox.showwarning("Hakediş", "Önce proje seçin.")
            return
        selected = self.service.get_selected_index_sets(project_id)
        if not selected:
            messagebox.showwarning("Hakediş", "En az bir endeks seti seçin.")
            return

        def worker():
            try:
                indices = self.service.fetch_indices_with_cache(selected)
                rows = self.service.calculate_price_difference(indices)
                self.indices_list.delete(0, tk.END)
                for row in rows:
                    self.indices_list.insert(
                        tk.END,
                        f"{row.dataset}: {row.base_value:.2f} → {row.current_value:.2f} | Katsayı={row.coefficient:.4f}",
                    )
                self.lbl_indices_status.config(text="Durum: Endeksler güncellendi")
            except Exception as exc:
                self.lbl_indices_status.config(text=f"Durum: {exc}")

        threading.Thread(target=worker, daemon=True).start()

    def _load_index_selections(self):
        project_id = self._selected_project_id()
        if not project_id:
            return
        rows = self.service.repo.list_index_selections(project_id)
        selected = {str(r["dataset_key"]): int(r["enabled"] or 0) for r in rows}
        for key, var in self.index_vars.items():
            var.set(1 if selected.get(key) == 1 else 0)

    # -----------------
    # Rapor tab
    # -----------------
    def _build_reports_tab(self):
        frm = ttk.Frame(self.tab_reports)
        frm.pack(fill=tk.X, padx=8, pady=8)

        ttk.Label(frm, text="Hakediş Dönemi ID").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.ent_report_period = ttk.Entry(frm, width=12)
        self.ent_report_period.grid(row=0, column=1, padx=4, pady=4)

        ttk.Button(frm, text="📤 Rapor Üret (Arka Plan)", command=self._on_report_export).grid(
            row=0, column=2, padx=4, pady=4
        )

        self.lbl_report_status = ttk.Label(frm, text="Durum: -")
        self.lbl_report_status.grid(row=1, column=0, columnspan=3, sticky="w", padx=4, pady=4)

        if not HAS_OPENPYXL:
            ttk.Label(frm, text="Not: Excel export için openpyxl yüklenmeli.").grid(
                row=2, column=0, columnspan=3, sticky="w", padx=4, pady=4
            )

    def _on_report_export(self):
        try:
            period_id = int(self.ent_report_period.get().strip())
        except Exception:
            messagebox.showwarning("Hakediş", "Geçerli dönem ID girin.")
            return
        directory = filedialog.askdirectory(title="Rapor klasörü seç")
        if not directory:
            return

        def worker():
            try:
                self.service.export_reports(period_id, directory)
                self.lbl_report_status.config(text="Durum: Raporlar oluşturuldu")
            except Exception as exc:
                self.lbl_report_status.config(text=f"Durum: {exc}")

        threading.Thread(target=worker, daemon=True).start()

    # -----------------
    # Helpers
    # -----------------
    def _user_id(self) -> Optional[int]:
        try:
            return int(self.app.user["id"])
        except Exception:
            return None

    def _selected_project_id(self) -> Optional[int]:
        sel = self.project_list.curselection()
        if not sel:
            return None
        value = self.project_list.get(sel[0])
        try:
            return int(value.split("#")[1].strip())
        except Exception:
            return None

    def _selected_period_id(self) -> Optional[int]:
        sel = self.periods_list.curselection()
        if not sel:
            return None
        value = self.periods_list.get(sel[0])
        try:
            return int(value.split("#")[1].strip())
        except Exception:
            return None

    def refresh_projects(self):
        self.project_list.delete(0, tk.END)
        for row in self.service.repo.list_projects():
            self.project_list.insert(tk.END, f"{row['isin_adi']} (# {row['id']})")

    def refresh_positions(self):
        self.positions_list.delete(0, tk.END)
        project_id = self._selected_project_id()
        if not project_id:
            return
        for row in self.service.repo.list_positions(project_id):
            self.positions_list.insert(
                tk.END,
                f"{row['kod']} | {row['aciklama']} | {row['birim']} | {fmt_amount(row['birim_fiyat'])}",
            )

    def refresh_periods(self):
        self.periods_list.delete(0, tk.END)
        project_id = self._selected_project_id()
        if not project_id:
            return
        for row in self.service.repo.list_periods(project_id):
            self.periods_list.insert(
                tk.END,
                f"{row['hakedis_no']} ({row['ay']:02d}/{row['yil']}) [{row['status']}] (# {row['id']})",
            )

    def refresh_all(self):
        self.refresh_projects()
        self.refresh_positions()
        self.refresh_periods()
        self._load_index_selections()
