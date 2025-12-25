# -*- coding: utf-8 -*-
"""UI Plugin: Cari Hareket Ekle / Düzenle.

Bu ekran, sadece cari hareket kaydı ekleme (ve admin için düzenleme) işini yapar.
Listeleme/filtreleme ayrı bir eklentiye taşınmıştır.
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

import tkinter as tk
from tkinter import ttk, messagebox

from ...config import APP_TITLE
from ...utils import center_window, today_iso, fmt_tr_date, fmt_amount
from ..base import BaseView
from ..widgets import SimpleField, LabeledEntry, LabeledCombo, MoneyEntry

if TYPE_CHECKING:
    from ...app import App

PLUGIN_META = {
    "key": "cari_hareket_ekle",
    "nav_text": "➕ Cari Hareket Ekle",
    "page_title": "Cari Hareket Ekle",
    "order": 35,
}


class CariHareketEkleFrame(BaseView):
    def __init__(self, master, app: "App"):
        self.app = app
        super().__init__(master, app)
        self.edit_id: Optional[int] = None
        self._aciklama_win = None
        self._aciklama_txt = None
        self.in_aciklama = SimpleField("")
        self.build_ui()

    def build_ui(self) -> None:
        self._build()

    def _build(self):
        top = ttk.LabelFrame(self, text="Cari Hareket Ekle")
        top.pack(fill=tk.X, padx=10, pady=10)

        r1 = ttk.Frame(top)
        r1.pack(fill=tk.X, pady=4)
        self.in_tarih = LabeledEntry(r1, "Tarih:", 14)
        self.in_tarih.pack(side=tk.LEFT, padx=6)
        ttk.Button(r1, text="Bugün", command=lambda: self.in_tarih.set(fmt_tr_date(today_iso()))).pack(side=tk.LEFT, padx=6)

        self.in_cari = LabeledCombo(r1, "Cari:", ["Seç"], 26)
        self.in_cari.pack(side=tk.LEFT, padx=6)
        self.in_tip = LabeledCombo(r1, "Tip:", ["Borç", "Alacak"], 10)
        self.in_tip.pack(side=tk.LEFT, padx=6)
        self.in_tip.set("Borç")

        self.in_tutar = MoneyEntry(r1, "Tutar:")
        self.in_tutar.pack(side=tk.LEFT, padx=6)
        self.in_para = LabeledCombo(r1, "Para:", self.app.db.list_currencies(), 8)
        self.in_para.pack(side=tk.LEFT, padx=6)
        self.in_para.set("TL")

        r2 = ttk.Frame(top)
        r2.pack(fill=tk.X, pady=4)
        self.in_odeme = LabeledCombo(r2, "Ödeme:", self.app.db.list_payments(), 14)
        self.in_odeme.pack(side=tk.LEFT, padx=6)
        self.in_belge = LabeledEntry(r2, "Belge:", 14)
        self.in_belge.pack(side=tk.LEFT, padx=6)
        self.in_etiket = LabeledEntry(r2, "Etiket:", 14)
        self.in_etiket.pack(side=tk.LEFT, padx=6)

        # Açıklama: buton + sekmeli editör
        desc_box = ttk.Frame(r2)
        ttk.Label(desc_box, text="Açıklama:").pack(side=tk.LEFT, padx=(0, 6))
        self.btn_aciklama = ttk.Button(desc_box, text="Açıklama yaz…", command=self._open_aciklama_editor)
        self.btn_aciklama.pack(side=tk.LEFT, fill=tk.X, expand=True)
        desc_box.pack(side=tk.LEFT, padx=6, fill=tk.X, expand=True)

        self.btn_save = ttk.Button(r2, text="Kaydet", command=self.save)
        self.btn_save.pack(side=tk.LEFT, padx=10)
        self.btn_new = ttk.Button(r2, text="Yeni", command=self.clear_form)
        self.btn_new.pack(side=tk.LEFT, padx=6)
        self.lbl_mode = ttk.Label(r2, text="", foreground="#666")
        self.lbl_mode.pack(side=tk.LEFT, padx=10)

        # İlk değerler
        self.reload_cari()
        self.clear_form()

    def reload_cari(self):
        values = [f"{r['id']} - {r['ad']}" for r in self.app.db.cari_list(only_active=True)]
        try:
            self.in_cari.cmb["values"] = ["Seç"] + values
        except Exception:
            pass
        try:
            if self.in_cari.get() not in ("Seç", ""):
                return
        except Exception:
            pass
        self.in_cari.set("Seç")

    def reload_settings(self):
        """App.reload_settings çağırır."""
        try:
            self.in_para.cmb["values"] = self.app.db.list_currencies()
            self.in_odeme.cmb["values"] = self.app.db.list_payments()
        except Exception:
            pass

    def _selected_cari_id(self, combo_value: str) -> Optional[int]:
        if not combo_value or combo_value == "Seç":
            return None
        if " - " in combo_value:
            try:
                return int(combo_value.split(" - ", 1)[0])
            except Exception:
                return None
        return None

    def _ensure_combo_value(self, lc: "LabeledCombo", value: str):
        try:
            cmb = lc.cmb
        except Exception:
            return
        vals = list(cmb["values"]) if cmb["values"] else []
        if value and value not in vals:
            cmb["values"] = tuple(vals + [value])

    def _set_cari_by_id(self, cid: int):
        c = self.app.db.cari_get(int(cid))
        if not c:
            self.in_cari.set("Seç")
            return
        val = f"{c['id']} - {c['ad']}"
        try:
            cmb = self.in_cari.cmb
            vals = list(cmb["values"]) if cmb["values"] else []
            if val not in vals:
                cmb["values"] = tuple(vals + [val])
        except Exception:
            pass
        self.in_cari.set(val)

    def _sync_aciklama_button(self):
        val = (self.in_aciklama.get() or "").strip()
        try:
            self.btn_aciklama.config(text=("Açıklama (dolu)" if val else "Açıklama yaz…"))
        except Exception:
            pass

    def _clear_aciklama_editor(self):
        try:
            txt = getattr(self, "_aciklama_txt", None)
            if txt is not None:
                txt.delete("1.0", "end")
        except Exception:
            pass

    def _open_aciklama_editor(self):
        win = getattr(self, "_aciklama_win", None)
        try:
            if win is not None and win.winfo_exists():
                win.deiconify()
                win.lift()
                win.focus_force()
                return
        except Exception:
            pass

        root = self.winfo_toplevel()
        win = tk.Toplevel(root)
        self._aciklama_win = win
        win.title("Açıklama")
        win.geometry("560x360")
        try:
            win.transient(root)
        except Exception:
            pass

        nb = ttk.Notebook(win)
        nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        tab = ttk.Frame(nb)
        nb.add(tab, text="Açıklama")

        txt = tk.Text(tab, wrap="word", height=10)
        ysb = ttk.Scrollbar(tab, orient="vertical", command=txt.yview)
        txt.configure(yscrollcommand=ysb.set)
        txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ysb.pack(side=tk.RIGHT, fill=tk.Y)
        self._aciklama_txt = txt

        cur = (self.in_aciklama.get() or "")
        if cur:
            txt.insert("1.0", cur)

        btns = ttk.Frame(win)
        btns.pack(fill=tk.X, padx=10, pady=(0, 10))

        def on_close():
            try:
                self._aciklama_win = None
                self._aciklama_txt = None
            except Exception:
                pass
            try:
                win.destroy()
            except Exception:
                pass

        def apply(close: bool = False):
            val = txt.get("1.0", "end").rstrip("\n")
            self.in_aciklama.set(val)
            self._sync_aciklama_button()
            if close:
                on_close()

        ttk.Button(btns, text="Uygula", command=lambda: apply(False)).pack(side=tk.RIGHT, padx=6)
        ttk.Button(btns, text="Uygula & Kapat", command=lambda: apply(True)).pack(side=tk.RIGHT, padx=6)
        ttk.Button(btns, text="Kapat", command=on_close).pack(side=tk.RIGHT, padx=6)

        center_window(win, root)

        win.protocol("WM_DELETE_WINDOW", on_close)
        win.bind("<Escape>", lambda _e: on_close())

    def clear_form(self):
        self.edit_id = None
        try:
            self.btn_save.config(text="Kaydet")
        except Exception:
            pass
        try:
            self.lbl_mode.config(text="")
        except Exception:
            pass

        self.in_tarih.set(fmt_tr_date(today_iso()))
        self.in_cari.set("Seç")
        self.in_tip.set("Borç")
        self.in_tutar.set("")
        self.in_para.set("TL")

        # ödeme varsayılanı
        try:
            vals_od = list(self.in_odeme.cmb["values"]) or []
            if "Nakit" in vals_od:
                self.in_odeme.set("Nakit")
            elif vals_od:
                self.in_odeme.set(vals_od[0])
        except Exception:
            pass

        self.in_belge.set("")
        self.in_etiket.set("")
        self.in_aciklama.set("")
        self._clear_aciklama_editor()
        self._sync_aciklama_button()

    def load_for_edit(self, hareket_id: int):
        """Admin için: seçili kaydı bu ekranda düzenlemeye hazırlar."""
        row = self.app.db.cari_hareket_get(int(hareket_id))
        if not row:
            messagebox.showwarning(APP_TITLE, "Kayıt bulunamadı.")
            return

        self.edit_id = int(hareket_id)
        try:
            self.btn_save.config(text="Güncelle")
            self.lbl_mode.config(text=f"Düzenleme modu: id={self.edit_id}")
        except Exception:
            pass

        self.in_tarih.set(fmt_tr_date(row["tarih"]))
        self._set_cari_by_id(int(row["cari_id"]))
        self.in_tip.set(row["tip"] or "Borç")
        self.in_tutar.set(fmt_amount(row["tutar"]))

        self._ensure_combo_value(self.in_para, row["para"] or "")
        self.in_para.set(row["para"] or "TL")

        self._ensure_combo_value(self.in_odeme, row["odeme"] or "")
        self.in_odeme.set(row["odeme"] or "")

        self.in_belge.set(row["belge"] or "")
        self.in_etiket.set(row["etiket"] or "")
        self.in_aciklama.set(row["aciklama"] or "")
        self._sync_aciklama_button()

    def save(self):
        cid = self._selected_cari_id(self.in_cari.get())
        if not cid:
            messagebox.showwarning(APP_TITLE, "Cari seçmelisin.")
            return

        tutar = self.in_tutar.get_float()
        if tutar <= 0:
            messagebox.showwarning(APP_TITLE, "Tutar 0'dan büyük olmalı.")
            return

        belge = (self.in_belge.get() or "").strip()
        if not belge:
            try:
                belge = self.app.db.next_belge_no("C")
            except Exception:
                belge = ""
            self.in_belge.set(belge)

        # Güncelleme modu
        if self.edit_id is not None:
            if not self.app.is_admin:
                messagebox.showwarning(APP_TITLE, "Bu işlem için admin yetkisi gerekiyor.")
                return
            self.app.db.cari_hareket_update(
                int(self.edit_id),
                self.in_tarih.get(),
                int(cid),
                self.in_tip.get() or "Borç",
                float(tutar),
                self.in_para.get() or "TL",
                self.in_aciklama.get(),
                self.in_odeme.get(),
                belge,
                self.in_etiket.get(),
            )
            try:
                self.app.db.log("UI", f"Cari hareket güncellendi (id={self.edit_id})")
            except Exception:
                pass

            # Liste ekranını yenile
            try:
                if "cari_hareketler" in self.app.frames and hasattr(self.app.frames["cari_hareketler"], "refresh"):
                    self.app.frames["cari_hareketler"].refresh()  # type: ignore
            except Exception:
                pass

            self.clear_form()
            return

        # Yeni kayıt
        self.app.db.cari_hareket_add(
            self.in_tarih.get(),
            int(cid),
            self.in_tip.get() or "Borç",
            float(tutar),
            self.in_para.get() or "TL",
            self.in_aciklama.get(),
            self.in_odeme.get(),
            belge,
            self.in_etiket.get(),
        )
        try:
            self.app.db.log("UI", "Cari hareket eklendi")
        except Exception:
            pass

        # Liste ekranını yenile
        try:
            if "cari_hareketler" in self.app.frames and hasattr(self.app.frames["cari_hareketler"], "refresh"):
                self.app.frames["cari_hareketler"].refresh()  # type: ignore
        except Exception:
            pass

        # Bir sonraki kayıt için alanları temizle
        self.in_aciklama.set("")
        self._clear_aciklama_editor()
        self._sync_aciklama_button()
        self.in_belge.set("")
        self.in_tutar.set("")


def build(master, app):
    return CariHareketEkleFrame(master, app)
