# -*- coding: utf-8 -*-
"""UI Plugin: Maaş Meslekleri

İstek:
- Maaş -> Çalışanlar kısmında çalışanlara meslek atanabilsin
- Meslekler ayrıca yönetilebilsin (ekle/düzenle/sil)

Bu eklenti iki ekran sağlar:
1) Meslek tanımları
2) Çalışanlara meslek atama
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

import tkinter as tk
from tkinter import ttk, messagebox

from ...config import APP_TITLE
from ..widgets import LabeledEntry, LabeledCombo

if TYPE_CHECKING:
    from ...app import App

PLUGIN_META = {
    "key": "maas_meslekler",
    "nav_text": "🧑‍🏭 Meslekler",
    "page_title": "Maaş Meslek Yönetimi",
    "order": 37,
}


class MaasMesleklerFrame(ttk.Frame):
    def __init__(self, master, app: "App"):
        super().__init__(master)
        self.app = app
        self._selected_meslek_id: Optional[int] = None
        self._build()

    def _build(self):
        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.tab_meslek = ttk.Frame(nb)
        self.tab_atama = ttk.Frame(nb)
        nb.add(self.tab_meslek, text="🧑‍🏭 Meslek Tanımları")
        nb.add(self.tab_atama, text="👥 Çalışana Meslek Ata")

        self._build_meslek_tab(self.tab_meslek)
        self._build_assign_tab(self.tab_atama)

        self.refresh_all()

    # -----------------
    # Meslek Tab
    # -----------------
    def _build_meslek_tab(self, parent: ttk.Frame):
        top = ttk.LabelFrame(parent, text="Meslek Tanımı")
        top.pack(fill=tk.X, padx=6, pady=(6, 8))

        self.e_ad = LabeledEntry(top, "Meslek:", 28)
        self.e_ad.pack(side=tk.LEFT, padx=6, pady=6)
        ttk.Label(top, text="Durum:").pack(side=tk.LEFT, padx=(6, 2))
        self.cmb_meslek_durum = ttk.Combobox(top, values=["Aktif", "Aktif değil"], state="readonly", width=10)
        self.cmb_meslek_durum.pack(side=tk.LEFT, padx=6)
        self.cmb_meslek_durum.set("Aktif")
        self.e_notlar = LabeledEntry(top, "Not:", 32)
        self.e_notlar.pack(side=tk.LEFT, padx=6, pady=6)

        btns = ttk.Frame(parent)
        btns.pack(fill=tk.X, padx=6, pady=(0, 8))
        ttk.Button(btns, text="Kaydet", command=self.save_meslek).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Yeni", command=self.clear_meslek_form).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Sil", command=self.delete_meslek).pack(side=tk.LEFT, padx=6)
        self.lbl_mode = ttk.Label(btns, text="")
        self.lbl_mode.pack(side=tk.LEFT, padx=10)

        cols = ("id", "ad", "aktif", "notlar")
        self.tree = ttk.Treeview(parent, columns=cols, show="headings", height=16, selectmode="browse")
        for c in cols:
            self.tree.heading(c, text=c.upper())
        self.tree.column("id", width=60, anchor="center")
        self.tree.column("ad", width=260)
        self.tree.column("aktif", width=80, anchor="center")
        self.tree.column("notlar", width=380)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self.load_selected_meslek())

    def refresh_meslek(self):
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        try:
            rows = self.app.db.maas_meslek_list()  # type: ignore
        except Exception:
            rows = []
        for r in rows:
            aktif = "Aktif" if int(r["aktif"] or 0) == 1 else "Aktif değil"
            self.tree.insert(
                "",
                "end",
                values=(int(r["id"]), str(r["ad"] or ""), aktif, str(r["notlar"] or "")),
            )
        self._refresh_meslek_combo()

    def clear_meslek_form(self):
        self._selected_meslek_id = None
        self.e_ad.set("")
        try:
            self.cmb_meslek_durum.set("Aktif")
        except Exception:
            pass
        self.e_notlar.set("")
        self.lbl_mode.config(text="Yeni")

    def load_selected_meslek(self):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        if not vals:
            return
        try:
            self._selected_meslek_id = int(vals[0])
        except Exception:
            self._selected_meslek_id = None
            return
        self.e_ad.set(str(vals[1] or ""))
        try:
            self.cmb_meslek_durum.set(str(vals[2]) or "Aktif")
        except Exception:
            pass
        self.e_notlar.set(str(vals[3] or ""))
        self.lbl_mode.config(text=f"Düzenle: #{self._selected_meslek_id}")

    def save_meslek(self):
        name = (self.e_ad.get() or "").strip()
        if not name:
            messagebox.showerror(APP_TITLE, "Meslek adı boş olamaz.")
            return
        aktif = 1 if (getattr(self, "cmb_meslek_durum", None) and (self.cmb_meslek_durum.get() or "").strip() == "Aktif") else 0
        notlar = (self.e_notlar.get() or "").strip()
        try:
            if self._selected_meslek_id:
                self.app.db.maas_meslek_update(int(self._selected_meslek_id), name, aktif=aktif, notlar=notlar)  # type: ignore
            else:
                self.app.db.maas_meslek_add(name, aktif=aktif, notlar=notlar)  # type: ignore
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Kaydetme başarısız: {e}")
            return
        self.clear_meslek_form()
        self.refresh_meslek()
        self.refresh_employees()

    def delete_meslek(self):
        if not self._selected_meslek_id:
            messagebox.showinfo(APP_TITLE, "Silmek için meslek seç.")
            return
        if not messagebox.askyesno(APP_TITLE, "Seçili meslek silinsin mi? (Çalışanlardan bağı kaldırılır)"):
            return
        try:
            self.app.db.maas_meslek_delete(int(self._selected_meslek_id))  # type: ignore
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Silme başarısız: {e}")
            return
        self.clear_meslek_form()
        self.refresh_meslek()
        self.refresh_employees()

    # -----------------
    # Atama Tab
    # -----------------
    def _build_assign_tab(self, parent: ttk.Frame):
        box = ttk.LabelFrame(parent, text="Çalışanlara Meslek Atama")
        box.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        top = ttk.Frame(box)
        top.pack(fill=tk.X, padx=6, pady=6)

        self._meslek_name_to_id: dict[str, int] = {}
        self.cmb_meslek = LabeledCombo(top, "Meslek:", ["(Yok)"], 24)
        self.cmb_meslek.pack(side=tk.LEFT, padx=6)
        self.cmb_meslek.set("(Yok)")

        ttk.Button(top, text="✅ Seçili Çalışanlara Ata", command=self.apply_meslek_to_selected).pack(
            side=tk.LEFT, padx=6
        )
        ttk.Button(top, text="Yenile", command=self.refresh_employees).pack(side=tk.LEFT, padx=6)

        cols = ("id", "ad", "meslek", "aylik", "para", "aktif")
        self.emp_tree = ttk.Treeview(box, columns=cols, show="headings", height=18, selectmode="extended")
        for c in cols:
            self.emp_tree.heading(c, text=c.upper())
        self.emp_tree.column("id", width=60, anchor="center")
        self.emp_tree.column("ad", width=240)
        self.emp_tree.column("meslek", width=180)
        self.emp_tree.column("aylik", width=120, anchor="e")
        self.emp_tree.column("para", width=60, anchor="center")
        self.emp_tree.column("aktif", width=80, anchor="center")
        self.emp_tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

    def _refresh_meslek_combo(self):
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
            cur = (self.cmb_meslek.get() or "").strip()
        except Exception:
            cur = ""
        try:
            self.cmb_meslek.cmb["values"] = opts
            if cur and cur in opts:
                self.cmb_meslek.set(cur)
            else:
                self.cmb_meslek.set("(Yok)")
        except Exception:
            pass

    def refresh_employees(self):
        for iid in self.emp_tree.get_children():
            self.emp_tree.delete(iid)
        self._refresh_meslek_combo()
        try:
            rows = self.app.db.maas_calisan_list()  # type: ignore
        except Exception:
            rows = []
        for r in rows:
            aktif = "Aktif" if int(r["aktif"] or 0) == 1 else "Aktif değil"
            meslek = str(r["meslek_ad"] or "")
            try:
                from ...utils import fmt_amount

                aylik = fmt_amount(float(r["aylik_tutar"] or 0))
            except Exception:
                aylik = str(r["aylik_tutar"] or "")
            self.emp_tree.insert(
                "",
                "end",
                values=(
                    int(r["id"]),
                    str(r["ad"] or ""),
                    meslek,
                    aylik,
                    str(r["para"] or "TL"),
                    aktif,
                ),
            )

    def apply_meslek_to_selected(self):
        sel = self.emp_tree.selection()
        if not sel:
            messagebox.showinfo(APP_TITLE, "Önce çalışan seç.")
            return
        name = (self.cmb_meslek.get() or "").strip()
        meslek_id = None
        if name and name != "(Yok)":
            try:
                meslek_id = int(self._meslek_name_to_id.get(name) or 0) or None
            except Exception:
                meslek_id = None

        try:
            rows = self.app.db.maas_calisan_list()  # type: ignore
            by_id = {int(r["id"]): r for r in rows}
        except Exception:
            by_id = {}

        n_ok = 0
        for iid in sel:
            vals = self.emp_tree.item(iid, "values")
            if not vals:
                continue
            try:
                cid = int(vals[0])
            except Exception:
                continue
            r = by_id.get(cid)
            if not r:
                continue
            try:
                self.app.db.maas_calisan_update(
                    cid,
                    str(r["ad"] or ""),
                    float(r["aylik_tutar"] or 0),
                    para=str(r["para"] or "TL"),
                    aktif=int(r["aktif"] or 0),
                    notlar=str(r["notlar"] or ""),
                    meslek_id=meslek_id,
                )  # type: ignore
                n_ok += 1
            except Exception:
                continue

        if n_ok:
            messagebox.showinfo(APP_TITLE, f"Meslek atandı: {n_ok} çalışan")
        self.refresh_employees()

    def refresh_all(self):
        self.clear_meslek_form()
        self.refresh_meslek()
        self.refresh_employees()


def build(master, app):
    return MaasMesleklerFrame(master, app)
