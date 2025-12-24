# -*- coding: utf-8 -*-
"""KasaPro v3 - Ana ekran frame'leri"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from ...config import APP_TITLE

if TYPE_CHECKING:
    from ...app import App

class SirketlerFrame(ttk.Frame):
    """Kullanıcı girişinden sonra birden fazla şirket (firma) yönetimi.

    Her şirketin kendi SQLite DB dosyası vardır
    böylece cariler/hareketler/ayarlar
    şirket bazında tamamen ayrılır.
    """
    def __init__(self, master, app: "App"):
        super().__init__(master)
        self.app = app
        self._build()

    def _build(self):
        top = ttk.LabelFrame(self, text="Şirketler (Firma Yönetimi)")
        top.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        info = ("Her şirketin verileri ayrı tutulur.\n"
                "Şirket seçtiğinizde program o şirketin veritabanına geçer (cariler/hareketler/raporlar).")
        ttk.Label(top, text=info, foreground="#555").pack(anchor="w", padx=10, pady=(8, 10))

        row = ttk.Frame(top)
        row.pack(fill=tk.X, padx=10, pady=(0, 8))
        self.lbl_active = ttk.Label(row, text="")
        self.lbl_active.pack(side=tk.LEFT)

        btns = ttk.Frame(top)
        btns.pack(fill=tk.X, padx=10, pady=(0, 8))
        ttk.Button(btns, text="➕ Yeni Şirket", command=self.on_new).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="✅ Seç / Aç", command=self.on_open).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="✏️ Yeniden Adlandır", command=self.on_rename).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="🗑️ Sil", command=self.on_delete).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="🔄 Yenile", command=self.refresh).pack(side=tk.RIGHT, padx=4)

        cols = ("id", "name", "created_at", "db_file")
        self.tree = ttk.Treeview(top, columns=cols, show="headings", height=18)
        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Şirket Adı")
        self.tree.heading("created_at", text="Oluşturma")
        self.tree.heading("db_file", text="DB Dosyası")

        self.tree.column("id", width=60, anchor="center")
        self.tree.column("name", width=260, anchor="w")
        self.tree.column("created_at", width=170, anchor="w")
        self.tree.column("db_file", width=260, anchor="w")

        ysb = ttk.Scrollbar(top, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=ysb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=(0, 10))
        ysb.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 10), pady=(0, 10))

        try:
            self.tree.bind("<Double-1>", lambda _e: self.on_open())
        except Exception:
            pass

        self.refresh()

    def _selected_company_id(self) -> Optional[int]:
        try:
            sel = self.tree.selection()
            if not sel:
                return None
            iid = sel[0]
            vals = self.tree.item(iid, "values")
            if not vals:
                return None
            return int(vals[0])
        except Exception:
            return None

    def refresh(self):
        try:
            active_name = getattr(self.app, "active_company_name", "") or ""
            self.lbl_active.config(text=f"Aktif Şirket: {active_name}")
        except Exception:
            pass

        for x in self.tree.get_children():
            self.tree.delete(x)

        uid = self.app.get_active_user_id()
        if not uid:
            return

        try:
            comps = self.app.usersdb.list_companies(int(uid))
        except Exception:
            comps = []

        active_id = getattr(self.app, "active_company_id", None)

        for c in comps:
            cid = int(c["id"])
            created = ""
            dbf = ""
            try:
                created = str(c["created_at"])
            except Exception:
                pass
            try:
                dbf = str(c["db_file"])
            except Exception:
                pass
            vals = (cid, str(c["name"]), created, dbf)
            iid = self.tree.insert("", "end", values=vals)
            if active_id and cid == int(active_id):
                try:
                    self.tree.selection_set(iid)
                    self.tree.see(iid)
                except Exception:
                    pass

    def on_new(self):
        uid = self.app.get_active_user_id()
        if not uid:
            return
        name = simpledialog.askstring(APP_TITLE, "Yeni şirket adı:")
        if not name:
            return
        try:
            cid = self.app.usersdb.add_company(int(uid), str(name))
            # Yeni oluşturulan şirkete geç
            self.app.switch_company(cid)
            self.refresh()
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Şirket oluşturulamadı:\n{e}")

    def on_open(self):
        cid = self._selected_company_id()
        if not cid:
            messagebox.showinfo(APP_TITLE, "Lütfen listeden bir şirket seçin.")
            return
        try:
            self.app.switch_company(int(cid))
            self.refresh()
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Şirkete geçilemedi:\n{e}")

    def on_rename(self):
        cid = self._selected_company_id()
        if not cid:
            messagebox.showinfo(APP_TITLE, "Lütfen listeden bir şirket seçin.")
            return
        try:
            c = self.app.usersdb.get_company_by_id(int(cid))
            old = str(c["name"]) if c else ""
        except Exception:
            old = ""
        name = simpledialog.askstring(APP_TITLE, "Yeni şirket adı:", initialvalue=old)
        if not name:
            return
        try:
            self.app.usersdb.rename_company(int(cid), str(name))
            # aktif şirket adı değiştiyse etiketi güncelle
            if getattr(self.app, "active_company_id", None) and int(self.app.active_company_id or 0) == int(cid):
                try:
                    self.app.active_company_name = str(name)
                    self.app._update_company_label()
                except Exception:
                    pass
            self.refresh()
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Yeniden adlandırılamadı:\n{e}")

    def on_delete(self):
        cid = self._selected_company_id()
        if not cid:
            messagebox.showinfo(APP_TITLE, "Lütfen listeden bir şirket seçin.")
            return
        if not messagebox.askyesno(APP_TITLE, "Seçili şirket silinsin mi?\n(DB dosyası da silinir)"):
            return
        uid = self.app.get_active_user_id()
        if not uid:
            return
        try:
            was_active = (getattr(self.app, "active_company_id", None) is not None and int(self.app.active_company_id or 0) == int(cid))
            self.app.usersdb.delete_company(int(cid), delete_db_file=True)

            # aktif şirket silindiyse otomatik başka şirkete geç
            if was_active:
                urow = self.app.get_active_user_row()
                try:
                    # kullanıcı satırını tazele (last_company_id değişmiş olabilir)
                    urow2 = self.app.usersdb.get_user_by_username(str(urow["username"])) if urow else None
                except Exception:
                    urow2 = urow
                crow = self.app.usersdb.get_active_company_for_user(urow2) if urow2 else None
                if crow:
                    self.app.switch_company(int(crow["id"]))
            self.refresh()
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Silinemedi:\n{e}")

