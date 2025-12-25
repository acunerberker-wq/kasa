# -*- coding: utf-8 -*-
"""UI Plugin: Stok Yönetimi."""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

import tkinter as tk
from tkinter import ttk, messagebox

from ...config import APP_TITLE
from ...utils import today_iso, fmt_tr_date, parse_number_smart, safe_float, fmt_amount
from ..base import BaseView
from ..widgets import LabeledEntry, LabeledCombo

if TYPE_CHECKING:
    from ...app import App

PLUGIN_META = {
    "key": "stok",
    "nav_text": "📦 Stok",
    "page_title": "Stok Yönetimi",
    "order": 18,
}


class StokFrame(BaseView):
    def __init__(self, master, app: "App"):
        self.app = app
        super().__init__(master, app)
        self.edit_urun_id: Optional[int] = None
        self.build_ui()

    def build_ui(self) -> None:
        self._build()

    # -----------------
    # UI
    # -----------------
    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=10, pady=(10, 6))

        ttk.Button(top, text="Yenile", command=self.refresh).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(top, text="Yeni Ürün", command=self.clear_urun_form).pack(side=tk.LEFT)
        ttk.Button(top, text="Yeni Hareket", command=self.clear_hareket_form).pack(side=tk.LEFT, padx=6)

        self.lbl_summary = ttk.Label(top, text="")
        self.lbl_summary.pack(side=tk.LEFT, padx=12)

        mid = ttk.Frame(self)
        mid.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.nb = ttk.Notebook(mid)
        self.nb.pack(fill=tk.BOTH, expand=True)

        self.tab_urun = ttk.Frame(self.nb)
        self.tab_hareket = ttk.Frame(self.nb)
        self.tab_lokasyon = ttk.Frame(self.nb)
        self.tab_parti = ttk.Frame(self.nb)
        self.tab_rapor = ttk.Frame(self.nb)

        self.nb.add(self.tab_urun, text="📦 Ürünler")
        self.nb.add(self.tab_hareket, text="🔁 Hareketler")
        self.nb.add(self.tab_lokasyon, text="🏷️ Lokasyonlar")
        self.nb.add(self.tab_parti, text="🧪 Partiler")
        self.nb.add(self.tab_rapor, text="📊 Raporlar")

        self._build_urun_tab(self.tab_urun)
        self._build_hareket_tab(self.tab_hareket)
        self._build_lokasyon_tab(self.tab_lokasyon)
        self._build_parti_tab(self.tab_parti)
        self._build_rapor_tab(self.tab_rapor)

        self.reload_settings()
        self.refresh()

    def reload_settings(self):
        try:
            self.in_urun_kategori.cmb.configure(values=self.app.db.list_stock_categories())
        except Exception:
            pass
        try:
            self.in_urun_birim.cmb.configure(values=self.app.db.list_stock_units())
        except Exception:
            pass
        try:
            self.in_hareket_birim.cmb.configure(values=self.app.db.list_stock_units())
        except Exception:
            pass
        try:
            self._reload_tedarikci_combo()
        except Exception:
            pass
        try:
            self._reload_urun_combo()
        except Exception:
            pass
        try:
            self._reload_lokasyon_combo()
        except Exception:
            pass

    # -----------------
    # Ürünler
    # -----------------
    def _build_urun_tab(self, parent: ttk.Frame):
        form = ttk.LabelFrame(parent, text="Ürün Kartı")
        form.pack(fill=tk.X, padx=6, pady=6)

        row1 = ttk.Frame(form)
        row1.pack(fill=tk.X, pady=4)
        self.in_urun_kod = LabeledEntry(row1, "Kod:", 14)
        self.in_urun_kod.pack(side=tk.LEFT, padx=6)
        self.in_urun_ad = LabeledEntry(row1, "Ad:", 24)
        self.in_urun_ad.pack(side=tk.LEFT, padx=6)
        self.in_urun_kategori = LabeledCombo(row1, "Kategori:", [], 18)
        self.in_urun_kategori.pack(side=tk.LEFT, padx=6)
        self.in_urun_birim = LabeledCombo(row1, "Birim:", [], 10)
        self.in_urun_birim.pack(side=tk.LEFT, padx=6)

        row2 = ttk.Frame(form)
        row2.pack(fill=tk.X, pady=4)
        self.in_urun_min = LabeledEntry(row2, "Min Stok:", 12)
        self.in_urun_min.pack(side=tk.LEFT, padx=6)
        self.in_urun_kritik = LabeledEntry(row2, "Kritik:", 12)
        self.in_urun_kritik.pack(side=tk.LEFT, padx=6)
        self.in_urun_max = LabeledEntry(row2, "Max Stok:", 12)
        self.in_urun_max.pack(side=tk.LEFT, padx=6)
        self.in_urun_raf = LabeledEntry(row2, "Raf:", 12)
        self.in_urun_raf.pack(side=tk.LEFT, padx=6)
        self.in_urun_barkod = LabeledEntry(row2, "Barkod:", 16)
        self.in_urun_barkod.pack(side=tk.LEFT, padx=6)

        row3 = ttk.Frame(form)
        row3.pack(fill=tk.X, pady=4)
        self.in_urun_tedarikci = LabeledCombo(row3, "Tedarikçi:", ["(Yok)"], 22)
        self.in_urun_tedarikci.pack(side=tk.LEFT, padx=6)
        self.in_urun_aktif = LabeledCombo(row3, "Durum:", ["Aktif", "Pasif"], 10)
        self.in_urun_aktif.pack(side=tk.LEFT, padx=6)
        self.in_urun_aktif.set("Aktif")
        self.in_urun_aciklama = LabeledEntry(row3, "Açıklama:", 40)
        self.in_urun_aciklama.pack(side=tk.LEFT, padx=6, fill=tk.X, expand=True)

        row4 = ttk.Frame(form)
        row4.pack(fill=tk.X, pady=(6, 2))
        ttk.Button(row4, text="Kaydet", command=self.save_urun).pack(side=tk.LEFT, padx=6)
        ttk.Button(row4, text="Yeni", command=self.clear_urun_form).pack(side=tk.LEFT, padx=6)
        ttk.Button(row4, text="Seçiliyi Sil", command=self.delete_urun).pack(side=tk.LEFT, padx=6)
        self.lbl_urun_mode = ttk.Label(row4, text="")
        self.lbl_urun_mode.pack(side=tk.LEFT, padx=10)

        filt = ttk.LabelFrame(parent, text="Filtre")
        filt.pack(fill=tk.X, padx=6, pady=(0, 6))
        frow = ttk.Frame(filt)
        frow.pack(fill=tk.X, pady=4)
        self.f_urun_q = LabeledEntry(frow, "Ara:", 22)
        self.f_urun_q.pack(side=tk.LEFT, padx=6)
        self.f_urun_durum = LabeledCombo(frow, "Durum:", ["(Tümü)", "Aktif", "Pasif"], 10)
        self.f_urun_durum.pack(side=tk.LEFT, padx=6)
        self.f_urun_durum.set("(Tümü)")
        ttk.Button(frow, text="Ara", command=self.refresh_urun_list).pack(side=tk.LEFT, padx=6)

        cols = (
            "id",
            "kod",
            "ad",
            "kategori",
            "birim",
            "stok",
            "min",
            "kritik",
            "max",
            "raf",
            "tedarikci",
            "aktif",
        )
        self.tree_urun = ttk.Treeview(parent, columns=cols, show="headings", height=12, selectmode="browse")
        for c in cols:
            self.tree_urun.heading(c, text=c.upper())
        self.tree_urun.column("id", width=55, anchor="center")
        self.tree_urun.column("kod", width=110)
        self.tree_urun.column("ad", width=180)
        self.tree_urun.column("kategori", width=120)
        self.tree_urun.column("birim", width=70, anchor="center")
        self.tree_urun.column("stok", width=90, anchor="e")
        self.tree_urun.column("min", width=80, anchor="e")
        self.tree_urun.column("kritik", width=80, anchor="e")
        self.tree_urun.column("max", width=80, anchor="e")
        self.tree_urun.column("raf", width=80)
        self.tree_urun.column("tedarikci", width=160)
        self.tree_urun.column("aktif", width=70, anchor="center")
        self.tree_urun.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))
        self.tree_urun.bind("<Double-1>", lambda _e: self.edit_selected_urun())

    def _reload_tedarikci_combo(self):
        caris = self.app.db.cari_list(only_active=True)
        values = ["(Yok)"] + [f"{r['id']} - {r['ad']}" for r in caris]
        cur = self.in_urun_tedarikci.get() or "(Yok)"
        self.in_urun_tedarikci.cmb.configure(values=values)
        if cur not in values:
            cur = "(Yok)"
        self.in_urun_tedarikci.set(cur)

    def _parse_tedarikci_id(self, val: str) -> Optional[int]:
        if not val or val == "(Yok)":
            return None
        try:
            return int(str(val).split("-", 1)[0].strip())
        except Exception:
            return None

    def clear_urun_form(self):
        self.edit_urun_id = None
        self.in_urun_kod.set("")
        self.in_urun_ad.set("")
        try:
            self.in_urun_kategori.set("")
        except Exception:
            pass
        try:
            self.in_urun_birim.set("Adet")
        except Exception:
            pass
        self.in_urun_min.set("0")
        self.in_urun_kritik.set("0")
        self.in_urun_max.set("0")
        self.in_urun_raf.set("")
        self.in_urun_barkod.set("")
        self.in_urun_tedarikci.set("(Yok)")
        self.in_urun_aktif.set("Aktif")
        self.in_urun_aciklama.set("")
        self.lbl_urun_mode.config(text="Yeni kayıt")

    def save_urun(self):
        kod = self.in_urun_kod.get().strip()
        ad = self.in_urun_ad.get().strip()
        if not kod or not ad:
            messagebox.showerror(APP_TITLE, "Kod ve ad zorunludur.")
            return
        kategori = self.in_urun_kategori.get().strip()
        birim = self.in_urun_birim.get().strip() or "Adet"
        min_stok = parse_number_smart(self.in_urun_min.get())
        kritik_stok = parse_number_smart(self.in_urun_kritik.get())
        max_stok = parse_number_smart(self.in_urun_max.get())
        raf = self.in_urun_raf.get().strip()
        barkod = self.in_urun_barkod.get().strip()
        tedarikci_id = self._parse_tedarikci_id(self.in_urun_tedarikci.get())
        aktif = 1 if self.in_urun_aktif.get() == "Aktif" else 0
        aciklama = self.in_urun_aciklama.get().strip()
        try:
            if self.edit_urun_id:
                self.app.db.stok_urun_update(
                    self.edit_urun_id,
                    kod,
                    ad,
                    kategori,
                    birim,
                    min_stok,
                    max_stok,
                    kritik_stok,
                    raf,
                    tedarikci_id,
                    barkod,
                    aktif,
                    aciklama,
                )
            else:
                self.app.db.stok_urun_add(
                    kod,
                    ad,
                    kategori,
                    birim,
                    min_stok,
                    max_stok,
                    kritik_stok,
                    raf,
                    tedarikci_id,
                    barkod,
                    aktif,
                    aciklama,
                )
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Ürün kaydedilemedi: {e}")
            return
        self.refresh_urun_list()
        self.clear_urun_form()
        self._reload_urun_combo()
        self._reload_parti_urun_combo()

    def edit_selected_urun(self):
        sel = self.tree_urun.selection()
        if not sel:
            return
        iid = sel[0]
        values = self.tree_urun.item(iid, "values")
        if not values:
            return
        try:
            uid = int(values[0])
        except Exception:
            return
        r = self.app.db.stok_urun_get(uid)
        if not r:
            return
        self.edit_urun_id = uid
        self.in_urun_kod.set(r["kod"])
        self.in_urun_ad.set(r["ad"])
        self.in_urun_kategori.set(r["kategori"])
        self.in_urun_birim.set(r["birim"])
        self.in_urun_min.set(str(r["min_stok"]))
        self.in_urun_kritik.set(str(r["kritik_stok"]))
        self.in_urun_max.set(str(r["max_stok"]))
        self.in_urun_raf.set(r["raf"])
        self.in_urun_barkod.set(r["barkod"])
        if r["tedarikci_id"]:
            if hasattr(r, "get"):
                self.in_urun_tedarikci.set(f"{r['tedarikci_id']} - {r.get('tedarikci_ad', '')}")
            else:
                self.in_urun_tedarikci.set(str(r["tedarikci_id"]))
        else:
            self.in_urun_tedarikci.set("(Yok)")
        self.in_urun_aktif.set("Aktif" if int(r["aktif"]) == 1 else "Pasif")
        self.in_urun_aciklama.set(r["aciklama"])
        self.lbl_urun_mode.config(text=f"Düzenleniyor: {uid}")

    def delete_urun(self):
        sel = self.tree_urun.selection()
        if not sel:
            return
        iid = sel[0]
        values = self.tree_urun.item(iid, "values")
        if not values:
            return
        try:
            uid = int(values[0])
        except Exception:
            return
        if not messagebox.askyesno(APP_TITLE, "Seçili ürünü silmek istiyor musunuz?"):
            return
        try:
            self.app.db.stok_urun_delete(uid)
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Silinemedi: {e}")
            return
        self.refresh_urun_list()
        self.clear_urun_form()
        self._reload_urun_combo()
        self._reload_parti_urun_combo()

    def refresh_urun_list(self):
        self.tree_urun.delete(*self.tree_urun.get_children())
        q = self.f_urun_q.get().strip()
        durum = self.f_urun_durum.get()
        only_active = True if durum == "Aktif" else False
        rows = self.app.db.stok_urun_list(q=q, only_active=only_active)
        if durum == "Pasif":
            rows = [r for r in rows if int(r["aktif"]) == 0]
        total = 0.0
        for r in rows:
            stok = self.app.db.stok_urun_stok_ozet(int(r["id"]))["toplam"]
            total += stok
            self.tree_urun.insert(
                "",
                tk.END,
                values=(
                    r["id"],
                    r["kod"],
                    r["ad"],
                    r["kategori"],
                    r["birim"],
                    fmt_amount(stok),
                    fmt_amount(r["min_stok"]),
                    fmt_amount(r["kritik_stok"]),
                    fmt_amount(r["max_stok"]),
                    r["raf"],
                    r.get("tedarikci_ad", "") if hasattr(r, "get") else r["tedarikci_id"],
                    "Aktif" if int(r["aktif"]) == 1 else "Pasif",
                ),
            )
        self.lbl_summary.config(text=f"Toplam ürün: {len(rows)} | Stok toplam: {fmt_amount(total)}")

    # -----------------
    # Hareketler
    # -----------------
    def _build_hareket_tab(self, parent: ttk.Frame):
        form = ttk.LabelFrame(parent, text="Stok Hareketi")
        form.pack(fill=tk.X, padx=6, pady=6)

        row1 = ttk.Frame(form)
        row1.pack(fill=tk.X, pady=4)
        self.in_hareket_tarih = LabeledEntry(row1, "Tarih:", 12)
        self.in_hareket_tarih.pack(side=tk.LEFT, padx=6)
        ttk.Button(row1, text="Bugün", command=lambda: self.in_hareket_tarih.set(fmt_tr_date(today_iso()))).pack(side=tk.LEFT, padx=6)

        self.in_hareket_tip = LabeledCombo(
            row1,
            "Tip:",
            ["Giris", "Cikis", "Transfer", "Fire", "Sayim", "Duzeltme", "Uretim"],
            12,
        )
        self.in_hareket_tip.pack(side=tk.LEFT, padx=6)
        self.in_hareket_miktar = LabeledEntry(row1, "Miktar:", 12)
        self.in_hareket_miktar.pack(side=tk.LEFT, padx=6)
        self.in_hareket_birim = LabeledCombo(row1, "Birim:", [], 10)
        self.in_hareket_birim.pack(side=tk.LEFT, padx=6)

        row2 = ttk.Frame(form)
        row2.pack(fill=tk.X, pady=4)
        self.in_hareket_urun = LabeledCombo(row2, "Ürün:", ["(Seç)"], 30)
        self.in_hareket_urun.pack(side=tk.LEFT, padx=6)
        try:
            self.in_hareket_urun.cmb.bind("<<ComboboxSelected>>", lambda _e: self._reload_parti_combo())
        except Exception:
            pass
        self.in_hareket_kaynak = LabeledCombo(row2, "Kaynak:", ["(Yok)"], 18)
        self.in_hareket_kaynak.pack(side=tk.LEFT, padx=6)
        self.in_hareket_hedef = LabeledCombo(row2, "Hedef:", ["(Yok)"], 18)
        self.in_hareket_hedef.pack(side=tk.LEFT, padx=6)

        row3 = ttk.Frame(form)
        row3.pack(fill=tk.X, pady=4)
        self.in_hareket_parti = LabeledCombo(row3, "Parti:", ["(Yok)"], 16)
        self.in_hareket_parti.pack(side=tk.LEFT, padx=6)
        self.in_hareket_maliyet = LabeledEntry(row3, "Maliyet:", 12)
        self.in_hareket_maliyet.pack(side=tk.LEFT, padx=6)
        self.in_hareket_aciklama = LabeledEntry(row3, "Açıklama:", 45)
        self.in_hareket_aciklama.pack(side=tk.LEFT, padx=6, fill=tk.X, expand=True)

        row4 = ttk.Frame(form)
        row4.pack(fill=tk.X, pady=(6, 2))
        ttk.Button(row4, text="Kaydet", command=self.save_hareket).pack(side=tk.LEFT, padx=6)
        ttk.Button(row4, text="Yeni", command=self.clear_hareket_form).pack(side=tk.LEFT, padx=6)
        ttk.Button(row4, text="Seçiliyi Sil", command=self.delete_hareket).pack(side=tk.LEFT, padx=6)

        filt = ttk.LabelFrame(parent, text="Filtre")
        filt.pack(fill=tk.X, padx=6, pady=(0, 6))
        frow = ttk.Frame(filt)
        frow.pack(fill=tk.X, pady=4)
        self.f_hareket_q = LabeledEntry(frow, "Ara:", 22)
        self.f_hareket_q.pack(side=tk.LEFT, padx=6)
        self.f_hareket_urun = LabeledCombo(frow, "Ürün:", ["(Tümü)"], 24)
        self.f_hareket_urun.pack(side=tk.LEFT, padx=6)
        ttk.Button(frow, text="Ara", command=self.refresh_hareket_list).pack(side=tk.LEFT, padx=6)

        cols = (
            "id",
            "tarih",
            "urun_kod",
            "urun_ad",
            "tip",
            "miktar",
            "birim",
            "kaynak",
            "hedef",
            "parti",
            "maliyet",
            "aciklama",
        )
        self.tree_hareket = ttk.Treeview(parent, columns=cols, show="headings", height=12, selectmode="browse")
        for c in cols:
            self.tree_hareket.heading(c, text=c.upper())
        self.tree_hareket.column("id", width=55, anchor="center")
        self.tree_hareket.column("tarih", width=95)
        self.tree_hareket.column("urun_kod", width=110)
        self.tree_hareket.column("urun_ad", width=180)
        self.tree_hareket.column("tip", width=90, anchor="center")
        self.tree_hareket.column("miktar", width=90, anchor="e")
        self.tree_hareket.column("birim", width=70, anchor="center")
        self.tree_hareket.column("kaynak", width=120)
        self.tree_hareket.column("hedef", width=120)
        self.tree_hareket.column("parti", width=100)
        self.tree_hareket.column("maliyet", width=100, anchor="e")
        self.tree_hareket.column("aciklama", width=280)
        self.tree_hareket.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

    def _reload_urun_combo(self):
        urunler = self.app.db.stok_urun_list(only_active=True)
        values = ["(Seç)"] + [f"{r['id']} - {r['kod']} | {r['ad']}" for r in urunler]
        cur = self.in_hareket_urun.get() or "(Seç)"
        self.in_hareket_urun.cmb.configure(values=values)
        if cur not in values:
            cur = "(Seç)"
        self.in_hareket_urun.set(cur)

        values_filter = ["(Tümü)"] + [f"{r['id']} - {r['kod']} | {r['ad']}" for r in urunler]
        cur_filter = self.f_hareket_urun.get() or "(Tümü)"
        self.f_hareket_urun.cmb.configure(values=values_filter)
        if cur_filter not in values_filter:
            cur_filter = "(Tümü)"
        self.f_hareket_urun.set(cur_filter)

    def _reload_lokasyon_combo(self):
        loks = self.app.db.stok_lokasyon_list(only_active=True)
        values = ["(Yok)"] + [f"{r['id']} - {r['ad']}" for r in loks]
        for cmb in (self.in_hareket_kaynak, self.in_hareket_hedef):
            cur = cmb.get() or "(Yok)"
            cmb.cmb.configure(values=values)
            if cur not in values:
                cur = "(Yok)"
            cmb.set(cur)

    def _reload_parti_combo(self):
        urun_id = self._parse_urun_id(self.in_hareket_urun.get())
        if not urun_id:
            self.in_hareket_parti.cmb.configure(values=["(Yok)"])
            self.in_hareket_parti.set("(Yok)")
            return
        partiler = self.app.db.stok_parti_list(urun_id=urun_id)
        values = ["(Yok)"] + [f"{r['id']} - {r['parti_no']}" for r in partiler]
        cur = self.in_hareket_parti.get() or "(Yok)"
        self.in_hareket_parti.cmb.configure(values=values)
        if cur not in values:
            cur = "(Yok)"
        self.in_hareket_parti.set(cur)

    def _parse_urun_id(self, val: str) -> Optional[int]:
        if not val or val in ("(Seç)", "(Tümü)"):
            return None
        try:
            return int(str(val).split("-", 1)[0].strip())
        except Exception:
            return None

    def _parse_lokasyon_id(self, val: str) -> Optional[int]:
        if not val or val == "(Yok)":
            return None
        try:
            return int(str(val).split("-", 1)[0].strip())
        except Exception:
            return None

    def _parse_parti_id(self, val: str) -> Optional[int]:
        if not val or val == "(Yok)":
            return None
        try:
            return int(str(val).split("-", 1)[0].strip())
        except Exception:
            return None

    def clear_hareket_form(self):
        self.in_hareket_tarih.set(fmt_tr_date(today_iso()))
        self.in_hareket_tip.set("Giris")
        self.in_hareket_miktar.set("0")
        self.in_hareket_birim.set("Adet")
        self.in_hareket_urun.set("(Seç)")
        self.in_hareket_kaynak.set("(Yok)")
        self.in_hareket_hedef.set("(Yok)")
        self.in_hareket_parti.set("(Yok)")
        self.in_hareket_maliyet.set("0")
        self.in_hareket_aciklama.set("")

    def save_hareket(self):
        urun_id = self._parse_urun_id(self.in_hareket_urun.get())
        if not urun_id:
            messagebox.showerror(APP_TITLE, "Ürün seçiniz.")
            return
        tip = self.in_hareket_tip.get().strip()
        miktar = parse_number_smart(self.in_hareket_miktar.get())
        if tip in ("Cikis", "Fire", "Transfer"):
            miktar = abs(miktar)
        birim = self.in_hareket_birim.get().strip() or "Adet"
        kaynak = self._parse_lokasyon_id(self.in_hareket_kaynak.get())
        hedef = self._parse_lokasyon_id(self.in_hareket_hedef.get())
        parti_id = self._parse_parti_id(self.in_hareket_parti.get())
        maliyet = parse_number_smart(self.in_hareket_maliyet.get())
        aciklama = self.in_hareket_aciklama.get().strip()
        try:
            self.app.db.stok_hareket_add(
                self.in_hareket_tarih.get(),
                urun_id,
                tip,
                miktar,
                birim,
                kaynak,
                hedef,
                parti_id,
                "manuel",
                None,
                maliyet,
                aciklama,
            )
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Hareket kaydedilemedi: {e}")
            return
        self.refresh_hareket_list()
        self.refresh_urun_list()
        self.refresh_raporlar()
        self.clear_hareket_form()

    def delete_hareket(self):
        sel = self.tree_hareket.selection()
        if not sel:
            return
        values = self.tree_hareket.item(sel[0], "values")
        if not values:
            return
        try:
            hid = int(values[0])
        except Exception:
            return
        if not messagebox.askyesno(APP_TITLE, "Seçili hareket silinsin mi?"):
            return
        try:
            self.app.db.stok_hareket_delete(hid)
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Silinemedi: {e}")
            return
        self.refresh_hareket_list()
        self.refresh_urun_list()
        self.refresh_raporlar()

    def refresh_hareket_list(self):
        self.tree_hareket.delete(*self.tree_hareket.get_children())
        q = self.f_hareket_q.get().strip()
        urun_id = self._parse_urun_id(self.f_hareket_urun.get())
        rows = self.app.db.stok_hareket_list(q=q, urun_id=urun_id, limit=800)
        for r in rows:
            self.tree_hareket.insert(
                "",
                tk.END,
                values=(
                    r["id"],
                    fmt_tr_date(r["tarih"]),
                    r["urun_kod"],
                    r["urun_ad"],
                    r["tip"],
                    fmt_amount(r["miktar"]),
                    r["birim"],
                    r["kaynak_lokasyon"] or "",
                    r["hedef_lokasyon"] or "",
                    r["parti_no"] or "",
                    fmt_amount(r["maliyet"]),
                    r["aciklama"],
                ),
            )

    # -----------------
    # Lokasyonlar
    # -----------------
    def _build_lokasyon_tab(self, parent: ttk.Frame):
        form = ttk.LabelFrame(parent, text="Lokasyon")
        form.pack(fill=tk.X, padx=6, pady=6)
        row = ttk.Frame(form)
        row.pack(fill=tk.X, pady=4)
        self.in_lokasyon_ad = LabeledEntry(row, "Ad:", 20)
        self.in_lokasyon_ad.pack(side=tk.LEFT, padx=6)
        self.in_lokasyon_aciklama = LabeledEntry(row, "Açıklama:", 40)
        self.in_lokasyon_aciklama.pack(side=tk.LEFT, padx=6, fill=tk.X, expand=True)
        ttk.Button(row, text="Kaydet", command=self.save_lokasyon).pack(side=tk.LEFT, padx=6)
        ttk.Button(row, text="Yeni", command=self.clear_lokasyon_form).pack(side=tk.LEFT, padx=6)
        ttk.Button(row, text="Aktif/Pasif", command=self.toggle_lokasyon).pack(side=tk.LEFT, padx=6)

        cols = ("id", "ad", "aciklama", "aktif")
        self.tree_lokasyon = ttk.Treeview(parent, columns=cols, show="headings", height=14, selectmode="browse")
        for c in cols:
            self.tree_lokasyon.heading(c, text=c.upper())
        self.tree_lokasyon.column("id", width=55, anchor="center")
        self.tree_lokasyon.column("ad", width=200)
        self.tree_lokasyon.column("aciklama", width=360)
        self.tree_lokasyon.column("aktif", width=80, anchor="center")
        self.tree_lokasyon.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))
        self.tree_lokasyon.bind("<Double-1>", lambda _e: self.edit_selected_lokasyon())

    def clear_lokasyon_form(self):
        self.in_lokasyon_ad.set("")
        self.in_lokasyon_aciklama.set("")

    def save_lokasyon(self):
        ad = self.in_lokasyon_ad.get().strip()
        if not ad:
            messagebox.showerror(APP_TITLE, "Lokasyon adı gerekli.")
            return
        aciklama = self.in_lokasyon_aciklama.get().strip()
        try:
            self.app.db.stok_lokasyon_upsert(ad=ad, aciklama=aciklama, aktif=1)
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Kaydedilemedi: {e}")
            return
        self.refresh_lokasyon_list()
        self._reload_lokasyon_combo()
        self.clear_lokasyon_form()

    def edit_selected_lokasyon(self):
        sel = self.tree_lokasyon.selection()
        if not sel:
            return
        values = self.tree_lokasyon.item(sel[0], "values")
        if not values:
            return
        self.in_lokasyon_ad.set(values[1])
        self.in_lokasyon_aciklama.set(values[2])

    def toggle_lokasyon(self):
        sel = self.tree_lokasyon.selection()
        if not sel:
            return
        values = self.tree_lokasyon.item(sel[0], "values")
        if not values:
            return
        try:
            lid = int(values[0])
        except Exception:
            return
        aktif = 0 if str(values[3]) == "Aktif" else 1
        try:
            self.app.db.stok_lokasyon_set_active(lid, aktif)
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Güncellenemedi: {e}")
            return
        self.refresh_lokasyon_list()
        self._reload_lokasyon_combo()

    def refresh_lokasyon_list(self):
        self.tree_lokasyon.delete(*self.tree_lokasyon.get_children())
        rows = self.app.db.stok_lokasyon_list(only_active=False)
        for r in rows:
            self.tree_lokasyon.insert(
                "",
                tk.END,
                values=(r["id"], r["ad"], r["aciklama"], "Aktif" if int(r["aktif"]) == 1 else "Pasif"),
            )

    # -----------------
    # Partiler
    # -----------------
    def _build_parti_tab(self, parent: ttk.Frame):
        form = ttk.LabelFrame(parent, text="Parti")
        form.pack(fill=tk.X, padx=6, pady=6)
        row = ttk.Frame(form)
        row.pack(fill=tk.X, pady=4)
        self.in_parti_urun = LabeledCombo(row, "Ürün:", ["(Seç)"], 28)
        self.in_parti_urun.pack(side=tk.LEFT, padx=6)
        self.in_parti_no = LabeledEntry(row, "Parti No:", 16)
        self.in_parti_no.pack(side=tk.LEFT, padx=6)
        self.in_parti_skt = LabeledEntry(row, "SKT:", 12)
        self.in_parti_skt.pack(side=tk.LEFT, padx=6)
        self.in_parti_uretim = LabeledEntry(row, "Üretim:", 12)
        self.in_parti_uretim.pack(side=tk.LEFT, padx=6)

        row2 = ttk.Frame(form)
        row2.pack(fill=tk.X, pady=4)
        self.in_parti_aciklama = LabeledEntry(row2, "Açıklama:", 60)
        self.in_parti_aciklama.pack(side=tk.LEFT, padx=6, fill=tk.X, expand=True)
        ttk.Button(row2, text="Kaydet", command=self.save_parti).pack(side=tk.LEFT, padx=6)
        ttk.Button(row2, text="Yeni", command=self.clear_parti_form).pack(side=tk.LEFT, padx=6)

        cols = ("id", "urun_id", "parti_no", "skt", "uretim_tarih", "aciklama")
        self.tree_parti = ttk.Treeview(parent, columns=cols, show="headings", height=14, selectmode="browse")
        for c in cols:
            self.tree_parti.heading(c, text=c.upper())
        self.tree_parti.column("id", width=55, anchor="center")
        self.tree_parti.column("urun_id", width=90, anchor="center")
        self.tree_parti.column("parti_no", width=140)
        self.tree_parti.column("skt", width=110)
        self.tree_parti.column("uretim_tarih", width=110)
        self.tree_parti.column("aciklama", width=360)
        self.tree_parti.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

    def _reload_parti_urun_combo(self):
        urunler = self.app.db.stok_urun_list(only_active=True)
        values = ["(Seç)"] + [f"{r['id']} - {r['kod']} | {r['ad']}" for r in urunler]
        cur = self.in_parti_urun.get() or "(Seç)"
        self.in_parti_urun.cmb.configure(values=values)
        if cur not in values:
            cur = "(Seç)"
        self.in_parti_urun.set(cur)

    def clear_parti_form(self):
        self.in_parti_urun.set("(Seç)")
        self.in_parti_no.set("")
        self.in_parti_skt.set("")
        self.in_parti_uretim.set("")
        self.in_parti_aciklama.set("")

    def save_parti(self):
        urun_id = self._parse_urun_id(self.in_parti_urun.get())
        parti_no = self.in_parti_no.get().strip()
        if not urun_id or not parti_no:
            messagebox.showerror(APP_TITLE, "Ürün ve parti numarası gerekli.")
            return
        skt = self.in_parti_skt.get().strip()
        uretim = self.in_parti_uretim.get().strip()
        aciklama = self.in_parti_aciklama.get().strip()
        try:
            self.app.db.stok_parti_upsert(urun_id=urun_id, parti_no=parti_no, skt=skt, uretim_tarih=uretim, aciklama=aciklama)
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Kaydedilemedi: {e}")
            return
        self.refresh_parti_list()
        self._reload_parti_combo()
        self.clear_parti_form()

    def refresh_parti_list(self):
        self.tree_parti.delete(*self.tree_parti.get_children())
        rows = self.app.db.stok_parti_list()
        for r in rows:
            self.tree_parti.insert(
                "",
                tk.END,
                values=(r["id"], r["urun_id"], r["parti_no"], r["skt"], r["uretim_tarih"], r["aciklama"]),
            )

    # -----------------
    # Raporlar
    # -----------------
    def _build_rapor_tab(self, parent: ttk.Frame):
        top = ttk.Frame(parent)
        top.pack(fill=tk.X, padx=6, pady=6)
        ttk.Button(top, text="Yenile", command=self.refresh_raporlar).pack(side=tk.LEFT, padx=6)

        self.lbl_rapor = ttk.Label(top, text="")
        self.lbl_rapor.pack(side=tk.LEFT, padx=10)

        box_low = ttk.LabelFrame(parent, text="Kritik / Minimum Stoklar")
        box_low.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

        cols_low = ("id", "kod", "ad", "stok", "min", "kritik", "birim")
        self.tree_low = ttk.Treeview(box_low, columns=cols_low, show="headings", height=8, selectmode="browse")
        for c in cols_low:
            self.tree_low.heading(c, text=c.upper())
        self.tree_low.column("id", width=55, anchor="center")
        self.tree_low.column("kod", width=120)
        self.tree_low.column("ad", width=200)
        self.tree_low.column("stok", width=90, anchor="e")
        self.tree_low.column("min", width=90, anchor="e")
        self.tree_low.column("kritik", width=90, anchor="e")
        self.tree_low.column("birim", width=80, anchor="center")
        self.tree_low.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        box_loc = ttk.LabelFrame(parent, text="Lokasyon Bazlı Toplam Stok")
        box_loc.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))
        cols_loc = ("lokasyon", "miktar")
        self.tree_loc = ttk.Treeview(box_loc, columns=cols_loc, show="headings", height=8, selectmode="browse")
        for c in cols_loc:
            self.tree_loc.heading(c, text=c.upper())
        self.tree_loc.column("lokasyon", width=220)
        self.tree_loc.column("miktar", width=120, anchor="e")
        self.tree_loc.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

    def refresh_raporlar(self):
        self.tree_low.delete(*self.tree_low.get_children())
        rows = self.app.db.stok_urun_list(only_active=True)
        low_count = 0
        for r in rows:
            stok = self.app.db.stok_urun_stok_ozet(int(r["id"]))["toplam"]
            min_stok = safe_float(r["min_stok"])
            kritik = safe_float(r["kritik_stok"])
            if stok <= kritik or stok <= min_stok:
                low_count += 1
                self.tree_low.insert(
                    "",
                    tk.END,
                    values=(
                        r["id"],
                        r["kod"],
                        r["ad"],
                        fmt_amount(stok),
                        fmt_amount(min_stok),
                        fmt_amount(kritik),
                        r["birim"],
                    ),
                )
        self.tree_loc.delete(*self.tree_loc.get_children())
        loc_rows = self.app.db.stok_summary_by_location()
        for r in loc_rows:
            self.tree_loc.insert("", tk.END, values=(r["lokasyon"], fmt_amount(r["miktar"])))
        self.lbl_rapor.config(text=f"Kritik/Minimum kayıt: {low_count}")

    # -----------------
    # Genel refresh
    # -----------------
    def refresh(self, data=None):
        self._reload_tedarikci_combo()
        self._reload_urun_combo()
        self._reload_parti_urun_combo()
        self._reload_lokasyon_combo()
        self._reload_parti_combo()
        self.clear_urun_form()
        self.clear_hareket_form()
        self.clear_lokasyon_form()
        self.clear_parti_form()
        self.refresh_urun_list()
        self.refresh_hareket_list()
        self.refresh_lokasyon_list()
        self.refresh_parti_list()
        self.refresh_raporlar()


def build(master, app):
    return StokFrame(master, app)
