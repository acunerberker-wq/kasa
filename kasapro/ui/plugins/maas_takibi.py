# -*- coding: utf-8 -*-
"""UI Plugin: Şirket Maaş Takibi.

İstek:
- Çalışan maaşları ayrı bir ekranda tutulsun
- Bulunulan ay için "Ödendi/Ödenmedi" takibi yapılsın
- Önceki aylar "Maaş Geçmişi" sekmesinde listelensin
- Aylık toplam raporu alınsın

Not:
- Bu modül maaş kayıtlarını şirket DB'sinde `maas_calisan` ve `maas_odeme` tablolarında saklar.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional, Dict, Any, Tuple, TYPE_CHECKING

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from ...config import APP_TITLE, HAS_OPENPYXL
from ...utils import today_iso, fmt_amount, safe_float
from ...core.fuzzy import best_substring_similarity, amount_score, combine_scores, combine3_scores, normalize_text
from ..windows.import_wizard import ImportWizard
from ..windows import BankaWorkspaceWindow
from ..base import BaseView
from ..widgets import LabeledEntry, LabeledCombo, MoneyEntry

if TYPE_CHECKING:
    from ...app import App

PLUGIN_META = {
    "key": "maas_takibi",
    "nav_text": "💼 Maaş Takibi",
    "page_title": "Şirket Maaş Takibi",
    "order": 34,
}


def _current_period() -> str:
    return date.today().strftime("%Y-%m")


class MaasTakibiFrame(BaseView):
    def __init__(self, master, app: "App"):
        self.app = app
        super().__init__(master, app)

        self._selected_employee_id: Optional[int] = None
        self._selected_payment_id: Optional[int] = None

        self.build_ui()

    def build_ui(self) -> None:
        self._build()

    # -----------------
    # UI
    # -----------------
    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=10, pady=(10, 6))
        self.lbl_period = ttk.Label(top, text="")
        self.lbl_period.pack(side=tk.LEFT)
        ttk.Button(top, text="Bu Ayı Yenile", command=self._ensure_and_refresh_current).pack(side=tk.LEFT, padx=10)
        self.lbl_summary = ttk.Label(top, text="")
        self.lbl_summary.pack(side=tk.LEFT, padx=(10, 0))

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.tab_employees = ttk.Frame(self.nb)
        self.tab_current = ttk.Frame(self.nb)
        self.tab_match = ttk.Frame(self.nb)
        # Maaş Eklentileri -> Maaş Takibi içine taşındı
        self.tab_scan = ttk.Frame(self.nb)
        self.tab_account = ttk.Frame(self.nb)
        self.tab_history = ttk.Frame(self.nb)
        self.tab_reports = ttk.Frame(self.nb)

        self.nb.add(self.tab_employees, text="👥 Çalışanlar")
        self.nb.add(self.tab_current, text="📌 Bu Ay")
        self.nb.add(self.tab_match, text="🧩 Excel & Eşleştirme")
        self.nb.add(self.tab_scan, text="💼 Bankada Maaş Bul")
        self.nb.add(self.tab_account, text="🧾 Hesap Hareketleri")
        self.nb.add(self.tab_history, text="🗂️ Maaş Geçmişi")
        self.nb.add(self.tab_reports, text="📊 Aylık Rapor")

        self._build_employees(self.tab_employees)
        self._build_current(self.tab_current)
        self._build_match(self.tab_match)
        self._build_scan(self.tab_scan)
        self._build_account(self.tab_account)
        self._build_history(self.tab_history)
        self._build_reports(self.tab_reports)

        self.nb.bind("<<NotebookTabChanged>>", lambda _e: self._on_tab_change())

        self.refresh_all()

    # -----------------
    # Tabs
    # -----------------
    def _build_employees(self, parent: ttk.Frame):
        box = ttk.LabelFrame(parent, text="Çalışan Tanımları")
        box.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        form = ttk.Frame(box)
        form.pack(fill=tk.X, padx=6, pady=6)

        self.e_ad = LabeledEntry(form, "Ad Soyad:", 26)
        self.e_ad.pack(side=tk.LEFT, padx=6)

        self.e_tutar = MoneyEntry(form, "Aylık Maaş:")
        self.e_tutar.pack(side=tk.LEFT, padx=6)

        self.e_para = LabeledCombo(form, "Para:", self.app.db.list_currencies(), 8)
        self.e_para.pack(side=tk.LEFT, padx=6)
        self.e_para.set("TL")

        # Meslekler
        self._meslek_name_to_id: dict[str, int] = {}
        self.e_meslek = LabeledCombo(form, "Meslek:", ["(Yok)"], 18)
        self.e_meslek.pack(side=tk.LEFT, padx=6)
        self.e_meslek.set("(Yok)")
        ttk.Button(form, text="Meslekler…", command=self._open_meslek_manager).pack(side=tk.LEFT, padx=(0, 6))

        ttk.Label(form, text="Durum:").pack(side=tk.LEFT, padx=(10, 2))
        self.cmb_emp_durum = ttk.Combobox(form, values=["Aktif", "Aktif değil"], state="readonly", width=10)
        self.cmb_emp_durum.pack(side=tk.LEFT, padx=(0, 10))
        self.cmb_emp_durum.set("Aktif")

        self.e_notlar = LabeledEntry(form, "Not:", 24)
        self.e_notlar.pack(side=tk.LEFT, padx=6)

        btns = ttk.Frame(box)
        btns.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Button(btns, text="Kaydet", command=self.save_employee).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Yeni", command=self.clear_employee_form).pack(side=tk.LEFT, padx=6)
        self.btn_emp_del = ttk.Button(btns, text="Sil", command=self.delete_employee)
        self.btn_emp_del.pack(side=tk.LEFT, padx=6)
        self.lbl_emp_mode = ttk.Label(btns, text="")
        self.lbl_emp_mode.pack(side=tk.LEFT, padx=10)

        cols = ("id", "ad", "meslek", "aylik", "para", "aktif", "notlar")
        self.emp_tree = ttk.Treeview(box, columns=cols, show="headings", height=14, selectmode="browse")
        for c in cols:
            self.emp_tree.heading(c, text=c.upper())
        self.emp_tree.column("id", width=55, anchor="center")
        self.emp_tree.column("ad", width=220)
        self.emp_tree.column("meslek", width=160)
        self.emp_tree.column("aylik", width=120, anchor="e")
        self.emp_tree.column("para", width=55, anchor="center")
        self.emp_tree.column("aktif", width=70, anchor="center")
        self.emp_tree.column("notlar", width=400)
        self.emp_tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.emp_tree.bind("<Double-1>", lambda _e: self.load_selected_employee())

    def _build_current(self, parent: ttk.Frame):
        box = ttk.LabelFrame(parent, text="Bulunulan Ay Maaşları")
        box.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        row = ttk.Frame(box)
        row.pack(fill=tk.X, padx=6, pady=6)
        self.cur_date = LabeledEntry(row, "Ödeme Tarihi:", 12)
        self.cur_date.pack(side=tk.LEFT, padx=6)
        self.cur_date.set(today_iso())

        ttk.Button(row, text="Bugün", command=lambda: self.cur_date.set(today_iso())).pack(side=tk.LEFT, padx=6)
        ttk.Button(row, text="Ödendi Yap", command=lambda: self.set_paid_selected(1)).pack(side=tk.LEFT, padx=6)
        ttk.Button(row, text="Ödenmedi Yap", command=lambda: self.set_paid_selected(0)).pack(side=tk.LEFT, padx=6)
        ttk.Button(row, text="Yenile", command=self.refresh_current).pack(side=tk.LEFT, padx=6)

        cols = ("id", "calisan", "tutar", "para", "odendi", "odeme_tarihi", "aciklama")
        self.cur_tree = ttk.Treeview(box, columns=cols, show="headings", height=14, selectmode="browse")
        for c in cols:
            self.cur_tree.heading(c, text=c.upper())
        self.cur_tree.column("id", width=55, anchor="center")
        self.cur_tree.column("calisan", width=220)
        self.cur_tree.column("tutar", width=120, anchor="e")
        self.cur_tree.column("para", width=55, anchor="center")
        self.cur_tree.column("odendi", width=90, anchor="center")
        self.cur_tree.column("odeme_tarihi", width=110)
        self.cur_tree.column("aciklama", width=420)
        self.cur_tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.cur_tree.bind("<<TreeviewSelect>>", lambda _e: self._on_select_current())

    def _build_match(self, parent: ttk.Frame):
        """Excel içe aktarma + banka hareketleri ile eşleştirme."""

        box = ttk.LabelFrame(parent, text="Excel İçe Aktarma ve Banka Eşleştirme")
        box.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        top = ttk.Frame(box)
        top.pack(fill=tk.X, padx=6, pady=6)

        self.m_period = LabeledCombo(top, "Dönem:", ["(Seç)"] + self._period_candidates(), 10)
        self.m_period.pack(side=tk.LEFT, padx=6)
        self.m_period.set(_current_period())
        try:
            self.m_period.cmb.bind("<<ComboboxSelected>>", lambda _e: self._sync_match_date_range())
        except Exception:
            pass

        self.btn_maas_excel = ttk.Button(top, text="📥 Maaş Exceli İçe Aktar", command=self.import_maas_excel)
        self.btn_maas_excel.pack(side=tk.LEFT, padx=6)

        ttk.Separator(top, orient="vertical").pack(side=tk.LEFT, fill=tk.Y, padx=10)

        # Banka aralığı varsayılan: seçili dönemin ayı
        self.m_from = LabeledEntry(top, "Banka Başlangıç:", 12)
        self.m_from.pack(side=tk.LEFT, padx=6)
        self.m_to = LabeledEntry(top, "Banka Bitiş:", 12)
        self.m_to.pack(side=tk.LEFT, padx=6)

        self.var_m_only_unpaid = tk.BooleanVar(value=True)
        ttk.Checkbutton(top, text="Sadece ödenmemiş", variable=self.var_m_only_unpaid).pack(side=tk.LEFT, padx=6)

        self.m_min_score = LabeledEntry(top, "Skor eşiği:", 6)
        self.m_min_score.pack(side=tk.LEFT, padx=6)
        self.m_min_score.set("0.78")

        self.m_abs_tol = LabeledEntry(top, "± TL:", 6)
        self.m_abs_tol.pack(side=tk.LEFT, padx=6)
        self.m_abs_tol.set("2")

        ttk.Button(top, text="🔎 Öner", command=self.suggest_salary_matches).pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text="✅ Seçili Uygula", command=self.apply_selected_matches).pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text="🧹 Bağı Temizle", command=self.clear_selected_links).pack(side=tk.LEFT, padx=6)

        # Tree
        cols = (
            "pid",
            "calisan",
            "tutar",
            "para",
            "odendi",
            "banka_id",
            "banka_tarih",
            "banka_tutar",
            "banka_aciklama",
            "score",
        )
        self.m_tree = ttk.Treeview(box, columns=cols, show="headings", height=16, selectmode="extended")
        for c in cols:
            self.m_tree.heading(c, text=c.upper())
        self.m_tree.column("pid", width=55, anchor="center")
        self.m_tree.column("calisan", width=200)
        self.m_tree.column("tutar", width=110, anchor="e")
        self.m_tree.column("para", width=55, anchor="center")
        self.m_tree.column("odendi", width=70, anchor="center")
        self.m_tree.column("banka_id", width=70, anchor="center")
        self.m_tree.column("banka_tarih", width=100)
        self.m_tree.column("banka_tutar", width=110, anchor="e")
        self.m_tree.column("banka_aciklama", width=420)
        self.m_tree.column("score", width=70, anchor="center")
        self.m_tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # Renklendirme
        try:
            self.m_tree.tag_configure("ok", background="#D1FAE5")
            self.m_tree.tag_configure("warn", background="#FEF3C7")
            self.m_tree.tag_configure("no", background="#FEE2E2")
        except Exception:
            pass

        # Varsayılan tarih aralıklarını doldur
        self._sync_match_date_range()


    # -----------------
    # Tab: Bankada Maaş Bul (Maaş Eklentileri'nden taşındı)
    # -----------------
    def _build_scan(self, parent: ttk.Frame):
        box = ttk.LabelFrame(parent, text="Banka Çalışma Alanı - Maaş Tarama")
        box.pack(fill=tk.X, padx=6, pady=6)

        row = ttk.Frame(box)
        row.pack(fill=tk.X, padx=6, pady=8)

        self.s_from = LabeledEntry(row, "Başlangıç:", 12)
        self.s_from.pack(side=tk.LEFT, padx=6)
        self.s_to = LabeledEntry(row, "Bitiş:", 12)
        self.s_to.pack(side=tk.LEFT, padx=6)

        ttk.Button(row, text="Bu Ay", command=self._scan_this_month).pack(side=tk.LEFT, padx=6)
        ttk.Button(row, text="Son 30 gün", command=self._scan_last30).pack(side=tk.LEFT, padx=6)

        ttk.Separator(row, orient="vertical").pack(side=tk.LEFT, fill=tk.Y, padx=10)

        ttk.Button(row, text="🧾 Çalışma Alanını Aç", command=lambda: self._open_bank_workspace(auto_run=False)).pack(
            side=tk.LEFT, padx=6
        )
        ttk.Button(row, text="💼 Aç + Maaşları Bul", command=lambda: self._open_bank_workspace(auto_run=True)).pack(
            side=tk.LEFT, padx=6
        )

        info = ttk.Label(
            parent,
            text=(
                "Not: 'Maaşları Bul' taraması banka açıklamalarında çalışan isimlerini (fuzzy) arar.\n"
                "Büyük/küçük harf, Türkçe karakter ve küçük yazım hatalarına toleranslıdır."
            ),
        )
        info.pack(anchor="w", padx=12, pady=(6, 0))

        self._scan_this_month()

    def _scan_this_month(self):
        today = date.today()
        start = today.replace(day=1)
        if start.month == 12:
            end = date(start.year + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(start.year, start.month + 1, 1) - timedelta(days=1)
        try:
            self.s_from.set(start.isoformat())
            self.s_to.set(end.isoformat())
        except Exception:
            pass

    def _scan_last30(self):
        today = date.today()
        start = today - timedelta(days=30)
        try:
            self.s_from.set(start.isoformat())
            self.s_to.set(today.isoformat())
        except Exception:
            pass

    def _open_bank_workspace(self, *, auto_run: bool):
        s_from = getattr(self, "s_from", None)
        s_to = getattr(self, "s_to", None)
        date_from = s_from.get().strip() if isinstance(s_from, tk.StringVar) else ""
        date_to = s_to.get().strip() if isinstance(s_to, tk.StringVar) else ""

        flt = {
            "q": "",
            "tip": "Çıkış",
            "banka": "",
            "hesap": "",
            "import_grup": "(Tümü)",
            "date_from": date_from,
            "date_to": date_to,
        }

        w = BankaWorkspaceWindow(self.app, ids=None, initial_filters=flt, title_suffix="Maaş Tarama")
        if auto_run:
            try:
                w.after(250, w.macro_find_salary)
            except Exception:
                pass




    def _build_account(self, parent: ttk.Frame):
        """Maaş eşleştirme geçmişi / hesap hareketleri kayıtları."""
        box = ttk.LabelFrame(parent, text="Maaş Geçmişi / Hesap Hareketleri")
        box.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        top = ttk.Frame(box)
        top.pack(fill=tk.X, padx=6, pady=6)

        self.a_period = LabeledCombo(top, "Dönem:", ["(Seç)"] + self._period_candidates(), 10)
        self.a_period.pack(side=tk.LEFT, padx=6)
        self.a_period.set(_current_period())

        self.a_from = LabeledEntry(top, "Tarih Başlangıç:", 12)
        self.a_from.pack(side=tk.LEFT, padx=6)
        self.a_to = LabeledEntry(top, "Tarih Bitiş:", 12)
        self.a_to.pack(side=tk.LEFT, padx=6)

        self.a_q = LabeledEntry(top, "Ara:", 18)
        self.a_q.pack(side=tk.LEFT, padx=6)

        ttk.Button(top, text="Yenile", command=self.refresh_account).pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text="Temizle (Dönem)", command=self.clear_account_period).pack(side=tk.LEFT, padx=6)

        # varsayılan tarih aralığı
        try:
            s, e = self._period_to_range(_current_period())
            self.a_from.set(s)
            self.a_to.set(e)
        except Exception:
            pass

        cols = (
            "id",
            "created_at",
            "calisan",
            "donem",
            "banka_id",
            "banka_tarih",
            "banka_tutar",
            "banka_aciklama",
            "skor",
            "eslesme",
            "odeme_id",
            "odendi",
        )
        self.a_tree = ttk.Treeview(box, columns=cols, show="headings", height=14, selectmode="browse")
        for c in cols:
            self.a_tree.heading(c, text=c.upper())

        self.a_tree.column("id", width=55, anchor="center")
        self.a_tree.column("created_at", width=130)
        self.a_tree.column("calisan", width=200)
        self.a_tree.column("donem", width=90, anchor="center")
        self.a_tree.column("banka_id", width=75, anchor="center")
        self.a_tree.column("banka_tarih", width=110)
        self.a_tree.column("banka_tutar", width=110, anchor="e")
        self.a_tree.column("banka_aciklama", width=520)
        self.a_tree.column("skor", width=60, anchor="center")
        self.a_tree.column("eslesme", width=120)
        self.a_tree.column("odeme_id", width=75, anchor="center")
        self.a_tree.column("odendi", width=90, anchor="center")

        self.a_tree.tag_configure("ok", foreground="")
        self.a_tree.tag_configure("warn", foreground="")
        self.a_tree.tag_configure("no", foreground="gray")

        self.a_tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.a_tree.bind("<Double-1>", lambda _e: self._show_account_row_detail())

    def _show_account_row_detail(self):
        sel = self.a_tree.selection()
        if not sel:
            return
        vals = self.a_tree.item(sel[0], "values")
        if not vals:
            return
        try:
            msg = (
                f"Çalışan: {vals[2]}\n"
                f"Dönem: {vals[3]}\n"
                f"Banka ID: {vals[4]}\n"
                f"Tarih: {vals[5]}\n"
                f"Tutar: {vals[6]}\n"
                f"Açıklama: {vals[7]}\n"
                f"Skor: {vals[8]} ({vals[9]})"
            )
        except Exception:
            msg = str(vals)
        messagebox.showinfo(APP_TITLE, msg)

    def refresh_account(self):
        # tree temizle
        try:
            for i in self.a_tree.get_children():
                self.a_tree.delete(i)
        except Exception:
            return

        per = (self.a_period.get() or "").strip()
        if not per or per == "(Seç)":
            per = _current_period()

        date_from = (self.a_from.get() or "").strip()
        date_to = (self.a_to.get() or "").strip()
        if not date_from or not date_to:
            date_from, date_to = self._period_to_range(per)

        q = (self.a_q.get() or "").strip()

        try:
            rows = self.app.db.maas_hesap_hareket_list(donem=per, q=q, date_from=date_from, date_to=date_to, limit=8000, include_inactive=True)  # type: ignore
        except Exception:
            rows = []

        for r in rows or []:
            try:
                rid = int(r["id"])
                created_at = str(r["created_at"] or "")
                calisan = str(r["calisan_ad"] or "")
                donem = str(r["donem"] or "")
                bank_id = int(r["banka_hareket_id"])
                btarih = str(r["banka_tarih"] or "")
                btutar = fmt_amount(float(r["banka_tutar"] or 0))
                baciklama = str(r["banka_aciklama"] or "")
                skor = float(r["match_score"] or 0)
                eslesme = str(r["match_type"] or "")
                oid = r["odeme_id"]
                odeme_id = ("" if oid is None else int(oid))
                odendi = "Ödendi" if int(r["maas_odendi"] or 0) == 1 else "Ödenmedi"
            except Exception:
                continue

            tag = "ok" if skor >= 0.87 else ("warn" if skor >= 0.78 else "no")
            self.a_tree.insert(
                "",
                "end",
                values=(rid, created_at, calisan, donem, bank_id, btarih, btutar, baciklama, ("" if skor <= 0 else f"{skor:.2f}"), eslesme, odeme_id, odendi),
                tags=(tag,),
            )

    def clear_account_period(self):
        per = (self.a_period.get() or "").strip()
        if not per or per == "(Seç)":
            per = _current_period()
        if not messagebox.askyesno(APP_TITLE, f"{per} dönemi hesap hareketi geçmişi silinsin mi?"):
            return
        try:
            n = int(self.app.db.maas_hesap_hareket_clear_donem(per) or 0)  # type: ignore
        except Exception:
            n = 0
        messagebox.showinfo(APP_TITLE, f"Silindi: {n} kayıt")
        self.refresh_account()
    def _build_history(self, parent: ttk.Frame):
        box = ttk.LabelFrame(parent, text="Maaş Geçmişi")
        box.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        row = ttk.Frame(box)
        row.pack(fill=tk.X, padx=6, pady=6)

        self.h_period = LabeledCombo(row, "Dönem:", ["(Seç)"] + self._period_candidates(), 10)
        self.h_period.pack(side=tk.LEFT, padx=6)
        self.h_q = LabeledEntry(row, "Ara:", 22)
        self.h_q.pack(side=tk.LEFT, padx=6)
        self.h_paid = LabeledCombo(row, "Durum:", ["(Tümü)", "Ödendi", "Ödenmedi"], 10)
        self.h_paid.pack(side=tk.LEFT, padx=6)
        self.h_paid.set("(Tümü)")
        ttk.Button(row, text="Yenile", command=self.refresh_history).pack(side=tk.LEFT, padx=6)

        cols = ("donem", "calisan", "tutar", "para", "odendi", "odeme_tarihi", "aciklama")
        self.h_tree = ttk.Treeview(box, columns=cols, show="headings", height=14, selectmode="browse")
        for c in cols:
            self.h_tree.heading(c, text=c.upper())
        self.h_tree.column("donem", width=90, anchor="center")
        self.h_tree.column("calisan", width=220)
        self.h_tree.column("tutar", width=120, anchor="e")
        self.h_tree.column("para", width=55, anchor="center")
        self.h_tree.column("odendi", width=90, anchor="center")
        self.h_tree.column("odeme_tarihi", width=110)
        self.h_tree.column("aciklama", width=460)
        self.h_tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

    def _build_reports(self, parent: ttk.Frame):
        top = ttk.Frame(parent)
        top.pack(fill=tk.X, padx=6, pady=6)

        self.r_period = LabeledCombo(top, "Dönem:", self._period_candidates(), 10)
        self.r_period.pack(side=tk.LEFT, padx=6)
        self.r_period.set(_current_period())
        ttk.Button(top, text="Hesapla", command=self.refresh_reports).pack(side=tk.LEFT, padx=6)

        self.r_txt = tk.Text(parent, height=6)
        self.r_txt.pack(fill=tk.X, padx=6, pady=(0, 6))

        box = ttk.LabelFrame(parent, text="Aylık Toplamlar (Son 24 Ay)")
        box.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        cols = ("donem", "toplam", "odenen", "odenmeyen")
        self.r_tree = ttk.Treeview(box, columns=cols, show="headings", height=12, selectmode="browse")
        for c in cols:
            self.r_tree.heading(c, text=c.upper())
        self.r_tree.column("donem", width=90, anchor="center")
        self.r_tree.column("toplam", width=140, anchor="e")
        self.r_tree.column("odenen", width=140, anchor="e")
        self.r_tree.column("odenmeyen", width=140, anchor="e")
        self.r_tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.r_tree.bind("<Double-1>", lambda _e: self._jump_period_from_report())

    # -----------------
    # Helpers
    # -----------------
    def _period_candidates(self) -> list[str]:
        """Son 36 ay + DB'den gelen dönemler."""
        # son 36 ay
        out: list[str] = []
        today = date.today()
        y, m = today.year, today.month
        for i in range(0, 36):
            yy = y
            mm = m - i
            while mm <= 0:
                mm += 12
                yy -= 1
            out.append(f"{yy:04d}-{mm:02d}")

        # DB'den ek dönemler
        try:
            existing = self.app.db.maas_donem_list(limit=60)  # type: ignore
            for p in existing:
                if p and p not in out:
                    out.append(p)
        except Exception:
            pass
        return out

    def _on_tab_change(self):
        # dönem listeleri güncel kalsın
        try:
            self.h_period.cmb["values"] = ["(Seç)"] + self._period_candidates()
        except Exception:
            pass
        try:
            self.a_period.cmb["values"] = ["(Seç)"] + self._period_candidates()
        except Exception:
            pass
        try:
            self.r_period.cmb["values"] = self._period_candidates()
        except Exception:
            pass

        idx = int(self.nb.index("current"))
        if idx == 1:
            self._ensure_and_refresh_current()
        elif idx == 2:
            self._sync_match_date_range()
        elif idx == 3:
            self.refresh_account()
        elif idx == 4:
            self.refresh_history()
        elif idx == 5:
            self.refresh_reports()

    def refresh_all(self):
        self.lbl_period.config(text=f"Aktif Dönem: {_current_period()}")
        self.refresh_employees()
        self._ensure_and_refresh_current()
        self.refresh_account()
        self.refresh_history()
        self.refresh_reports()

    # -----------------
    # Çalışanlar
    # -----------------
    def clear_employee_form(self):
        self._selected_employee_id = None
        self.e_ad.set("")
        self.e_tutar.set("")
        self.e_para.set("TL")
        try:
            self._refresh_meslek_options()
            self.e_meslek.set("(Yok)")
        except Exception:
            pass
        try:
            self.cmb_emp_durum.set("Aktif")
        except Exception:
            pass
        self.e_notlar.set("")
        self.lbl_emp_mode.config(text="Yeni")

    def refresh_employees(self):
        for i in self.emp_tree.get_children():
            self.emp_tree.delete(i)
        self._refresh_meslek_options()
        try:
            rows = self.app.db.maas_calisan_list()  # type: ignore
        except Exception:
            rows = []
        for r in rows:
            aktif = 'Aktif' if int(r['aktif'] or 0) == 1 else 'Aktif değil'
            try:
                meslek = str(r["meslek_ad"] or "")
            except Exception:
                meslek = ""
            self.emp_tree.insert(
                "", "end",
                values=(
                    int(r["id"]),
                    str(r["ad"]),
                    meslek,
                    fmt_amount(float(r["aylik_tutar"] or 0)),
                    str(r["para"] or "TL"),
                    aktif,
                    str(r["notlar"] or ""),
                ),
            )

    def _refresh_meslek_options(self):
        """Meslek combobox seçeneklerini DB'den yeniler."""
        self._meslek_name_to_id = {}
        opts = ["(Yok)"]
        try:
            rows = self.app.db.maas_meslek_list(only_active=True)  # type: ignore
        except Exception:
            rows = []
        for r in rows:
            try:
                name = str(r["ad"] or "").strip()
                if not name:
                    continue
                self._meslek_name_to_id[name] = int(r["id"])
                opts.append(name)
            except Exception:
                continue
        try:
            cur = (self.e_meslek.get() or "").strip()
        except Exception:
            cur = ""
        try:
            self.e_meslek.cmb["values"] = opts
            if cur and cur in opts:
                self.e_meslek.set(cur)
            else:
                if cur and cur != "(Yok)" and cur not in opts:
                    self.e_meslek.set("(Yok)")
        except Exception:
            pass

    def _open_meslek_manager(self):
        """Basit meslek yönetimi penceresi."""
        win = tk.Toplevel(self)
        win.title(f"{APP_TITLE} - Meslekler")
        win.geometry("720x420")

        frm = ttk.Frame(win)
        frm.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        top = ttk.LabelFrame(frm, text="Meslek Tanımı")
        top.pack(fill=tk.X, pady=(0, 8))

        e_ad = LabeledEntry(top, "Meslek:", 28)
        e_ad.pack(side=tk.LEFT, padx=6, pady=6)
        ttk.Label(top, text="Durum:").pack(side=tk.LEFT, padx=(6, 2))
        cmb_durum = ttk.Combobox(top, values=["Aktif", "Aktif değil"], state="readonly", width=10)
        cmb_durum.pack(side=tk.LEFT, padx=6)
        cmb_durum.set("Aktif")
        e_not = LabeledEntry(top, "Not:", 28)
        e_not.pack(side=tk.LEFT, padx=6, pady=6)

        selected_mid: dict[str, Optional[int]] = {"id": None}

        def refresh():
            for iid in tree.get_children():
                tree.delete(iid)
            try:
                rows = self.app.db.maas_meslek_list()  # type: ignore
            except Exception:
                rows = []
            for r in rows:
                aktif = 'Aktif' if int(r['aktif'] or 0) == 1 else 'Aktif değil'
                try:
                    notlar = str(r["notlar"] or "")
                except Exception:
                    notlar = ""
                tree.insert("", "end", values=(int(r["id"]), str(r["ad"]), aktif, notlar))
            self._refresh_meslek_options()

        def clear_form():
            selected_mid["id"] = None
            e_ad.set("")
            try:
                cmb_durum.set('Aktif')
            except Exception:
                pass
            e_not.set("")

        def on_select(_e=None):
            sel = tree.selection()
            if not sel:
                return
            vals = tree.item(sel[0], "values")
            if not vals:
                return
            try:
                selected_mid["id"] = int(vals[0])
            except Exception:
                selected_mid["id"] = None
                return
            e_ad.set(str(vals[1] or ""))
            try:
                cmb_durum.set(str(vals[2]) or 'Aktif')
            except Exception:
                pass
            e_not.set(str(vals[3] or ""))

        def save():
            name = (e_ad.get() or "").strip()
            if not name:
                messagebox.showerror(APP_TITLE, "Meslek adı boş olamaz.")
                return
            aktif = 1 if (cmb_durum.get() or '').strip() == 'Aktif' else 0
            notlar = (e_not.get() or "").strip()
            try:
                if selected_mid["id"]:
                    self.app.db.maas_meslek_update(int(selected_mid["id"]), name, aktif=aktif, notlar=notlar)  # type: ignore
                else:
                    self.app.db.maas_meslek_add(name, aktif=aktif, notlar=notlar)  # type: ignore
            except Exception as ex:
                messagebox.showerror(APP_TITLE, f"Kaydetme başarısız: {ex}")
                return
            clear_form()
            refresh()

        def delete():
            if not selected_mid["id"]:
                messagebox.showinfo(APP_TITLE, "Silmek için meslek seç.")
                return
            if not messagebox.askyesno(APP_TITLE, "Seçili meslek silinsin mi? (Çalışanlardan bağı kaldırılır)"):
                return
            try:
                self.app.db.maas_meslek_delete(int(selected_mid["id"]))  # type: ignore
            except Exception as ex:
                messagebox.showerror(APP_TITLE, f"Silme başarısız: {ex}")
                return
            clear_form()
            refresh()

        btns = ttk.Frame(frm)
        btns.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(btns, text="Kaydet", command=save).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Yeni", command=clear_form).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Sil", command=delete).pack(side=tk.LEFT, padx=6)

        cols = ("id", "ad", "aktif", "notlar")
        tree = ttk.Treeview(frm, columns=cols, show="headings", height=12, selectmode="browse")
        for c in cols:
            tree.heading(c, text=c.upper())
        tree.column("id", width=60, anchor="center")
        tree.column("ad", width=260)
        tree.column("aktif", width=80, anchor="center")
        tree.column("notlar", width=280)
        tree.pack(fill=tk.BOTH, expand=True)
        tree.bind("<<TreeviewSelect>>", on_select)

        refresh()

        def on_close():
            try:
                self._refresh_meslek_options()
            except Exception:
                pass
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", on_close)

    def load_selected_employee(self):
        sel = self.emp_tree.selection()
        if not sel:
            return
        vals = self.emp_tree.item(sel[0], "values")
        if not vals:
            return
        try:
            self._selected_employee_id = int(vals[0])
        except Exception:
            self._selected_employee_id = None
            return

        try:
            # form değerlerini DB'den çekelim
            rows = self.app.db.maas_calisan_list()  # type: ignore
            row = next((x for x in rows if int(x["id"]) == int(self._selected_employee_id or 0)), None)
        except Exception:
            row = None
        if not row:
            return

        self.e_ad.set(str(row["ad"] or ""))
        self.e_tutar.set(fmt_amount(float(row["aylik_tutar"] or 0)))
        self.e_para.set(str(row["para"] or "TL"))
        try:
            self._refresh_meslek_options()
            meslek_ad = str(row["meslek_ad"] or "")
            self.e_meslek.set(meslek_ad if meslek_ad else "(Yok)")
        except Exception:
            try:
                self.e_meslek.set("(Yok)")
            except Exception:
                pass
        try:
            self.cmb_emp_durum.set("Aktif" if int(row["aktif"] or 0) == 1 else "Aktif değil")
        except Exception:
            pass
        self.e_notlar.set(str(row["notlar"] or ""))
        self.lbl_emp_mode.config(text=f"Düzenle: #{self._selected_employee_id}")

    def save_employee(self):
        ad = (self.e_ad.get() or "").strip()
        if not ad:
            messagebox.showerror(APP_TITLE, "Ad Soyad boş olamaz.")
            return
        try:
            tutar = float(self.e_tutar.get_float())
        except Exception:
            tutar = 0.0
        para = (self.e_para.get() or "TL").strip() or "TL"
        meslek_name = (self.e_meslek.get() or "").strip()
        meslek_id = None
        if meslek_name and meslek_name != "(Yok)":
            try:
                meslek_id = int(self._meslek_name_to_id.get(meslek_name) or 0) or None
            except Exception:
                meslek_id = None
        aktif = 1 if (self.cmb_emp_durum.get() or '').strip() == 'Aktif' else 0
        notlar = (self.e_notlar.get() or "").strip()

        try:
            if self._selected_employee_id:
                self.app.db.maas_calisan_update(
                    self._selected_employee_id,
                    ad,
                    tutar,
                    para=para,
                    aktif=aktif,
                    notlar=notlar,
                    meslek_id=meslek_id,
                )  # type: ignore
            else:
                self.app.db.maas_calisan_add(ad, tutar, para=para, aktif=aktif, notlar=notlar, meslek_id=meslek_id)  # type: ignore
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Kaydetme başarısız: {e}")
            return

        self.clear_employee_form()
        self.refresh_employees()
        self._ensure_and_refresh_current()

    def delete_employee(self):
        if not self._selected_employee_id:
            messagebox.showinfo(APP_TITLE, "Silmek için önce bir çalışan seç.")
            return
        if not messagebox.askyesno(APP_TITLE, "Seçili çalışan silinsin mi? (Maaş geçmişi de silinir)"):
            return
        try:
            self.app.db.maas_calisan_delete(int(self._selected_employee_id))  # type: ignore
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Silme başarısız: {e}")
            return
        self.clear_employee_form()
        self.refresh_employees()
        self._ensure_and_refresh_current()

    # -----------------
    # Bu Ay
    # -----------------
    def _ensure_and_refresh_current(self):
        try:
            self.app.db.maas_ensure_donem(_current_period())  # type: ignore
        except Exception:
            pass
        self.refresh_current()

    def refresh_current(self):
        period = _current_period()
        self.lbl_period.config(text=f"Aktif Dönem: {period}")

        for i in self.cur_tree.get_children():
            self.cur_tree.delete(i)

        try:
            rows = self.app.db.maas_odeme_list(donem=period)  # type: ignore
        except Exception:
            rows = []

        for r in rows:
            paid = "Ödendi" if int(r["odendi"] or 0) == 1 else "Ödenmedi"
            self.cur_tree.insert(
                "", "end",
                values=(
                    int(r["id"]),
                    str(r["calisan_ad"]),
                    fmt_amount(float(r["tutar"] or 0)),
                    str(r["para"] or "TL"),
                    paid,
                    str(r["odeme_tarihi"] or ""),
                    str(r["aciklama"] or ""),
                ),
            )

        # üst özet
        try:
            o = self.app.db.maas_donem_ozet(period)  # type: ignore
            toplam = float(o["toplam"] or 0)
            odenen = float(o["odenen"] or 0)
            odenmeyen = float(o["odenmeyen"] or 0)
            self.lbl_summary.config(
                text=f"Toplam: {fmt_amount(toplam)}  •  Ödenen: {fmt_amount(odenen)}  •  Ödenmeyen: {fmt_amount(odenmeyen)}"
            )
        except Exception:
            self.lbl_summary.config(text="")

    def _on_select_current(self):
        sel = self.cur_tree.selection()
        if not sel:
            self._selected_payment_id = None
            return
        vals = self.cur_tree.item(sel[0], "values")
        try:
            self._selected_payment_id = int(vals[0])
        except Exception:
            self._selected_payment_id = None

    def set_paid_selected(self, odendi: int):
        if not self._selected_payment_id:
            messagebox.showinfo(APP_TITLE, "Önce bir maaş satırı seç.")
            return
        dt = (self.cur_date.get() or "").strip() if int(odendi) == 1 else ""
        try:
            self.app.db.maas_odeme_set_paid(int(self._selected_payment_id), int(odendi), odeme_tarihi=dt)  # type: ignore
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Güncelleme başarısız: {e}")
            return
        self.refresh_current()
        self.refresh_reports()

    # -----------------
    # Excel & Eşleştirme
    # -----------------
    @staticmethod
    def _period_to_range(period: str) -> Tuple[str, str]:
        """YYYY-MM -> (start_iso, end_iso)"""
        try:
            y, m = [int(x) for x in (period or "").split("-")[:2]]
            start = date(y, m, 1)
        except Exception:
            start = date.today().replace(day=1)
        # next month
        if start.month == 12:
            nxt = date(start.year + 1, 1, 1)
        else:
            nxt = date(start.year, start.month + 1, 1)
        end = nxt - timedelta(days=1)
        return (start.isoformat(), end.isoformat())

    @staticmethod
    def _to_date(v: Any) -> Optional[date]:
        """YYYY-MM-DD (veya datetime/date) -> date."""
        if v is None:
            return None
        if isinstance(v, date) and not isinstance(v, datetime):
            return v
        if isinstance(v, datetime):
            return v.date()
        try:
            s = str(v).strip()[:10]
            if not s:
                return None
            return date.fromisoformat(s)
        except Exception:
            return None

    @classmethod
    def _date_score(cls, bank_date: Any, pay_date: Any) -> float:
        """Tarih yakınlığı skoru (0..1)."""
        bd = cls._to_date(bank_date)
        pd = cls._to_date(pay_date)
        if not bd or not pd:
            return 0.0
        diff = abs((bd - pd).days)
        if diff == 0:
            return 1.0
        if diff == 1:
            return 0.92
        if diff == 2:
            return 0.85
        if diff == 3:
            return 0.75
        if diff <= 7:
            return 0.55
        if diff <= 14:
            return 0.35
        return 0.0

    def _sync_match_date_range(self):
        try:
            per = (self.m_period.get() or "").strip()
        except Exception:
            per = ""
        if not per or per == "(Seç)":
            per = _current_period()
        start, end = self._period_to_range(per)
        try:
            self.m_from.set(start)
            self.m_to.set(end)
        except Exception:
            pass

    def import_maas_excel(self):
        """Maaş Exceli içe aktar (Import Wizard)"""
        if not HAS_OPENPYXL:
            messagebox.showerror(APP_TITLE, "Excel içe aktarma için 'openpyxl' kurulu değil.\n\nKomut: pip install openpyxl")
            return

        period = (self.m_period.get() or "").strip()
        if not period or period == "(Seç)":
            period = _current_period()
        try:
            self.app.db.maas_ensure_donem(period)  # type: ignore
        except Exception:
            pass

        p = filedialog.askopenfilename(
            title="Maaş Exceli Seç",
            filetypes=[("Excel", "*.xlsx *.xlsm *.xltx *.xltm"), ("Tüm Dosyalar", "*.*")],
        )
        if not p:
            return

        w = ImportWizard(self.app, p, mode="maas", context={"donem": period})
        self.app.root.wait_window(w)
        # refresh
        self._ensure_and_refresh_current()
        # Ad-soyad ile banka hareketlerinde otomatik tarama + geçmiş kaydı
        try:
            self._auto_record_name_matches(period)
        except Exception:
            pass
        # Hızlı öneri listesini güncelle
        try:
            self.suggest_salary_matches()
        except Exception:
            pass
        self.refresh_account()
        self.refresh_history()
        self.refresh_reports()


    def _auto_record_name_matches(self, period: str, *, date_from: str = "", date_to: str = "", name_min: float = 0.78) -> tuple[int, int]:
        """İçe aktarımdan sonra banka hareketlerini tarar:

        1) Çalışan ad-soyadının açıklama içinde geçmesi (fuzzy)
        2) (Varsa) ödeme tarihi + tutar yakınlığına göre muhtemel satırlar

        Tüm adaylar 'maas_hesap_hareket' tablosuna yazılır.
        Ayrıca çok güçlü ve belirginse otomatik link yapılır.

        Dönüş: (eklenen_kayıt_sayısı, otomatik_link_sayısı)
        """

        period = (period or "").strip() or _current_period()
        if not date_from or not date_to:
            date_from, date_to = self._period_to_range(period)

        try:
            pay_rows = self.app.db.maas_odeme_list(donem=period, odendi=None, include_inactive=True)  # type: ignore
        except Exception:
            pay_rows = []
        if not pay_rows:
            return (0, 0)

        try:
            bank_rows = self.app.db.banka_list(date_from=date_from, date_to=date_to, tip="Çıkış", limit=20000)
        except Exception:
            bank_rows = []
        bank_rows = list(bank_rows or [])
        if not bank_rows:
            return (0, 0)

        def _get(r: Any, k: str, d: Any = "") -> Any:
            if isinstance(r, dict):
                return r.get(k, d)
            try:
                return r[k]
            except Exception:
                return d

        # Banka açıklamalarını/tokenlarını ve tutar bucket'larını ön-indexle
        token_index: dict[str, list[int]] = {}
        amount_buckets: dict[int, list[int]] = {}
        bank_by_id: dict[int, tuple[Any, str, str, float, Any]] = {}  # id -> (row, norm_desc, para, abs_tutar, tarih)

        for b in bank_rows:
            try:
                bid = int(_get(b, "id", 0) or 0)
            except Exception:
                continue
            if bid <= 0:
                continue
            desc = str(_get(b, "aciklama", "") or "")
            nd = normalize_text(desc)
            para = str(_get(b, "para", "") or "")
            try:
                btutar = abs(float(_get(b, "tutar", 0.0) or 0.0))
            except Exception:
                btutar = 0.0
            tarih = _get(b, "tarih", "")
            bank_by_id[bid] = (b, nd, para, btutar, tarih)

            # token index (>=3)
            for tok in set(nd.split()):
                if len(tok) >= 3:
                    token_index.setdefault(tok, []).append(bid)

            # amount bucket (TL bazında)
            try:
                bucket = int(round(btutar))
            except Exception:
                bucket = 0
            if bucket > 0:
                amount_buckets.setdefault(bucket, []).append(bid)

        # Dönemde zaten linklenmiş bankaları otomatik linkte kullanma
        used_bank_ids: set[int] = set()
        for pr in pay_rows:
            try:
                ub = int((_get(pr, "banka_hareket_id", 0) or 0))
            except Exception:
                ub = 0
            if ub:
                used_bank_ids.add(ub)

        added = 0
        auto_linked = 0

        for pr in pay_rows:
            try:
                oid = int(_get(pr, "id", 0) or 0)
                cid = int(_get(pr, "calisan_id", 0) or 0)
                emp_name = str(_get(pr, "calisan_ad", "") or "")
                expected = abs(float(_get(pr, "tutar", 0.0) or 0.0))
                epara = str(_get(pr, "para", "TL") or "TL")
                existing_link = int(_get(pr, "banka_hareket_id", 0) or 0)
                pay_date = _get(pr, "odeme_tarihi", "")
            except Exception:
                continue
            if not oid or not cid or not emp_name or expected <= 0:
                continue

            nname = normalize_text(emp_name)

            # --- 1) İsim üzerinden adaylar
            name_cand_ids: list[int] = []
            tokens = [t for t in nname.split() if len(t) >= 3]
            if tokens:
                anchor = max(tokens, key=len)
                name_cand_ids = list(token_index.get(anchor, []) or [])

            # --- 2) (Varsa) tarih+tutar üzerinden adaylar
            amtdate_cand_set: set[int] = set()
            if self._to_date(pay_date) is not None:
                tol = max(2.0, expected * 0.03)
                lo = int(round(max(0.0, expected - tol)))
                hi = int(round(expected + tol))
                for buck in range(lo, hi + 1):
                    for bid in amount_buckets.get(buck, []) or []:
                        amtdate_cand_set.add(int(bid))

            # Adayları skorla
            best_link: tuple[float, Optional[int], float, float, float, str] = (0.0, None, 0.0, 0.0, 0.0, "")
            second_link = 0.0

            def _score_and_store(bid: int, *, mode: str, do_store: bool = True) -> Optional[tuple[float, float, float, float]]:
                nonlocal added, best_link, second_link
                if bid not in bank_by_id:
                    return None
                brow, _nd, bpara, btutar, btarih = bank_by_id[bid]
                desc = str(_get(brow, "aciklama", "") or "")

                name_sc = float(best_substring_similarity(emp_name, desc)) if mode == "name" else float(best_substring_similarity(emp_name, desc))
                # tek isim (ör: "Ali") ise eşiği yükselt
                thr = float(name_min + (0.08 if len(nname.split()) < 2 else 0.0))
                if mode == "name" and name_sc < thr:
                    return None

                # Para filtresi (ikisi de doluysa uyuşmazsa ele)
                try:
                    if epara and bpara and str(epara).strip().upper() != str(bpara).strip().upper():
                        return None
                except Exception:
                    pass

                # Tutar skoru
                try:
                    amt_sc = float(amount_score(btutar, expected, abs_tol=2.0, pct_tol=0.03))
                except Exception:
                    amt_sc = 0.0

                date_sc = float(self._date_score(btarih, pay_date)) if self._to_date(pay_date) is not None else 0.0

                # Skor ağırlıkları: isim varsa güçlü, tarih+tutar yakınlığı varsa onu öne çıkar
                if self._to_date(pay_date) is not None:
                    if name_sc >= 0.78:
                        score = float(combine3_scores(name_sc, amt_sc, date_sc, w_a=0.55, w_b=0.25, w_c=0.20))
                    elif date_sc >= 0.85:
                        score = float(combine3_scores(name_sc, amt_sc, date_sc, w_a=0.15, w_b=0.55, w_c=0.30))
                    else:
                        score = float(combine3_scores(name_sc, amt_sc, date_sc, w_a=0.25, w_b=0.65, w_c=0.10))
                else:
                    score = float(combine_scores(name_sc, amt_sc, w_name=0.85 if mode == "name" else 0.55, w_amt=0.15 if mode == "name" else 0.45))

                # geçmişe kaydet
                if do_store:
                    try:
                        rid = int(
                            self.app.db.maas_hesap_hareket_add(
                                donem=period,
                                calisan_id=cid,
                                banka_hareket_id=int(bid),
                                odeme_id=oid,
                                match_score=float(score),
                                match_type=("auto_name_scan" if mode == "name" else "auto_amt_date_scan"),
                            )
                            or 0
                        )  # type: ignore
                        if rid:
                            added += 1
                    except Exception:
                        pass

                # otomatik link için en iyi adayı bul (kullanılmamış banka)
                if bid not in used_bank_ids and existing_link == 0:
                    if score > best_link[0]:
                        second_link = best_link[0]
                        best_link = (score, bid, name_sc, amt_sc, date_sc, mode)
                    elif score > second_link:
                        second_link = score

                return (score, name_sc, amt_sc, date_sc)

            # name candidates: hepsini kaydet (kısıtlı set)
            for bid in name_cand_ids[:300]:
                _score_and_store(int(bid), mode="name")

            # amount-date candidates: sadece en iyi birkaçını kaydet
            if amtdate_cand_set:
                tmp: list[tuple[float, int]] = []
                # Önce skorla, sonra en iyi 6 adayı yaz
                for bid in list(amtdate_cand_set)[:1200]:
                    res = _score_and_store(int(bid), mode="amtdate", do_store=False)
                    if res is None:
                        continue
                    sc, _ns, _as, ds = res
                    # bu mod için çok zayıfları ele
                    if sc >= 0.70 and ds >= 0.35:
                        tmp.append((sc, int(bid)))
                tmp.sort(key=lambda x: x[0], reverse=True)
                for _sc, bid in tmp[:6]:
                    _score_and_store(int(bid), mode="amtdate", do_store=True)

            # otomatik link (sadece çok güçlü ve belirginse)
            if existing_link or best_link[1] is None:
                continue

            score, bid_opt, name_sc, amt_sc, date_sc, mode = best_link
            if bid_opt is None:
                continue
            bid = int(bid_opt)
            strong_by_name = (name_sc >= 0.90)
            strong_by_date_amt = (amt_sc >= 0.92 and date_sc >= 0.92)
            if score >= 0.92 and (score - second_link) >= 0.07 and (strong_by_name or strong_by_date_amt):
                try:
                    note = "auto_name_scan" if mode == "name" else "auto_amt_date"
                    self.app.db.maas_odeme_link_bank(oid, bid, score=float(score), note=note)  # type: ignore
                    used_bank_ids.add(bid)
                    auto_linked += 1
                except Exception:
                    pass

        return (added, auto_linked)

    def suggest_salary_matches(self):
        """Seçili dönemdeki maaşları banka hareketleriyle eşleştirmek için öneri üret."""
        period = (self.m_period.get() or "").strip()
        if not period or period == "(Seç)":
            period = _current_period()

        date_from = (self.m_from.get() or "").strip()
        date_to = (self.m_to.get() or "").strip()
        if not date_from or not date_to:
            date_from, date_to = self._period_to_range(period)

        min_score = float(safe_float(self.m_min_score.get()))
        abs_tol = float(safe_float(self.m_abs_tol.get()))
        only_unpaid = bool(self.var_m_only_unpaid.get())

        # temizle
        for i in self.m_tree.get_children():
            self.m_tree.delete(i)

        try:
            pay_rows = self.app.db.maas_odeme_list(donem=period, odendi=(0 if only_unpaid else None))  # type: ignore
        except Exception:
            pay_rows = []

        try:
            bank_rows = self.app.db.banka_list(date_from=date_from, date_to=date_to, tip="Çıkış", limit=8000)
        except Exception:
            bank_rows = []

        bank_rows = list(bank_rows or [])

        def _get(r: Any, k: str, d: Any = "") -> Any:
            if isinstance(r, dict):
                return r.get(k, d)
            try:
                return r[k]
            except Exception:
                return d

        bank_by_id: Dict[int, Any] = {}
        bank_meta: Dict[int, Tuple[str, float, Any, str]] = {}  # id -> (para, abs_tutar, tarih, aciklama)
        amount_buckets: Dict[int, list[int]] = {}

        for br in bank_rows:
            try:
                bid = int(_get(br, "id", 0) or 0)
            except Exception:
                continue
            if bid <= 0:
                continue
            bank_by_id[bid] = br
            bpara = str(_get(br, "para", "") or "")
            try:
                btutar = abs(float(_get(br, "tutar", 0.0) or 0.0))
            except Exception:
                btutar = 0.0
            btarih = _get(br, "tarih", "")
            baciklama = str(_get(br, "aciklama", "") or "")
            bank_meta[bid] = (bpara, btutar, btarih, baciklama)
            try:
                buck = int(round(btutar))
            except Exception:
                buck = 0
            if buck > 0:
                amount_buckets.setdefault(buck, []).append(bid)

        unused_bank_ids = set(bank_by_id.keys())

        # Önce DB'de linkli olanları göster
        for pr in pay_rows:
            existing_bank_id = int(pr.get("banka_hareket_id") or 0) if isinstance(pr, dict) else int(pr["banka_hareket_id"] or 0)
            if existing_bank_id:
                b = self.app.db.banka_get(existing_bank_id)
                if b is not None:
                    unused_bank_ids.discard(existing_bank_id)
                    score = float(pr.get("banka_match_score") or 1.0) if isinstance(pr, dict) else float(pr["banka_match_score"] or 1.0)
                    self._insert_match_row(pr, b, score, force_tag="ok")

        # Linkli olmayanlara öneri üret (greedy)
        pending: list[tuple[int, float, Any, Any, str]] = []  # (tag_rank, score, pr, br_or_None, tag)
        for pr in pay_rows:
            existing_bank_id = int(pr.get("banka_hareket_id") or 0) if isinstance(pr, dict) else int(pr["banka_hareket_id"] or 0)
            if existing_bank_id:
                continue

            emp_name = str(_get(pr, "calisan_ad", "") or "")
            expected = abs(float(_get(pr, "tutar", 0.0) or 0.0))
            para = str(_get(pr, "para", "TL") or "TL")
            pay_date = _get(pr, "odeme_tarihi", "")
            has_pay_date = self._to_date(pay_date) is not None

            if not emp_name or expected <= 0:
                pending.append((0, 0.0, pr, None, "no"))
                continue

            # Adayları önce tutar bucket'larıyla daralt
            tol_amt = max(abs_tol, expected * 0.03, 0.01)
            lo = int(round(max(0.0, expected - tol_amt)))
            hi = int(round(expected + tol_amt))

            cand: set[int] = set()
            for buck in range(lo, hi + 1):
                for bid in amount_buckets.get(buck, []) or []:
                    if bid in unused_bank_ids:
                        cand.add(int(bid))

            # fallback (çok az veri varsa)
            if not cand:
                cand = set(list(unused_bank_ids)[:2500])

            best_score = 0.0
            best_id: Optional[int] = None

            for bid in cand:
                if bid not in unused_bank_ids:
                    continue
                meta = bank_meta.get(int(bid))
                if not meta:
                    continue
                bpara, btutar, btarih, baciklama = meta

                # Para filtresi
                try:
                    if para and bpara and para.strip().upper() != str(bpara).strip().upper():
                        continue
                except Exception:
                    pass

                amt_sc = float(amount_score(btutar, expected, abs_tol=max(abs_tol, 0.01), pct_tol=0.03))
                if amt_sc <= 0:
                    continue
                name_sc = float(best_substring_similarity(emp_name, baciklama))
                date_sc = float(self._date_score(btarih, pay_date)) if has_pay_date else 0.0

                if has_pay_date:
                    if name_sc >= 0.78:
                        score = float(combine3_scores(name_sc, amt_sc, date_sc, w_a=0.55, w_b=0.25, w_c=0.20))
                    elif date_sc >= 0.85:
                        score = float(combine3_scores(name_sc, amt_sc, date_sc, w_a=0.15, w_b=0.55, w_c=0.30))
                    else:
                        score = float(combine3_scores(name_sc, amt_sc, date_sc, w_a=0.25, w_b=0.65, w_c=0.10))
                else:
                    score = float(combine_scores(name_sc, amt_sc, w_name=0.75, w_amt=0.25))

                if score > best_score:
                    best_score = score
                    best_id = int(bid)

            if best_id is not None and best_score >= min_score:
                b = bank_by_id.get(int(best_id))
                unused_bank_ids.discard(int(best_id))
                tag = "ok" if best_score >= 0.87 else "warn"
                rank = 2 if tag == "ok" else 1
                pending.append((rank, best_score, pr, b, tag))
            else:
                pending.append((0, 0.0, pr, None, "no"))

        # En muhtemel eşleşmeleri üste getir
        pending.sort(key=lambda x: (x[0], x[1]), reverse=True)
        for _rank, sc, pr, br, tag in pending:
            self._insert_match_row(pr, br, float(sc), force_tag=tag)

    def _insert_match_row(self, pr: Any, br: Any, score: float, force_tag: str = ""):
        try:
            pid = int(pr["id"])
            emp = str(pr["calisan_ad"])
            tutar = float(pr["tutar"] or 0)
            para = str(pr["para"] or "TL")
            odendi_val = int(pr["odendi"] or 0)
            odendi = "Ödendi" if odendi_val == 1 else "Ödenmedi"
        except Exception:
            return

        if br is not None:
            try:
                bid = int(br["id"])
                btarih = str(br["tarih"] or "")
                btutar = float(br["tutar"] or 0)
                baciklama = str(br["aciklama"] or "")
            except Exception:
                bid = 0
                btarih = ""
                btutar = 0.0
                baciklama = ""
        else:
            bid = 0
            btarih = ""
            btutar = 0.0
            baciklama = ""

        values = (
            pid,
            emp,
            fmt_amount(tutar),
            para,
            odendi,
            ("" if bid == 0 else bid),
            btarih,
            fmt_amount(btutar),
            baciklama,
            ("" if score <= 0 else f"{score:.2f}"),
        )
        tag = force_tag or ("ok" if score >= 0.87 else ("warn" if score >= 0.78 else "no"))
        self.m_tree.insert("", "end", values=values, tags=(tag,))

    def apply_selected_matches(self):
        sel = self.m_tree.selection()
        if not sel:
            messagebox.showinfo(APP_TITLE, "Uygulamak için en az bir satır seç.")
            return

        ok = 0
        for iid in sel:
            vals = self.m_tree.item(iid, "values")
            if not vals or len(vals) < 10:
                continue
            try:
                pid = int(vals[0])
                bank_id = int(vals[5])
            except Exception:
                continue
            if bank_id <= 0:
                continue
            bank_date = str(vals[6] or "")
            try:
                score = float(str(vals[9] or "0").replace(",", "."))
            except Exception:
                score = 0.0
            try:
                self.app.db.maas_odeme_set_paid(pid, 1, odeme_tarihi=bank_date)  # type: ignore
                self.app.db.maas_odeme_link_bank(pid, bank_id, score=score)  # type: ignore
                # geçmişe de yaz
                try:
                    meta = self.app.db.maas_odeme_get(pid)  # type: ignore
                    if meta is not None:
                        self.app.db.maas_hesap_hareket_add(
                            donem=str(meta["donem"] or ""),
                            calisan_id=int(meta["calisan_id"]),
                            banka_hareket_id=int(bank_id),
                            odeme_id=int(pid),
                            match_score=float(score or 0.0),
                            match_type="manual_apply",
                        )  # type: ignore
                except Exception:
                    pass
                ok += 1
            except Exception:
                continue

        messagebox.showinfo(APP_TITLE, f"Uygulandı: {ok} satır")
        self._ensure_and_refresh_current()
        self.refresh_account()
        self.refresh_reports()
        self.suggest_salary_matches()

    def clear_selected_links(self):
        sel = self.m_tree.selection()
        if not sel:
            messagebox.showinfo(APP_TITLE, "Temizlemek için en az bir satır seç.")
            return

        ok = 0
        for iid in sel:
            vals = self.m_tree.item(iid, "values")
            if not vals:
                continue
            try:
                pid = int(vals[0])
            except Exception:
                continue
            try:
                self.app.db.maas_odeme_clear_bank_link(pid)  # type: ignore
                ok += 1
            except Exception:
                continue
        messagebox.showinfo(APP_TITLE, f"Temizlendi: {ok} satır")
        self.refresh_account()
        self.suggest_salary_matches()

    # -----------------
    # Geçmiş
    # -----------------
    def refresh_history(self):
        for i in self.h_tree.get_children():
            self.h_tree.delete(i)

        period = (self.h_period.get() or "").strip()
        if period == "(Seç)":
            period = ""

        q = (self.h_q.get() or "").strip()
        paid = (self.h_paid.get() or "(Tümü)").strip()
        odendi: Optional[int] = None
        if paid == "Ödendi":
            odendi = 1
        elif paid == "Ödenmedi":
            odendi = 0

        try:
            rows = self.app.db.maas_odeme_list(donem=period, q=q, odendi=odendi)  # type: ignore
        except Exception:
            rows = []

        for r in rows:
            paid_txt = "Ödendi" if int(r["odendi"] or 0) == 1 else "Ödenmedi"
            self.h_tree.insert(
                "", "end",
                values=(
                    str(r["donem"]),
                    str(r["calisan_ad"]),
                    fmt_amount(float(r["tutar"] or 0)),
                    str(r["para"] or "TL"),
                    paid_txt,
                    str(r["odeme_tarihi"] or ""),
                    str(r["aciklama"] or ""),
                ),
            )

    # -----------------
    # Rapor
    # -----------------
    def refresh_reports(self):
        period = (self.r_period.get() or "").strip() or _current_period()
        try:
            self.app.db.maas_ensure_donem(period)  # type: ignore
        except Exception:
            pass

        try:
            o = self.app.db.maas_donem_ozet(period)  # type: ignore
            toplam = float(o["toplam"] or 0)
            odenen = float(o["odenen"] or 0)
            odenmeyen = float(o["odenmeyen"] or 0)
            adet = int(o["adet"] or 0)
            odenen_adet = int(o["odenen_adet"] or 0)
            oran = (odenen_adet / adet * 100) if adet else 0.0
        except Exception:
            toplam = odenen = odenmeyen = 0.0
            adet = odenen_adet = 0
            oran = 0.0

        try:
            self.r_txt.delete("1.0", "end")
            self.r_txt.insert(
                "end",
                f"Dönem: {period}\n"
                f"Toplam Maaş: {fmt_amount(toplam)}\n"
                f"Ödenen: {fmt_amount(odenen)}  •  Ödenmeyen: {fmt_amount(odenmeyen)}\n"
                f"Ödeme Durumu: {odenen_adet}/{adet} satır  (≈ %{oran:.0f})\n",
            )
        except Exception:
            pass

        for i in self.r_tree.get_children():
            self.r_tree.delete(i)

        try:
            rows = self.app.db.maas_aylik_toplamlar(limit=24)  # type: ignore
        except Exception:
            rows = []

        for r in rows:
            self.r_tree.insert(
                "", "end",
                values=(
                    str(r["donem"]),
                    fmt_amount(float(r["toplam"] or 0)),
                    fmt_amount(float(r["odenen"] or 0)),
                    fmt_amount(float(r["odenmeyen"] or 0)),
                ),
            )

    def _jump_period_from_report(self):
        sel = self.r_tree.selection()
        if not sel:
            return
        vals = self.r_tree.item(sel[0], "values")
        if not vals:
            return
        per = str(vals[0])
        try:
            self.h_period.set(per)
        except Exception:
            pass
        self.nb.select(self.tab_history)
        self.refresh_history()


    def select_employees_tab(self):
        """Sol menüde "Çalışanlar" kısayolundan gelince Çalışanlar sekmesini aç."""
        try:
            self.nb.select(self.tab_employees)
        except Exception:
            pass

    def select_tab(self, tab_key: str):
        """Bu plugin içindeki sekmeler arasında programatik geçiş.

        Desteklenen anahtarlar: employees, current, match, scan, account, history, reports
        """
        k = (tab_key or "").strip().lower()
        m = {
            "employees": getattr(self, "tab_employees", None),
            "calisanlar": getattr(self, "tab_employees", None),
            "current": getattr(self, "tab_current", None),
            "buay": getattr(self, "tab_current", None),
            "match": getattr(self, "tab_match", None),
            "eslestirme": getattr(self, "tab_match", None),
            "scan": getattr(self, "tab_scan", None),
            "maasbul": getattr(self, "tab_scan", None),
            "account": getattr(self, "tab_account", None),
            "hesap": getattr(self, "tab_account", None),
            "history": getattr(self, "tab_history", None),
            "gecmis": getattr(self, "tab_history", None),
            "reports": getattr(self, "tab_reports", None),
            "rapor": getattr(self, "tab_reports", None),
        }
        target = m.get(k)
        if target is None:
            target = getattr(self, "tab_current", None)
        try:
            if target is not None:
                self.nb.select(target)
        except Exception:
            pass


def build(master, app) -> ttk.Frame:
    return MaasTakibiFrame(master, app)
