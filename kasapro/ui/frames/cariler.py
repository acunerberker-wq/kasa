# -*- coding: utf-8 -*-
"""KasaPro v3 - Cari kartları ekranı."""

from __future__ import annotations

import sqlite3
from typing import Optional, List, Tuple

import tkinter as tk
from tkinter import ttk, messagebox

from ...config import APP_TITLE
from ...utils import parse_number_smart, safe_float, fmt_amount
from ..widgets import LabeledEntry, LabeledCombo
from ..windows import CariEkstreWindow


class CarilerFrame(ttk.Frame):
    def __init__(self, master, app: "App"):
        super().__init__(master)
        self.app = app
        self.selected_id: Optional[int] = None
        self._build()

    def _build(self):
        top = ttk.LabelFrame(self, text="Cari Kartları")
        top.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left = ttk.Frame(top)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))
        right = ttk.LabelFrame(top, text="Cari Ekle / Güncelle")
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(8, 0))

        frow = ttk.Frame(left)
        frow.pack(fill=tk.X, pady=4)
        self.q = LabeledEntry(frow, "Ara:", 20)
        self.q.pack(side=tk.LEFT, padx=6)

        self.only_active = tk.BooleanVar(value=True)
        ttk.Checkbutton(frow, text="Sadece aktif", variable=self.only_active, command=self.refresh).pack(
            side=tk.LEFT, padx=(6, 10)
        )
        ttk.Button(frow, text="Yenile", command=self.refresh).pack(side=tk.LEFT, padx=6)

        cols = ("id", "durum", "ad", "tur", "telefon", "acilis")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", height=16)
        headings = {
            "id": "ID",
            "durum": "DURUM",
            "ad": "CARI ADI",
            "tur": "TÜR",
            "telefon": "TELEFON",
            "acilis": "AÇILIŞ",
        }
        for c in cols:
            self.tree.heading(c, text=headings.get(c, c.upper()))

        self.tree.column("id", width=50, anchor="center")
        self.tree.column("durum", width=95, anchor="center")
        self.tree.column("ad", width=240)
        self.tree.column("tur", width=140)
        self.tree.column("telefon", width=140)
        self.tree.column("acilis", width=110, anchor="e")

        self.tree.tag_configure("inactive", foreground="gray")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.tree.bind("<Double-1>", lambda _e: self.edit_selected())
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Return>", lambda _e: self.open_ekstre())

        btm = ttk.Frame(left)
        btm.pack(fill=tk.X, pady=(0, 6))
        self.btn_edit = ttk.Button(btm, text="Düzenle", command=self.edit_selected)
        self.btn_edit.pack(side=tk.LEFT, padx=6)
        self.btn_del = ttk.Button(btm, text="Sil", command=self.delete)
        self.btn_del.pack(side=tk.LEFT, padx=6)
        ttk.Button(btm, text="📒 Hareket / Ekstre", command=self.open_ekstre).pack(side=tk.LEFT, padx=6)

        self.e_ad = LabeledEntry(right, "Cari Adı:", 26)
        self.e_ad.pack(fill=tk.X, padx=10, pady=(10, 4))
        self.e_tur = LabeledEntry(right, "Tür:", 26)
        self.e_tur.pack(fill=tk.X, padx=10, pady=4)
        self.e_tel = LabeledEntry(right, "Telefon:", 26)
        self.e_tel.pack(fill=tk.X, padx=10, pady=4)

        # LabeledCombo imzası: (master, label, values, width=..., state=...)
        # Burada 24 genişlik (width) olmalı.
        self.e_durum = LabeledCombo(right, "Durum:", ["Aktif", "Aktif değil"], width=24)
        self.e_durum.pack(fill=tk.X, padx=10, pady=4)

        self.e_acilis = LabeledEntry(right, "Açılış Bakiyesi:", 26)
        self.e_acilis.pack(fill=tk.X, padx=10, pady=4)
        self.e_acilis.ent.bind("<FocusOut>", lambda _e: self._format_acilis())
        self.e_acilis.ent.bind("<Return>", self._acilis_return)

        ttk.Label(right, text="Notlar:").pack(anchor="w", padx=10, pady=(8, 0))
        self.e_not = tk.Text(right, width=28, height=6)
        self.e_not.pack(padx=10, pady=4)

        rbtn = ttk.Frame(right)
        rbtn.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(rbtn, text="Yeni", command=self.clear_form).pack(side=tk.LEFT)
        ttk.Button(rbtn, text="Kaydet", command=self.save).pack(side=tk.LEFT, padx=6)

        self._apply_permissions()
        self.clear_form()
        self.refresh()

    def _apply_permissions(self):
        state = ("normal" if self.app.is_admin else "disabled")
        self.btn_del.config(state=state)
        self.btn_edit.config(state=state)

    def refresh(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        q = self.q.get()
        only_active = bool(self.only_active.get())
        for r in self.app.db.cari_list(q, only_active=only_active):
            aktif = int(r["aktif"] or 0)
            durum = "Aktif" if aktif == 1 else "Aktif değil"
            tags = ("inactive",) if aktif == 0 else ()
            self.tree.insert(
                "",
                tk.END,
                values=(
                    r["id"],
                    durum,
                    r["ad"],
                    r.get("tur", "") if hasattr(r, "get") else r["tur"],
                    r.get("telefon", "") if hasattr(r, "get") else r["telefon"],
                    fmt_amount(r["acilis_bakiye"]),
                ),
                tags=tags,
            )

        self.selected_id = None

        # bağlı ekranlar (cari seçim listeleri)
        try:
            kf = self.app.frames.get("kasa")
            if kf:
                kf.reload_cari_combo()
        except Exception:
            pass
        try:
            chf = self.app.frames.get("cari_hareket")
            if chf:
                chf.reload_cari()
        except Exception:
            pass
        try:
            chf2 = self.app.frames.get("cari_hareketler")
            if chf2 and hasattr(chf2, "reload_cari"):
                chf2.reload_cari()
        except Exception:
            pass

    def clear_form(self):
        self.selected_id = None
        self.e_ad.set("")
        self.e_tur.set("")
        self.e_tel.set("")
        self.e_durum.set("Aktif")
        self.e_acilis.set(fmt_amount(0))
        self.e_not.delete("1.0", tk.END)

    def _format_acilis(self):
        s = (self.e_acilis.get() or "").strip()
        if not s:
            return
        val = parse_number_smart(s)
        self.e_acilis.set(fmt_amount(val))

    def _acilis_return(self, _e):
        self._format_acilis()
        return "break"

    def on_select(self, _evt=None):
        sel = self.tree.selection()
        if not sel:
            return
        self.selected_id = int(self.tree.item(sel[0], "values")[0])
        r = self.app.db.cari_get(self.selected_id)
        if not r:
            return
        self.e_ad.set(r["ad"])
        self.e_tur.set(r["tur"])
        self.e_tel.set(r["telefon"])
        self.e_acilis.set(fmt_amount(r["acilis_bakiye"]))
        self.e_durum.set("Aktif" if int(r["aktif"] or 0) == 1 else "Aktif değil")
        self.e_not.delete("1.0", tk.END)
        self.e_not.insert("1.0", r["notlar"] or "")

    def save(self):
        ad = (self.e_ad.get() or "").strip()
        if not ad:
            messagebox.showwarning(APP_TITLE, "Cari adı boş olamaz.")
            return
        tur = (self.e_tur.get() or "").strip()
        tel = (self.e_tel.get() or "").strip()
        acilis = safe_float(self.e_acilis.get())
        notlar = self.e_not.get("1.0", tk.END).strip()
        aktif = 1 if (self.e_durum.get() or "Aktif") == "Aktif" else 0

        try:
            if self.selected_id:
                if not self.app.is_admin:
                    messagebox.showwarning(APP_TITLE, "Cari güncellemek için admin yetkisi gerekiyor.")
                    return
                self.app.db.conn.execute(
                    "UPDATE cariler SET ad=?, tur=?, telefon=?, notlar=?, acilis_bakiye=?, aktif=? WHERE id=?",
                    (ad, tur, tel, notlar, float(acilis), int(aktif), int(self.selected_id)),
                )
                self.app.db.conn.commit()
                self.app.db.log("Cari Güncelle", ad)
            else:
                self.app.db.cari_upsert(ad, tur, tel, notlar, acilis, aktif=aktif)
                self.app.db.log("Cari Ekle", ad)
            self.refresh()
            self.clear_form()
        except sqlite3.IntegrityError:
            messagebox.showerror(APP_TITLE, "Bu cari adı zaten var.")
        except Exception as e:
            messagebox.showerror(APP_TITLE, str(e))

    def edit_selected(self):
        if not self.app.is_admin:
            messagebox.showwarning(APP_TITLE, "Düzenleme için admin yetkisi gerekiyor.")
            return
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo(APP_TITLE, "Düzenlemek için bir cari seç.")
            return
        self.on_select()
        try:
            self.e_ad.ent.focus_set()
            self.e_ad.ent.selection_range(0, tk.END)
        except Exception:
            pass

    def open_ekstre(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning(APP_TITLE, "Önce bir cari seçmelisin.")
            return
        cid = int(self.tree.item(sel[0], "values")[0])
        CariEkstreWindow(self.app, cid)

    def delete(self):
        if not self.app.is_admin:
            return
        sel = self.tree.selection()
        if not sel:
            return
        vid = int(self.tree.item(sel[0], "values")[0])
        r = self.app.db.cari_get(vid)
        if not r:
            return
        if messagebox.askyesno(APP_TITLE, f"Cari silinsin mi?\n\n{r['ad']}"):
            try:
                self.app.db.cari_delete(vid)
                self.refresh()
            except Exception as e:
                messagebox.showerror(APP_TITLE, str(e))
