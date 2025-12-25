# -*- coding: utf-8 -*-
"""KasaPro v3 - Ana ekran frame'leri"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

import tkinter as tk
from tkinter import ttk, messagebox

from ...config import APP_TITLE
from ..base import BaseView
from ..ui_logging import wrap_callback
from ..dialogs import simple_input, simple_choice

if TYPE_CHECKING:
    from ...app import App

class KullanicilarFrame(BaseView):
    def __init__(self, master, app: "App"):
        self.app = app
        super().__init__(master, app)
        self.build_ui()

    def build_ui(self) -> None:
        self._build()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=12, pady=12)
        ttk.Label(top, text="Kullanıcılar", font=("Calibri", 16, "bold")).pack(side=tk.LEFT)

        btns = ttk.Frame(top)
        btns.pack(side=tk.RIGHT)
        ttk.Button(btns, text="➕ Yeni", command=wrap_callback("users_add", self.add_user)).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="🔑 Şifre", command=wrap_callback("users_reset", self.reset_password)).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(btns, text="🗑 Sil", command=wrap_callback("users_delete", self.delete_user)).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="🔄 Yenile", command=wrap_callback("users_refresh", self.refresh)).pack(side=tk.LEFT, padx=4)

        cols = ("username", "role", "created_at", "last_login", "db_file")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=18)
        self.tree.heading("username", text="Kullanıcı")
        self.tree.heading("role", text="Rol")
        self.tree.heading("created_at", text="Oluşturma")
        self.tree.heading("last_login", text="Son Giriş")
        self.tree.heading("db_file", text="DB Dosyası")

        self.tree.column("username", width=160, anchor="w")
        self.tree.column("role", width=80, anchor="center")
        self.tree.column("created_at", width=160, anchor="w")
        self.tree.column("last_login", width=160, anchor="w")
        self.tree.column("db_file", width=220, anchor="w")

        self.tree.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0,12))
        self.tree.bind("<Double-1>", wrap_callback("users_reset_double", lambda _e: self.reset_password()))
        self.refresh()

    def _selected_username(self) -> Optional[str]:
        sel = self.tree.selection()
        if not sel:
            return None
        iid = sel[0]
        vals = self.tree.item(iid, "values")
        if not vals:
            return None
        return str(vals[0])

    def refresh(self, data=None):
        try:
            for i in self.tree.get_children():
                self.tree.delete(i)
        except Exception:
            pass

        try:
            users = self.app.usersdb.list_users()
        except Exception:
            users = []

        for u in users:
            self.tree.insert(
                "", "end",
                values=(
                    u["username"],
                    u["role"],
                    (u["created_at"] or ""),
                    (u["last_login"] or ""),
                    (u["db_file"] or ""),
                )
            )
        try:
            self.app.on_users_changed()
        except Exception:
            pass


    def add_user(self):
        if not self.app.is_admin:
            return
        username = simple_input(self, "Yeni Kullanıcı", "Kullanıcı adı:")
        if not username:
            return
        username = username.strip()
        if not username:
            return

        p1 = simple_input(self, "Yeni Kullanıcı", "Şifre:", password=True)
        if p1 is None:
            return
        p2 = simple_input(self, "Yeni Kullanıcı", "Şifre (tekrar):", password=True)
        if p2 is None:
            return
        if p1 != p2:
            messagebox.showerror(APP_TITLE, "Şifreler eşleşmiyor.")
            return

        role = simple_choice(self, "Yeni Kullanıcı", "Rol seç:", ["user", "admin"], default="user") or "user"
        try:
            self.app.usersdb.add_user(username, p1, role=role, create_db=True)
            messagebox.showinfo(APP_TITLE, f"Kullanıcı eklendi: {username}")
        except Exception as e:
            messagebox.showerror(APP_TITLE, str(e))
            return
        self.refresh()

    def reset_password(self):
        if not self.app.is_admin:
            return
        username = self._selected_username()
        if not username:
            messagebox.showwarning(APP_TITLE, "Önce bir kullanıcı seç.")
            return

        p1 = simple_input(self, "Şifre Sıfırla", f"{username} için yeni şifre:", password=True)
        if p1 is None:
            return
        p2 = simple_input(self, "Şifre Sıfırla", "Şifre (tekrar):", password=True)
        if p2 is None:
            return
        if p1 != p2:
            messagebox.showerror(APP_TITLE, "Şifreler eşleşmiyor.")
            return

        try:
            self.app.usersdb.set_password(username, p1)
            messagebox.showinfo(APP_TITLE, "Şifre güncellendi.")
        except Exception as e:
            messagebox.showerror(APP_TITLE, str(e))
        self.refresh()

    def delete_user(self):
        if not self.app.is_admin:
            return
        username = self._selected_username()
        if not username:
            messagebox.showwarning(APP_TITLE, "Önce bir kullanıcı seç.")
            return
        if username == "admin":
            messagebox.showerror(APP_TITLE, "admin silinemez.")
            return
        if not messagebox.askyesno(APP_TITLE, f"'{username}' kullanıcısı silinsin mi?"):
            return
        del_db = messagebox.askyesno(APP_TITLE, "Kullanıcının veritabanı dosyası da silinsin mi?")
        try:
            self.app.usersdb.delete_user(username, delete_db_file=del_db)
            messagebox.showinfo(APP_TITLE, "Silindi.")
        except Exception as e:
            messagebox.showerror(APP_TITLE, str(e))
        self.refresh()
