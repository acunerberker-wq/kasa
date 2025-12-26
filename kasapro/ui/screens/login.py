# -*- coding: utf-8 -*-
"""Login screen layout (embedded variant)."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..components import PageHeader


class LoginScreen(ttk.Frame):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self._build()

    def _build(self) -> None:
        container = ttk.Frame(self, style="Panel.TFrame")
        container.pack(fill=tk.BOTH, expand=True, padx=24, pady=24)

        header = PageHeader(container, title="Giriş")
        header.pack(fill=tk.X, pady=(0, 12))

        form = ttk.Frame(container, style="Panel.TFrame")
        form.pack(fill=tk.X)

        ttk.Label(form, text="E-posta", style="Muted.TLabel").pack(anchor="w")
        ttk.Entry(form).pack(fill=tk.X, pady=(4, 12))

        ttk.Label(form, text="Şifre", style="Muted.TLabel").pack(anchor="w")
        ttk.Entry(form, show="*").pack(fill=tk.X, pady=(4, 12))

        ttk.Checkbutton(form, text="Beni hatırla").pack(anchor="w")
        ttk.Button(container, text="Giriş Yap", style="Primary.TButton").pack(fill=tk.X, pady=(12, 0))
