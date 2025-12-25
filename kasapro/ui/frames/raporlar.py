# -*- coding: utf-8 -*-
"""KasaPro v3 - Ana ekran frame'leri"""

from __future__ import annotations

from datetime import timedelta, date
from typing import List, Tuple, TYPE_CHECKING

import tkinter as tk
from tkinter import ttk

from ...utils import (
    fmt_tr_date,
    safe_float,
    fmt_amount,
)
from ..base import BaseView
from ..ui_logging import wrap_callback
from ..widgets import LabeledEntry

if TYPE_CHECKING:
    from ...app import App

class RaporlarFrame(BaseView):
    def __init__(self, master, app: "App"):
        self.app = app
        super().__init__(master, app)
        self.build_ui()

    def build_ui(self) -> None:
        self._build()

    def _build(self):
        top = ttk.LabelFrame(self, text="Raporlar / Özet")
        top.pack(fill=tk.X, padx=10, pady=10)

        r = ttk.Frame(top)
        r.pack(fill=tk.X, pady=6)
        self.d_from = LabeledEntry(r, "Başlangıç:", 12)
        self.d_from.pack(side=tk.LEFT, padx=6)
        self.d_to = LabeledEntry(r, "Bitiş:", 12)
        self.d_to.pack(side=tk.LEFT, padx=6)
        ttk.Button(r, text="Son 30 gün", command=wrap_callback("raporlar_last30", self.last30)).pack(
            side=tk.LEFT, padx=6
        )
        ttk.Button(r, text="Yenile", command=wrap_callback("raporlar_refresh", self.refresh)).pack(side=tk.LEFT, padx=6)

        self.lbl_kasa = ttk.Label(top, text="")
        self.lbl_kasa.pack(anchor="w", padx=10, pady=(0,10))

        body = ttk.Frame(self)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,10))
        left = ttk.LabelFrame(body, text="Seçili Carileri Topla")
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,8))
        right = ttk.LabelFrame(body, text="Kasa Analiz")
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(8,0))

        self.cari_rows: List[Tuple[int, tk.BooleanVar]] = []
        self.canvas = tk.Canvas(left, highlightthickness=0)
        self.scroll = ttk.Scrollbar(left, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas)
        self.inner.bind(
            "<Configure>",
            wrap_callback("raporlar_canvas_config", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))),
        )
        self.canvas.create_window((0,0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scroll.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.scroll.pack(side=tk.RIGHT, fill=tk.Y)

        btmL = ttk.Frame(left)
        btmL.pack(fill=tk.X, padx=6, pady=6)
        ttk.Button(btmL, text="Tümünü Seç", command=wrap_callback("raporlar_select_all", lambda: self.set_all(True))).pack(
            side=tk.LEFT, padx=6
        )
        ttk.Button(
            btmL,
            text="Tümünü Kaldır",
            command=wrap_callback("raporlar_clear_all", lambda: self.set_all(False)),
        ).pack(side=tk.LEFT, padx=6)
        ttk.Button(btmL, text="Hesapla", command=wrap_callback("raporlar_calc", self.calc_selected)).pack(
            side=tk.LEFT, padx=6
        )
        self.lbl_sel = ttk.Label(btmL, text="", justify="left")
        self.lbl_sel.pack(side=tk.RIGHT, padx=6)

        self.txt_kasa = tk.Text(right, height=20)
        self.txt_kasa.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # Başlangıç değerleri - otomatik yükleme yapma
        self.lbl_kasa.config(text="Rapor oluşturmak için 'Son 30 gün' veya 'Yenile' butonuna basın.")
        self.lbl_sel.config(text="Bakiye: 0,00")

    def last30(self):
        d_to = date.today()
        d_from = d_to - timedelta(days=30)
        self.d_from.set(d_from.strftime("%d.%m.%Y"))
        self.d_to.set(d_to.strftime("%d.%m.%Y"))
        self.refresh()

    def refresh(self, data=None):
        totals = self.app.db.kasa_toplam(self.d_from.get(), self.d_to.get())
        self.lbl_kasa.config(text=f"KASA → Gelir: {fmt_amount(totals['gelir'])} | Gider: {fmt_amount(totals['gider'])} | Net: {fmt_amount(totals['net'])}")

        for w in self.inner.winfo_children():
            w.destroy()
        self.cari_rows.clear()
        for r in self.app.db.cari_list(only_active=True):
            var = tk.BooleanVar(value=False)
            cid = int(r["id"])
            frm = ttk.Frame(self.inner)
            frm.pack(fill=tk.X, pady=2, padx=6)
            ttk.Checkbutton(frm, variable=var, text=r["ad"]).pack(side=tk.LEFT)
            b = self.app.db.cari_bakiye(cid)
            ttk.Label(frm, text=f"Bakiye: {fmt_amount(b['bakiye'])}").pack(side=tk.RIGHT)
            self.cari_rows.append((cid, var))

        self.calc_selected()
        self._refresh_kasa_analysis()

    def set_all(self, state: bool):
        for _, var in self.cari_rows:
            var.set(state)
        self.calc_selected()

    def calc_selected(self):
        total_borc = total_alacak = total_bakiye = 0.0
        for cid, var in self.cari_rows:
            if var.get():
                b = self.app.db.cari_bakiye(cid)
                total_borc += b["borc"]
                total_alacak += b["alacak"]
                total_bakiye += b["bakiye"]
        self.lbl_sel.config(text=f"Borç: {fmt_amount(total_borc)} | Alacak: {fmt_amount(total_alacak)} | Bakiye: {fmt_amount(total_bakiye)}")

    def _refresh_kasa_analysis(self):
        self.txt_kasa.delete("1.0", tk.END)
        df, dt = self.d_from.get(), self.d_to.get()
        self.txt_kasa.insert(tk.END, "Kategori Bazlı (Gider) - En Çoktan Aza\n")
        self.txt_kasa.insert(tk.END, "-"*55 + "\n")
        for r in self.app.db.kasa_kategori_ozet(df, dt, "Gider"):
            self.txt_kasa.insert(tk.END, f"{r['kategori'] or '(Boş)'} | adet={r['adet']} | toplam={fmt_amount(safe_float(r['toplam']))}\n")
        self.txt_kasa.insert(tk.END, "\nGünlük Özet\n")
        self.txt_kasa.insert(tk.END, "-"*55 + "\n")
        for r in self.app.db.kasa_gunluk(df, dt):
            gelir = safe_float(r["gelir"])
            gider = safe_float(r["gider"])
            self.txt_kasa.insert(tk.END, f"{fmt_tr_date(r['tarih'])} | gelir={fmt_amount(gelir)} | gider={fmt_amount(gider)} | net={fmt_amount((gelir-gider))}\n")
