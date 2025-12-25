# -*- coding: utf-8 -*-
"""Create Center form: Ürün."""

from __future__ import annotations

from typing import Optional

import tkinter as tk
from tkinter import ttk, messagebox

from ...config import APP_TITLE
from ...utils import parse_number_smart
from ..widgets import LabeledEntry, LabeledCombo
from .base import BaseCreateForm


class UrunCreateForm(BaseCreateForm):
    def build_ui(self) -> None:
        form = ttk.LabelFrame(self, text="Ürün Kartı")
        form.pack(fill=tk.X, padx=10, pady=10)

        row1 = ttk.Frame(form)
        row1.pack(fill=tk.X, padx=8, pady=(8, 4))
        self.in_kod = LabeledEntry(row1, "Kod:", 14)
        self.in_kod.pack(side=tk.LEFT, padx=4)
        self.in_ad = LabeledEntry(row1, "Ad:", 24)
        self.in_ad.pack(side=tk.LEFT, padx=4)
        self.in_kategori = LabeledCombo(row1, "Kategori:", [], 18)
        self.in_kategori.pack(side=tk.LEFT, padx=4)
        self.in_birim = LabeledCombo(row1, "Birim:", [], 10)
        self.in_birim.pack(side=tk.LEFT, padx=4)

        row2 = ttk.Frame(form)
        row2.pack(fill=tk.X, padx=8, pady=4)
        self.in_min = LabeledEntry(row2, "Min Stok:", 12)
        self.in_min.pack(side=tk.LEFT, padx=4)
        self.in_kritik = LabeledEntry(row2, "Kritik:", 12)
        self.in_kritik.pack(side=tk.LEFT, padx=4)
        self.in_max = LabeledEntry(row2, "Max Stok:", 12)
        self.in_max.pack(side=tk.LEFT, padx=4)
        self.in_raf = LabeledEntry(row2, "Raf:", 12)
        self.in_raf.pack(side=tk.LEFT, padx=4)
        self.in_barkod = LabeledEntry(row2, "Barkod:", 16)
        self.in_barkod.pack(side=tk.LEFT, padx=4)

        row3 = ttk.Frame(form)
        row3.pack(fill=tk.X, padx=8, pady=4)
        self.in_tedarikci = LabeledCombo(row3, "Tedarikçi:", ["(Yok)"], 22)
        self.in_tedarikci.pack(side=tk.LEFT, padx=4)
        self.in_durum = LabeledCombo(row3, "Durum:", ["Aktif", "Pasif"], 10)
        self.in_durum.pack(side=tk.LEFT, padx=4)
        self.in_durum.set("Aktif")
        self.in_aciklama = LabeledEntry(row3, "Açıklama:", 40)
        self.in_aciklama.pack(side=tk.LEFT, padx=4, fill=tk.X, expand=True)

        self._load_reference_data()
        self.reset_form()

    def focus_first(self) -> None:
        try:
            self.in_kod.ent.focus_set()
        except Exception:
            pass

    def _load_reference_data(self) -> None:
        def task() -> dict[str, list[str]]:
            categories = []
            units = []
            suppliers = ["(Yok)"]
            try:
                categories = list(self.app.db.list_stock_categories())
            except Exception:
                pass
            try:
                units = list(self.app.db.list_stock_units())
            except Exception:
                pass
            try:
                caris = self.app.db.cari_list(only_active=True)
                suppliers += [f"{r['id']} - {r['ad']}" for r in caris]
            except Exception:
                pass
            return {"categories": categories, "units": units, "suppliers": suppliers}

        def on_done(payload: dict[str, list[str]]) -> None:
            self.in_kategori.cmb.configure(values=payload.get("categories", []))
            self.in_birim.cmb.configure(values=payload.get("units", []))
            self.in_tedarikci.cmb.configure(values=payload.get("suppliers", ["(Yok)"]))
            if not self.in_birim.get():
                self.in_birim.set("Adet")

        self.run_in_background(task, on_done)

    def _parse_supplier_id(self, val: str) -> Optional[int]:
        if not val or val == "(Yok)":
            return None
        try:
            return int(str(val).split("-", 1)[0].strip())
        except Exception:
            return None

    def validate_form(self) -> bool:
        self.clear_errors()
        kod = (self.in_kod.get() or "").strip()
        ad = (self.in_ad.get() or "").strip()
        if not kod:
            self.mark_error(self.in_kod.ent, "Ürün kodu zorunlu.")
            return False
        if not ad:
            self.mark_error(self.in_ad.ent, "Ürün adı zorunlu.")
            return False
        return True

    def perform_save(self) -> bool:
        kod = (self.in_kod.get() or "").strip()
        ad = (self.in_ad.get() or "").strip()
        kategori = (self.in_kategori.get() or "").strip()
        birim = (self.in_birim.get() or "Adet").strip() or "Adet"
        min_stok = parse_number_smart(self.in_min.get())
        kritik = parse_number_smart(self.in_kritik.get())
        max_stok = parse_number_smart(self.in_max.get())
        raf = (self.in_raf.get() or "").strip()
        barkod = (self.in_barkod.get() or "").strip()
        tedarikci_id = self._parse_supplier_id(self.in_tedarikci.get())
        aktif = 1 if (self.in_durum.get() or "Aktif") == "Aktif" else 0
        aciklama = (self.in_aciklama.get() or "").strip()

        try:
            self.app.db.stok_urun_add(
                kod,
                ad,
                kategori,
                birim,
                min_stok,
                max_stok,
                kritik,
                raf,
                tedarikci_id,
                barkod,
                aktif,
                aciklama,
            )
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Ürün kaydedilemedi: {exc}")
            return False

        self.add_recent_entity("urun", ad)
        self._refresh_related_frames()
        return True

    def _refresh_related_frames(self) -> None:
        try:
            frame = self.app.frames.get("stok")
        except Exception:
            frame = None
        if frame is None:
            return
        try:
            if hasattr(frame, "refresh"):
                frame.refresh()
            if hasattr(frame, "reload_settings"):
                frame.reload_settings()
        except Exception:
            pass

    def reset_form(self) -> None:
        self.in_kod.set("")
        self.in_ad.set("")
        try:
            self.in_kategori.set("")
        except Exception:
            pass
        try:
            if self.in_birim.get() == "":
                self.in_birim.set("Adet")
        except Exception:
            pass
        self.in_min.set("0")
        self.in_kritik.set("0")
        self.in_max.set("0")
        self.in_raf.set("")
        self.in_barkod.set("")
        try:
            self.in_tedarikci.set("(Yok)")
        except Exception:
            pass
        self.in_durum.set("Aktif")
        self.in_aciklama.set("")
