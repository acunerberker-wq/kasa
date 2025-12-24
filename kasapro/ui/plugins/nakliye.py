# -*- coding: utf-8 -*-
"""UI Plugin: Nakliye (Taşıma) yönetimi."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import tkinter as tk
from tkinter import ttk, messagebox

from ...config import APP_TITLE
from ...utils import today_iso, fmt_tr_date, parse_date_smart, safe_float
from ..widgets import LabeledEntry, LabeledCombo, MoneyEntry, SimpleField


PLUGIN_META = {
    "key": "nakliye",
    "nav_text": "🚚 Nakliye",
    "page_title": "Nakliye Yönetimi",
    "order": 34,
}


class NakliyeFrame(ttk.Frame):
    def __init__(self, master, app: "App"):
        super().__init__(master)
        self.app = app

        self.edit_firma_id: Optional[int] = None
        self.edit_arac_id: Optional[int] = None
        self.edit_rota_id: Optional[int] = None
        self.edit_is_id: Optional[int] = None
        self.edit_islem_id: Optional[int] = None

        self.firma_map: Dict[str, Optional[int]] = {}
        self.arac_map: Dict[str, Optional[int]] = {}
        self.rota_map: Dict[str, Optional[int]] = {}
        self.is_map: Dict[str, Optional[int]] = {}

        self._build()

    # -----------------
    # UI
    # -----------------
    def _build(self):
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.tab_firma = ttk.Frame(self.nb)
        self.tab_arac = ttk.Frame(self.nb)
        self.tab_rota = ttk.Frame(self.nb)
        self.tab_is = ttk.Frame(self.nb)
        self.tab_islem = ttk.Frame(self.nb)

        self.nb.add(self.tab_firma, text="🏢 Firmalar")
        self.nb.add(self.tab_arac, text="🚛 Araçlar")
        self.nb.add(self.tab_rota, text="🗺️ Rotalar")
        self.nb.add(self.tab_is, text="🗓️ İş Planlama")
        self.nb.add(self.tab_islem, text="🧾 İşlemler")

        self._build_firmalar(self.tab_firma)
        self._build_araclar(self.tab_arac)
        self._build_rotalar(self.tab_rota)
        self._build_isler(self.tab_is)
        self._build_islemler(self.tab_islem)

        self.refresh_all()

    # -----------------
    # Firmalar
    # -----------------
    def _build_firmalar(self, parent: ttk.Frame):
        top = ttk.LabelFrame(parent, text="Nakliye Firması")
        top.pack(fill=tk.X, padx=6, pady=6)

        row1 = ttk.Frame(top); row1.pack(fill=tk.X, pady=4)
        self.in_firma_ad = LabeledEntry(row1, "Firma Adı:", 24)
        self.in_firma_ad.pack(side=tk.LEFT, padx=6)
        self.in_firma_tel = LabeledEntry(row1, "Telefon:", 16)
        self.in_firma_tel.pack(side=tk.LEFT, padx=6)
        self.in_firma_eposta = LabeledEntry(row1, "E-posta:", 22)
        self.in_firma_eposta.pack(side=tk.LEFT, padx=6)

        row2 = ttk.Frame(top); row2.pack(fill=tk.X, pady=4)
        self.in_firma_adres = LabeledEntry(row2, "Adres:", 50)
        self.in_firma_adres.pack(side=tk.LEFT, padx=6, fill=tk.X, expand=True)
        self.in_firma_aktif = tk.IntVar(value=1)
        ttk.Checkbutton(row2, text="Aktif", variable=self.in_firma_aktif).pack(side=tk.LEFT, padx=6)

        row3 = ttk.Frame(top); row3.pack(fill=tk.X, pady=4)
        ttk.Label(row3, text="Notlar:").pack(side=tk.LEFT, padx=(6, 4))
        self.in_firma_not = tk.Text(row3, height=2, width=60)
        self.in_firma_not.pack(side=tk.LEFT, padx=4, fill=tk.X, expand=True)

        row4 = ttk.Frame(top); row4.pack(fill=tk.X, pady=4)
        ttk.Button(row4, text="Kaydet", command=self.firma_save).pack(side=tk.LEFT, padx=6)
        ttk.Button(row4, text="Yeni", command=self.firma_clear).pack(side=tk.LEFT, padx=6)
        self.lbl_firma_mode = ttk.Label(row4, text="")
        self.lbl_firma_mode.pack(side=tk.LEFT, padx=10)

        mid = ttk.LabelFrame(parent, text="Firmalar")
        mid.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        frow = ttk.Frame(mid); frow.pack(fill=tk.X, pady=4)
        self.f_firma_q = LabeledEntry(frow, "Ara:", 24)
        self.f_firma_q.pack(side=tk.LEFT, padx=6)
        ttk.Button(frow, text="Yenile", command=self.firma_refresh).pack(side=tk.LEFT, padx=6)

        cols = ("id", "ad", "telefon", "eposta", "adres", "aktif", "notlar")
        self.tree_firma = ttk.Treeview(mid, columns=cols, show="headings", height=10)
        for c in cols:
            self.tree_firma.heading(c, text=c.upper())
        self.tree_firma.column("id", width=50, anchor="center")
        self.tree_firma.column("ad", width=180)
        self.tree_firma.column("telefon", width=120)
        self.tree_firma.column("eposta", width=160)
        self.tree_firma.column("adres", width=200)
        self.tree_firma.column("aktif", width=60, anchor="center")
        self.tree_firma.column("notlar", width=240)
        self.tree_firma.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.tree_firma.bind("<Double-1>", lambda _e: self.firma_edit_selected())

        btm = ttk.Frame(mid); btm.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(btm, text="Seçili Kaydı Düzenle", command=self.firma_edit_selected).pack(side=tk.LEFT, padx=6)
        ttk.Button(btm, text="Seçili Kaydı Sil", command=self.firma_delete_selected).pack(side=tk.LEFT, padx=6)

    def firma_clear(self):
        self.edit_firma_id = None
        self.in_firma_ad.set("")
        self.in_firma_tel.set("")
        self.in_firma_eposta.set("")
        self.in_firma_adres.set("")
        self.in_firma_aktif.set(1)
        try:
            self.in_firma_not.delete("1.0", tk.END)
        except Exception:
            pass
        self.lbl_firma_mode.config(text="")

    def firma_refresh(self):
        q = self.f_firma_q.get().strip()
        rows = self.app.db.nakliye_firma_list(q=q)
        self.tree_firma.delete(*self.tree_firma.get_children())
        for r in rows:
            self.tree_firma.insert(
                "",
                tk.END,
                values=(r["id"], r["ad"], r["telefon"], r["eposta"], r["adres"], "Evet" if r["aktif"] else "Hayır", r["notlar"]),
            )
        self._refresh_firma_combo()

    def firma_save(self):
        ad = self.in_firma_ad.get().strip()
        if not ad:
            messagebox.showerror(APP_TITLE, "Firma adı boş olamaz.")
            return
        telefon = self.in_firma_tel.get().strip()
        eposta = self.in_firma_eposta.get().strip()
        adres = self.in_firma_adres.get().strip()
        notlar = self.in_firma_not.get("1.0", tk.END).strip()
        aktif = int(self.in_firma_aktif.get() or 0)

        try:
            if self.edit_firma_id:
                self.app.db.nakliye_firma_update(self.edit_firma_id, ad, telefon=telefon, eposta=eposta, adres=adres, aktif=aktif, notlar=notlar)
                self.lbl_firma_mode.config(text="Güncellendi.")
            else:
                self.app.db.nakliye_firma_add(ad, telefon=telefon, eposta=eposta, adres=adres, aktif=aktif, notlar=notlar)
                self.lbl_firma_mode.config(text="Kaydedildi.")
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Firma kaydedilemedi: {exc}")
            return

        self.firma_refresh()
        self.firma_clear()

    def _firma_selected_id(self) -> Optional[int]:
        sel = self.tree_firma.selection()
        if not sel:
            return None
        vals = self.tree_firma.item(sel[0], "values")
        try:
            return int(vals[0])
        except Exception:
            return None

    def firma_edit_selected(self):
        fid = self._firma_selected_id()
        if not fid:
            messagebox.showinfo(APP_TITLE, "Lütfen bir firma seçin.")
            return
        r = self.app.db.nakliye_firma_get(fid)
        if not r:
            return
        self.edit_firma_id = int(r["id"])
        self.in_firma_ad.set(r["ad"])
        self.in_firma_tel.set(r["telefon"])
        self.in_firma_eposta.set(r["eposta"])
        self.in_firma_adres.set(r["adres"])
        self.in_firma_aktif.set(int(r["aktif"]))
        try:
            self.in_firma_not.delete("1.0", tk.END)
            self.in_firma_not.insert("1.0", r["notlar"] or "")
        except Exception:
            pass
        self.lbl_firma_mode.config(text="Düzenleme modu")

    def firma_delete_selected(self):
        fid = self._firma_selected_id()
        if not fid:
            messagebox.showinfo(APP_TITLE, "Lütfen bir firma seçin.")
            return
        if not messagebox.askyesno(APP_TITLE, "Seçili firmayı silmek istiyor musunuz?"):
            return
        try:
            self.app.db.nakliye_firma_delete(fid)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Firma silinemedi: {exc}")
            return
        self.firma_refresh()

    # -----------------
    # Araçlar
    # -----------------
    def _build_araclar(self, parent: ttk.Frame):
        top = ttk.LabelFrame(parent, text="Araç Bilgileri")
        top.pack(fill=tk.X, padx=6, pady=6)

        row1 = ttk.Frame(top); row1.pack(fill=tk.X, pady=4)
        self.in_arac_plaka = LabeledEntry(row1, "Plaka:", 14)
        self.in_arac_plaka.pack(side=tk.LEFT, padx=6)
        self.in_arac_firma = LabeledCombo(row1, "Firma:", [], 22)
        self.in_arac_firma.pack(side=tk.LEFT, padx=6)
        self.in_arac_tip = LabeledEntry(row1, "Tip:", 14)
        self.in_arac_tip.pack(side=tk.LEFT, padx=6)
        self.in_arac_marka = LabeledEntry(row1, "Marka:", 14)
        self.in_arac_marka.pack(side=tk.LEFT, padx=6)

        row2 = ttk.Frame(top); row2.pack(fill=tk.X, pady=4)
        self.in_arac_model = LabeledEntry(row2, "Model:", 14)
        self.in_arac_model.pack(side=tk.LEFT, padx=6)
        self.in_arac_yil = LabeledEntry(row2, "Yıl:", 8)
        self.in_arac_yil.pack(side=tk.LEFT, padx=6)
        self.in_arac_kapasite = LabeledEntry(row2, "Kapasite:", 12)
        self.in_arac_kapasite.pack(side=tk.LEFT, padx=6)
        self.in_arac_surucu = LabeledEntry(row2, "Sürücü:", 16)
        self.in_arac_surucu.pack(side=tk.LEFT, padx=6)
        self.in_arac_aktif = tk.IntVar(value=1)
        ttk.Checkbutton(row2, text="Aktif", variable=self.in_arac_aktif).pack(side=tk.LEFT, padx=6)

        row3 = ttk.Frame(top); row3.pack(fill=tk.X, pady=4)
        ttk.Label(row3, text="Notlar:").pack(side=tk.LEFT, padx=(6, 4))
        self.in_arac_not = tk.Text(row3, height=2, width=60)
        self.in_arac_not.pack(side=tk.LEFT, padx=4, fill=tk.X, expand=True)

        row4 = ttk.Frame(top); row4.pack(fill=tk.X, pady=4)
        ttk.Button(row4, text="Kaydet", command=self.arac_save).pack(side=tk.LEFT, padx=6)
        ttk.Button(row4, text="Yeni", command=self.arac_clear).pack(side=tk.LEFT, padx=6)
        self.lbl_arac_mode = ttk.Label(row4, text="")
        self.lbl_arac_mode.pack(side=tk.LEFT, padx=10)

        mid = ttk.LabelFrame(parent, text="Araçlar")
        mid.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        frow = ttk.Frame(mid); frow.pack(fill=tk.X, pady=4)
        self.f_arac_q = LabeledEntry(frow, "Ara:", 24)
        self.f_arac_q.pack(side=tk.LEFT, padx=6)
        ttk.Button(frow, text="Yenile", command=self.arac_refresh).pack(side=tk.LEFT, padx=6)

        cols = ("id", "plaka", "firma", "tip", "marka", "model", "yil", "kapasite", "surucu", "aktif")
        self.tree_arac = ttk.Treeview(mid, columns=cols, show="headings", height=10)
        for c in cols:
            self.tree_arac.heading(c, text=c.upper())
        self.tree_arac.column("id", width=50, anchor="center")
        self.tree_arac.column("plaka", width=100)
        self.tree_arac.column("firma", width=160)
        self.tree_arac.column("tip", width=110)
        self.tree_arac.column("marka", width=100)
        self.tree_arac.column("model", width=100)
        self.tree_arac.column("yil", width=70, anchor="center")
        self.tree_arac.column("kapasite", width=100)
        self.tree_arac.column("surucu", width=120)
        self.tree_arac.column("aktif", width=60, anchor="center")
        self.tree_arac.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.tree_arac.bind("<Double-1>", lambda _e: self.arac_edit_selected())

        btm = ttk.Frame(mid); btm.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(btm, text="Seçili Kaydı Düzenle", command=self.arac_edit_selected).pack(side=tk.LEFT, padx=6)
        ttk.Button(btm, text="Seçili Kaydı Sil", command=self.arac_delete_selected).pack(side=tk.LEFT, padx=6)

    def arac_clear(self):
        self.edit_arac_id = None
        self.in_arac_plaka.set("")
        self.in_arac_tip.set("")
        self.in_arac_marka.set("")
        self.in_arac_model.set("")
        self.in_arac_yil.set("")
        self.in_arac_kapasite.set("")
        self.in_arac_surucu.set("")
        self.in_arac_aktif.set(1)
        try:
            self.in_arac_not.delete("1.0", tk.END)
        except Exception:
            pass
        self.lbl_arac_mode.config(text="")

    def _refresh_firma_combo(self):
        rows = self.app.db.nakliye_firma_list(only_active=False)
        self.firma_map = {"(Seçiniz)": None}
        values = ["(Seçiniz)"]
        for r in rows:
            label = f"{r['ad']}"
            self.firma_map[label] = int(r["id"])
            values.append(label)
        self.in_arac_firma.cmb["values"] = values
        if not self.in_arac_firma.get():
            self.in_arac_firma.set("(Seçiniz)")
        self.in_is_firma.cmb["values"] = values
        if not self.in_is_firma.get():
            self.in_is_firma.set("(Seçiniz)")

    def arac_refresh(self):
        q = self.f_arac_q.get().strip()
        rows = self.app.db.nakliye_arac_list(q=q)
        self.tree_arac.delete(*self.tree_arac.get_children())
        for r in rows:
            self.tree_arac.insert(
                "",
                tk.END,
                values=(
                    r["id"],
                    r["plaka"],
                    r["firma_ad"] or "",
                    r["tip"],
                    r["marka"],
                    r["model"],
                    r["yil"],
                    r["kapasite"],
                    r["surucu"],
                    "Evet" if r["aktif"] else "Hayır",
                ),
            )
        self._refresh_arac_combo()

    def _refresh_arac_combo(self):
        rows = self.app.db.nakliye_arac_list(only_active=False)
        self.arac_map = {"(Seçiniz)": None}
        values = ["(Seçiniz)"]
        for r in rows:
            label = f"{r['plaka']}"
            self.arac_map[label] = int(r["id"])
            values.append(label)
        self.in_is_arac.cmb["values"] = values
        if not self.in_is_arac.get():
            self.in_is_arac.set("(Seçiniz)")

    def arac_save(self):
        plaka = self.in_arac_plaka.get().strip()
        if not plaka:
            messagebox.showerror(APP_TITLE, "Plaka boş olamaz.")
            return
        firma_id = self.firma_map.get(self.in_arac_firma.get())
        tip = self.in_arac_tip.get().strip()
        marka = self.in_arac_marka.get().strip()
        model = self.in_arac_model.get().strip()
        yil = self.in_arac_yil.get().strip()
        kapasite = self.in_arac_kapasite.get().strip()
        surucu = self.in_arac_surucu.get().strip()
        aktif = int(self.in_arac_aktif.get() or 0)
        notlar = self.in_arac_not.get("1.0", tk.END).strip()

        try:
            if self.edit_arac_id:
                self.app.db.nakliye_arac_update(
                    self.edit_arac_id,
                    plaka,
                    firma_id=firma_id,
                    tip=tip,
                    marka=marka,
                    model=model,
                    yil=yil,
                    kapasite=kapasite,
                    surucu=surucu,
                    aktif=aktif,
                    notlar=notlar,
                )
                self.lbl_arac_mode.config(text="Güncellendi.")
            else:
                self.app.db.nakliye_arac_add(
                    plaka,
                    firma_id=firma_id,
                    tip=tip,
                    marka=marka,
                    model=model,
                    yil=yil,
                    kapasite=kapasite,
                    surucu=surucu,
                    aktif=aktif,
                    notlar=notlar,
                )
                self.lbl_arac_mode.config(text="Kaydedildi.")
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Araç kaydedilemedi: {exc}")
            return

        self.arac_refresh()
        self.arac_clear()

    def _arac_selected_id(self) -> Optional[int]:
        sel = self.tree_arac.selection()
        if not sel:
            return None
        vals = self.tree_arac.item(sel[0], "values")
        try:
            return int(vals[0])
        except Exception:
            return None

    def arac_edit_selected(self):
        aid = self._arac_selected_id()
        if not aid:
            messagebox.showinfo(APP_TITLE, "Lütfen bir araç seçin.")
            return
        r = self.app.db.nakliye_arac_get(aid)
        if not r:
            return
        self.edit_arac_id = int(r["id"])
        self.in_arac_plaka.set(r["plaka"])
        self.in_arac_tip.set(r["tip"])
        self.in_arac_marka.set(r["marka"])
        self.in_arac_model.set(r["model"])
        self.in_arac_yil.set(r["yil"])
        self.in_arac_kapasite.set(r["kapasite"])
        self.in_arac_surucu.set(r["surucu"])
        self.in_arac_aktif.set(int(r["aktif"]))
        try:
            self.in_arac_not.delete("1.0", tk.END)
            self.in_arac_not.insert("1.0", r["notlar"] or "")
        except Exception:
            pass
        firmalabel = "(Seçiniz)"
        for label, fid in self.firma_map.items():
            if fid == r["firma_id"]:
                firmalabel = label
                break
        self.in_arac_firma.set(firmalabel)
        self.lbl_arac_mode.config(text="Düzenleme modu")

    def arac_delete_selected(self):
        aid = self._arac_selected_id()
        if not aid:
            messagebox.showinfo(APP_TITLE, "Lütfen bir araç seçin.")
            return
        if not messagebox.askyesno(APP_TITLE, "Seçili aracı silmek istiyor musunuz?"):
            return
        try:
            self.app.db.nakliye_arac_delete(aid)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Araç silinemedi: {exc}")
            return
        self.arac_refresh()

    # -----------------
    # Rotalar
    # -----------------
    def _build_rotalar(self, parent: ttk.Frame):
        top = ttk.LabelFrame(parent, text="Rota Bilgileri")
        top.pack(fill=tk.X, padx=6, pady=6)

        row1 = ttk.Frame(top); row1.pack(fill=tk.X, pady=4)
        self.in_rota_ad = LabeledEntry(row1, "Rota Adı:", 20)
        self.in_rota_ad.pack(side=tk.LEFT, padx=6)
        self.in_rota_cikis = LabeledEntry(row1, "Çıkış:", 16)
        self.in_rota_cikis.pack(side=tk.LEFT, padx=6)
        self.in_rota_varis = LabeledEntry(row1, "Varış:", 16)
        self.in_rota_varis.pack(side=tk.LEFT, padx=6)

        row2 = ttk.Frame(top); row2.pack(fill=tk.X, pady=4)
        self.in_rota_mesafe = LabeledEntry(row2, "Mesafe (km):", 12)
        self.in_rota_mesafe.pack(side=tk.LEFT, padx=6)
        self.in_rota_sure = LabeledEntry(row2, "Süre (saat):", 12)
        self.in_rota_sure.pack(side=tk.LEFT, padx=6)
        self.in_rota_aktif = tk.IntVar(value=1)
        ttk.Checkbutton(row2, text="Aktif", variable=self.in_rota_aktif).pack(side=tk.LEFT, padx=6)

        row3 = ttk.Frame(top); row3.pack(fill=tk.X, pady=4)
        ttk.Label(row3, text="Notlar:").pack(side=tk.LEFT, padx=(6, 4))
        self.in_rota_not = tk.Text(row3, height=2, width=60)
        self.in_rota_not.pack(side=tk.LEFT, padx=4, fill=tk.X, expand=True)

        row4 = ttk.Frame(top); row4.pack(fill=tk.X, pady=4)
        ttk.Button(row4, text="Kaydet", command=self.rota_save).pack(side=tk.LEFT, padx=6)
        ttk.Button(row4, text="Yeni", command=self.rota_clear).pack(side=tk.LEFT, padx=6)
        self.lbl_rota_mode = ttk.Label(row4, text="")
        self.lbl_rota_mode.pack(side=tk.LEFT, padx=10)

        mid = ttk.LabelFrame(parent, text="Rotalar")
        mid.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        frow = ttk.Frame(mid); frow.pack(fill=tk.X, pady=4)
        self.f_rota_q = LabeledEntry(frow, "Ara:", 24)
        self.f_rota_q.pack(side=tk.LEFT, padx=6)
        ttk.Button(frow, text="Yenile", command=self.rota_refresh).pack(side=tk.LEFT, padx=6)

        cols = ("id", "ad", "cikis", "varis", "mesafe", "sure", "aktif", "notlar")
        self.tree_rota = ttk.Treeview(mid, columns=cols, show="headings", height=10)
        for c in cols:
            self.tree_rota.heading(c, text=c.upper())
        self.tree_rota.column("id", width=50, anchor="center")
        self.tree_rota.column("ad", width=160)
        self.tree_rota.column("cikis", width=140)
        self.tree_rota.column("varis", width=140)
        self.tree_rota.column("mesafe", width=100, anchor="e")
        self.tree_rota.column("sure", width=100, anchor="e")
        self.tree_rota.column("aktif", width=60, anchor="center")
        self.tree_rota.column("notlar", width=240)
        self.tree_rota.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.tree_rota.bind("<Double-1>", lambda _e: self.rota_edit_selected())

        btm = ttk.Frame(mid); btm.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(btm, text="Seçili Kaydı Düzenle", command=self.rota_edit_selected).pack(side=tk.LEFT, padx=6)
        ttk.Button(btm, text="Seçili Kaydı Sil", command=self.rota_delete_selected).pack(side=tk.LEFT, padx=6)

    def rota_clear(self):
        self.edit_rota_id = None
        self.in_rota_ad.set("")
        self.in_rota_cikis.set("")
        self.in_rota_varis.set("")
        self.in_rota_mesafe.set("")
        self.in_rota_sure.set("")
        self.in_rota_aktif.set(1)
        try:
            self.in_rota_not.delete("1.0", tk.END)
        except Exception:
            pass
        self.lbl_rota_mode.config(text="")

    def _refresh_rota_combo(self):
        rows = self.app.db.nakliye_rota_list(only_active=False)
        self.rota_map = {"(Seçiniz)": None}
        values = ["(Seçiniz)"]
        for r in rows:
            label = f"{r['ad']} ({r['cikis']} → {r['varis']})"
            self.rota_map[label] = int(r["id"])
            values.append(label)
        self.in_is_rota.cmb["values"] = values
        if not self.in_is_rota.get():
            self.in_is_rota.set("(Seçiniz)")

    def rota_refresh(self):
        q = self.f_rota_q.get().strip()
        rows = self.app.db.nakliye_rota_list(q=q)
        self.tree_rota.delete(*self.tree_rota.get_children())
        for r in rows:
            self.tree_rota.insert(
                "",
                tk.END,
                values=(
                    r["id"],
                    r["ad"],
                    r["cikis"],
                    r["varis"],
                    f"{safe_float(r['mesafe_km']):.2f}",
                    f"{safe_float(r['sure_saat']):.2f}",
                    "Evet" if r["aktif"] else "Hayır",
                    r["notlar"],
                ),
            )
        self._refresh_rota_combo()

    def rota_save(self):
        ad = self.in_rota_ad.get().strip()
        if not ad:
            messagebox.showerror(APP_TITLE, "Rota adı boş olamaz.")
            return
        cikis = self.in_rota_cikis.get().strip()
        varis = self.in_rota_varis.get().strip()
        mesafe = safe_float(self.in_rota_mesafe.get())
        sure = safe_float(self.in_rota_sure.get())
        aktif = int(self.in_rota_aktif.get() or 0)
        notlar = self.in_rota_not.get("1.0", tk.END).strip()

        try:
            if self.edit_rota_id:
                self.app.db.nakliye_rota_update(self.edit_rota_id, ad, cikis=cikis, varis=varis, mesafe_km=mesafe, sure_saat=sure, aktif=aktif, notlar=notlar)
                self.lbl_rota_mode.config(text="Güncellendi.")
            else:
                self.app.db.nakliye_rota_add(ad, cikis=cikis, varis=varis, mesafe_km=mesafe, sure_saat=sure, aktif=aktif, notlar=notlar)
                self.lbl_rota_mode.config(text="Kaydedildi.")
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Rota kaydedilemedi: {exc}")
            return

        self.rota_refresh()
        self.rota_clear()

    def _rota_selected_id(self) -> Optional[int]:
        sel = self.tree_rota.selection()
        if not sel:
            return None
        vals = self.tree_rota.item(sel[0], "values")
        try:
            return int(vals[0])
        except Exception:
            return None

    def rota_edit_selected(self):
        rid = self._rota_selected_id()
        if not rid:
            messagebox.showinfo(APP_TITLE, "Lütfen bir rota seçin.")
            return
        r = self.app.db.nakliye_rota_get(rid)
        if not r:
            return
        self.edit_rota_id = int(r["id"])
        self.in_rota_ad.set(r["ad"])
        self.in_rota_cikis.set(r["cikis"])
        self.in_rota_varis.set(r["varis"])
        self.in_rota_mesafe.set(str(r["mesafe_km"] or ""))
        self.in_rota_sure.set(str(r["sure_saat"] or ""))
        self.in_rota_aktif.set(int(r["aktif"]))
        try:
            self.in_rota_not.delete("1.0", tk.END)
            self.in_rota_not.insert("1.0", r["notlar"] or "")
        except Exception:
            pass
        self.lbl_rota_mode.config(text="Düzenleme modu")

    def rota_delete_selected(self):
        rid = self._rota_selected_id()
        if not rid:
            messagebox.showinfo(APP_TITLE, "Lütfen bir rota seçin.")
            return
        if not messagebox.askyesno(APP_TITLE, "Seçili rotayı silmek istiyor musunuz?"):
            return
        try:
            self.app.db.nakliye_rota_delete(rid)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Rota silinemedi: {exc}")
            return
        self.rota_refresh()

    # -----------------
    # İş Planlama
    # -----------------
    def _build_isler(self, parent: ttk.Frame):
        top = ttk.LabelFrame(parent, text="İş Planı")
        top.pack(fill=tk.X, padx=6, pady=6)

        row1 = ttk.Frame(top); row1.pack(fill=tk.X, pady=4)
        self.in_is_no = LabeledEntry(row1, "İş No:", 16)
        self.in_is_no.pack(side=tk.LEFT, padx=6)
        self.in_is_tarih = LabeledEntry(row1, "Tarih:", 12)
        self.in_is_tarih.pack(side=tk.LEFT, padx=6)
        ttk.Button(row1, text="Bugün", command=lambda: self.in_is_tarih.set(fmt_tr_date(today_iso()))).pack(side=tk.LEFT, padx=4)
        self.in_is_saat = LabeledEntry(row1, "Saat:", 8)
        self.in_is_saat.pack(side=tk.LEFT, padx=6)
        self.in_is_durum = LabeledCombo(row1, "Durum:", ["Planlandı", "Yolda", "Teslim", "İptal"], 12)
        self.in_is_durum.pack(side=tk.LEFT, padx=6)

        row2 = ttk.Frame(top); row2.pack(fill=tk.X, pady=4)
        self.in_is_firma = LabeledCombo(row2, "Firma:", [], 22)
        self.in_is_firma.pack(side=tk.LEFT, padx=6)
        self.in_is_arac = LabeledCombo(row2, "Araç:", [], 16)
        self.in_is_arac.pack(side=tk.LEFT, padx=6)
        self.in_is_rota = LabeledCombo(row2, "Rota:", [], 22)
        self.in_is_rota.pack(side=tk.LEFT, padx=6)

        row3 = ttk.Frame(top); row3.pack(fill=tk.X, pady=4)
        self.in_is_cikis = LabeledEntry(row3, "Çıkış:", 16)
        self.in_is_cikis.pack(side=tk.LEFT, padx=6)
        self.in_is_varis = LabeledEntry(row3, "Varış:", 16)
        self.in_is_varis.pack(side=tk.LEFT, padx=6)
        self.in_is_yuk = LabeledEntry(row3, "Yük:", 18)
        self.in_is_yuk.pack(side=tk.LEFT, padx=6)

        row4 = ttk.Frame(top); row4.pack(fill=tk.X, pady=4)
        self.in_is_ucret = MoneyEntry(row4, "Ücret:")
        self.in_is_ucret.pack(side=tk.LEFT, padx=6)
        self.in_is_para = LabeledCombo(row4, "Para:", self.app.db.list_currencies(), 8)
        self.in_is_para.pack(side=tk.LEFT, padx=6)
        self.in_is_para.set("TL")
        ttk.Label(row4, text="Notlar:").pack(side=tk.LEFT, padx=(10, 4))
        self.in_is_not = SimpleField("")
        self.in_is_not_ent = ttk.Entry(row4, width=40)
        self.in_is_not_ent.pack(side=tk.LEFT, padx=4, fill=tk.X, expand=True)

        row5 = ttk.Frame(top); row5.pack(fill=tk.X, pady=4)
        ttk.Button(row5, text="Kaydet", command=self.is_save).pack(side=tk.LEFT, padx=6)
        ttk.Button(row5, text="Yeni", command=self.is_clear).pack(side=tk.LEFT, padx=6)
        self.lbl_is_mode = ttk.Label(row5, text="")
        self.lbl_is_mode.pack(side=tk.LEFT, padx=10)

        mid = ttk.LabelFrame(parent, text="İşler")
        mid.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        frow = ttk.Frame(mid); frow.pack(fill=tk.X, pady=4)
        self.f_is_q = LabeledEntry(frow, "Ara:", 24)
        self.f_is_q.pack(side=tk.LEFT, padx=6)
        self.f_is_from = LabeledEntry(frow, "Başlangıç:", 12)
        self.f_is_from.pack(side=tk.LEFT, padx=6)
        self.f_is_to = LabeledEntry(frow, "Bitiş:", 12)
        self.f_is_to.pack(side=tk.LEFT, padx=6)
        ttk.Button(frow, text="Yenile", command=self.is_refresh).pack(side=tk.LEFT, padx=6)

        cols = ("id", "is_no", "tarih", "saat", "firma", "arac", "rota", "cikis", "varis", "durum", "ucret")
        self.tree_is = ttk.Treeview(mid, columns=cols, show="headings", height=10)
        for c in cols:
            self.tree_is.heading(c, text=c.upper())
        self.tree_is.column("id", width=50, anchor="center")
        self.tree_is.column("is_no", width=120)
        self.tree_is.column("tarih", width=95)
        self.tree_is.column("saat", width=70)
        self.tree_is.column("firma", width=160)
        self.tree_is.column("arac", width=100)
        self.tree_is.column("rota", width=180)
        self.tree_is.column("cikis", width=120)
        self.tree_is.column("varis", width=120)
        self.tree_is.column("durum", width=100)
        self.tree_is.column("ucret", width=100, anchor="e")
        self.tree_is.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.tree_is.bind("<Double-1>", lambda _e: self.is_edit_selected())

        btm = ttk.Frame(mid); btm.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(btm, text="Seçili Kaydı Düzenle", command=self.is_edit_selected).pack(side=tk.LEFT, padx=6)
        ttk.Button(btm, text="Seçili Kaydı Sil", command=self.is_delete_selected).pack(side=tk.LEFT, padx=6)
        ttk.Button(btm, text="İşleme Git", command=self._jump_to_islem).pack(side=tk.LEFT, padx=6)

    def is_clear(self):
        self.edit_is_id = None
        self.in_is_no.set("")
        self.in_is_tarih.set(fmt_tr_date(today_iso()))
        self.in_is_saat.set("")
        self.in_is_durum.set("Planlandı")
        self.in_is_firma.set("(Seçiniz)")
        self.in_is_arac.set("(Seçiniz)")
        self.in_is_rota.set("(Seçiniz)")
        self.in_is_cikis.set("")
        self.in_is_varis.set("")
        self.in_is_yuk.set("")
        self.in_is_ucret.set("")
        self.in_is_para.set("TL")
        self.in_is_not_ent.delete(0, tk.END)
        self.lbl_is_mode.config(text="")

    def is_refresh(self):
        q = self.f_is_q.get().strip()
        date_from = self.f_is_from.get().strip()
        date_to = self.f_is_to.get().strip()
        rows = self.app.db.nakliye_is_list(q=q, date_from=date_from, date_to=date_to)
        self.tree_is.delete(*self.tree_is.get_children())
        for r in rows:
            tarih = fmt_tr_date(r["tarih"])
            ucret = f"{safe_float(r['ucret']):.2f} {r['para']}"
            self.tree_is.insert(
                "",
                tk.END,
                values=(
                    r["id"],
                    r["is_no"],
                    tarih,
                    r["saat"],
                    r["firma_ad"] or "",
                    r["arac_plaka"] or "",
                    r["rota_ad"] or "",
                    r["cikis"],
                    r["varis"],
                    r["durum"],
                    ucret,
                ),
            )
        self._refresh_is_combo()

    def _refresh_is_combo(self):
        rows = self.app.db.nakliye_is_list()
        self.is_map = {"(Seçiniz)": None}
        values = ["(Seçiniz)"]
        for r in rows:
            label = f"{r['is_no']} - {r['cikis']} → {r['varis']}"
            self.is_map[label] = int(r["id"])
            values.append(label)
        self.in_islem_is.cmb["values"] = values
        if not self.in_islem_is.get():
            self.in_islem_is.set("(Seçiniz)")

    def is_save(self):
        tarih = self.in_is_tarih.get().strip()
        if not tarih:
            messagebox.showerror(APP_TITLE, "Tarih boş olamaz.")
            return
        firma_id = self.firma_map.get(self.in_is_firma.get())
        arac_id = self.arac_map.get(self.in_is_arac.get())
        rota_id = self.rota_map.get(self.in_is_rota.get())
        is_no = self.in_is_no.get().strip()
        saat = self.in_is_saat.get().strip()
        cikis = self.in_is_cikis.get().strip()
        varis = self.in_is_varis.get().strip()
        yuk = self.in_is_yuk.get().strip()
        durum = self.in_is_durum.get().strip() or "Planlandı"
        ucret = self.in_is_ucret.get_float()
        para = self.in_is_para.get().strip() or "TL"
        notlar = self.in_is_not_ent.get().strip()

        try:
            if self.edit_is_id:
                self.app.db.nakliye_is_update(
                    self.edit_is_id,
                    is_no or "",
                    tarih,
                    saat=saat,
                    firma_id=firma_id,
                    arac_id=arac_id,
                    rota_id=rota_id,
                    cikis=cikis,
                    varis=varis,
                    yuk=yuk,
                    durum=durum,
                    ucret=ucret,
                    para=para,
                    notlar=notlar,
                )
                self.lbl_is_mode.config(text="Güncellendi.")
            else:
                self.app.db.nakliye_is_add(
                    is_no or None,
                    tarih,
                    saat=saat,
                    firma_id=firma_id,
                    arac_id=arac_id,
                    rota_id=rota_id,
                    cikis=cikis,
                    varis=varis,
                    yuk=yuk,
                    durum=durum,
                    ucret=ucret,
                    para=para,
                    notlar=notlar,
                )
                self.lbl_is_mode.config(text="Kaydedildi.")
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"İş kaydedilemedi: {exc}")
            return

        self.is_refresh()
        self.is_clear()

    def _is_selected_id(self) -> Optional[int]:
        sel = self.tree_is.selection()
        if not sel:
            return None
        vals = self.tree_is.item(sel[0], "values")
        try:
            return int(vals[0])
        except Exception:
            return None

    def is_edit_selected(self):
        iid = self._is_selected_id()
        if not iid:
            messagebox.showinfo(APP_TITLE, "Lütfen bir iş seçin.")
            return
        r = self.app.db.nakliye_is_get(iid)
        if not r:
            return
        self.edit_is_id = int(r["id"])
        self.in_is_no.set(r["is_no"])
        self.in_is_tarih.set(fmt_tr_date(r["tarih"]))
        self.in_is_saat.set(r["saat"])
        self.in_is_durum.set(r["durum"])
        self.in_is_cikis.set(r["cikis"])
        self.in_is_varis.set(r["varis"])
        self.in_is_yuk.set(r["yuk"])
        self.in_is_ucret.set(r["ucret"] or "")
        self.in_is_para.set(r["para"] or "TL")
        self.in_is_not_ent.delete(0, tk.END)
        self.in_is_not_ent.insert(0, r["notlar"] or "")

        firmalabel = "(Seçiniz)"
        for label, fid in self.firma_map.items():
            if fid == r["firma_id"]:
                firmalabel = label
                break
        self.in_is_firma.set(firmalabel)

        araclabel = "(Seçiniz)"
        for label, aid in self.arac_map.items():
            if aid == r["arac_id"]:
                araclabel = label
                break
        self.in_is_arac.set(araclabel)

        rotalabel = "(Seçiniz)"
        for label, rid in self.rota_map.items():
            if rid == r["rota_id"]:
                rotalabel = label
                break
        self.in_is_rota.set(rotalabel)

        self.lbl_is_mode.config(text="Düzenleme modu")

    def is_delete_selected(self):
        iid = self._is_selected_id()
        if not iid:
            messagebox.showinfo(APP_TITLE, "Lütfen bir iş seçin.")
            return
        if not messagebox.askyesno(APP_TITLE, "Seçili işi silmek istiyor musunuz?"):
            return
        try:
            self.app.db.nakliye_is_delete(iid)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"İş silinemedi: {exc}")
            return
        self.is_refresh()

    def _jump_to_islem(self):
        iid = self._is_selected_id()
        if not iid:
            messagebox.showinfo(APP_TITLE, "Lütfen bir iş seçin.")
            return
        label = None
        for k, v in self.is_map.items():
            if v == iid:
                label = k
                break
        if label:
            self.in_islem_is.set(label)
        self.nb.select(self.tab_islem)
        self.islem_refresh()

    # -----------------
    # İşlemler
    # -----------------
    def _build_islemler(self, parent: ttk.Frame):
        top = ttk.LabelFrame(parent, text="İşlem Kaydı")
        top.pack(fill=tk.X, padx=6, pady=6)

        row1 = ttk.Frame(top); row1.pack(fill=tk.X, pady=4)
        self.in_islem_is = LabeledCombo(row1, "İş:", [], 30)
        self.in_islem_is.pack(side=tk.LEFT, padx=6)
        self.in_islem_tarih = LabeledEntry(row1, "Tarih:", 12)
        self.in_islem_tarih.pack(side=tk.LEFT, padx=6)
        ttk.Button(row1, text="Bugün", command=lambda: self.in_islem_tarih.set(fmt_tr_date(today_iso()))).pack(side=tk.LEFT, padx=4)
        self.in_islem_saat = LabeledEntry(row1, "Saat:", 8)
        self.in_islem_saat.pack(side=tk.LEFT, padx=6)
        self.in_islem_tip = LabeledEntry(row1, "Tip:", 16)
        self.in_islem_tip.pack(side=tk.LEFT, padx=6)

        row2 = ttk.Frame(top); row2.pack(fill=tk.X, pady=4)
        ttk.Label(row2, text="Açıklama:").pack(side=tk.LEFT, padx=(6, 4))
        self.in_islem_aciklama = ttk.Entry(row2, width=60)
        self.in_islem_aciklama.pack(side=tk.LEFT, padx=4, fill=tk.X, expand=True)

        row3 = ttk.Frame(top); row3.pack(fill=tk.X, pady=4)
        ttk.Button(row3, text="Kaydet", command=self.islem_save).pack(side=tk.LEFT, padx=6)
        ttk.Button(row3, text="Yeni", command=self.islem_clear).pack(side=tk.LEFT, padx=6)
        self.lbl_islem_mode = ttk.Label(row3, text="")
        self.lbl_islem_mode.pack(side=tk.LEFT, padx=10)

        mid = ttk.LabelFrame(parent, text="İşlemler")
        mid.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        frow = ttk.Frame(mid); frow.pack(fill=tk.X, pady=4)
        ttk.Button(frow, text="Yenile", command=self.islem_refresh).pack(side=tk.LEFT, padx=6)

        cols = ("id", "tarih", "saat", "tip", "aciklama")
        self.tree_islem = ttk.Treeview(mid, columns=cols, show="headings", height=10)
        for c in cols:
            self.tree_islem.heading(c, text=c.upper())
        self.tree_islem.column("id", width=50, anchor="center")
        self.tree_islem.column("tarih", width=95)
        self.tree_islem.column("saat", width=70)
        self.tree_islem.column("tip", width=140)
        self.tree_islem.column("aciklama", width=500)
        self.tree_islem.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.tree_islem.bind("<Double-1>", lambda _e: self.islem_edit_selected())

        btm = ttk.Frame(mid); btm.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(btm, text="Seçili Kaydı Düzenle", command=self.islem_edit_selected).pack(side=tk.LEFT, padx=6)
        ttk.Button(btm, text="Seçili Kaydı Sil", command=self.islem_delete_selected).pack(side=tk.LEFT, padx=6)

    def islem_clear(self):
        self.edit_islem_id = None
        if not self.in_islem_tarih.get():
            self.in_islem_tarih.set(fmt_tr_date(today_iso()))
        self.in_islem_saat.set("")
        self.in_islem_tip.set("")
        self.in_islem_aciklama.delete(0, tk.END)
        self.lbl_islem_mode.config(text="")

    def islem_refresh(self):
        is_id = self.is_map.get(self.in_islem_is.get())
        if not is_id:
            self.tree_islem.delete(*self.tree_islem.get_children())
            return
        rows = self.app.db.nakliye_islem_list(is_id)
        self.tree_islem.delete(*self.tree_islem.get_children())
        for r in rows:
            self.tree_islem.insert(
                "",
                tk.END,
                values=(r["id"], fmt_tr_date(r["tarih"]), r["saat"], r["tip"], r["aciklama"]),
            )

    def islem_save(self):
        is_id = self.is_map.get(self.in_islem_is.get())
        if not is_id:
            messagebox.showerror(APP_TITLE, "Lütfen bir iş seçin.")
            return
        tarih = self.in_islem_tarih.get().strip()
        tip = self.in_islem_tip.get().strip() or "İşlem"
        saat = self.in_islem_saat.get().strip()
        aciklama = self.in_islem_aciklama.get().strip()

        try:
            if self.edit_islem_id:
                # basit güncelleme: silip yeniden ekle
                self.app.db.nakliye_islem_delete(self.edit_islem_id)
                self.app.db.nakliye_islem_add(is_id, tarih, saat=saat, tip=tip, aciklama=aciklama)
                self.lbl_islem_mode.config(text="Güncellendi.")
            else:
                self.app.db.nakliye_islem_add(is_id, tarih, saat=saat, tip=tip, aciklama=aciklama)
                self.lbl_islem_mode.config(text="Kaydedildi.")
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"İşlem kaydedilemedi: {exc}")
            return

        self.islem_refresh()
        self.islem_clear()

    def _islem_selected_id(self) -> Optional[int]:
        sel = self.tree_islem.selection()
        if not sel:
            return None
        vals = self.tree_islem.item(sel[0], "values")
        try:
            return int(vals[0])
        except Exception:
            return None

    def islem_edit_selected(self):
        islem_id = self._islem_selected_id()
        if not islem_id:
            messagebox.showinfo(APP_TITLE, "Lütfen bir işlem seçin.")
            return
        self.edit_islem_id = islem_id
        vals = self.tree_islem.item(self.tree_islem.selection()[0], "values")
        self.in_islem_tarih.set(vals[1])
        self.in_islem_saat.set(vals[2])
        self.in_islem_tip.set(vals[3])
        self.in_islem_aciklama.delete(0, tk.END)
        self.in_islem_aciklama.insert(0, vals[4])
        self.lbl_islem_mode.config(text="Düzenleme modu")

    def islem_delete_selected(self):
        islem_id = self._islem_selected_id()
        if not islem_id:
            messagebox.showinfo(APP_TITLE, "Lütfen bir işlem seçin.")
            return
        if not messagebox.askyesno(APP_TITLE, "Seçili işlemi silmek istiyor musunuz?"):
            return
        try:
            self.app.db.nakliye_islem_delete(islem_id)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"İşlem silinemedi: {exc}")
            return
        self.islem_refresh()

    # -----------------
    # Genel
    # -----------------
    def refresh_all(self):
        self.firma_refresh()
        self.arac_refresh()
        self.rota_refresh()
        self.is_refresh()
        self.islem_refresh()


def build(master, app: "App") -> ttk.Frame:
    return NakliyeFrame(master, app)
