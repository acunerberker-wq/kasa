# -*- coding: utf-8 -*-
"""UI Plugin: Şirket Diğer Giderler.

Amaç:
- Cari (müşteri/tedarikçi) ile ilişkisi olmayan giderlerin hızlıca girilmesi
  ve geçmiş/raporlarının ayrı bir ekranda izlenmesi.

Teknik:
- Veriler mevcut `kasa_hareket` tablosunda tutulur.
- Bu ekran sadece `tip='Gider'` ve `cari_id IS NULL` kayıtlarını gösterir.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

import tkinter as tk
from tkinter import ttk, messagebox

from ...config import APP_TITLE
from ...utils import today_iso, fmt_tr_date, fmt_amount
from ..widgets import LabeledEntry, LabeledCombo, MoneyEntry, SimpleField


PLUGIN_META = {
    "key": "diger_giderler",
    "nav_text": "🧾 Diğer Giderler",
    "page_title": "Şirket Diğer Giderler",
    "order": 33,
}


class DigerGiderlerFrame(ttk.Frame):
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

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.tab_form = ttk.Frame(self.nb)
        self.tab_history = ttk.Frame(self.nb)
        self.tab_reports = ttk.Frame(self.nb)
        self.nb.add(self.tab_form, text="➕ Gider Ekle")
        self.nb.add(self.tab_history, text="🗂️ Geçmiş")
        self.nb.add(self.tab_reports, text="📊 Rapor")

        self._build_form(self.tab_form)
        self._build_history(self.tab_history)
        self._build_reports(self.tab_reports)

        self.clear_form()
        self.refresh()
        self._apply_permissions()

    def _build_form(self, parent: ttk.Frame):
        top = ttk.LabelFrame(parent, text="Cari Olmayan Gider Kaydı")
        top.pack(fill=tk.X, padx=6, pady=6)

        row1 = ttk.Frame(top)
        row1.pack(fill=tk.X, pady=4)
        self.in_tarih = LabeledEntry(row1, "Tarih:", 16)
        self.in_tarih.pack(side=tk.LEFT, padx=6)
        ttk.Button(row1, text="Bugün", command=lambda: self.in_tarih.set(fmt_tr_date(today_iso()))).pack(
            side=tk.LEFT, padx=6
        )

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

        # Kategori burada "gider hesabı" gibi kullanılır
        self.in_kategori = LabeledCombo(row2, "Gider Hesabı:", self.app.db.list_categories(), 20)
        self.in_kategori.pack(side=tk.LEFT, padx=6)
        try:
            self.in_kategori.set("Diğer")
        except Exception:
            pass

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

        # Etiket alanını "Kurum/Hesap" gibi kullanmak pratik oluyor
        self.in_etiket = LabeledEntry(row3, "Kurum/Hesap:", 18)
        self.in_etiket.pack(side=tk.LEFT, padx=6)

        self.btn_save = ttk.Button(row3, text="Kaydet", command=self.save)
        self.btn_save.pack(side=tk.LEFT, padx=10)
        self.btn_new = ttk.Button(row3, text="Yeni", command=self.clear_form)
        self.btn_new.pack(side=tk.LEFT, padx=6)

        self.lbl_mode = ttk.Label(row3, text="")
        self.lbl_mode.pack(side=tk.LEFT, padx=10)

    def _build_history(self, parent: ttk.Frame):
        mid = ttk.LabelFrame(parent, text="Diğer Gider Geçmişi")
        mid.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        frow = ttk.Frame(mid)
        frow.pack(fill=tk.X, pady=4)

        self.f_q = LabeledEntry(frow, "Ara:", 22)
        self.f_q.pack(side=tk.LEFT, padx=6)

        self.f_kat = LabeledCombo(frow, "Gider Hesabı:", ["(Tümü)"] + self.app.db.list_categories(), 16)
        self.f_kat.pack(side=tk.LEFT, padx=6)
        self.f_kat.set("(Tümü)")

        self.f_from = LabeledEntry(frow, "Başlangıç:", 12)
        self.f_from.pack(side=tk.LEFT, padx=6)
        self.f_to = LabeledEntry(frow, "Bitiş:", 12)
        self.f_to.pack(side=tk.LEFT, padx=6)

        ttk.Button(frow, text="Bu Ay", command=self.this_month).pack(side=tk.LEFT, padx=6)
        ttk.Button(frow, text="Son 30 gün", command=self.last30).pack(side=tk.LEFT, padx=6)
        ttk.Button(frow, text="Yenile", command=self.refresh).pack(side=tk.LEFT, padx=6)

        cols = ("id", "tarih", "tutar", "para", "odeme", "kategori", "kurum", "belge", "aciklama")
        self.tree = ttk.Treeview(mid, columns=cols, show="headings", height=14, selectmode="browse")
        for c in cols:
            self.tree.heading(c, text=c.upper())

        self.tree.column("id", width=55, anchor="center")
        self.tree.column("tarih", width=95)
        self.tree.column("tutar", width=110, anchor="e")
        self.tree.column("para", width=55, anchor="center")
        self.tree.column("odeme", width=120)
        self.tree.column("kategori", width=160)
        self.tree.column("kurum", width=180)
        self.tree.column("belge", width=100)
        self.tree.column("aciklama", width=360)
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

        left = ttk.LabelFrame(body, text="Aylık Diğer Gider (Son 24 Ay)")
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        cols = ("ay", "gider")
        self.tree_monthly = ttk.Treeview(left, columns=cols, show="headings", height=12, selectmode="browse")
        for c in cols:
            self.tree_monthly.heading(c, text=c.upper())
        self.tree_monthly.column("ay", width=90, anchor="center")
        self.tree_monthly.column("gider", width=140, anchor="e")
        self.tree_monthly.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.tree_monthly.bind("<Double-1>", lambda _e: self._jump_month_from_report())

        right = ttk.LabelFrame(body, text="Gider Hesabı Dağılımı (Bu Ay)")
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))
        self.txt_kat = tk.Text(right, height=12)
        self.txt_kat.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

    def _apply_permissions(self):
        state = ("normal" if self.app.is_admin else "disabled")
        try:
            self.btn_del.config(state=state)
            self.btn_edit.config(state=state)
        except Exception:
            pass

    def reload_settings(self):
        try:
            self.in_para.cmb["values"] = self.app.db.list_currencies()
            self.in_odeme.cmb["values"] = self.app.db.list_payments()
            self.in_kategori.cmb["values"] = self.app.db.list_categories()
            self.f_kat.cmb["values"] = ["(Tümü)"] + self.app.db.list_categories()
        except Exception:
            pass

    # -----------------
    # Açıklama editörü
    # -----------------
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
                win.deiconify(); win.lift(); win.focus_force()
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
    # Form
    # -----------------
    def clear_form(self):
        self.edit_id = None
        try:
            self.btn_save.config(text="Kaydet")
            self.lbl_mode.config(text="")
        except Exception:
            pass

        self.in_tarih.set(fmt_tr_date(today_iso()))
        self.in_tutar.set("")
        self.in_para.set("TL")

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

        belge = (self.in_belge.get() or "").strip()
        if not belge:
            # Diğer gider prefix: DG
            try:
                belge = self.app.db.next_belge_no("DG")
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
                "Gider",
                tutar,
                self.in_para.get() or "TL",
                self.in_odeme.get(),
                self.in_kategori.get(),
                None,
                self.in_aciklama.get(),
                belge,
                self.in_etiket.get(),
            )
            try:
                self.app.db.log("UI", f"Diğer gider güncellendi (id={self.edit_id})")
            except Exception:
                pass
            self.edit_id = None
            self.clear_form()
            self.refresh()
            return

        self.app.db.kasa_add(
            self.in_tarih.get(),
            "Gider",
            tutar,
            self.in_para.get() or "TL",
            self.in_odeme.get(),
            self.in_kategori.get(),
            None,
            self.in_aciklama.get(),
            belge,
            self.in_etiket.get(),
        )
        try:
            self.app.db.log("UI", "Diğer gider eklendi")
        except Exception:
            pass

        # Sonraki giriş için bazı alanları boşalt
        self.in_tutar.set("")
        self.in_belge.set("")
        self.in_aciklama.set("")
        self._clear_aciklama_editor()
        self._sync_aciklama_button()

        self.refresh()
        try:
            self.nb.select(self.tab_history)
        except Exception:
            pass

    # -----------------
    # History
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
        # Güvenlik: cari bağlı veya tip farklı ise bu ekranda düzenletmeyelim
        try:
            if (row["tip"] or "") != "Gider" or row["cari_id"]:
                messagebox.showwarning(APP_TITLE, "Bu kayıt 'Diğer Giderler' kapsamına girmiyor.")
                return
        except Exception:
            pass

        self.edit_id = int(row["id"])
        try:
            self.btn_save.config(text="Güncelle")
            self.lbl_mode.config(text=f"Düzenleme modu: id={self.edit_id}")
        except Exception:
            pass

        self.in_tarih.set(fmt_tr_date(row["tarih"]))
        self.in_tutar.set(fmt_amount(row["tutar"]))
        self.in_para.set(row["para"] or "TL")
        self.in_odeme.set(row["odeme"] or "")
        self.in_kategori.set(row["kategori"] or "")
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
                self.app.db.log("UI", f"Diğer gider silindi (id={vid})")
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
        self._refresh_history()
        self._refresh_reports()
        self._refresh_summary_bar()

    def _refresh_history(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        kat = self.f_kat.get()
        kat = "" if kat == "(Tümü)" else kat

        rows = self.app.db.kasa_list(
            q=self.f_q.get(),
            date_from=self.f_from.get(),
            date_to=self.f_to.get(),
            tip="Gider",
            kategori=kat,
            has_cari=False,
        )

        gider = 0.0
        for r in rows:
            try:
                v = float(r["tutar"] or 0)
            except Exception:
                v = 0.0
            gider += v

            self.tree.insert(
                "",
                tk.END,
                values=(
                    r["id"],
                    fmt_tr_date(r["tarih"]),
                    fmt_amount(r["tutar"]),
                    r["para"],
                    r["odeme"],
                    r["kategori"],
                    r["etiket"] or "",
                    r["belge"] or "",
                    r["aciklama"] or "",
                ),
            )

        self.lbl_sum.config(text=f"Toplam Diğer Gider: {fmt_amount(gider)}")

    def _refresh_summary_bar(self):
        d = date.today()
        d_from = date(d.year, d.month, 1).isoformat()
        d_to = d.isoformat()
        month = self.app.db.kasa_toplam(d_from, d_to, has_cari=False)
        all_ = self.app.db.kasa_toplam("", "", has_cari=False)

        self.lbl_month.config(text=f"Bu Ay Diğer Gider: {fmt_amount(month['gider'])}")
        self.lbl_all.config(text=f"Genel Diğer Gider: {fmt_amount(all_['gider'])}")

    def _refresh_reports(self):
        d = date.today()
        d_from = date(d.year, d.month, 1).isoformat()
        d_to = d.isoformat()
        month = self.app.db.kasa_toplam(d_from, d_to, has_cari=False)
        all_ = self.app.db.kasa_toplam("", "", has_cari=False)

        self.lbl_rep_month.config(text=f"Toplam: {fmt_amount(month['gider'])}")
        self.lbl_rep_all.config(text=f"Toplam: {fmt_amount(all_['gider'])}")

        # Aylık diğer gider
        for i in self.tree_monthly.get_children():
            self.tree_monthly.delete(i)
        rows = self.app.db.kasa_aylik_ozet(limit=24, has_cari=False)
        for r in rows:
            self.tree_monthly.insert("", tk.END, values=(r["ay"], fmt_amount(r["gider"])))

        # Kategori dağılımı
        try:
            self.txt_kat.delete("1.0", "end")
        except Exception:
            pass
        krows = self.app.db.kasa_kategori_ozet(d_from, d_to, tip="Gider", has_cari=False)
        if not krows:
            self.txt_kat.insert("1.0", "(Bu ay kayıt yok)")
        else:
            lines = []
            for r in krows:
                lines.append(f"{r['kategori'] or 'Diğer'}  →  {fmt_amount(r['toplam'])}  ({r['adet']} kayıt)")
            self.txt_kat.insert("1.0", "\n".join(lines))

    def _jump_month_from_report(self):
        sel = self.tree_monthly.selection()
        if not sel:
            return
        try:
            ay = str(self.tree_monthly.item(sel[0], "values")[0])
        except Exception:
            return
        # ay: YYYY-MM
        try:
            y, m = ay.split("-", 1)
            y = int(y); m = int(m)
            d_from = date(y, m, 1)
            # sonraki ayın 1'i - 1 gün
            if m == 12:
                d_to = date(y + 1, 1, 1) - timedelta(days=1)
            else:
                d_to = date(y, m + 1, 1) - timedelta(days=1)
        except Exception:
            return

        self.f_from.set(d_from.strftime("%d.%m.%Y"))
        self.f_to.set(d_to.strftime("%d.%m.%Y"))
        self.refresh()
        try:
            self.nb.select(self.tab_history)
        except Exception:
            pass


def build(master, app: "App") -> ttk.Frame:
    return DigerGiderlerFrame(master, app)
