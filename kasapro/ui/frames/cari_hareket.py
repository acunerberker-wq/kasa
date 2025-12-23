# -*- coding: utf-8 -*-
"""KasaPro v3 - Ana ekran frame'leri"""

from __future__ import annotations

import os
import re
from datetime import datetime, timedelta
from typing import Any, Optional, List, Dict, Tuple

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog

from ...config import APP_TITLE, HAS_OPENPYXL, HAS_REPORTLAB
from ...utils import (
    center_window,
    today_iso,
    now_iso,
    fmt_tr_date,
    parse_date_smart,
    parse_number_smart,
    safe_float,
    fmt_amount,
)
from ..widgets import SimpleField, LabeledEntry, LabeledCombo, MoneyEntry
from ..windows import ImportWizard, CariEkstreWindow

class CariHareketFrame(ttk.Frame):
    def __init__(self, master, app:"App"):
        super().__init__(master)
        self.app = app
        self.edit_id: Optional[int] = None
        self._aciklama_win = None
        self._aciklama_txt = None
        self.multi_mode = tk.BooleanVar(value=False)
        self._build()

    def _build(self):
        top = ttk.LabelFrame(self, text="Cari Hareket Ekle")
        top.pack(fill=tk.X, padx=10, pady=10)

        r1 = ttk.Frame(top); r1.pack(fill=tk.X, pady=4)
        self.in_tarih = LabeledEntry(r1, "Tarih:", 14); self.in_tarih.pack(side=tk.LEFT, padx=6)
        ttk.Button(r1, text="Bugün", command=lambda: self.in_tarih.set(fmt_tr_date(today_iso()))).pack(side=tk.LEFT, padx=6)

        self.in_cari = LabeledCombo(r1, "Cari:", ["Seç"], 26); self.in_cari.pack(side=tk.LEFT, padx=6)
        self.in_tip = LabeledCombo(r1, "Tip:", ["Borç", "Alacak"], 10); self.in_tip.pack(side=tk.LEFT, padx=6)
        self.in_tip.set("Borç")

        self.in_tutar = MoneyEntry(r1, "Tutar:"); self.in_tutar.pack(side=tk.LEFT, padx=6)
        self.in_para = LabeledCombo(r1, "Para:", self.app.db.list_currencies(), 8); self.in_para.pack(side=tk.LEFT, padx=6)
        self.in_para.set("TL")

        r2 = ttk.Frame(top); r2.pack(fill=tk.X, pady=4)
        self.in_odeme = LabeledCombo(r2, "Ödeme:", self.app.db.list_payments(), 14); self.in_odeme.pack(side=tk.LEFT, padx=6)
        self.in_belge = LabeledEntry(r2, "Belge:", 14); self.in_belge.pack(side=tk.LEFT, padx=6)
        self.in_etiket = LabeledEntry(r2, "Etiket:", 14); self.in_etiket.pack(side=tk.LEFT, padx=6)
        # Açıklama: buton + sekmeli editör
        self.in_aciklama = SimpleField("")
        desc_box = ttk.Frame(r2)
        ttk.Label(desc_box, text="Açıklama:").pack(side=tk.LEFT, padx=(0,6))
        self.btn_aciklama = ttk.Button(desc_box, text="Açıklama yaz…", command=self._open_aciklama_editor)
        self.btn_aciklama.pack(side=tk.LEFT, fill=tk.X, expand=True)
        desc_box.pack(side=tk.LEFT, padx=6, fill=tk.X, expand=True)
        self.btn_save = ttk.Button(r2, text="Kaydet", command=self.save)
        self.btn_save.pack(side=tk.LEFT, padx=10)
        self.btn_new = ttk.Button(r2, text="Yeni", command=self.clear_form)
        self.btn_new.pack(side=tk.LEFT, padx=6)
        self.lbl_mode = ttk.Label(r2, text="", foreground="#666")
        self.lbl_mode.pack(side=tk.LEFT, padx=10)

        mid = ttk.LabelFrame(self, text="Liste / Filtre")
        mid.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,10))

        f = ttk.Frame(mid); f.pack(fill=tk.X, pady=4)
        self.btn_multi = ttk.Button(f, text="Çoklu Seçim: Kapalı", command=self.toggle_multi)
        self.btn_multi.pack(side=tk.LEFT, padx=6)
        self.f_cari = LabeledCombo(f, "Cari:", ["(Tümü)"], 26); self.f_cari.pack(side=tk.LEFT, padx=6)
        self.f_q = LabeledEntry(f, "Ara:", 20); self.f_q.pack(side=tk.LEFT, padx=6)
        self.f_from = LabeledEntry(f, "Başlangıç:", 12); self.f_from.pack(side=tk.LEFT, padx=6)
        self.f_to = LabeledEntry(f, "Bitiş:", 12); self.f_to.pack(side=tk.LEFT, padx=6)
        ttk.Button(f, text="Son 30 gün", command=self.last30).pack(side=tk.LEFT, padx=6)
        ttk.Button(f, text="Yenile", command=self.refresh).pack(side=tk.LEFT, padx=6)

        cols = ("id","tarih","cari","tip","tutar","para","odeme","belge","etiket","aciklama")
        self.tree = ttk.Treeview(mid, columns=cols, show="headings", height=14, selectmode="browse")
        for c in cols:
            self.tree.heading(c, text=c.upper())
        self.tree.column("id", width=50, anchor="center")
        self.tree.column("tarih", width=90)
        self.tree.column("cari", width=200)
        self.tree.column("tip", width=70)
        self.tree.column("tutar", width=90, anchor="e")
        self.tree.column("para", width=55, anchor="center")
        self.tree.column("odeme", width=110)
        self.tree.column("belge", width=90)
        self.tree.column("etiket", width=90)
        self.tree.column("aciklama", width=320)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        self.tree.bind("<Button-1>", self._on_tree_click)
        self.tree.bind("<Double-1>", lambda _e: self.edit_selected())

        btm = ttk.Frame(mid); btm.pack(fill=tk.X, pady=(0,6))
        self.btn_edit = ttk.Button(btm, text="Seçili Kaydı Düzenle", command=self.edit_selected)
        self.btn_edit.pack(side=tk.LEFT, padx=6)
        self.btn_del = ttk.Button(btm, text="Seçili Kaydı Sil", command=self.delete_selected)
        self.btn_del.pack(side=tk.LEFT, padx=6)

        self.reload_cari()
        self.refresh()
        self._apply_permissions()

    def _apply_permissions(self):
        state = ("normal" if self.app.is_admin else "disabled")
        self.btn_del.config(state=state)
        self.btn_edit.config(state=state)

    def reload_cari(self):
        values = [f"{r['id']} - {r['ad']}" for r in self.app.db.cari_list(only_active=True)]
        self.in_cari.cmb["values"] = ["Seç"] + values
        self.in_cari.set("Seç")
        self.f_cari.cmb["values"] = ["(Tümü)"] + values
        self.f_cari.set("(Tümü)")

    def _selected_cari_id(self, combo_value: str) -> Optional[int]:
        if not combo_value or combo_value in ("Seç", "(Tümü)"):
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
        if not hasattr(self, "btn_aciklama"):
            return
        val = (self.in_aciklama.get() or "").strip()
        if val:
            self.btn_aciklama.config(text="Açıklama (dolu)")
        else:
            self.btn_aciklama.config(text="Açıklama yaz…")

    def _clear_aciklama_editor(self):
        try:
            txt = getattr(self, "_aciklama_txt", None)
            if txt is not None:
                txt.delete("1.0", "end")
        except Exception:
            pass

    def _open_aciklama_editor(self):
        # Sekmeli açıklama editörü (Notebook)
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

        def apply(close=False):
            val = txt.get("1.0", "end").rstrip("\n")
            self.in_aciklama.set(val)
            self._sync_aciklama_button()
            if close:
                on_close()

        ttk.Button(btns, text="Uygula", command=lambda: apply(False)).pack(side=tk.RIGHT, padx=6)
        ttk.Button(btns, text="Uygula & Kapat", command=lambda: apply(True)).pack(side=tk.RIGHT, padx=6)
        ttk.Button(btns, text="Kapat", command=on_close).pack(side=tk.RIGHT, padx=6)

        # Pencereyi ekranın ortasında aç
        center_window(win, root)

        win.protocol("WM_DELETE_WINDOW", on_close)
        win.bind("<Escape>", lambda _e: on_close())

    def clear_form(self):
        self.edit_id = None
        if hasattr(self, "btn_save"):
            self.btn_save.config(text="Kaydet")
        if hasattr(self, "lbl_mode"):
            self.lbl_mode.config(text="")

        self.in_tarih.set(fmt_tr_date(today_iso()))
        self.in_cari.set("Seç")
        self.in_tip.set("Borç")
        self.in_tutar.set("")
        self.in_para.set("TL")

        try:
            vals_od = list(self.in_odeme.cmb["values"])
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
    def edit_selected(self):
        if not self.app.is_admin:
            messagebox.showwarning(APP_TITLE, "Düzenleme için admin yetkisi gerekiyor.")
            return
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo(APP_TITLE, "Düzenlemek için bir kayıt seç.")
            return
        if len(sel) > 1:
            messagebox.showinfo(APP_TITLE, "Düzenleme için tek kayıt seç. (Çoklu seçim açıkken birden fazla kayıt seçili.)")
            return
        try:
            hid = int(self.tree.item(sel[0], "values")[0])
        except Exception:
            messagebox.showwarning(APP_TITLE, "Kayıt seçimi okunamadı.")
            return
        row = self.app.db.cari_hareket_get(hid)
        if not row:
            messagebox.showwarning(APP_TITLE, "Kayıt bulunamadı.")
            return

        self.edit_id = hid
        self.btn_save.config(text="Güncelle")
        self.lbl_mode.config(text=f"Düzenleme modu: id={hid}")

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

        belge = (self.in_belge.get() or '').strip()
        if not belge:
            belge = self.app.db.next_belge_no('C')
            self.in_belge.set(belge)

        # Güncelleme modu
        if self.edit_id is not None:
            if not self.app.is_admin:
                messagebox.showwarning(APP_TITLE, "Bu işlem için admin yetkisi gerekiyor.")
                return
            self.app.db.cari_hareket_update(
                self.edit_id,
                self.in_tarih.get(),
                cid,
                self.in_tip.get() or "Borç",
                tutar,
                self.in_para.get() or "TL",
                self.in_aciklama.get(),
                self.in_odeme.get(),
                belge,
                self.in_etiket.get()
            )
            self.app.db.log("UI", f"Cari hareket güncellendi (id={self.edit_id})")
            self.refresh()
            self.clear_form()
            return

        # Yeni kayıt
        self.app.db.cari_hareket_add(
            self.in_tarih.get(),
            cid,
            self.in_tip.get() or "Borç",
            tutar,
            self.in_para.get() or "TL",
            self.in_aciklama.get(),
            self.in_odeme.get(),
            belge,
            self.in_etiket.get()
        )
        self.app.db.log("UI", "Cari hareket eklendi")
        self.refresh()


        # Bir sonraki kayıt için açıklamayı temizle
        self.in_aciklama.set("")
        self._clear_aciklama_editor()
        self._sync_aciklama_button()
        # Bir sonraki kayıt için belge/tutar alanını temizle
        self.in_belge.set("")
        self.in_tutar.set("")

    def refresh(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        cid = self._selected_cari_id(self.f_cari.get())
        rows = self.app.db.cari_hareket_list(cari_id=cid, q=self.f_q.get(), date_from=self.f_from.get(), date_to=self.f_to.get())
        for r in rows:
            self.tree.insert("", tk.END, values=(
                r["id"], fmt_tr_date(r["tarih"]), r["cari_ad"], r["tip"], f"{fmt_amount(r['tutar'])}",
                r["para"], r["odeme"], r["belge"], r["etiket"], r["aciklama"]
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
            # browse: tek seçim, extended: çoklu seçim
            self.tree.configure(selectmode=("extended" if on else "browse"))
        except Exception:
            pass

        # Çoklu seçim kapatılınca tek kayda düş
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
                return  # normal davranış (tek seçim)
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
                self.app.db.cari_hareket_delete(vid)
            except Exception:
                pass
            if getattr(self, 'edit_id', None) == vid:
                self.clear_form()

        self.refresh()
