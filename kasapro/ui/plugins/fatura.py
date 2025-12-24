# -*- coding: utf-8 -*-
"""UI Plugin: Fatura.

Amaç:
- Satış/Alış/İade/Proforma fatura kaydı
- Kalem bazlı (ürün/hizmet) tutar + iskonto + KDV hesaplama
- Tahsilat/ödeme takibi
- PDF çıktısı
- Seri/numara yönetimi

Not: e-Fatura/e-Arşiv entegrasyonu bu modülde sadece alan ve hazırlık olarak düşünülmüştür.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional, TYPE_CHECKING

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from ...config import APP_TITLE, HAS_REPORTLAB
from ...utils import fmt_amount, fmt_tr_date, safe_float, ensure_pdf_fonts
from ..widgets import LabeledEntry, LabeledCombo

if TYPE_CHECKING:
    from ...app import App

PLUGIN_META = {
    "key": "fatura",
    "nav_text": "🧾 Fatura",
    "page_title": "Fatura",
    "order": 23,
}


FATURA_TURLERI = ["Satış", "Alış", "İade", "Proforma"]
FATURA_DURUMLARI = ["Taslak", "Kesildi", "İptal"]
VAR_KDV = ["0", "1", "8", "10", "18", "20"]
VAR_BIRIM = ["Adet", "Kg", "m", "m²", "m³", "Saat", "Gün", "Ay", "Hizmet"]


def _s(v: Any) -> str:
    try:
        return str(v or "").strip()
    except Exception:
        return ""


def _today_str() -> str:
    try:
        return date.today().strftime("%d.%m.%Y")
    except Exception:
        return ""


class FaturaFrame(ttk.Frame):
    def __init__(self, master, app: "App"):
        super().__init__(master)
        self.app = app
        self.current_fid: Optional[int] = None
        self._items: List[Dict[str, Any]] = []
        self._build()

    # -----------------
    # UI
    # -----------------
    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=10, pady=(10, 6))

        ttk.Button(top, text="➕ Yeni Fatura", command=self.new_invoice).pack(side=tk.LEFT)
        ttk.Button(top, text="💾 Kaydet", command=self.save_invoice).pack(side=tk.LEFT, padx=6)
        self.btn_pdf = ttk.Button(top, text="🧾 PDF", command=self.export_pdf)
        self.btn_pdf.pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text="🗑️ Sil", command=self.delete_invoice).pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text="Yenile", command=self.refresh).pack(side=tk.LEFT, padx=10)

        if not HAS_REPORTLAB:
            try:
                self.btn_pdf.config(state="disabled")
            except Exception:
                pass

        self.lbl_top_info = ttk.Label(top, text="")
        self.lbl_top_info.pack(side=tk.LEFT, padx=(14, 0))

        mid = ttk.LabelFrame(self, text="Fatura")
        mid.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.nb = ttk.Notebook(mid)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # 1) Liste
        self.tab_list = ttk.Frame(self.nb)
        self.nb.add(self.tab_list, text="Faturalar")
        self._build_list_tab()

        # 2) Editor
        self.tab_edit = ttk.Frame(self.nb)
        self.nb.add(self.tab_edit, text="Fatura Oluştur / Düzenle")
        self._build_edit_tab()

        # 3) Tahsilat
        self.tab_pay = ttk.Frame(self.nb)
        self.nb.add(self.tab_pay, text="Tahsilat / Ödeme")
        self._build_pay_tab()

        # 4) Ayarlar
        self.tab_settings = ttk.Frame(self.nb)
        self.nb.add(self.tab_settings, text="Ayarlar")
        self._build_settings_tab()

        # 5) Rapor
        self.tab_report = ttk.Frame(self.nb)
        self.nb.add(self.tab_report, text="Raporlar")
        self._build_report_tab()

        self.new_invoice()
        self.refresh()

    # -----------------
    # Tab: Liste
    # -----------------
    def _build_list_tab(self):
        box = ttk.LabelFrame(self.tab_list, text="Filtre")
        box.pack(fill=tk.X, padx=8, pady=8)

        row = ttk.Frame(box)
        row.pack(fill=tk.X, pady=6)

        self.f_q = LabeledEntry(row, "Ara:", 24)
        self.f_q.pack(side=tk.LEFT, padx=6)

        self.f_tur = LabeledCombo(row, "Tür:", ["(Tümü)"] + FATURA_TURLERI, 12)
        self.f_tur.pack(side=tk.LEFT, padx=6)
        self.f_tur.set("(Tümü)")

        self.f_durum = LabeledCombo(row, "Durum:", ["(Tümü)"] + FATURA_DURUMLARI, 12)
        self.f_durum.pack(side=tk.LEFT, padx=6)
        self.f_durum.set("(Tümü)")

        self.f_from = LabeledEntry(row, "Başlangıç:", 12)
        self.f_from.pack(side=tk.LEFT, padx=6)
        self.f_to = LabeledEntry(row, "Bitiş:", 12)
        self.f_to.pack(side=tk.LEFT, padx=6)

        ttk.Button(row, text="Yenile", command=self.refresh).pack(side=tk.LEFT, padx=6)
        ttk.Button(row, text="Seçiliyi Aç", command=self.open_selected_invoice).pack(side=tk.LEFT, padx=6)

        cols = ("id", "tarih", "no", "tur", "durum", "cari", "para", "toplam", "odendi", "kalan")
        self.tree = ttk.Treeview(self.tab_list, columns=cols, show="headings", height=16, selectmode="browse")
        for c in cols:
            self.tree.heading(c, text=c.upper())

        self.tree.column("id", width=55, anchor="center")
        self.tree.column("tarih", width=95)
        self.tree.column("no", width=130)
        self.tree.column("tur", width=80, anchor="center")
        self.tree.column("durum", width=80, anchor="center")
        self.tree.column("cari", width=240)
        self.tree.column("para", width=55, anchor="center")
        self.tree.column("toplam", width=110, anchor="e")
        self.tree.column("odendi", width=110, anchor="e")
        self.tree.column("kalan", width=110, anchor="e")

        self.tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        scr = ttk.Scrollbar(self.tab_list, orient="vertical", command=self.tree.yview)
        scr.place(in_=self.tree, relx=1.0, rely=0, relheight=1.0, x=0)
        self.tree.configure(yscrollcommand=scr.set)

        try:
            self.tree.bind("<Double-1>", lambda _e: self.open_selected_invoice())
        except Exception:
            pass

    # -----------------
    # Tab: Editor
    # -----------------
    def _build_edit_tab(self):
        header = ttk.LabelFrame(self.tab_edit, text="Fatura Bilgileri")
        header.pack(fill=tk.X, padx=8, pady=8)

        row1 = ttk.Frame(header)
        row1.pack(fill=tk.X, pady=(6, 2))

        self.e_tarih = LabeledEntry(row1, "Tarih:", 12)
        self.e_tarih.pack(side=tk.LEFT, padx=6)

        self.e_vade = LabeledEntry(row1, "Vade:", 12)
        self.e_vade.pack(side=tk.LEFT, padx=6)

        self.e_seri = LabeledCombo(row1, "Seri:", ["A"], 8)
        self.e_seri.pack(side=tk.LEFT, padx=6)

        self.e_no = LabeledEntry(row1, "Fatura No:", 16)
        self.e_no.pack(side=tk.LEFT, padx=6)

        self.e_tur = LabeledCombo(row1, "Tür:", FATURA_TURLERI, 12)
        self.e_tur.pack(side=tk.LEFT, padx=6)

        self.e_durum = LabeledCombo(row1, "Durum:", FATURA_DURUMLARI, 12)
        self.e_durum.pack(side=tk.LEFT, padx=6)

        row2 = ttk.Frame(header)
        row2.pack(fill=tk.X, pady=(2, 6))

        self.e_cari = LabeledCombo(row2, "Cari:", [""], 30)
        self.e_cari.pack(side=tk.LEFT, padx=6)

        self.e_para = LabeledCombo(row2, "Para:", ["TL"], 8)
        self.e_para.pack(side=tk.LEFT, padx=6)

        self.e_vkn = LabeledEntry(row2, "VKN/TCKN:", 16)
        self.e_vkn.pack(side=tk.LEFT, padx=6)

        self.e_vd = LabeledEntry(row2, "Vergi D.:", 16)
        self.e_vd.pack(side=tk.LEFT, padx=6)

        self.e_eposta = LabeledEntry(row2, "E-posta:", 20)
        self.e_eposta.pack(side=tk.LEFT, padx=6)

        row3 = ttk.Frame(header)
        row3.pack(fill=tk.X, pady=(0, 8))

        self.e_adres = LabeledEntry(row3, "Adres:", 85)
        self.e_adres.pack(side=tk.LEFT, padx=6)

        # Kalemler
        items = ttk.LabelFrame(self.tab_edit, text="Kalemler")
        items.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        btns = ttk.Frame(items)
        btns.pack(fill=tk.X, padx=6, pady=(6, 4))

        ttk.Button(btns, text="➕ Kalem Ekle", command=self.add_item).pack(side=tk.LEFT)
        ttk.Button(btns, text="✏️ Düzenle", command=self.edit_item).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="🗑️ Sil", command=self.delete_item).pack(side=tk.LEFT, padx=6)

        cols = ("sira", "urun", "miktar", "birim", "fiyat", "isk", "kdv", "ara", "kdv_t", "top")
        self.items_tree = ttk.Treeview(items, columns=cols, show="headings", height=10, selectmode="browse")
        heads = {
            "sira": "Sıra",
            "urun": "Ürün/Hizmet",
            "miktar": "Miktar",
            "birim": "Birim",
            "fiyat": "B.Fiyat",
            "isk": "İsk%",
            "kdv": "KDV%",
            "ara": "Ara",
            "kdv_t": "KDV",
            "top": "Toplam",
        }
        for c in cols:
            self.items_tree.heading(c, text=heads.get(c, c))

        self.items_tree.column("sira", width=55, anchor="center")
        self.items_tree.column("urun", width=360)
        self.items_tree.column("miktar", width=80, anchor="e")
        self.items_tree.column("birim", width=70, anchor="center")
        self.items_tree.column("fiyat", width=100, anchor="e")
        self.items_tree.column("isk", width=65, anchor="e")
        self.items_tree.column("kdv", width=65, anchor="e")
        self.items_tree.column("ara", width=110, anchor="e")
        self.items_tree.column("kdv_t", width=110, anchor="e")
        self.items_tree.column("top", width=110, anchor="e")

        self.items_tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

        # Toplamlar + notlar
        btm = ttk.Frame(self.tab_edit)
        btm.pack(fill=tk.X, padx=8, pady=(0, 8))

        left = ttk.LabelFrame(btm, text="Notlar")
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.e_notlar = tk.Text(left, height=4, wrap="word")
        self.e_notlar.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        right = ttk.LabelFrame(btm, text="Toplam")
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(8, 0))

        self.sum_ara = ttk.Label(right, text="Ara Toplam: 0")
        self.sum_ara.pack(anchor="e", padx=10, pady=(8, 2))
        self.sum_isk = ttk.Label(right, text="İskonto: 0")
        self.sum_isk.pack(anchor="e", padx=10, pady=2)
        self.sum_kdv = ttk.Label(right, text="KDV: 0")
        self.sum_kdv.pack(anchor="e", padx=10, pady=2)
        self.sum_genel = ttk.Label(right, text="Genel: 0", style="TopTitle.TLabel")
        self.sum_genel.pack(anchor="e", padx=10, pady=(2, 10))

        # yüklemeler
        self._reload_edit_lists()

        try:
            self.items_tree.bind("<Double-1>", lambda _e: self.edit_item())
        except Exception:
            pass

    def _reload_edit_lists(self):
        # Cari listesi
        try:
            cariler = self.app.db.cari_list(q="", only_active=False)
            cari_names = [str(r["ad"]) for r in cariler]
        except Exception:
            cari_names = []

        try:
            self.e_cari.cmb["values"] = [""] + cari_names
        except Exception:
            pass

        # Para
        try:
            vals = self.app.db.list_currencies()
        except Exception:
            vals = ["TL"]
        try:
            self.e_para.cmb["values"] = vals
        except Exception:
            pass

        # Seri
        try:
            seriler = self.app.db.fatura_seri_list()
            uniq = []
            for s in seriler:
                ss = _s(s["seri"])
                if ss and ss not in uniq:
                    uniq.append(ss)
            if not uniq:
                uniq = ["A"]
        except Exception:
            uniq = ["A"]
        try:
            self.e_seri.cmb["values"] = uniq
        except Exception:
            pass

    # -----------------
    # Tab: Tahsilat
    # -----------------
    def _build_pay_tab(self):
        top = ttk.Frame(self.tab_pay)
        top.pack(fill=tk.X, padx=8, pady=8)

        ttk.Button(top, text="➕ Tahsilat/Ödeme Ekle", command=self.add_payment).pack(side=tk.LEFT)
        ttk.Button(top, text="🗑️ Sil", command=self.delete_payment).pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text="Yenile", command=self.refresh_payments).pack(side=tk.LEFT, padx=10)

        self.lbl_pay_sum = ttk.Label(top, text="")
        self.lbl_pay_sum.pack(side=tk.LEFT, padx=(10, 0))

        cols = ("id", "tarih", "tutar", "para", "odeme", "aciklama", "ref")
        self.pay_tree = ttk.Treeview(self.tab_pay, columns=cols, show="headings", height=16, selectmode="browse")
        for c in cols:
            self.pay_tree.heading(c, text=c.upper())

        self.pay_tree.column("id", width=55, anchor="center")
        self.pay_tree.column("tarih", width=95)
        self.pay_tree.column("tutar", width=110, anchor="e")
        self.pay_tree.column("para", width=55, anchor="center")
        self.pay_tree.column("odeme", width=140)
        self.pay_tree.column("aciklama", width=360)
        self.pay_tree.column("ref", width=140)

        self.pay_tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

    # -----------------
    # Tab: Ayarlar
    # -----------------
    def _build_settings_tab(self):
        hint = ttk.Label(
            self.tab_settings,
            text=(
                "Seri/Numara formatı: {yil} {seri} {no_pad} {no} {prefix} alanlarını kullanabilirsiniz.\n"
                "Örn: {yil}{seri}{no_pad}  =>  2025A000001"
            ),
        )
        hint.pack(anchor="w", padx=10, pady=(10, 4))

        top = ttk.Frame(self.tab_settings)
        top.pack(fill=tk.X, padx=10, pady=6)

        ttk.Button(top, text="➕/💾 Seri Kaydet", command=self.save_series).pack(side=tk.LEFT)
        ttk.Button(top, text="Varsayılan Seri (A) Oluştur", command=self.ensure_default_series).pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text="Yenile", command=self.refresh_series).pack(side=tk.LEFT, padx=10)

        form = ttk.LabelFrame(self.tab_settings, text="Seri")
        form.pack(fill=tk.X, padx=10, pady=(0, 8))

        r1 = ttk.Frame(form)
        r1.pack(fill=tk.X, pady=6)

        self.s_seri = LabeledEntry(r1, "Seri:", 10)
        self.s_seri.pack(side=tk.LEFT, padx=6)
        self.s_yil = LabeledEntry(r1, "Yıl:", 8)
        self.s_yil.pack(side=tk.LEFT, padx=6)
        self.s_prefix = LabeledEntry(r1, "Prefix:", 10)
        self.s_prefix.pack(side=tk.LEFT, padx=6)
        self.s_padding = LabeledEntry(r1, "Padding:", 8)
        self.s_padding.pack(side=tk.LEFT, padx=6)
        self.s_last = LabeledEntry(r1, "Son No:", 10)
        self.s_last.pack(side=tk.LEFT, padx=6)
        self.s_aktif = LabeledCombo(r1, "Aktif:", ["1", "0"], 6)
        self.s_aktif.pack(side=tk.LEFT, padx=6)

        r2 = ttk.Frame(form)
        r2.pack(fill=tk.X, pady=(0, 6))
        self.s_fmt = LabeledEntry(r2, "Format:", 70)
        self.s_fmt.pack(side=tk.LEFT, padx=6)

        cols = ("id", "seri", "yil", "prefix", "last_no", "padding", "format", "aktif")
        self.series_tree = ttk.Treeview(self.tab_settings, columns=cols, show="headings", height=10, selectmode="browse")
        for c in cols:
            self.series_tree.heading(c, text=c.upper())

        self.series_tree.column("id", width=55, anchor="center")
        self.series_tree.column("seri", width=70, anchor="center")
        self.series_tree.column("yil", width=70, anchor="center")
        self.series_tree.column("prefix", width=80)
        self.series_tree.column("last_no", width=80, anchor="e")
        self.series_tree.column("padding", width=70, anchor="e")
        self.series_tree.column("format", width=320)
        self.series_tree.column("aktif", width=60, anchor="center")

        self.series_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        try:
            self.series_tree.bind("<Double-1>", lambda _e: self.load_selected_series_into_form())
        except Exception:
            pass

        try:
            self.s_yil.set(str(date.today().year))
            self.s_prefix.set("FTR")
            self.s_padding.set("6")
            self.s_last.set("0")
            self.s_fmt.set("{yil}{seri}{no_pad}")
            self.s_aktif.set("1")
        except Exception:
            pass

        self.refresh_series()

    # -----------------
    # Tab: Rapor
    # -----------------
    def _build_report_tab(self):
        top = ttk.Frame(self.tab_report)
        top.pack(fill=tk.X, padx=8, pady=8)

        ttk.Button(top, text="Açık Faturalar", command=self.report_open_invoices).pack(side=tk.LEFT)
        ttk.Button(top, text="Satın Alma Siparişleri", command=self.report_purchase_orders).pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text="Bu Ay", command=lambda: self.report_month(date.today().year, date.today().month)).pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text="Satın Alma (Bu Ay)", command=lambda: self.report_purchase_month(date.today().year, date.today().month)).pack(
            side=tk.LEFT, padx=6
        )
        ttk.Button(top, text="Satın Alma (Tümü)", command=self.report_purchase_all).pack(side=tk.LEFT, padx=6)

        self.lbl_report = ttk.Label(top, text="")
        self.lbl_report.pack(side=tk.LEFT, padx=(10, 0))

        cols = ("id", "tarih", "no", "cari", "tur", "durum", "para", "toplam", "kalan")
        self.report_tree = ttk.Treeview(self.tab_report, columns=cols, show="headings", height=16, selectmode="browse")
        for c in cols:
            self.report_tree.heading(c, text=c.upper())

        self.report_tree.column("id", width=55, anchor="center")
        self.report_tree.column("tarih", width=95)
        self.report_tree.column("no", width=130)
        self.report_tree.column("cari", width=260)
        self.report_tree.column("tur", width=80, anchor="center")
        self.report_tree.column("durum", width=80, anchor="center")
        self.report_tree.column("para", width=55, anchor="center")
        self.report_tree.column("toplam", width=110, anchor="e")
        self.report_tree.column("kalan", width=110, anchor="e")

        self.report_tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

    def _clear_report_tree(self) -> None:
        try:
            for item_id in self.report_tree.get_children():
                self.report_tree.delete(item_id)
        except Exception:
            pass

    # -----------------
    # Genel: Refresh
    # -----------------
    def refresh(self):
        self._reload_edit_lists()
        self.refresh_list()
        self.refresh_payments()
        self.refresh_series()
        self.report_open_invoices(silent=True)

    def refresh_list(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        tur = self.f_tur.get()
        if tur == "(Tümü)":
            tur = ""
        durum = self.f_durum.get()
        if durum == "(Tümü)":
            durum = ""

        rows = self.app.db.fatura_list(
            q=self.f_q.get(),
            date_from=self.f_from.get(),
            date_to=self.f_to.get(),
            tur=tur,
            durum=durum,
        )

        total = 0.0
        for r in rows:
            fid = int(r["id"])
            tarih = fmt_tr_date(r["tarih"])
            no = _s(r["fatura_no"])
            cari = _s(r["cari_ad"])
            if not cari:
                try:
                    if r["cari_id"]:
                        cr = self.app.db.cari_get(int(r["cari_id"]))
                        cari = _s(cr["ad"]) if cr else ""
                except Exception:
                    pass
            para = _s(r["para"] or "TL")
            toplam = float(safe_float(r["genel_toplam"]))
            odendi = float(safe_float(r["odendi"]))
            kalan = float(safe_float(r["kalan"]))
            total += toplam
            self.tree.insert("", tk.END, values=(
                fid,
                tarih,
                no,
                _s(r["tur"]),
                _s(r["durum"]),
                cari,
                para,
                fmt_amount(toplam),
                fmt_amount(odendi),
                fmt_amount(kalan),
            ))

        self.lbl_top_info.config(text=f"Fatura Sayısı: {len(rows)}  •  Toplam: {fmt_amount(total)}")

    def refresh_payments(self):
        for i in self.pay_tree.get_children():
            self.pay_tree.delete(i)

        fid = self.current_fid
        if not fid:
            self.lbl_pay_sum.config(text="Seçili fatura yok")
            return

        pays = self.app.db.fatura_odeme_list(fid)
        odendi = self.app.db.fatura_odeme_toplam(fid)
        inv = self.app.db.fatura_get(fid)
        toplam = float(safe_float(inv["genel_toplam"])) if inv else 0.0
        kalan = toplam - float(odendi)

        for p in pays:
            self.pay_tree.insert("", tk.END, values=(
                int(p["id"]),
                fmt_tr_date(p["tarih"]),
                fmt_amount(p["tutar"]),
                _s(p["para"]),
                _s(p["odeme"]),
                _s(p["aciklama"]),
                _s(p["ref"]),
            ))

        self.lbl_pay_sum.config(text=f"Toplam: {fmt_amount(toplam)}  •  Ödendi: {fmt_amount(odendi)}  •  Kalan: {fmt_amount(kalan)}")

    # -----------------
    # Liste -> Aç
    # -----------------
    def _selected_invoice_id(self) -> Optional[int]:
        sel = self.tree.selection()
        if not sel:
            return None
        try:
            v = self.tree.item(sel[0], "values")
            return int(v[0])
        except Exception:
            return None

    def open_selected_invoice(self):
        fid = self._selected_invoice_id()
        if not fid:
            messagebox.showinfo(APP_TITLE, "Lütfen listeden bir fatura seçin.")
            return
        self.load_invoice(fid)
        try:
            self.nb.select(self.tab_edit)
        except Exception:
            pass

    # -----------------
    # Yeni / Yükle
    # -----------------
    def new_invoice(self):
        self.current_fid = None
        self._items = []

        try:
            self.e_tarih.set(_today_str())
            self.e_vade.set("")
            self.e_tur.set("Satış")
            self.e_durum.set("Taslak")
            self.e_para.set("TL")
        except Exception:
            pass

        # seri + no
        try:
            seri = self.e_seri.get() or "A"
            self.e_seri.set(seri)
            self.e_no.set(self.app.db.fatura_next_no(seri=seri))
        except Exception:
            self.e_no.set("")

        for w in (self.e_cari, self.e_vkn, self.e_vd, self.e_eposta, self.e_adres):
            try:
                w.set("")
            except Exception:
                pass

        try:
            self.e_notlar.delete("1.0", tk.END)
        except Exception:
            pass

        self._render_items()
        self._update_totals()
        self.refresh_payments()

    def load_invoice(self, fid: int):
        inv = self.app.db.fatura_get(int(fid))
        if not inv:
            messagebox.showerror(APP_TITLE, "Fatura bulunamadı")
            return

        self.current_fid = int(inv["id"])

        try:
            self.e_tarih.set(fmt_tr_date(inv["tarih"]))
            self.e_vade.set(fmt_tr_date(inv["vade"]) if _s(inv["vade"]) else "")
            self.e_tur.set(_s(inv["tur"]))
            self.e_durum.set(_s(inv["durum"]))
            self.e_seri.set(_s(inv["seri"]))
            self.e_no.set(_s(inv["fatura_no"]))
            self.e_para.set(_s(inv["para"]) or "TL")
            self.e_cari.set(_s(inv["cari_ad"]))
            self.e_vkn.set(_s(inv["cari_vkn"]))
            self.e_vd.set(_s(inv["cari_vergi_dairesi"]))
            self.e_eposta.set(_s(inv["cari_eposta"]))
            self.e_adres.set(_s(inv["cari_adres"]))
        except Exception:
            pass

        try:
            self.e_notlar.delete("1.0", tk.END)
            self.e_notlar.insert("1.0", _s(inv["notlar"]))
        except Exception:
            pass

        self._items = []
        for r in self.app.db.fatura_kalem_list(int(fid)):
            self._items.append({
                "sira": int(r["sira"] or 1),
                "urun": _s(r["urun"]),
                "aciklama": _s(r["aciklama"]),
                "miktar": float(safe_float(r["miktar"])),
                "birim": _s(r["birim"]),
                "birim_fiyat": float(safe_float(r["birim_fiyat"])),
                "iskonto_oran": float(safe_float(r["iskonto_oran"])),
                "kdv_oran": float(safe_float(r["kdv_oran"])),
                "ara_tutar": float(safe_float(r["ara_tutar"])),
                "iskonto_tutar": float(safe_float(r["iskonto_tutar"])),
                "kdv_tutar": float(safe_float(r["kdv_tutar"])),
                "toplam": float(safe_float(r["toplam"])),
            })

        self._render_items()
        self._update_totals()
        self.refresh_payments()

    # -----------------
    # Kalem işlemleri
    # -----------------
    def _render_items(self):
        for i in self.items_tree.get_children():
            self.items_tree.delete(i)

        self._items.sort(key=lambda x: int(x.get("sira") or 0))
        for k in self._items:
            self.items_tree.insert("", tk.END, values=(
                int(k.get("sira") or 0),
                _s(k.get("urun")),
                fmt_amount(k.get("miktar")),
                _s(k.get("birim")),
                fmt_amount(k.get("birim_fiyat")),
                fmt_amount(k.get("iskonto_oran")),
                fmt_amount(k.get("kdv_oran")),
                fmt_amount(k.get("ara_tutar")),
                fmt_amount(k.get("kdv_tutar")),
                fmt_amount(k.get("toplam")),
            ))

    def _selected_item_index(self) -> Optional[int]:
        sel = self.items_tree.selection()
        if not sel:
            return None
        try:
            v = self.items_tree.item(sel[0], "values")
            sira = int(float(v[0]))
        except Exception:
            return None
        for i, k in enumerate(self._items):
            if int(k.get("sira") or 0) == sira:
                return i
        return None

    def add_item(self):
        data = self._item_dialog(title="Kalem Ekle")
        if not data:
            return
        if not data.get("sira"):
            data["sira"] = (max([int(x.get("sira") or 0) for x in self._items]) + 1) if self._items else 1
        self._items.append(data)
        self._render_items()
        self._update_totals()

    def edit_item(self):
        idx = self._selected_item_index()
        if idx is None:
            messagebox.showinfo(APP_TITLE, "Lütfen bir kalem seçin.")
            return
        cur = dict(self._items[idx])
        data = self._item_dialog(title="Kalem Düzenle", initial=cur)
        if not data:
            return
        self._items[idx] = data
        self._render_items()
        self._update_totals()

    def delete_item(self):
        idx = self._selected_item_index()
        if idx is None:
            return
        if not messagebox.askyesno(APP_TITLE, "Kalemi silmek istiyor musunuz?"):
            return
        self._items.pop(idx)
        self._render_items()
        self._update_totals()

    def _item_dialog(self, *, title: str, initial: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        init = initial or {}

        win = tk.Toplevel(self)
        win.title(title)
        win.geometry("760x360")
        win.transient(self.winfo_toplevel())
        win.grab_set()

        frm = ttk.Frame(win)
        frm.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        r1 = ttk.Frame(frm)
        r1.pack(fill=tk.X, pady=6)

        e_sira = LabeledEntry(r1, "Sıra:", 6)
        e_sira.pack(side=tk.LEFT, padx=6)
        e_urun = LabeledEntry(r1, "Ürün/Hizmet:", 40)
        e_urun.pack(side=tk.LEFT, padx=6)

        r2 = ttk.Frame(frm)
        r2.pack(fill=tk.X, pady=6)

        e_miktar = LabeledEntry(r2, "Miktar:", 10)
        e_miktar.pack(side=tk.LEFT, padx=6)
        e_birim = LabeledCombo(r2, "Birim:", VAR_BIRIM, 10)
        e_birim.pack(side=tk.LEFT, padx=6)
        e_fiyat = LabeledEntry(r2, "Birim Fiyat:", 12)
        e_fiyat.pack(side=tk.LEFT, padx=6)
        e_isk = LabeledEntry(r2, "İskonto %:", 10)
        e_isk.pack(side=tk.LEFT, padx=6)
        e_kdv = LabeledCombo(r2, "KDV %:", VAR_KDV, 8)
        e_kdv.pack(side=tk.LEFT, padx=6)

        r3 = ttk.Frame(frm)
        r3.pack(fill=tk.X, pady=6)
        e_ack = LabeledEntry(r3, "Açıklama:", 70)
        e_ack.pack(side=tk.LEFT, padx=6)

        sum_lbl = ttk.Label(frm, text="")
        sum_lbl.pack(anchor="w", padx=6, pady=(6, 0))

        # defaults
        try:
            e_sira.set(_s(init.get("sira")))
            e_urun.set(_s(init.get("urun")))
            e_miktar.set(_s(init.get("miktar")) or "1")
            e_birim.set(_s(init.get("birim")) or "Adet")
            e_fiyat.set(_s(init.get("birim_fiyat")) or "0")
            e_isk.set(_s(init.get("iskonto_oran")) or "0")
            e_kdv.set(_s(init.get("kdv_oran")) or "20")
            e_ack.set(_s(init.get("aciklama")))
        except Exception:
            pass

        def calc_preview():
            miktar = float(safe_float(e_miktar.get()))
            fiyat = float(safe_float(e_fiyat.get()))
            isk = float(safe_float(e_isk.get()))
            kdv = float(safe_float(e_kdv.get()))
            ara = miktar * fiyat
            isk_t = ara * (isk / 100.0)
            ara2 = ara - isk_t
            kdv_t = ara2 * (kdv / 100.0)
            top = ara2 + kdv_t
            sum_lbl.config(text=f"Ara: {fmt_amount(ara2)}  •  KDV: {fmt_amount(kdv_t)}  •  Toplam: {fmt_amount(top)}")

        try:
            for w in (e_miktar, e_fiyat, e_isk):
                w.ent.bind("<KeyRelease>", lambda _e: calc_preview())
            e_kdv.cmb.bind("<<ComboboxSelected>>", lambda _e: calc_preview())
        except Exception:
            pass

        calc_preview()

        out: Dict[str, Any] = {}

        def ok():
            try:
                out["sira"] = int(float(safe_float(e_sira.get()))) if _s(e_sira.get()) else None
            except Exception:
                out["sira"] = None

            out["urun"] = _s(e_urun.get())
            out["aciklama"] = _s(e_ack.get())
            out["miktar"] = float(safe_float(e_miktar.get()))
            out["birim"] = _s(e_birim.get()) or "Adet"
            out["birim_fiyat"] = float(safe_float(e_fiyat.get()))
            out["iskonto_oran"] = float(safe_float(e_isk.get()))
            out["kdv_oran"] = float(safe_float(e_kdv.get()))

            ara = float(out["miktar"]) * float(out["birim_fiyat"])
            isk_t = ara * (float(out["iskonto_oran"]) / 100.0)
            ara2 = ara - isk_t
            kdv_t = ara2 * (float(out["kdv_oran"]) / 100.0)
            top = ara2 + kdv_t
            out["ara_tutar"] = ara2
            out["iskonto_tutar"] = isk_t
            out["kdv_tutar"] = kdv_t
            out["toplam"] = top

            if not out["urun"]:
                messagebox.showerror(APP_TITLE, "Ürün/Hizmet boş olamaz.")
                return

            win.destroy()

        def cancel():
            out.clear()
            win.destroy()

        b = ttk.Frame(frm)
        b.pack(fill=tk.X, pady=(12, 0))
        ttk.Button(b, text="İptal", command=cancel).pack(side=tk.RIGHT)
        ttk.Button(b, text="Tamam", command=ok).pack(side=tk.RIGHT, padx=8)

        win.wait_window()
        return out if out else None

    # -----------------
    # Toplam hesap
    # -----------------
    def _update_totals(self):
        ara = sum(float(safe_float(x.get("ara_tutar"))) for x in self._items)
        isk = sum(float(safe_float(x.get("iskonto_tutar"))) for x in self._items)
        kdv = sum(float(safe_float(x.get("kdv_tutar"))) for x in self._items)
        genel = sum(float(safe_float(x.get("toplam"))) for x in self._items)

        try:
            self.sum_ara.config(text=f"Ara Toplam: {fmt_amount(ara)}")
            self.sum_isk.config(text=f"İskonto: {fmt_amount(isk)}")
            self.sum_kdv.config(text=f"KDV: {fmt_amount(kdv)}")
            self.sum_genel.config(text=f"Genel: {fmt_amount(genel)}")
        except Exception:
            pass

    # -----------------
    # Kaydet / Sil
    # -----------------
    def _resolve_cari_id(self, cari_ad: str) -> Optional[int]:
        ad = _s(cari_ad)
        if not ad:
            return None
        try:
            r = self.app.db.cari_get_by_name(ad)
            return int(r["id"]) if r else None
        except Exception:
            return None

    def save_invoice(self):
        if not self._items:
            messagebox.showerror(APP_TITLE, "En az 1 kalem ekleyin.")
            return

        self._update_totals()

        header: Dict[str, Any] = {
            "tarih": self.e_tarih.get(),
            "vade": self.e_vade.get(),
            "tur": self.e_tur.get(),
            "durum": self.e_durum.get(),
            "seri": self.e_seri.get(),
            "fatura_no": self.e_no.get(),
            "cari_id": self._resolve_cari_id(self.e_cari.get()),
            "cari_ad": self.e_cari.get(),
            "cari_vkn": self.e_vkn.get(),
            "cari_vergi_dairesi": self.e_vd.get(),
            "cari_adres": self.e_adres.get(),
            "cari_eposta": self.e_eposta.get(),
            "para": self.e_para.get(),
            "ara_toplam": sum(float(safe_float(x.get("ara_tutar"))) for x in self._items),
            "iskonto_toplam": sum(float(safe_float(x.get("iskonto_tutar"))) for x in self._items),
            "kdv_toplam": sum(float(safe_float(x.get("kdv_tutar"))) for x in self._items),
            "genel_toplam": sum(float(safe_float(x.get("toplam"))) for x in self._items),
            "notlar": self.e_notlar.get("1.0", tk.END).strip(),
            "etiket": "",
        }

        # fatura no boşsa otomatik üret
        if not _s(header.get("fatura_no")):
            try:
                header["fatura_no"] = self.app.db.fatura_next_no(seri=_s(header.get("seri")) or "A")
                self.e_no.set(header["fatura_no"])
            except Exception:
                pass

        try:
            if self.current_fid:
                self.app.db.fatura_update(int(self.current_fid), header, self._items)
                self.app.db.log("Fatura", f"Güncellendi: {header.get('fatura_no')}")
            else:
                fid = self.app.db.fatura_create(header, self._items)
                self.current_fid = int(fid)
                self.app.db.log("Fatura", f"Oluşturuldu: {header.get('fatura_no')}")
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Kaydedilemedi: {e}")
            return

        self.refresh()
        messagebox.showinfo(APP_TITLE, "Fatura kaydedildi.")

    def delete_invoice(self):
        if not self.current_fid:
            messagebox.showinfo(APP_TITLE, "Seçili fatura yok.")
            return
        if not messagebox.askyesno(APP_TITLE, "Faturayı silmek istiyor musunuz?"):
            return
        try:
            self.app.db.fatura_delete(int(self.current_fid))
            self.app.db.log("Fatura", f"Silindi: {self.e_no.get()}")
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Silinemedi: {e}")
            return
        self.new_invoice()
        self.refresh()

    # -----------------
    # Tahsilat ekle/sil
    # -----------------
    def add_payment(self):
        if not self.current_fid:
            messagebox.showinfo(APP_TITLE, "Önce bir fatura kaydedin.")
            return

        win = tk.Toplevel(self)
        win.title("Tahsilat / Ödeme")
        win.geometry("520x240")
        win.transient(self.winfo_toplevel())
        win.grab_set()

        frm = ttk.Frame(win)
        frm.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        r1 = ttk.Frame(frm)
        r1.pack(fill=tk.X, pady=6)

        e_tarih = LabeledEntry(r1, "Tarih:", 12)
        e_tarih.pack(side=tk.LEFT, padx=6)
        e_tutar = LabeledEntry(r1, "Tutar:", 14)
        e_tutar.pack(side=tk.LEFT, padx=6)
        e_para = LabeledCombo(r1, "Para:", self.app.db.list_currencies(), 8)
        e_para.pack(side=tk.LEFT, padx=6)

        r2 = ttk.Frame(frm)
        r2.pack(fill=tk.X, pady=6)

        try:
            odeme_vals = self.app.db.list_payments()
        except Exception:
            odeme_vals = ["Nakit", "Havale", "Kredi Kartı"]
        e_odeme = LabeledCombo(r2, "Yöntem:", odeme_vals, 18)
        e_odeme.pack(side=tk.LEFT, padx=6)
        e_ref = LabeledEntry(r2, "Ref:", 18)
        e_ref.pack(side=tk.LEFT, padx=6)

        r3 = ttk.Frame(frm)
        r3.pack(fill=tk.X, pady=6)
        e_ack = LabeledEntry(r3, "Açıklama:", 52)
        e_ack.pack(side=tk.LEFT, padx=6)

        try:
            e_tarih.set(_today_str())
            e_para.set(self.e_para.get() or "TL")
            e_odeme.set(odeme_vals[0] if odeme_vals else "")
        except Exception:
            pass

        def ok():
            try:
                self.app.db.fatura_odeme_add(
                    fid=int(self.current_fid),
                    tarih=e_tarih.get(),
                    tutar=float(safe_float(e_tutar.get())),
                    para=e_para.get(),
                    odeme=e_odeme.get(),
                    aciklama=e_ack.get(),
                    ref=e_ref.get(),
                )
                self.app.db.log("Fatura Tahsilat", f"{self.e_no.get()} / {e_odeme.get()} / {e_tutar.get()}")
            except Exception as e:
                messagebox.showerror(APP_TITLE, f"Kaydedilemedi: {e}")
                return
            win.destroy()
            self.refresh_payments()
            self.refresh_list()

        ttk.Button(frm, text="İptal", command=lambda: win.destroy()).pack(side=tk.RIGHT)
        ttk.Button(frm, text="Kaydet", command=ok).pack(side=tk.RIGHT, padx=8)

    def delete_payment(self):
        sel = self.pay_tree.selection()
        if not sel:
            return
        try:
            v = self.pay_tree.item(sel[0], "values")
            oid = int(v[0])
        except Exception:
            return
        if not messagebox.askyesno(APP_TITLE, "Tahsilat/ödeme kaydını silmek istiyor musunuz?"):
            return
        try:
            self.app.db.fatura_odeme_delete(oid)
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Silinemedi: {e}")
            return
        self.refresh_payments()
        self.refresh_list()

    # -----------------
    # Seri ayarları
    # -----------------
    def ensure_default_series(self):
        try:
            y = int(self.s_yil.get() or date.today().year)
        except Exception:
            y = date.today().year
        try:
            self.app.db.fatura_seri_upsert(
                seri="A",
                yil=y,
                prefix="FTR",
                last_no=0,
                padding=6,
                fmt="{yil}{seri}{no_pad}",
                aktif=1,
            )
        except Exception as e:
            messagebox.showerror(APP_TITLE, str(e))
            return
        self.refresh_series()
        self._reload_edit_lists()
        messagebox.showinfo(APP_TITLE, "Varsayılan seri oluşturuldu.")

    def refresh_series(self):
        if not hasattr(self, "series_tree"):
            return
        for i in self.series_tree.get_children():
            self.series_tree.delete(i)
        try:
            rows = self.app.db.fatura_seri_list()
        except Exception:
            rows = []
        for r in rows:
            self.series_tree.insert("", tk.END, values=(
                int(r["id"]),
                _s(r["seri"]),
                int(r["yil"]),
                _s(r["prefix"]),
                int(r["last_no"]),
                int(r["padding"]),
                _s(r["format"]),
                int(r["aktif"]),
            ))

    def load_selected_series_into_form(self):
        sel = self.series_tree.selection()
        if not sel:
            return
        try:
            v = self.series_tree.item(sel[0], "values")
            # id, seri, yil, prefix, last_no, padding, format, aktif
            self.s_seri.set(v[1])
            self.s_yil.set(v[2])
            self.s_prefix.set(v[3])
            self.s_last.set(v[4])
            self.s_padding.set(v[5])
            self.s_fmt.set(v[6])
            self.s_aktif.set(v[7])
        except Exception:
            pass

    def save_series(self):
        try:
            seri = _s(self.s_seri.get())
            yil = int(float(safe_float(self.s_yil.get())))
            prefix = _s(self.s_prefix.get()) or "FTR"
            last_no = int(float(safe_float(self.s_last.get())))
            padding = int(float(safe_float(self.s_padding.get())))
            fmt = _s(self.s_fmt.get()) or "{yil}{seri}{no_pad}"
            aktif = int(float(safe_float(self.s_aktif.get() or 1)))
        except Exception:
            messagebox.showerror(APP_TITLE, "Seri formu hatalı.")
            return

        if not seri:
            messagebox.showerror(APP_TITLE, "Seri boş olamaz.")
            return

        try:
            self.app.db.fatura_seri_upsert(
                seri=seri,
                yil=yil,
                prefix=prefix,
                last_no=last_no,
                padding=padding,
                fmt=fmt,
                aktif=aktif,
            )
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Kaydedilemedi: {e}")
            return

        self.refresh_series()
        self._reload_edit_lists()
        messagebox.showinfo(APP_TITLE, "Seri kaydedildi.")

    # -----------------
    # Raporlar
    # -----------------
    def report_open_invoices(self, silent: bool = False):
        self._clear_report_tree()

        try:
            rows = self.app.db.fatura_list()
        except Exception:
            rows = []

        out = [r for r in rows if float(safe_float(r["kalan"])) > 0.0001 and _s(r["durum"]) != "İptal"]
        total_kalan = 0.0
        for r in out:
            fid = int(r["id"])
            tarih = fmt_tr_date(r["tarih"])
            no = _s(r["fatura_no"])
            cari = _s(r["cari_ad"])
            para = _s(r["para"] or "TL")
            toplam = float(safe_float(r["genel_toplam"]))
            kalan = float(safe_float(r["kalan"]))
            total_kalan += kalan
            self.report_tree.insert("", tk.END, values=(
                fid, tarih, no, cari, _s(r["tur"]), _s(r["durum"]), para, fmt_amount(toplam), fmt_amount(kalan)
            ))

        self.lbl_report.config(text=f"Açık fatura: {len(out)}  •  Kalan toplam: {fmt_amount(total_kalan)}")
        if not silent:
            try:
                self.nb.select(self.tab_report)
            except Exception:
                pass

    def report_purchase_orders(self, silent: bool = False):
        self._clear_report_tree()

        try:
            rows = self.app.db.fatura_list(tur="Alış")
        except Exception:
            rows = []

        out = [r for r in rows if _s(r["durum"]) != "İptal"]
        total = 0.0
        total_kalan = 0.0
        for r in out:
            fid = int(r["id"])
            tarih = fmt_tr_date(r["tarih"])
            no = _s(r["fatura_no"])
            cari = _s(r["cari_ad"])
            para = _s(r["para"] or "TL")
            toplam = float(safe_float(r["genel_toplam"]))
            kalan = float(safe_float(r["kalan"]))
            total += toplam
            total_kalan += kalan
            self.report_tree.insert("", tk.END, values=(
                fid, tarih, no, cari, _s(r["tur"]), _s(r["durum"]), para, fmt_amount(toplam), fmt_amount(kalan)
            ))

        self.lbl_report.config(
            text=f"Satın alma siparişi: {len(out)}  •  Toplam: {fmt_amount(total)}  •  Kalan: {fmt_amount(total_kalan)}"
        )
        if not silent:
            try:
                self.nb.select(self.tab_report)
            except Exception:
                pass

    def report_month(self, year: int, month: int):
        # basit rapor: belirtilen ayın faturaları
        for i in self.report_tree.get_children():
            self.report_tree.delete(i)
        try:
            df = date(year, month, 1).strftime("%d.%m.%Y")
            if month == 12:
                dt = date(year, 12, 31).strftime("%d.%m.%Y")
            else:
                dt = (date(year, month + 1, 1) - timedelta(days=1)).strftime("%d.%m.%Y")
        except Exception:
            # fallback: kullanma
            df, dt = "", ""

        try:
            rows = self.app.db.fatura_list(date_from=df, date_to=dt)
        except Exception:
            rows = []

        label = f"{year}-{month:02d}"
        total = 0.0
        for r in rows:
            fid = int(r["id"])
            tarih = fmt_tr_date(r["tarih"])
            no = _s(r["fatura_no"])
            cari = _s(r["cari_ad"])
            para = _s(r["para"] or "TL")
            toplam = float(safe_float(r["genel_toplam"]))
            kalan = float(safe_float(r["kalan"]))
            total += toplam
            self.report_tree.insert("", tk.END, values=(
                fid, tarih, no, cari, _s(r["tur"]), _s(r["durum"]), para, fmt_amount(toplam), fmt_amount(kalan)
            ))

        self.lbl_report.config(text=f"{label}: {len(rows)}  •  Toplam: {fmt_amount(total)}")
        try:
            self.nb.select(self.tab_report)
        except Exception:
            pass

    # -----------------
    # PDF
    # -----------------
    def export_pdf(self):
        if not self.current_fid:
            messagebox.showinfo(APP_TITLE, "PDF için önce bir fatura seçin/kaydedin.")
            return

        inv = self.app.db.fatura_get(int(self.current_fid))
        if not inv:
            return

        p = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            title="Fatura PDF Kaydet",
            initialfile=f"{_s(inv['fatura_no'])}.pdf",
        )
        if not p:
            return

        try:
            self._build_invoice_pdf(inv, self.app.db.fatura_kalem_list(int(self.current_fid)), p)
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"PDF oluşturulamadı: {e}")
            return

        messagebox.showinfo(APP_TITLE, "PDF kaydedildi.")

    def _build_invoice_pdf(self, inv, kalemler, filepath: str):
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors

        doc = SimpleDocTemplate(filepath, pagesize=A4, leftMargin=28, rightMargin=28, topMargin=28, bottomMargin=28)
        font_reg, font_bold = ensure_pdf_fonts()

        styles = getSampleStyleSheet()
        for k in ("Normal", "Title", "Heading1", "Heading2"):
            if k in styles:
                styles[k].fontName = (font_bold if k != "Normal" else font_reg)

        story = []
        story.append(Paragraph(f"<b>Fatura</b> - {_s(inv['fatura_no'])}", styles["Title"]))
        story.append(Spacer(1, 6))
        story.append(Paragraph(f"Tarih: {fmt_tr_date(inv['tarih'])}  •  Tür: {_s(inv['tur'])}  •  Durum: {_s(inv['durum'])}", styles["Normal"]))
        if _s(inv.get('vade')):
            story.append(Paragraph(f"Vade: {fmt_tr_date(inv['vade'])}", styles["Normal"]))
        story.append(Spacer(1, 8))

        cari = _s(inv.get('cari_ad'))
        story.append(Paragraph(f"<b>Cari:</b> {cari}", styles["Normal"]))
        vkn = _s(inv.get('cari_vkn'))
        if vkn:
            story.append(Paragraph(f"<b>VKN/TCKN:</b> {vkn}", styles["Normal"]))
        vd = _s(inv.get('cari_vergi_dairesi'))
        if vd:
            story.append(Paragraph(f"<b>Vergi Dairesi:</b> {vd}", styles["Normal"]))
        adr = _s(inv.get('cari_adres'))
        if adr:
            story.append(Paragraph(f"<b>Adres:</b> {adr}", styles["Normal"]))
        story.append(Spacer(1, 10))

        table_data = [["Sıra", "Ürün/Hizmet", "Miktar", "Birim", "B.Fiyat", "Ara", "KDV", "Toplam"]]
        for k in kalemler:
            table_data.append([
                str(k['sira']),
                (_s(k['urun']) + ("\n" + _s(k['aciklama']) if _s(k['aciklama']) else ""))[:120],
                fmt_amount(k['miktar']),
                _s(k['birim']),
                fmt_amount(k['birim_fiyat']),
                fmt_amount(k['ara_tutar']),
                fmt_amount(k['kdv_tutar']),
                fmt_amount(k['toplam']),
            ])

        tbl = Table(table_data, repeatRows=1, colWidths=[35, 220, 55, 45, 60, 55, 55, 60])
        tbl.setStyle(TableStyle([
            ("FONTNAME", (0,0), (-1,0), font_bold),
            ("FONTNAME", (0,1), (-1,-1), font_reg),
            ("FONTSIZE", (0,0), (-1,0), 9),
            ("FONTSIZE", (0,1), (-1,-1), 8),
            ("GRID", (0,0), (-1,-1), 0.25, colors.grey),
            ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
            ("ALIGN", (2,1), (-1,-1), "RIGHT"),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 10))

        story.append(Paragraph(
            f"Ara Toplam: {fmt_amount(inv['ara_toplam'])}  •  İskonto: {fmt_amount(inv['iskonto_toplam'])}  •  "
            f"KDV: {fmt_amount(inv['kdv_toplam'])}  •  <b>Genel: {fmt_amount(inv['genel_toplam'])}</b>",
            styles["Normal"],
        ))

        notlar = _s(inv.get('notlar'))
        if notlar:
            story.append(Spacer(1, 8))
            story.append(Paragraph(f"<b>Notlar:</b> {notlar}", styles["Normal"]))

        doc.build(story)


def build(master, app):
    return FaturaFrame(master, app)
