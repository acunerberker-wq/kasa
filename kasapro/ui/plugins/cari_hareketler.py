# -*- coding: utf-8 -*-
"""UI Plugin: Cari Hareketler (Liste / Filtre).

Bu ekran, cari hareketleri listeleme/filtreleme ve admin için silme/düzenleme
işlemlerini sağlar. Kayıt ekleme/düzenleme formu ayrı eklentiye ayrılmıştır.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import List, Optional, TYPE_CHECKING

import tkinter as tk
from tkinter import ttk, messagebox

from ...config import APP_TITLE
from ...utils import fmt_tr_date, fmt_amount
from ..widgets import LabeledEntry, LabeledCombo

if TYPE_CHECKING:
    from ...app import App

PLUGIN_META = {
    "key": "cari_hareketler",
    "nav_text": "📒 Cari Hareketler",
    "page_title": "Cari Hareketler",
    "order": 34,
}


class CariHareketlerFrame(ttk.Frame):
    def __init__(self, master, app: "App"):
        super().__init__(master)
        self.app = app
        self.multi_mode = tk.BooleanVar(value=False)
        self._build()

    def _build(self):
        mid = ttk.LabelFrame(self, text="Liste / Filtre")
        mid.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        f = ttk.Frame(mid)
        f.pack(fill=tk.X, pady=4)
        self.btn_multi = ttk.Button(f, text="Çoklu Seçim: Kapalı", command=self.toggle_multi)
        self.btn_multi.pack(side=tk.LEFT, padx=6)
        self.f_cari = LabeledCombo(f, "Cari:", ["(Tümü)"], 26)
        self.f_cari.pack(side=tk.LEFT, padx=6)
        self.f_q = LabeledEntry(f, "Ara:", 20)
        self.f_q.pack(side=tk.LEFT, padx=6)
        self.f_from = LabeledEntry(f, "Başlangıç:", 12)
        self.f_from.pack(side=tk.LEFT, padx=6)
        self.f_to = LabeledEntry(f, "Bitiş:", 12)
        self.f_to.pack(side=tk.LEFT, padx=6)
        ttk.Button(f, text="Son 30 gün", command=self.last30).pack(side=tk.LEFT, padx=6)
        ttk.Button(f, text="Yenile", command=self.refresh).pack(side=tk.LEFT, padx=6)

        cols = ("id", "tarih", "cari", "tip", "tutar", "para", "odeme", "belge", "etiket", "aciklama")
        self.tree = ttk.Treeview(mid, columns=cols, show="headings", height=16, selectmode="browse")
        for c in cols:
            self.tree.heading(c, text=c.upper())
        self.tree.column("id", width=50, anchor="center")
        self.tree.column("tarih", width=90)
        self.tree.column("cari", width=220)
        self.tree.column("tip", width=70)
        self.tree.column("tutar", width=100, anchor="e")
        self.tree.column("para", width=55, anchor="center")
        self.tree.column("odeme", width=120)
        self.tree.column("belge", width=95)
        self.tree.column("etiket", width=95)
        self.tree.column("aciklama", width=360)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        self.tree.bind("<Button-1>", self._on_tree_click)
        self.tree.bind("<Double-1>", lambda _e: self.edit_selected())

        btm = ttk.Frame(mid)
        btm.pack(fill=tk.X, pady=(0, 6))
        self.btn_edit = ttk.Button(btm, text="Seçili Kaydı Düzenle", command=self.edit_selected)
        self.btn_edit.pack(side=tk.LEFT, padx=6)
        self.btn_del = ttk.Button(btm, text="Seçili Kaydı Sil", command=self.delete_selected)
        self.btn_del.pack(side=tk.LEFT, padx=6)

        self.reload_cari()
        self.refresh()
        self._apply_permissions()

    def _apply_permissions(self):
        state = ("normal" if self.app.is_admin else "disabled")
        try:
            self.btn_del.config(state=state)
            self.btn_edit.config(state=state)
        except Exception:
            pass

    def reload_cari(self):
        values = [f"{r['id']} - {r['ad']}" for r in self.app.db.cari_list(only_active=True)]
        try:
            self.f_cari.cmb["values"] = ["(Tümü)"] + values
        except Exception:
            pass
        try:
            if self.f_cari.get() in ("", None):
                self.f_cari.set("(Tümü)")
        except Exception:
            pass
        if self.f_cari.get() not in ("(Tümü)",) and self.f_cari.get() not in ("", None):
            return
        self.f_cari.set("(Tümü)")

    def _selected_cari_id(self, combo_value: str) -> Optional[int]:
        if not combo_value or combo_value == "(Tümü)":
            return None
        if " - " in combo_value:
            try:
                return int(combo_value.split(" - ", 1)[0])
            except Exception:
                return None
        return None

    def reload_settings(self):
        # bu ekranda sadece cari listesi var
        try:
            self.reload_cari()
        except Exception:
            pass

    def refresh(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        cid = self._selected_cari_id(self.f_cari.get())
        rows = self.app.db.cari_hareket_list(
            cari_id=cid,
            q=self.f_q.get(),
            date_from=self.f_from.get(),
            date_to=self.f_to.get(),
        )
        for r in rows:
            self.tree.insert("", tk.END, values=(
                r["id"],
                fmt_tr_date(r["tarih"]),
                r["cari_ad"],
                r["tip"],
                f"{fmt_amount(r['tutar'])}",
                r["para"],
                r["odeme"],
                r["belge"],
                r["etiket"],
                r["aciklama"],
            ))

    def last30(self):
        d_to = date.today()
        d_from = d_to - timedelta(days=30)
        self.f_from.set(d_from.strftime("%d.%m.%Y"))
        self.f_to.set(d_to.strftime("%d.%m.%Y"))
        self.refresh()

    def toggle_multi(self):
        on = not self.multi_mode.get()
        self.multi_mode.set(on)
        try:
            self.btn_multi.config(text=("Çoklu Seçim: Açık" if on else "Çoklu Seçim: Kapalı"))
        except Exception:
            pass
        try:
            self.tree.configure(selectmode=("extended" if on else "browse"))
        except Exception:
            pass

        if not on:
            try:
                sel = self.tree.selection()
                if len(sel) > 1:
                    self.tree.selection_set(sel[0])
            except Exception:
                pass

    def _on_tree_click(self, event):
        """Çoklu seçim açıkken Ctrl gerektirmeden tıklayarak seçim ekle/çıkar."""
        try:
            if not self.multi_mode.get():
                return
            iid = self.tree.identify_row(event.y)
            if not iid:
                return
            if iid in self.tree.selection():
                self.tree.selection_remove(iid)
            else:
                self.tree.selection_add(iid)
            return "break"
        except Exception:
            return

    def edit_selected(self):
        if not self.app.is_admin:
            messagebox.showwarning(APP_TITLE, "Düzenleme için admin yetkisi gerekiyor.")
            return
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo(APP_TITLE, "Düzenlemek için bir kayıt seç.")
            return
        if len(sel) > 1:
            messagebox.showinfo(APP_TITLE, "Düzenleme için tek kayıt seç.")
            return
        try:
            hid = int(self.tree.item(sel[0], "values")[0])
        except Exception:
            messagebox.showwarning(APP_TITLE, "Kayıt seçimi okunamadı.")
            return

        # Düzenleme ekranına geç ve kaydı yükle
        try:
            self.app.show("cari_hareket_ekle")
        except Exception:
            pass
        try:
            fr = self.app.frames.get("cari_hareket_ekle")
            if fr is not None and hasattr(fr, "load_for_edit"):
                fr.load_for_edit(hid)  # type: ignore
        except Exception:
            pass

    def delete_selected(self):
        if not self.app.is_admin:
            return
        sel = list(self.tree.selection())
        if not sel:
            return

        ids: List[int] = []
        for it in sel:
            try:
                ids.append(int(self.tree.item(it, "values")[0]))
            except Exception:
                pass
        if not ids:
            return

        if len(ids) == 1:
            msg = f"Cari hareket silinsin mi? (id={ids[0]})"
        else:
            preview = ", ".join(str(x) for x in ids[:8])
            if len(ids) > 8:
                preview += "..."
            msg = f"Seçili {len(ids)} cari hareket silinsin mi? (id: {preview})"

        if not messagebox.askyesno(APP_TITLE, msg):
            return

        for vid in ids:
            try:
                self.app.db.cari_hareket_delete(int(vid))
            except Exception:
                pass

        self.refresh()


def build(master, app):
    return CariHareketlerFrame(master, app)
