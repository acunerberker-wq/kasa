# -*- coding: utf-8 -*-
"""KasaPro v3 - Ayarlar penceresi (Toplevel).

- Liste düzenleyiciler (para birimleri, ödeme tipleri, kategoriler)
- Maaş modülü: aktif/pasif yönetimi (Çalışan / Meslek)
- (Admin) şirket içi kullanıcı yönetimi
- Veritabanı: DB yedek / geri yükleme
"""

from __future__ import annotations

from typing import Optional, List, TYPE_CHECKING

import os
import sys
import subprocess
from glob import glob

import json
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from ...config import APP_TITLE, APP_BASE_DIR, SHARED_STORAGE_DIRNAME
from ...utils import center_window, fmt_amount, _safe_slug
from ..dialogs import simple_input, simple_choice

if TYPE_CHECKING:
    from ...app import App

class SettingsWindow(tk.Toplevel):
    def __init__(self, app: "App"):
        super().__init__(app.root)
        self.app = app
        self.db = app.db
        self.title("Ayarlar")
        self.geometry("820x560")
        self._build()
        center_window(self, app.root)

    def _build(self):
        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        tab_lists = ttk.Frame(nb)
        nb.add(tab_lists, text="Listeler")

        tab_active = ttk.Frame(nb)
        nb.add(tab_active, text="Aktif / Aktif Değil")

        tab_companies = ttk.Frame(nb)
        nb.add(tab_companies, text="Şirketler")

        tab_users = ttk.Frame(nb)
        nb.add(tab_users, text="Kullanıcılar")

        tab_stock = ttk.Frame(nb)
        nb.add(tab_stock, text="Stok")

        tab_db_backup = ttk.Frame(nb)
        nb.add(tab_db_backup, text="DB Yedek")

        tab_db_restore = ttk.Frame(nb)
        nb.add(tab_db_restore, text="DB Geri Yükle")

        tab_shared_storage = ttk.Frame(nb)
        nb.add(tab_shared_storage, text="Ortak Depolama")

        # ---- Listeler ----
        self._list_editor(tab_lists, "Para Birimleri", "currencies", self.db.list_currencies(), y=0)
        self._list_editor(tab_lists, "Ödeme Tipleri", "payments", self.db.list_payments(), y=170)
        self._list_editor(tab_lists, "Kategoriler", "categories", self.db.list_categories(), y=340)

        self._list_editor(tab_stock, "Stok Birimleri", "stock_units", self.db.list_stock_units(), y=0)
        self._list_editor(tab_stock, "Stok Kategorileri", "stock_categories", self.db.list_stock_categories(), y=170)

        # ---- Aktif/Pasif (Maaş) ----
        self._build_active_tab(tab_active)

        # ---- Şirketler (Firma Yönetimi) ----
        self._build_companies_tab(tab_companies)

        # ---- Kullanıcılar (admin) ----
        self._build_users_tab(tab_users)

        # ---- DB Yedek / Geri Yükle ----
        self._build_db_backup_tab(tab_db_backup)
        self._build_db_restore_tab(tab_db_restore)
        self._build_shared_storage_tab(tab_shared_storage)

        # Varsayılan olarak ilk sekmede kalsın.

    def _list_editor(self, master, title, key, items, y=0):
        box = ttk.LabelFrame(master, text=title)
        box.place(x=10, y=10 + y, width=780, height=150)

        txt = tk.Text(box, height=6)
        txt.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        txt.insert("1.0", "\n".join(items))

        def save():
            lines = [line.strip() for line in txt.get("1.0", tk.END).splitlines() if line.strip()]
            self.db.set_setting(key, json.dumps(lines, ensure_ascii=False))
            self.db.log("Settings", f"{key} updated ({len(lines)})")
            self.app.reload_settings()
            messagebox.showinfo(APP_TITLE, f"{title} kaydedildi.")

        ttk.Button(box, text="Kaydet", command=save).pack(anchor="e", padx=8, pady=(0, 8))

    # -----------------
    # Helpers
    # -----------------
    @staticmethod
    def _row_get(row, key: str, default=None):
        """Row/Dict güvenli alan erişimi.

        Not: sqlite3.Row, Mapping benzeri olsa da .get() metodu yok.
        """
        if row is None:
            return default
        # dict
        try:
            if isinstance(row, dict):
                return row.get(key, default)
        except Exception:
            pass
        # sqlite3.Row veya tuple benzeri
        try:
            return row[key]  # type: ignore[index]
        except Exception:
            return default

    # -----------------
    # Şirket Yönetimi
    # -----------------

    def _build_companies_tab(self, master: ttk.Frame):
        info = ttk.Label(
            master,
            text=(
                "Şirketler burada yönetilir. Her şirketin verileri ayrı bir veritabanında tutulur.\n"
                "Şirket değiştirince cariler/hareketler/raporlar otomatik o şirkete geçer."
            ),
            justify="left",
        )
        info.pack(anchor="w", padx=10, pady=(10, 6))

        row = ttk.Frame(master)
        row.pack(fill=tk.X, padx=10, pady=(0, 8))
        self.lbl_active_company = ttk.Label(row, text="")
        self.lbl_active_company.pack(side=tk.LEFT)

        btns = ttk.Frame(master)
        btns.pack(fill=tk.X, padx=10, pady=(0, 8))

        ttk.Button(btns, text="➕ Yeni Şirket", command=self._company_new).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="✅ Seç / Aç", command=self._company_open).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="✏️ Yeniden Adlandır", command=self._company_rename).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="🗑️ Sil", command=self._company_delete).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="🔄 Yenile", command=self._companies_refresh).pack(side=tk.RIGHT, padx=4)

        cols = ("id", "name", "created_at", "db_file")
        self.tree_companies = ttk.Treeview(master, columns=cols, show="headings", height=18)
        self.tree_companies.heading("id", text="ID")
        self.tree_companies.heading("name", text="Şirket Adı")
        self.tree_companies.heading("created_at", text="Oluşturma")
        self.tree_companies.heading("db_file", text="DB Dosyası")

        self.tree_companies.column("id", width=60, anchor="center")
        self.tree_companies.column("name", width=260, anchor="w")
        self.tree_companies.column("created_at", width=170, anchor="w")
        self.tree_companies.column("db_file", width=260, anchor="w")

        ysb = ttk.Scrollbar(master, orient="vertical", command=self.tree_companies.yview)
        self.tree_companies.configure(yscrollcommand=ysb.set)
        self.tree_companies.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=(0, 10))
        ysb.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 10), pady=(0, 10))

        try:
            self.tree_companies.bind("<Double-1>", lambda _e: self._company_open())
        except Exception:
            pass

        self._companies_refresh()

    def _selected_company_id(self) -> Optional[int]:
        if not hasattr(self, "tree_companies"):
            return None
        try:
            sel = self.tree_companies.selection()  # type: ignore
            if not sel:
                return None
            vals = self.tree_companies.item(sel[0], "values")  # type: ignore
            if not vals:
                return None
            return int(vals[0])
        except Exception:
            return None

    def _companies_refresh(self):
        # Aktif şirket etiketi
        try:
            active_name = getattr(self.app, "active_company_name", "") or ""
            self.lbl_active_company.config(text=f"Aktif Şirket: {active_name}")
        except Exception:
            pass

        if not hasattr(self, "tree_companies"):
            return

        for x in self.tree_companies.get_children():  # type: ignore
            self.tree_companies.delete(x)  # type: ignore

        uid = self.app.get_active_user_id() if hasattr(self.app, "get_active_user_id") else None
        if not uid:
            return

        try:
            comps = self.app.usersdb.list_companies(int(uid))
        except Exception:
            comps = []

        active_id = getattr(self.app, "active_company_id", None)
        for c in comps:
            try:
                cid = int(c["id"])
            except Exception:
                continue
            created = str(self._row_get(c, "created_at", "") or "")
            dbf = str(self._row_get(c, "db_file", "") or "")
            vals = (cid, str(self._row_get(c, "name", "") or ""), created, dbf)
            iid = self.tree_companies.insert("", tk.END, values=vals)  # type: ignore
            if active_id and cid == int(active_id):
                try:
                    self.tree_companies.selection_set(iid)  # type: ignore
                    self.tree_companies.see(iid)  # type: ignore
                except Exception:
                    pass

    def _company_new(self):
        uid = self.app.get_active_user_id() if hasattr(self.app, "get_active_user_id") else None
        if not uid:
            return
        name = simpledialog.askstring(APP_TITLE, "Yeni şirket adı:", parent=self)
        if not name:
            return
        try:
            cid = self.app.usersdb.add_company(int(uid), str(name))
            self.app.switch_company(int(cid))
            self._companies_refresh()
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Şirket oluşturulamadı:\n{e}", parent=self)

    def _company_open(self):
        cid = self._selected_company_id()
        if not cid:
            messagebox.showinfo(APP_TITLE, "Lütfen listeden bir şirket seçin.", parent=self)
            return
        try:
            self.app.switch_company(int(cid))
            self._companies_refresh()
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Şirkete geçilemedi:\n{e}", parent=self)

    def _company_rename(self):
        cid = self._selected_company_id()
        if not cid:
            messagebox.showinfo(APP_TITLE, "Lütfen listeden bir şirket seçin.", parent=self)
            return

        old = ""
        try:
            c = self.app.usersdb.get_company_by_id(int(cid))
            old = str(self._row_get(c, "name", "") or "") if c else ""
        except Exception:
            old = ""

        name = simpledialog.askstring(APP_TITLE, "Yeni şirket adı:", initialvalue=old, parent=self)
        if not name:
            return
        try:
            self.app.usersdb.rename_company(int(cid), str(name))
            # aktif şirket adı değiştiyse etiketi güncelle
            if getattr(self.app, "active_company_id", None) is not None and int(self.app.active_company_id or 0) == int(cid):
                try:
                    self.app.active_company_name = str(name)
                    self.app._update_company_label()
                except Exception:
                    pass
            self._companies_refresh()
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Yeniden adlandırılamadı:\n{e}", parent=self)

    def _company_delete(self):
        cid = self._selected_company_id()
        if not cid:
            messagebox.showinfo(APP_TITLE, "Lütfen listeden bir şirket seçin.", parent=self)
            return
        if not messagebox.askyesno(APP_TITLE, "Seçili şirket silinsin mi?\n(DB dosyası da silinir)", parent=self):
            return

        try:
            was_active = (
                getattr(self.app, "active_company_id", None) is not None
                and int(self.app.active_company_id or 0) == int(cid)
            )

            self.app.usersdb.delete_company(int(cid), delete_db_file=True)

            # aktif şirket silindiyse otomatik başka şirkete geç
            if was_active:
                try:
                    urow = self.app.get_active_user_row() if hasattr(self.app, "get_active_user_row") else None
                except Exception:
                    urow = None
                crow = None
                try:
                    crow = self.app.usersdb.get_active_company_for_user(urow) if urow else None
                except Exception:
                    crow = None
                if crow:
                    try:
                        self.app.switch_company(int(crow["id"]))
                    except Exception:
                        pass

            self._companies_refresh()
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Silinemedi:\n{e}", parent=self)

    # -----------------
    # Aktif/Pasif Yönetimi (Maaş)
    # -----------------

    def _build_active_tab(self, master: ttk.Frame):
        info = ttk.Label(
            master,
            text=(
                "Buradan meslek, çalışan ve cari kayıtlarını 'Aktif' / 'Aktif değil' olarak işaretleyebilirsin.\n"
                "Aktif değil olan çalışanlar maaş toplamlarında ve eşleştirmelerde hesap dışı kalır.\n"
                "Aktif değil cariler, cari seçim listelerinde ve cari bazlı raporlarda hesap dışı kalır."
            ),
            justify="left",
        )
        info.pack(anchor="w", padx=10, pady=(10, 6))

        nb = ttk.Notebook(master)
        nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        tab_emp = ttk.Frame(nb)
        tab_mes = ttk.Frame(nb)
        tab_cari = ttk.Frame(nb)
        nb.add(tab_emp, text="Çalışanlar")
        nb.add(tab_mes, text="Meslekler")
        nb.add(tab_cari, text="Cariler")

        self._build_active_employees(tab_emp)
        self._build_active_professions(tab_mes)
        self._build_active_caris(tab_cari)

    def _build_active_employees(self, master: ttk.Frame):

        top = ttk.Frame(master)
        top.pack(fill=tk.X, pady=(0, 6))

        ttk.Label(top, text="Ara:").pack(side=tk.LEFT)
        self.emp_q = tk.StringVar()
        ent = ttk.Entry(top, textvariable=self.emp_q, width=28)
        ent.pack(side=tk.LEFT, padx=6)
        ent.bind("<Return>", lambda _e: self._refresh_active_employees())

        self.emp_only_active = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="Sadece aktif", variable=self.emp_only_active, command=self._refresh_active_employees).pack(
            side=tk.LEFT, padx=(6, 10)
        )

        ttk.Button(top, text="Yenile", command=self._refresh_active_employees).pack(side=tk.LEFT)
        ttk.Button(top, text="Aktif Yap", command=lambda: self._set_selected_emp_active(1)).pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text="Aktif Değil Yap", command=lambda: self._set_selected_emp_active(0)).pack(side=tk.LEFT, padx=6)

        cols = ("id", "ad", "durum", "meslek", "aylik", "para", "notlar")
        self.tree_emp = ttk.Treeview(master, columns=cols, show="headings", height=16, selectmode="extended")
        self.tree_emp.pack(fill=tk.BOTH, expand=True)

        headings = {
            "id": "ID",
            "ad": "AD SOYAD",
            "durum": "DURUM",
            "meslek": "MESLEK",
            "aylik": "AYLIK",
            "para": "PARA",
            "notlar": "NOT",
        }
        for c in cols:
            self.tree_emp.heading(c, text=headings.get(c, c.upper()))

        self.tree_emp.column("id", width=60, anchor="center")
        self.tree_emp.column("ad", width=200)
        self.tree_emp.column("durum", width=110, anchor="center")
        self.tree_emp.column("meslek", width=150)
        self.tree_emp.column("aylik", width=110, anchor="e")
        self.tree_emp.column("para", width=60, anchor="center")
        self.tree_emp.column("notlar", width=240)

        self._refresh_active_employees()

    def _build_active_professions(self, master: ttk.Frame):
        top = ttk.Frame(master)
        top.pack(fill=tk.X, pady=(0, 6))

        ttk.Label(top, text="Ara:").pack(side=tk.LEFT)
        self.mes_q = tk.StringVar()
        ent = ttk.Entry(top, textvariable=self.mes_q, width=28)
        ent.pack(side=tk.LEFT, padx=6)
        ent.bind("<Return>", lambda _e: self._refresh_active_professions())

        self.mes_only_active = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="Sadece aktif", variable=self.mes_only_active, command=self._refresh_active_professions).pack(
            side=tk.LEFT, padx=(6, 10)
        )

        ttk.Button(top, text="Yenile", command=self._refresh_active_professions).pack(side=tk.LEFT)
        ttk.Button(top, text="Aktif Yap", command=lambda: self._set_selected_mes_active(1)).pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text="Aktif Değil Yap", command=lambda: self._set_selected_mes_active(0)).pack(side=tk.LEFT, padx=6)

        cols = ("id", "ad", "durum", "notlar")
        self.tree_mes = ttk.Treeview(master, columns=cols, show="headings", height=18, selectmode="extended")
        self.tree_mes.pack(fill=tk.BOTH, expand=True)

        headings = {"id": "ID", "ad": "MESLEK", "durum": "DURUM", "notlar": "NOT"}
        for c in cols:
            self.tree_mes.heading(c, text=headings.get(c, c.upper()))

        self.tree_mes.column("id", width=60, anchor="center")
        self.tree_mes.column("ad", width=260)
        self.tree_mes.column("durum", width=110, anchor="center")
        self.tree_mes.column("notlar", width=420)

        self._refresh_active_professions()

    def _get_selected_ids(self, tree: ttk.Treeview) -> List[int]:
        ids: List[int] = []
        for iid in tree.selection() or []:
            vals = tree.item(iid, "values")
            if not vals:
                continue
            try:
                ids.append(int(vals[0]))
            except Exception:
                continue
        return ids

    def _refresh_active_employees(self):
        for iid in self.tree_emp.get_children():
            self.tree_emp.delete(iid)

        q = (self.emp_q.get() or "").strip()
        only_active = bool(self.emp_only_active.get())

        try:
            rows = self.db.maas_calisan_list(q=q, only_active=only_active)  # type: ignore
        except Exception:
            rows = []

        for r in rows:
            try:
                durum = "Aktif" if int(r["aktif"] or 0) == 1 else "Aktif değil"
            except Exception:
                durum = "Aktif"
            try:
                meslek = str(r["meslek_ad"] or "")
            except Exception:
                meslek = ""

            try:
                aylik = fmt_amount(float(r["aylik_tutar"] or 0))
            except Exception:
                aylik = "0,00"

            self.tree_emp.insert(
                "",
                tk.END,
                values=(
                    int(r["id"]),
                    str(r["ad"] or ""),
                    durum,
                    meslek,
                    aylik,
                    str(r["para"] or "TL"),
                    str(r["notlar"] or ""),
                ),
            )

    def _refresh_active_professions(self):
        for iid in self.tree_mes.get_children():
            self.tree_mes.delete(iid)

        q = (self.mes_q.get() or "").strip()
        only_active = bool(self.mes_only_active.get())

        try:
            rows = self.db.maas_meslek_list(q=q, only_active=only_active)  # type: ignore
        except Exception:
            rows = []

        for r in rows:
            try:
                durum = "Aktif" if int(r["aktif"] or 0) == 1 else "Aktif değil"
            except Exception:
                durum = "Aktif"
            self.tree_mes.insert(
                "",
                tk.END,
                values=(int(r["id"]), str(r["ad"] or ""), durum, str(r["notlar"] or "")),
            )

    def _set_selected_emp_active(self, aktif: int):
        ids = self._get_selected_ids(self.tree_emp)
        if not ids:
            messagebox.showinfo(APP_TITLE, "Önce çalışan seç.")
            return
        ok = 0
        for cid in ids:
            try:
                self.db.maas_calisan_set_active(cid, int(aktif))  # type: ignore
                ok += 1
            except Exception:
                continue
        self._refresh_active_employees()
        try:
            self.app.reload_settings()
        except Exception:
            pass
        messagebox.showinfo(APP_TITLE, f"Güncellendi: {ok} çalışan")

    def _set_selected_mes_active(self, aktif: int):
        ids = self._get_selected_ids(self.tree_mes)
        if not ids:
            messagebox.showinfo(APP_TITLE, "Önce meslek seç.")
            return
        ok = 0
        for mid in ids:
            try:
                self.db.maas_meslek_set_active(mid, int(aktif))  # type: ignore
                ok += 1
            except Exception:
                continue
        self._refresh_active_professions()
        try:
            self.app.reload_settings()
        except Exception:
            pass
        messagebox.showinfo(APP_TITLE, f"Güncellendi: {ok} meslek")



    # -----------------
    # Aktif/Pasif Yönetimi (Cariler)
    # -----------------
    def _build_active_caris(self, master: ttk.Frame):
        top = ttk.Frame(master)
        top.pack(fill=tk.X, pady=(0, 6))

        ttk.Label(top, text="Ara:").pack(side=tk.LEFT)
        self.cari_q = tk.StringVar()
        ent = ttk.Entry(top, textvariable=self.cari_q, width=28)
        ent.pack(side=tk.LEFT, padx=6)
        ent.bind("<Return>", lambda _e: self._refresh_active_caris())

        self.cari_only_active = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="Sadece aktif", variable=self.cari_only_active, command=self._refresh_active_caris).pack(
            side=tk.LEFT, padx=(6, 10)
        )

        ttk.Button(top, text="Yenile", command=self._refresh_active_caris).pack(side=tk.LEFT)
        ttk.Button(top, text="Aktif Yap", command=lambda: self._set_selected_cari_active(1)).pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text="Aktif Değil Yap", command=lambda: self._set_selected_cari_active(0)).pack(side=tk.LEFT, padx=6)

        cols = ("id", "ad", "durum", "tur", "telefon", "acilis", "notlar")
        self.tree_cari = ttk.Treeview(master, columns=cols, show="headings", height=18, selectmode="extended")
        self.tree_cari.pack(fill=tk.BOTH, expand=True)

        headings = {
            "id": "ID",
            "ad": "CARI AD",
            "durum": "DURUM",
            "tur": "TÜR",
            "telefon": "TELEFON",
            "acilis": "AÇILIŞ",
            "notlar": "NOT",
        }
        for c in cols:
            self.tree_cari.heading(c, text=headings.get(c, c.upper()))

        self.tree_cari.column("id", width=60, anchor="center")
        self.tree_cari.column("ad", width=220)
        self.tree_cari.column("durum", width=110, anchor="center")
        self.tree_cari.column("tur", width=140)
        self.tree_cari.column("telefon", width=130)
        self.tree_cari.column("acilis", width=110, anchor="e")
        self.tree_cari.column("notlar", width=300)

        self._refresh_active_caris()

    def _refresh_active_caris(self):
        if not hasattr(self, "tree_cari"):
            return
        for iid in self.tree_cari.get_children():
            self.tree_cari.delete(iid)

        q = (self.cari_q.get() or "").strip() if hasattr(self, "cari_q") else ""
        only_active = bool(self.cari_only_active.get()) if hasattr(self, "cari_only_active") else False

        try:
            rows = self.db.cari_list(q=q, only_active=only_active)  # type: ignore
        except Exception:
            rows = []

        for r in rows:
            try:
                durum = "Aktif" if int(r["aktif"] or 0) == 1 else "Aktif değil"
            except Exception:
                durum = "Aktif"

            try:
                ac = fmt_amount(float(r["acilis_bakiye"] or 0))
            except Exception:
                ac = "0,00"

            self.tree_cari.insert(
                "",
                tk.END,
                values=(
                    int(r["id"]),
                    str(r["ad"] or ""),
                    durum,
                    str(r["tur"] or ""),
                    str(r["telefon"] or ""),
                    ac,
                    str(r["notlar"] or ""),
                ),
            )

    def _set_selected_cari_active(self, aktif: int):
        ids = self._get_selected_ids(self.tree_cari)
        if not ids:
            messagebox.showinfo(APP_TITLE, "Önce cari seç.")
            return
        ok = 0
        for cid in ids:
            try:
                self.db.cari_set_active(cid, int(aktif))  # type: ignore
                ok += 1
            except Exception:
                continue

        self._refresh_active_caris()

        # ilgili ekranları tazele
        try:
            # Cariler artık Tanımlar hub içinde
            if "tanimlar" in self.app.frames and hasattr(self.app.frames["tanimlar"], "refresh"):
                self.app.frames["tanimlar"].refresh()  # type: ignore
        except Exception:
            pass
        try:
            if "kasa" in self.app.frames and hasattr(self.app.frames["kasa"], "reload_cari_combo"):
                self.app.frames["kasa"].reload_cari_combo()  # type: ignore
        except Exception:
            pass
        try:
            for k2 in ("cari_hareket", "cari_hareketler", "cari_hareket_ekle"):
                if k2 in self.app.frames and hasattr(self.app.frames[k2], "reload_cari"):
                    self.app.frames[k2].reload_cari()  # type: ignore
        except Exception:
            pass

        messagebox.showinfo(APP_TITLE, f"Güncellendi: {ok} cari")
    # -----------------
    # Kullanıcılar (Admin)
    # -----------------
    def _build_users_tab(self, master: ttk.Frame):
        if not bool(getattr(self.app, "is_admin", False)):
            ttk.Label(master, text="Kullanıcı yönetimi sadece admin içindir.").pack(padx=10, pady=10, anchor="w")
            return

        top = ttk.Frame(master)
        top.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(top, text="Yenile", command=self._users_refresh).pack(side=tk.LEFT)
        ttk.Button(top, text="Yeni", command=self._user_add).pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text="Şifre", command=self._user_pass).pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text="Rol", command=self._user_role).pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text="Sil", command=self._user_del).pack(side=tk.LEFT, padx=6)

        cols = ("id", "username", "role", "created_at")
        self.tree_users = ttk.Treeview(master, columns=cols, show="headings", height=18)
        for c in cols:
            self.tree_users.heading(c, text=c.upper())
        self.tree_users.column("id", width=50, anchor="center")
        self.tree_users.column("username", width=160)
        self.tree_users.column("role", width=90, anchor="center")
        self.tree_users.column("created_at", width=160)
        self.tree_users.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self._users_refresh()

    def _selected_user_id(self) -> Optional[int]:
        if not hasattr(self, "tree_users"):
            return None
        s = self.tree_users.selection()
        if not s:
            return None
        return int(self.tree_users.item(s[0], "values")[0])

    def _users_refresh(self):
        if not hasattr(self, "tree_users"):
            return
        for i in self.tree_users.get_children():
            self.tree_users.delete(i)
        # Login kullanıcıları UsersDB'de tutulur (kasa_users.db)
        try:
            rows = self.app.usersdb.list_users()
        except Exception:
            rows = []
        for r in rows:
            try:
                rid = int(r["id"])
            except Exception:
                continue
            try:
                uname = str(r["username"])
            except Exception:
                uname = ""
            try:
                role = str(r["role"])
            except Exception:
                role = "user"
            try:
                created = str(r["created_at"])
            except Exception:
                created = ""
            self.tree_users.insert("", tk.END, values=(rid, uname, role, created))

    def _user_add(self):
        u = simple_input(self, "Yeni Kullanıcı", "Kullanıcı adı:")
        if not u:
            return
        # Şifre doğrulama (iki kez sor)
        p1 = simple_input(self, "Yeni Kullanıcı", "Şifre:", password=True)
        if p1 is None:
            return
        p2 = simple_input(self, "Yeni Kullanıcı", "Şifre (tekrar):", password=True)
        if p2 is None:
            return
        if p1 != p2:
            messagebox.showerror(APP_TITLE, "Şifreler eşleşmiyor.")
            return
        role = simple_choice(self, "Rol", "Rol seç:", ["admin", "user"], default="user")
        if not role:
            return
        try:
            self.app.usersdb.add_user(u, p1, role=str(role), create_db=True)
            self._users_refresh()
        except Exception as e:
            messagebox.showerror(APP_TITLE, str(e))

    def _user_pass(self):
        uid = self._selected_user_id()
        if not uid:
            return
        # Şifre doğrulama (iki kez sor)
        p1 = simple_input(self, "Şifre Değiştir", "Yeni şifre:", password=True)
        if p1 is None:
            return
        p2 = simple_input(self, "Şifre Değiştir", "Yeni şifre (tekrar):", password=True)
        if p2 is None:
            return
        if p1 != p2:
            messagebox.showerror(APP_TITLE, "Şifreler eşleşmiyor.")
            return
        # UsersDB set_password username ile çalışır; seçili kullanıcı adını alalım.
        s = self.tree_users.selection()
        try:
            username = str(self.tree_users.item(s[0], "values")[1]) if s else ""
        except Exception:
            username = ""
        if not username:
            return
        self.app.usersdb.set_password(username, p1)
        messagebox.showinfo(APP_TITLE, "Şifre güncellendi.")

    def _user_role(self):
        uid = self._selected_user_id()
        if not uid:
            return
        role = simple_choice(self, "Rol Değiştir", "Rol seç:", ["admin", "user"], default="user")
        if not role:
            return
        self.app.usersdb.set_role(int(uid), str(role))
        self._users_refresh()

    def _user_del(self):
        uid = self._selected_user_id()
        if not uid:
            return
        if messagebox.askyesno(APP_TITLE, "Kullanıcı silinsin mi?"):
            s = self.tree_users.selection()
            try:
                username = str(self.tree_users.item(s[0], "values")[1]) if s else ""
            except Exception:
                username = ""
            if not username:
                return
            # DB dosyalarını otomatik silmeyelim; güvenli olsun.
            self.app.usersdb.delete_user(username, delete_db_file=False)
            self._users_refresh()

    # -----------------
    # Veritabanı (DB) - Yedek / Geri Yükle
    # -----------------

    def _get_base_dir(self) -> str:
        return getattr(self.app, "base_dir", None) or APP_BASE_DIR

    def _get_shared_storage_root(self) -> str:
        base = self._get_base_dir()
        return os.path.join(base, SHARED_STORAGE_DIRNAME)

    def _get_shared_storage_path(self) -> str:
        root = self._get_shared_storage_root()
        company_name = getattr(self.app, "active_company_name", "") or "sirket"
        company_id = getattr(self.app, "active_company_id", None)
        slug = _safe_slug(company_name)
        if company_id:
            folder = f"{company_id}_{slug}"
        else:
            folder = slug or "sirket"
        return os.path.join(root, folder)

    def _refresh_shared_storage_info(self) -> None:
        if not hasattr(self, "lbl_shared_storage"):
            return
        path = self._get_shared_storage_path()
        root = self._get_shared_storage_root()
        text = (
            "Şirket içi ortak dosya alanı.\n"
            f"Kök klasör: {root}\n"
            f"Aktif şirket klasörü: {path}"
        )
        self.lbl_shared_storage.config(text=text)

    def _build_shared_storage_tab(self, master: ttk.Frame):
        self.lbl_shared_storage = ttk.Label(master, text="", justify="left")
        self.lbl_shared_storage.pack(anchor="w", padx=10, pady=(10, 8))
        self._refresh_shared_storage_info()

        btns = ttk.Frame(master)
        btns.pack(fill=tk.X, padx=10, pady=(0, 8))

        def ensure_and_open():
            path = self._get_shared_storage_path()
            try:
                os.makedirs(path, exist_ok=True)
            except Exception as e:
                messagebox.showerror(APP_TITLE, f"Klasör oluşturulamadı:\n{e}", parent=self)
                return
            self._open_in_file_manager(path)

        def copy_path():
            path = self._get_shared_storage_path()
            try:
                self.clipboard_clear()
                self.clipboard_append(path)
                messagebox.showinfo(APP_TITLE, "Klasör yolu kopyalandı.", parent=self)
            except Exception as e:
                messagebox.showerror(APP_TITLE, f"Kopyalanamadı:\n{e}", parent=self)

        ttk.Button(btns, text="📂 Klasörü Aç", command=ensure_and_open).pack(side=tk.LEFT)
        ttk.Button(btns, text="📋 Yolu Kopyala", command=copy_path).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="🔄 Yenile", command=self._refresh_shared_storage_info).pack(side=tk.RIGHT)

    def _list_backup_files(self) -> List[str]:
        base = self._get_base_dir()
        files = glob(os.path.join(base, "kasa_backup_*.db"))
        try:
            files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        except Exception:
            files = sorted(files, reverse=True)
        return files

    def _open_in_file_manager(self, path: str):
        try:
            if not os.path.exists(path):
                messagebox.showinfo(APP_TITLE, f"Bulunamadı:\n{path}", parent=self)
                return

            if sys.platform.startswith("win"):
                os.startfile(path)  # type: ignore[attr-defined]
                return
            if sys.platform == "darwin":
                subprocess.Popen(["open", path])
                return
            subprocess.Popen(["xdg-open", path])
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Açılamadı:\n{e}", parent=self)

    def _build_db_backup_tab(self, master: ttk.Frame):
        base = self._get_base_dir()

        info = ttk.Label(
            master,
            text=(
                "Bu sekmeden mevcut şirket veritabanının yedeğini alabilirsin.\n"
                "Yedek dosyaları uygulama klasörüne kaydedilir (kasa_backup_*.db).\n"
                f"Klasör: {base}"
            ),
            justify="left",
        )
        info.pack(anchor="w", padx=10, pady=(10, 8))

        top = ttk.Frame(master)
        top.pack(fill=tk.X, padx=10)

        def do_backup():
            try:
                self.app.backup_db()
            except Exception as e:
                messagebox.showerror(APP_TITLE, f"Yedek alınamadı:\n{e}", parent=self)
            self._refresh_backup_list(getattr(self, "tree_db_backup", None))

        ttk.Button(top, text="💾 Yedek Al", command=do_backup).pack(side=tk.LEFT)
        ttk.Button(top, text="🔄 Listeyi Yenile", command=lambda: self._refresh_backup_list(getattr(self, "tree_db_backup", None))).pack(
            side=tk.LEFT, padx=6
        )
        ttk.Button(top, text="📂 Klasörü Aç", command=lambda: self._open_in_file_manager(base)).pack(side=tk.RIGHT)

        self.tree_db_backup = self._make_backup_tree(master)
        self._refresh_backup_list(self.tree_db_backup)

    def _build_db_restore_tab(self, master: ttk.Frame):
        base = self._get_base_dir()

        warn = ttk.Label(
            master,
            text=(
                "Uyarı: Geri yükleme mevcut şirket DB'sinin üzerine yazar.\n"
                "Önce DB Yedek sekmesinden yedek alman önerilir."
            ),
            justify="left",
        )
        warn.pack(anchor="w", padx=10, pady=(10, 8))

        top = ttk.Frame(master)
        top.pack(fill=tk.X, padx=10)

        if not bool(getattr(self.app, "is_admin", False)):
            ttk.Label(top, text="Bu işlem için admin yetkisi gerekir.").pack(side=tk.LEFT)
        else:
            def do_restore():
                try:
                    self.app.restore_db()
                except Exception as e:
                    messagebox.showerror(APP_TITLE, f"Geri yükleme başarısız:\n{e}", parent=self)
                # DB değişmiş olabileceği için referansı tazele
                try:
                    self.db = self.app.db
                except Exception:
                    pass
                self._refresh_backup_list(getattr(self, "tree_db_restore", None))

            ttk.Button(top, text="♻️ Yedek Seç ve Geri Yükle", command=do_restore).pack(side=tk.LEFT)

        ttk.Button(top, text="🔄 Listeyi Yenile", command=lambda: self._refresh_backup_list(getattr(self, "tree_db_restore", None))).pack(
            side=tk.LEFT, padx=6
        )
        ttk.Button(top, text="📂 Klasörü Aç", command=lambda: self._open_in_file_manager(base)).pack(side=tk.RIGHT)

        self.tree_db_restore = self._make_backup_tree(master)
        self._refresh_backup_list(self.tree_db_restore)

    def _make_backup_tree(self, master: ttk.Frame) -> ttk.Treeview:
        box = ttk.LabelFrame(master, text="Mevcut Yedekler")
        box.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        cols = ("file", "modified", "size")
        tree = ttk.Treeview(box, columns=cols, show="headings", height=14)
        tree.heading("file", text="Dosya")
        tree.heading("modified", text="Değiştirme")
        tree.heading("size", text="Boyut")

        tree.column("file", width=440, anchor="w")
        tree.column("modified", width=170, anchor="w")
        tree.column("size", width=120, anchor="e")

        ysb = ttk.Scrollbar(box, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=ysb.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=8)
        ysb.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 8), pady=8)

        # Çift tıklayınca dosyanın bulunduğu klasörü aç
        def on_dbl(_e):
            try:
                sel = tree.selection()
                if not sel:
                    return
                vals = tree.item(sel[0], "values")
                if not vals:
                    return
                f = str(vals[0])
                base = self._get_base_dir()
                p = os.path.join(base, f)
                self._open_in_file_manager(os.path.dirname(p))
            except Exception:
                return

        try:
            tree.bind("<Double-1>", on_dbl)
        except Exception:
            pass

        return tree

    def _refresh_backup_list(self, tree: Optional[ttk.Treeview]):
        if tree is None:
            return
        try:
            for iid in tree.get_children():
                tree.delete(iid)
        except Exception:
            return

        for p in self._list_backup_files():
            try:
                name = os.path.basename(p)
                m = ""
                try:
                    m = tk.StringVar(value="").get()  # placeholder for tk init safety
                except Exception:
                    pass
                try:
                    from datetime import datetime

                    m = datetime.fromtimestamp(os.path.getmtime(p)).strftime("%Y-%m-%d %H:%M")
                except Exception:
                    m = ""
                try:
                    size = os.path.getsize(p)
                    size_txt = f"{size/1024/1024:.2f} MB"
                except Exception:
                    size_txt = ""
                tree.insert("", tk.END, values=(name, m, size_txt))
            except Exception:
                continue
