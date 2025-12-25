# -*- coding: utf-8 -*-
"""Create Center form: Cari."""

from __future__ import annotations

from typing import Any

import tkinter as tk
from tkinter import ttk, messagebox

from ...config import APP_TITLE
from ...utils import safe_float, fmt_amount
from ..widgets import LabeledEntry, LabeledCombo
from .base import BaseCreateForm


class CariCreateForm(BaseCreateForm):
    def build_ui(self) -> None:
        form = ttk.LabelFrame(self, text="Cari Kartı")
        form.pack(fill=tk.X, padx=10, pady=10)

        self.e_ad = LabeledEntry(form, "Cari Adı:", 28)
        self.e_ad.pack(fill=tk.X, padx=10, pady=(10, 4))

        self.e_tur = LabeledEntry(form, "Tür:", 28)
        self.e_tur.pack(fill=tk.X, padx=10, pady=4)

        self.e_tel = LabeledEntry(form, "Telefon:", 28)
        self.e_tel.pack(fill=tk.X, padx=10, pady=4)

        self.e_durum = LabeledCombo(form, "Durum:", ["Aktif", "Aktif değil"], width=24)
        self.e_durum.pack(fill=tk.X, padx=10, pady=4)

        self.e_acilis = LabeledEntry(form, "Açılış Bakiyesi:", 28)
        self.e_acilis.pack(fill=tk.X, padx=10, pady=4)

        ttk.Label(form, text="Notlar:").pack(anchor="w", padx=10, pady=(8, 0))
        self.e_not = tk.Text(form, width=34, height=6)
        self.e_not.pack(fill=tk.X, padx=10, pady=(4, 10))

        self.reset_form()

    def focus_first(self) -> None:
        try:
            self.e_ad.ent.focus_set()
        except Exception:
            pass

    def validate_form(self) -> bool:
        self.clear_errors()
        ad = (self.e_ad.get() or "").strip()
        if not ad:
            self.mark_error(self.e_ad.ent, "Cari adı boş olamaz.")
            return False
        return True

    def perform_save(self) -> bool:
        ad = (self.e_ad.get() or "").strip()
        tur = (self.e_tur.get() or "").strip()
        tel = (self.e_tel.get() or "").strip()
        notlar = (self.e_not.get("1.0", tk.END) or "").strip()
        acilis = safe_float(self.e_acilis.get())
        aktif = 1 if (self.e_durum.get() or "Aktif") == "Aktif" else 0

        try:
            self.app.db.cari_upsert(ad, tur=tur, telefon=tel, notlar=notlar, acilis_bakiye=float(acilis), aktif=aktif)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Cari kaydedilemedi: {exc}")
            return False

        self.add_recent_entity("cari", ad)
        self._refresh_related_frames()
        return True

    def _refresh_related_frames(self) -> None:
        for key in ("tanimlar", "kasa", "cari_hareket", "cari_hareketler"):
            try:
                frame = self.app.frames.get(key)
            except Exception:
                frame = None
            if frame is None:
                continue
            try:
                if hasattr(frame, "refresh"):
                    frame.refresh()
                if hasattr(frame, "reload_cari"):
                    frame.reload_cari()
                if hasattr(frame, "reload_cari_combo"):
                    frame.reload_cari_combo()
            except Exception:
                continue

    def reset_form(self) -> None:
        self.e_ad.set("")
        self.e_tur.set("")
        self.e_tel.set("")
        try:
            self.e_durum.set("Aktif")
        except Exception:
            pass
        self.e_acilis.set(fmt_amount(0))
        try:
            self.e_not.delete("1.0", tk.END)
        except Exception:
            pass
