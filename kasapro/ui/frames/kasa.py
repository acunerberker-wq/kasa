# -*- coding: utf-8 -*-
"""Kasa ekranı.

Bu ekran
kasa hareketi ekleme/düzenleme, geçmiş listeleme ve raporları tek yerde toplar.

Not: DB'de para birimi dönüşümü yapılmadığı için raporlar (gelir/gider/net)
tek para birimi varsayımıyla gösterilir. (Çok para birimi kullanıyorsanız,
aynı raporda farklı para birimleri karışabilir.)
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional, TYPE_CHECKING

import tkinter as tk
from tkinter import ttk, messagebox

from ...config import APP_TITLE
from ...utils import today_iso, fmt_tr_date, fmt_amount
from ..widgets import SimpleField, LabeledEntry, LabeledCombo, MoneyEntry

if TYPE_CHECKING:
    from ...app import App

class KasaFrame(ttk.Frame):
    def __init__(self, master, app: "App"):
        super().__init__(master)
        self.app = app

        self.edit_id: Optional[int] = None
        self._aciklama_win = None
        self._aciklama_txt = None

        self._build()

    # -----------------
    # UI
    # -----------------
    def _build(self):
        # Üst özet
        self.summary_bar = ttk.Frame(self)
        self.summary_bar.pack(fill=tk.X, padx=10, pady=(10, 6))

        self.lbl_month = ttk.Label(self.summary_bar, text="")
        self.lbl_month.pack(side=tk.LEFT, padx=(0, 12))
        self.lbl_all = ttk.Label(self.summary_bar, text="")
        self.lbl_all.pack(side=tk.LEFT)
        self.lbl_overdue = ttk.Label(self.summary_bar, text="Geciken Hatırlatmalar: 0")
        self.lbl_overdue.pack(side=tk.RIGHT, padx=(12, 0))

        # Sekmeler
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.tab_form = ttk.Frame(self.nb)
        self.tab_history = ttk.Frame(self.nb)
        self.tab_reports = ttk.Frame(self.nb)
        self.nb.add(self.tab_form, text="➕ İşlem Ekle")
        self.nb.add(self.tab_history, text="🗂️ Geçmiş")
        self.nb.add(self.tab_reports, text="📊 Raporlar")

        self._build_form(self.tab_form)
        self._build_history(self.tab_history)
        self._build_reports(self.tab_reports)

        self.reload_cari_combo()
        self.clear_form()
        self.refresh()
        self._apply_permissions()

    def _build_form(self, parent: ttk.Frame):
        top = ttk.LabelFrame(parent, text="Kasa Hareketi")
        top.pack(fill=tk.X, padx=6, pady=6)

        row1 = ttk.Frame(top)
        row1.pack(fill=tk.X, pady=4)
        self.in_tarih = LabeledEntry(row1, "Tarih:", 16)
        self.in_tarih.pack(side=tk.LEFT, padx=6)
        ttk.Button(row1, text="Bugün", command=lambda: self.in_tarih.set(fmt_tr_date(today_iso()))).pack(
            side=tk.LEFT, padx=6
        )

        self.in_tip = LabeledCombo(row1, "Tip:", ["Gelir", "Gider"], 10)
        self.in_tip.pack(side=tk.LEFT, padx=6)

        self.in_tutar = MoneyEntry(row1, "Tutar:")
        self.in_tutar.pack(side=tk.LEFT, padx=6)

        self.in_para = LabeledCombo(row1, "Para:", self.app.db.list_currencies(), 8)
        self.in_para.pack(side=tk.LEFT, padx=6)
        self.in_para.set("TL")

        row2 = ttk.Frame(top)
        row2.pack(fill=tk.X, pady=4)
        self.in_odeme = LabeledCombo(row2, "Ödeme:", self.app.db.list_payments(), 14)
        self.in_odeme.pack(side=tk.LEFT, padx=6)
        try:
            self.in_odeme.set("Nakit")
        except Exception:
            pass

        self.in_kategori = LabeledCombo(row2, "Kategori:", self.app.db.list_categories(), 16)
        self.in_kategori.pack(side=tk.LEFT, padx=6)
        try:
            self.in_kategori.set("Diğer")
        except Exception:
            pass

        self.in_cari = LabeledCombo(row2, "Cari (ops):", ["(Yok)"], 22)
        self.in_cari.pack(side=tk.LEFT, padx=6)

        # Açıklama (buton -> editor)
        self.in_aciklama = SimpleField("")
        desc_box = ttk.Frame(row2)
        ttk.Label(desc_box, text="Açıklama:").pack(side=tk.LEFT, padx=(0, 6))
        self.btn_aciklama = ttk.Button(desc_box, text="Açıklama yaz…", command=self._open_aciklama_editor)
        self.btn_aciklama.pack(side=tk.LEFT, fill=tk.X, expand=True)
        desc_box.pack(side=tk.LEFT, padx=6, fill=tk.X, expand=True)

        row3 = ttk.Frame(top)
        row3.pack(fill=tk.X, pady=4)
        self.in_belge = LabeledEntry(row3, "Belge No:", 16)
        self.in_belge.pack(side=tk.LEFT, padx=6)
        self.in_etiket = LabeledEntry(row3, "Etiket:", 16)
        self.in_etiket.pack(side=tk.LEFT, padx=6)

        self.btn_save = ttk.Button(row3, text="Kaydet", command=self.save)
        self.btn_save.pack(side=tk.LEFT, padx=10)
        self.btn_new = ttk.Button(row3, text="Yeni", command=self.clear_form)
        self.btn_new.pack(side=tk.LEFT, padx=6)
        self.lbl_mode = ttk.Label(row3, text="")
        self.lbl_mode.pack(side=tk.LEFT, padx=10)

    def _build_history(self, parent: ttk.Frame):
        mid = ttk.LabelFrame(parent, text="Kasa Geçmişi")
        mid.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        frow = ttk.Frame(mid)
        frow.pack(fill=tk.X, pady=4)

        self.f_q = LabeledEntry(frow, "Ara:", 22)
        self.f_q.pack(side=tk.LEFT, padx=6)

        self.f_tip = LabeledCombo(frow, "Tip:", ["(Tümü)", "Gelir", "Gider"], 10)
        self.f_tip.pack(side=tk.LEFT, padx=6)
        self.f_tip.set("(Tümü)")

        self.f_kat = LabeledCombo(frow, "Kategori:", ["(Tümü)"] + self.app.db.list_categories(), 14)
        self.f_kat.pack(side=tk.LEFT, padx=6)
        self.f_kat.set("(Tümü)")

        self.f_from = LabeledEntry(frow, "Başlangıç:", 12)
        self.f_from.pack(side=tk.LEFT, padx=6)
        self.f_to = LabeledEntry(frow, "Bitiş:", 12)
        self.f_to.pack(side=tk.LEFT, padx=6)

        ttk.Button(frow, text="Bu Ay", command=self.this_month).pack(side=tk.LEFT, padx=6)
        ttk.Button(frow, text="Son 30 gün", command=self.last30).pack(side=tk.LEFT, padx=6)
        ttk.Button(frow, text="Yenile", command=self.refresh).pack(side=tk.LEFT, padx=6)

        cols = ("id", "tarih", "tip", "tutar", "para", "odeme", "kategori", "cari", "aciklama", "belge", "etiket")
        self.tree = ttk.Treeview(mid, columns=cols, show="headings", height=14, selectmode="browse")
        for c in cols:
            self.tree.heading(c, text=c.upper())

        self.tree.column("id", width=55, anchor="center")
        self.tree.column("tarih", width=95)
        self.tree.column("tip", width=70, anchor="center")
        self.tree.column("tutar", width=100, anchor="e")
        self.tree.column("para", width=55, anchor="center")
        self.tree.column("odeme", width=105)
        self.tree.column("kategori", width=120)
        self.tree.column("cari", width=160)
        self.tree.column("aciklama", width=300)
        self.tree.column("belge", width=90)
        self.tree.column("etiket", width=90)

        self.tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.tree.bind("<Double-1>", lambda _e: self.edit_selected())

        btm = ttk.Frame(mid)
        btm.pack(fill=tk.X, pady=(0, 6))

        self.btn_edit = ttk.Button(btm, text="Seçili Kaydı Düzenle", command=self.edit_selected)
        self.btn_edit.pack(side=tk.LEFT, padx=6)
        self.btn_del = ttk.Button(btm, text="Seçili Kaydı Sil", command=self.delete_selected)
        self.btn_del.pack(side=tk.LEFT, padx=6)

        self.lbl_sum = ttk.Label(btm, text="")
        self.lbl_sum.pack(side=tk.RIGHT, padx=10)

    def _build_reports(self, parent: ttk.Frame):
        top = ttk.Frame(parent)
        top.pack(fill=tk.X, padx=6, pady=6)

        # Bu ay / genel kartları
        self.grp_month = ttk.LabelFrame(top, text="Bu Ay")
        self.grp_month.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.lbl_rep_month = ttk.Label(self.grp_month, text="")
        self.lbl_rep_month.pack(anchor="w", padx=10, pady=10)

        self.grp_all = ttk.LabelFrame(top, text="Genel")
        self.grp_all.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))
        self.lbl_rep_all = ttk.Label(self.grp_all, text="")
        self.lbl_rep_all.pack(anchor="w", padx=10, pady=10)

        body = ttk.Frame(parent)
        body.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

        left = ttk.LabelFrame(body, text="Aylık Özet (Son 24 Ay)")
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        cols = ("ay", "gelir", "gider", "net")
        self.tree_monthly = ttk.Treeview(left, columns=cols, show="headings", height=12, selectmode="browse")
        for c in cols:
            self.tree_monthly.heading(c, text=c.upper())
        self.tree_monthly.column("ay", width=90, anchor="center")
        self.tree_monthly.column("gelir", width=120, anchor="e")
        self.tree_monthly.column("gider", width=120, anchor="e")
        self.tree_monthly.column("net", width=120, anchor="e")
        self.tree_monthly.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.tree_monthly.bind("<Double-1>", lambda _e: self._jump_month_from_report())

        right = ttk.LabelFrame(body, text="Gider Kategorileri (Bu Ay)")
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))

        self.txt_kat = tk.Text(right, height=12)
        self.txt_kat.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

    # -----------------
    # Helpers
    # -----------------
    def _apply_permissions(self):
        state = ("normal" if self.app.is_admin else "disabled")
        try:
            self.btn_del.config(state=state)
            self.btn_edit.config(state=state)
        except Exception:
            pass

    def reload_settings(self):
        """App.reload_settings çağırıyor."""
        try:
            self.in_para.cmb["values"] = self.app.db.list_currencies()
            self.in_odeme.cmb["values"] = self.app.db.list_payments()
            self.in_kategori.cmb["values"] = self.app.db.list_categories()
            self.f_kat.cmb["values"] = ["(Tümü)"] + self.app.db.list_categories()
        except Exception:
            pass

    def reload_cari_combo(self):
        values = ["(Yok)"]
        try:
            for r in self.app.db.cari_list(only_active=True):
                values.append(f"{r['id']} - {r['ad']}")
        except Exception:
            pass
        try:
            self.in_cari.cmb["values"] = values
            if self.in_cari.get() not in values:
                self.in_cari.set("(Yok)")
        except Exception:
            pass

    def _sync_aciklama_button(self):
        try:
            val = (self.in_aciklama.get() or "").strip()
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

        def apply(close=False):
            val = txt.get("1.0", "end").rstrip("\n")
            self.in_aciklama.set(val)
            self._sync_aciklama_button()
            if close:
                on_close()

        ttk.Button(btns, text="Uygula", command=lambda: apply(False)).pack(side=tk.RIGHT, padx=6)
        ttk.Button(btns, text="Uygula & Kapat", command=lambda: apply(True)).pack(side=tk.RIGHT, padx=6)
        ttk.Button(btns, text="Kapat", command=on_close).pack(side=tk.RIGHT, padx=6)

        win.protocol("WM_DELETE_WINDOW", on_close)
        win.bind("<Escape>", lambda _e: on_close())

    # -----------------
    # Form actions
    # -----------------
    def clear_form(self):
        self.edit_id = None
        try:
            self.btn_save.config(text="Kaydet")
            self.lbl_mode.config(text="")
        except Exception:
            pass

        self.in_tarih.set(fmt_tr_date(today_iso()))
        self.in_tip.set("Gelir")
        self.in_tutar.set("")
        self.in_para.set("TL")

        # Varsayılanlar
        try:
            vals_od = list(self.in_odeme.cmb["values"]) or []
            self.in_odeme.set("Nakit" if "Nakit" in vals_od else (vals_od[0] if vals_od else ""))
        except Exception:
            pass
        try:
            vals_k = list(self.in_kategori.cmb["values"]) or []
            self.in_kategori.set("Diğer" if "Diğer" in vals_k else (vals_k[0] if vals_k else ""))
        except Exception:
            pass

        self.in_cari.set("(Yok)")
        self.in_belge.set("")
        self.in_etiket.set("")
        self.in_aciklama.set("")
        self._clear_aciklama_editor()
        self._sync_aciklama_button()

    def save(self):
        tutar = self.in_tutar.get_float()
        if tutar <= 0:
            messagebox.showwarning(APP_TITLE, "Tutar 0'dan büyük olmalı.")
            return

        tip = (self.in_tip.get() or "").strip() or "Gelir"
        if tip not in ("Gelir", "Gider"):
            messagebox.showwarning(APP_TITLE, "Tip 'Gelir' veya 'Gider' olmalı.")
            return

        cari_id = None
        sel = (self.in_cari.get() or "").strip()
        if sel and sel != "(Yok)" and " - " in sel:
            try:
                cari_id = int(sel.split(" - ", 1)[0])
            except Exception:
                cari_id = None

        belge = (self.in_belge.get() or "").strip()
        if not belge:
            # Kasa için prefix: K
            try:
                belge = self.app.db.next_belge_no("K")
                self.in_belge.set(belge)
            except Exception:
                belge = ""

        if self.edit_id is not None:
            if not self.app.is_admin:
                messagebox.showwarning(APP_TITLE, "Bu işlem için admin yetkisi gerekiyor.")
                return
            self.app.db.kasa_update(
                self.edit_id,
                self.in_tarih.get(),
                tip,
                tutar,
                self.in_para.get() or "TL",
                self.in_odeme.get(),
                self.in_kategori.get(),
                cari_id,
                self.in_aciklama.get(),
                belge,
                self.in_etiket.get(),
            )
            try:
                self.app.db.log("UI", f"Kasa kaydı güncellendi (id={self.edit_id})")
            except Exception:
                pass
            self.edit_id = None
            self.clear_form()
            self.refresh()
            return

        self.app.db.kasa_add(
            self.in_tarih.get(),
            tip,
            tutar,
            self.in_para.get() or "TL",
            self.in_odeme.get(),
            self.in_kategori.get(),
            cari_id,
            self.in_aciklama.get(),
            belge,
            self.in_etiket.get(),
        )
        try:
            self.app.db.log("UI", "Kasa kaydı eklendi")
        except Exception:
            pass

        # Sonraki giriş için bazı alanları boşalt
        self.in_tutar.set("")
        self.in_belge.set("")
        self.in_aciklama.set("")
        self._clear_aciklama_editor()
        self._sync_aciklama_button()

        self.refresh()
        # Geçmiş sekmesini de gösterelim (kayıt eklendiği görülsün)
        try:
            self.nb.select(self.tab_history)
        except Exception:
            pass

    # -----------------
    # History actions
    # -----------------
    def edit_selected(self):
        if not self.app.is_admin:
            messagebox.showwarning(APP_TITLE, "Düzenleme için admin yetkisi gerekiyor.")
            return
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo(APP_TITLE, "Düzenlemek için bir kayıt seç.")
            return
        try:
            kid = int(self.tree.item(sel[0], "values")[0])
        except Exception:
            messagebox.showwarning(APP_TITLE, "Kayıt seçimi okunamadı.")
            return

        row = self.app.db.kasa_get(kid)
        if not row:
            messagebox.showwarning(APP_TITLE, "Kayıt bulunamadı.")
            return

        self.edit_id = int(row["id"])
        try:
            self.btn_save.config(text="Güncelle")
            self.lbl_mode.config(text=f"Düzenleme modu: id={self.edit_id}")
        except Exception:
            pass

        self.in_tarih.set(fmt_tr_date(row["tarih"]))
        self.in_tip.set(row["tip"] or "Gelir")
        self.in_tutar.set(fmt_amount(row["tutar"]))
        self.in_para.set(row["para"] or "TL")
        self.in_odeme.set(row["odeme"] or "")
        self.in_kategori.set(row["kategori"] or "")

        cid = row["cari_id"]
        if cid:
            c = self.app.db.cari_get(int(cid))
            if c:
                self.in_cari.set(f"{c['id']} - {c['ad']}")
            else:
                self.in_cari.set("(Yok)")
        else:
            self.in_cari.set("(Yok)")

        self.in_aciklama.set(row["aciklama"] or "")
        self._sync_aciklama_button()
        self.in_belge.set(row["belge"] or "")
        self.in_etiket.set(row["etiket"] or "")

        try:
            self.nb.select(self.tab_form)
        except Exception:
            pass

    def delete_selected(self):
        if not self.app.is_admin:
            return
        sel = self.tree.selection()
        if not sel:
            return
        try:
            vid = int(self.tree.item(sel[0], "values")[0])
        except Exception:
            return
        if messagebox.askyesno(APP_TITLE, f"Kayıt silinsin mi? (id={vid})"):
            self.app.db.kasa_delete(vid)
            try:
                self.app.db.log("UI", f"Kasa kaydı silindi (id={vid})")
            except Exception:
                pass
            if self.edit_id == vid:
                self.clear_form()
            self.refresh()

    # -----------------
    # Filters / refresh
    # -----------------
    def last30(self):
        d_to = date.today()
        d_from = d_to - timedelta(days=30)
        self.f_from.set(d_from.strftime("%d.%m.%Y"))
        self.f_to.set(d_to.strftime("%d.%m.%Y"))
        self.refresh()

    def this_month(self):
        d = date.today()
        d_from = date(d.year, d.month, 1)
        self.f_from.set(d_from.strftime("%d.%m.%Y"))
        self.f_to.set(d.strftime("%d.%m.%Y"))
        self.refresh()

    def refresh(self):
        """Geçmiş + raporlar + üst özet."""
        self._refresh_history()
        self._refresh_reports()
        self._refresh_summary_bar()

    def update_overdue_reminders(self, count: int) -> None:
        try:
            self.lbl_overdue.config(text=f"Geciken Hatırlatmalar: {int(count)}")
        except Exception:
            pass

    def _refresh_history(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        kat = self.f_kat.get()
        kat = "" if kat == "(Tümü)" else kat
        tip = self.f_tip.get()
        tip = "" if tip == "(Tümü)" else tip

        rows = self.app.db.kasa_list(
            q=self.f_q.get(),
            date_from=self.f_from.get(),
            date_to=self.f_to.get(),
            tip=tip,
            kategori=kat,
        )

        gelir = gider = 0.0
        for r in rows:
            t = (r["tip"] or "").strip()
            try:
                v = float(r["tutar"] or 0)
            except Exception:
                v = 0.0
            if t == "Gelir":
                gelir += v
            elif t == "Gider":
                gider += v

            self.tree.insert(
                "",
                tk.END,
                values=(
                    r["id"],
                    fmt_tr_date(r["tarih"]),
                    r["tip"],
                    fmt_amount(r["tutar"]),
                    r["para"],
                    r["odeme"],
                    r["kategori"],
                    r["cari_ad"] or "",
                    r["aciklama"] or "",
                    r["belge"] or "",
                    r["etiket"] or "",
                ),
            )

        net = gelir - gider
        self.lbl_sum.config(text=f"Gelir: {fmt_amount(gelir)} | Gider: {fmt_amount(gider)} | Net: {fmt_amount(net)}")

    def _refresh_summary_bar(self):
        d = date.today()
        d_from = date(d.year, d.month, 1).isoformat()
        d_to = d.isoformat()
        month = self.app.db.kasa_toplam(d_from, d_to)
        all_ = self.app.db.kasa_toplam("", "")

        self.lbl_month.config(
            text=f"Bu Ay → Gelir: {fmt_amount(month['gelir'])} | Gider: {fmt_amount(month['gider'])} | Net: {fmt_amount(month['net'])}"
        )
        self.lbl_all.config(
            text=f"Genel → Gelir: {fmt_amount(all_['gelir'])} | Gider: {fmt_amount(all_['gider'])} | Net: {fmt_amount(all_['net'])}"
        )

    def _refresh_reports(self):
        d = date.today()
        d_from = date(d.year, d.month, 1).isoformat()
        d_to = d.isoformat()

        m = self.app.db.kasa_toplam(d_from, d_to)
        a = self.app.db.kasa_toplam("", "")

        self.lbl_rep_month.config(text=f"Gelir: {fmt_amount(m['gelir'])}\nGider: {fmt_amount(m['gider'])}\nNet: {fmt_amount(m['net'])}")
        self.lbl_rep_all.config(text=f"Gelir: {fmt_amount(a['gelir'])}\nGider: {fmt_amount(a['gider'])}\nNet: {fmt_amount(a['net'])}")

        # Aylık özet
        for i in self.tree_monthly.get_children():
            self.tree_monthly.delete(i)
        try:
            rows = self.app.db.kasa_aylik_ozet(limit=24)
        except Exception:
            rows = []
        for r in rows:
            self.tree_monthly.insert(
                "",
                tk.END,
                values=(
                    r["ay"],
                    fmt_amount(r["gelir"]),
                    fmt_amount(r["gider"]),
                    fmt_amount(r["net"]),
                ),
            )

        # Bu ay gider kategorileri
        self.txt_kat.delete("1.0", tk.END)
        self.txt_kat.insert(tk.END, "Kategori | Adet | Toplam\n")
        self.txt_kat.insert(tk.END, "-" * 42 + "\n")
        try:
            for r in self.app.db.kasa_kategori_ozet(d_from, d_to, tip="Gider"):
                self.txt_kat.insert(
                    tk.END,
                    f"{r['kategori'] or '(Boş)'} | {r['adet']} | {fmt_amount(r['toplam'])}\n",
                )
        except Exception:
            pass

    def _jump_month_from_report(self):
        sel = self.tree_monthly.selection()
        if not sel:
            return
        try:
            ay = str(self.tree_monthly.item(sel[0], "values")[0])  # YYYY-MM
        except Exception:
            return
        if len(ay) != 7 or "-" not in ay:
            return
        # Ayın ilk ve son gününe filtrele
        try:
            y = int(ay.split("-", 1)[0])
            m = int(ay.split("-", 1)[1])
        except Exception:
            return
        d1 = date(y, m, 1)
        if m == 12:
            d2 = date(y + 1, 1, 1) - timedelta(days=1)
        else:
            d2 = date(y, m + 1, 1) - timedelta(days=1)

        self.f_from.set(d1.strftime("%d.%m.%Y"))
        self.f_to.set(d2.strftime("%d.%m.%Y"))
        self.f_tip.set("(Tümü)")
        self.f_kat.set("(Tümü)")
        self.f_q.set("")
        self.refresh()
        try:
            self.nb.select(self.tab_history)
        except Exception:
            pass
