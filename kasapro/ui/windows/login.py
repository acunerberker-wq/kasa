# -*- coding: utf-8 -*-
"""KasaPro v3 - Login penceresi (Toplevel)."""

from __future__ import annotations

import sqlite3
from typing import Optional

import tkinter as tk
from tkinter import ttk, messagebox

from ...config import APP_TITLE
from ...db.users_db import UsersDB
from ...utils import center_window
from ..widgets import LabeledEntry, LabeledCombo

class LoginWindow(tk.Toplevel):
    def __init__(self, root: tk.Tk, usersdb: UsersDB):
        super().__init__(root)
        self.usersdb = usersdb
        self.user: Optional[sqlite3.Row] = None
        self.title("Giriş")
        self.geometry("520x420")
        self.resizable(False, False)
        # root withdraw durumunda transient sorun çıkarabiliyor
        try:
            if bool(root.winfo_viewable()):
                self.transient(root)
        except Exception:
            pass
        self.protocol("WM_DELETE_WINDOW", self.do_exit)

        self.configure(padx=0, pady=0)
        container = ttk.Frame(self, style="TFrame")
        container.pack(fill=tk.BOTH, expand=True, padx=24, pady=24)

        card = ttk.Frame(container, style="Panel.TFrame")
        card.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        ttk.Label(card, text="KasaPro", style="H1.TLabel").pack(pady=(16, 4))
        ttk.Label(card, text="Hesabına giriş yap", style="Muted.TLabel").pack(pady=(0, 12))

        frm = ttk.Frame(card, style="Panel.TFrame")
        frm.pack(fill=tk.X, padx=18, pady=6)

        # Kullanıcı seçimi (liste)
        self.pick_user = LabeledCombo(frm, "Kullanıcı Seç:", self.usersdb.list_usernames(), 18)
        self.pick_user.pack(fill=tk.X, pady=6)
        try:
            self.pick_user.cmb.bind("<<ComboboxSelected>>", lambda _e: self._on_pick_user())
        except Exception:
            pass

        # Varsayılan kullanıcı: listedeki ilk değer
        try:
            vals = list(self.pick_user.cmb["values"])
            if vals:
                self.pick_user.set(vals[0])
        except Exception:
            pass


        self.e_user = LabeledEntry(frm, "Kullanıcı:", 18)
        self.e_user.pack(fill=tk.X, pady=6)
        self.e_pass = LabeledEntry(frm, "Şifre:", 18)
        self.e_pass.pack(fill=tk.X, pady=6)
        self.e_pass.ent.config(show="*")

        # Başlangıçta seçilen kullanıcıyı kullanıcı alanına yansıt
        try:
            self._on_pick_user()
        except Exception:
            pass

        self.remember_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(frm, text="Beni hatırla", variable=self.remember_var).pack(anchor="w", pady=(8, 0))

        btn = ttk.Frame(card, style="Panel.TFrame")
        btn.pack(fill=tk.X, padx=18, pady=(10, 4))
        ttk.Button(btn, text="Giriş Yap", style="Primary.TButton", command=self.do_login).pack(fill=tk.X)

        ttk.Button(card, text="Şifremi unuttum", style="Secondary.TButton", command=self.do_exit).pack(
            pady=(6, 0)
        )

        ttk.Label(card, text="İlk kurulum: admin / admin", style="Muted.TLabel").pack(pady=(8, 6))
        self.bind("<Return>", lambda _e: self.do_login())
        # ✅ Daha sağlam modal gösterimi (root withdraw olsa bile)
        self.protocol("WM_DELETE_WINDOW", self.do_exit)
        center_window(self)

        # Bazı sistemlerde pencere görünür olmadan wait_visibility/grab_set kilitleyebiliyor.
        # Bu yüzden her şeyi biraz gecikmeli yapıyoruz.
        try:
            self.deiconify()
        except Exception:
            pass

        def _post_show():
            try:
                self.lift()
                self.focus_force()
            except Exception:
                pass
            try:
                self.attributes("-topmost", True)
                self.after(300, lambda: self.attributes("-topmost", False))
            except Exception:
                pass
            try:
                self.grab_set()
            except Exception:
                pass
            try:
                self.e_user.ent.focus_set()
            except Exception:
                pass

        self.after(50, _post_show)

    def _on_pick_user(self):
        u = self.pick_user.get().strip() if hasattr(self, 'pick_user') else ''
        if u:
            try:
                self.e_user.set(u)
            except Exception:
                try:
                    self.e_user.ent.delete(0, tk.END)
                    self.e_user.ent.insert(0, u)
                except Exception:
                    pass
            try:
                self.e_pass.ent.focus_set()
            except Exception:
                pass

    def do_login(self):
        u = self.e_user.get().strip()
        p = self.e_pass.get()
        user = self.usersdb.auth(u, p)
        if not user:
            messagebox.showerror(APP_TITLE, "Hatalı kullanıcı/şifre.")
            return
        self.user = user
        # Login başarılı (log, kullanıcı DB'si açıldıktan sonra App içinde yazılır)
        self.destroy()

    def do_exit(self):
        self.user = None
        self.destroy()
