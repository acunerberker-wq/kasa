# -*- coding: utf-8 -*-
"""Satış raporları ekranı."""

from __future__ import annotations

import queue
import threading
from typing import Any, Dict, List, Tuple, TYPE_CHECKING

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from ...config import APP_TITLE, HAS_OPENPYXL, HAS_REPORTLAB
from ...utils import fmt_amount, fmt_tr_date, safe_float
from ..base import BaseView
from ..widgets import LabeledEntry, LabeledCombo

if TYPE_CHECKING:
    from ...app import App


REPORT_TYPES = {
    "Günlük Satış Özeti": "daily",
    "Müşteri Bazlı Satış / Borç-Alacak": "customer",
    "Ürün Bazlı Satış & Kârlılık": "product",
    "Satış Temsilcisi Performansı": "salesperson",
}


class SatisRaporlariFrame(BaseView):
    def __init__(self, master, app: "App"):
        self.app = app
        super().__init__(master, app)
        self._cari_map: Dict[str, int] = {}
        self._report_key = "daily"
        self._page = 0
        self._page_size = 200
        self._running = False
        self._current_rows: List[Dict[str, Any]] = []
        self._current_headers: List[str] = []
        self._current_title = ""
        self.build_ui()

    def build_ui(self) -> None:
        self._build()

    def _build(self):
        top = ttk.LabelFrame(self, text="Satış Raporları")
        top.pack(fill=tk.X, padx=10, pady=10)

        r1 = ttk.Frame(top)
        r1.pack(fill=tk.X, pady=4)
        self.cmb_report = LabeledCombo(r1, "Rapor:", list(REPORT_TYPES.keys()), 28)
        self.cmb_report.pack(side=tk.LEFT, padx=6)
        self.cmb_report.set("Günlük Satış Özeti")

        self.d_from = LabeledEntry(r1, "Başlangıç:", 12)
        self.d_from.pack(side=tk.LEFT, padx=6)
        self.d_to = LabeledEntry(r1, "Bitiş:", 12)
        self.d_to.pack(side=tk.LEFT, padx=6)

        self.cmb_durum = LabeledCombo(r1, "Durum:", ["Kesildi", "Taslak", "(Tümü)"], 10)
        self.cmb_durum.pack(side=tk.LEFT, padx=6)
        self.cmb_durum.set("Kesildi")

        r2 = ttk.Frame(top)
        r2.pack(fill=tk.X, pady=4)
        self.cmb_cari = LabeledCombo(r2, "Müşteri:", [""], 28, state="normal")
        self.cmb_cari.pack(side=tk.LEFT, padx=6)
        self.cmb_urun = LabeledCombo(r2, "Ürün:", [""], 22, state="normal")
        self.cmb_urun.pack(side=tk.LEFT, padx=6)
        self.cmb_kategori = LabeledCombo(r2, "Kategori:", [""], 16, state="normal")
        self.cmb_kategori.pack(side=tk.LEFT, padx=6)

        r3 = ttk.Frame(top)
        r3.pack(fill=tk.X, pady=4)
        self.cmb_sube = LabeledCombo(r3, "Şube:", [""], 14, state="normal")
        self.cmb_sube.pack(side=tk.LEFT, padx=6)
        self.cmb_depo = LabeledCombo(r3, "Depo:", [""], 14, state="normal")
        self.cmb_depo.pack(side=tk.LEFT, padx=6)
        self.cmb_odeme = LabeledCombo(r3, "Ödeme:", [""], 14, state="normal")
        self.cmb_odeme.pack(side=tk.LEFT, padx=6)
        self.cmb_temsilci = LabeledCombo(r3, "Temsilci:", [""], 18, state="normal")
        self.cmb_temsilci.pack(side=tk.LEFT, padx=6)

        r4 = ttk.Frame(top)
        r4.pack(fill=tk.X, pady=(4, 6))
        self.lbl_company = ttk.Label(r4, text="")
        self.lbl_company.pack(side=tk.LEFT, padx=6)

        actions = ttk.Frame(top)
        actions.pack(fill=tk.X, pady=(4, 6))
        ttk.Button(actions, text="Hesapla", command=self.run_report).pack(side=tk.LEFT, padx=6)
        ttk.Button(actions, text="Filtreleri Temizle", command=self.reset_filters).pack(side=tk.LEFT, padx=6)
        ttk.Button(actions, text="Listeleri Yenile", command=self.refresh).pack(side=tk.LEFT, padx=6)

        ttk.Button(actions, text="CSV", command=self.export_csv).pack(side=tk.RIGHT, padx=6)
        ttk.Button(actions, text="Excel", command=self.export_excel).pack(side=tk.RIGHT, padx=6)
        ttk.Button(actions, text="Yazdır", command=self.export_pdf).pack(side=tk.RIGHT, padx=6)

        self.lbl_status = ttk.Label(top, text="")
        self.lbl_status.pack(anchor="w", padx=6)
        self.pb = ttk.Progressbar(top, mode="indeterminate", length=360)
        self.pb.pack(anchor="w", padx=6, pady=(2, 0))

        body = ttk.Frame(self)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        left = ttk.Frame(body)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(left, columns=(), show="headings", height=18)
        self.tree.pack(fill=tk.BOTH, expand=True)
        scr = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        scr.place(in_=self.tree, relx=1.0, rely=0, relheight=1.0, x=0)
        self.tree.configure(yscrollcommand=scr.set)

        nav = ttk.Frame(left)
        nav.pack(fill=tk.X, pady=(6, 0))
        ttk.Button(nav, text="◀ Önceki", command=self.prev_page).pack(side=tk.LEFT, padx=4)
        ttk.Button(nav, text="Sonraki ▶", command=self.next_page).pack(side=tk.LEFT, padx=4)
        self.lbl_page = ttk.Label(nav, text="")
        self.lbl_page.pack(side=tk.LEFT, padx=8)

        right = ttk.Frame(body)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))

        kpi_box = ttk.LabelFrame(right, text="KPI")
        kpi_box.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        self.txt_kpi = tk.Text(kpi_box, width=42, height=18, wrap="word")
        self.txt_kpi.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        warn_box = ttk.LabelFrame(right, text="Uyarılar")
        warn_box.pack(fill=tk.BOTH, expand=True)
        self.txt_warn = tk.Text(warn_box, width=42, height=10, wrap="word")
        self.txt_warn.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        self.refresh()
        self._setup_tree("daily")
        self.run_report()

    def refresh(self, data=None):
        try:
            self.lbl_company.config(
                text=f"Aktif Şirket: {getattr(self.app, 'active_company_name', '') or '-'}"
            )
        except Exception:
            pass

        # Cari listesi
        self._cari_map.clear()
        try:
            cariler = self.app.db.cari_list(q="", only_active=False)
            names = [str(r["ad"]) for r in cariler]
            self._cari_map.update({str(r["ad"]): int(r["id"]) for r in cariler if r})
        except Exception:
            names = []

        try:
            self.cmb_cari.cmb["values"] = [""] + names
        except Exception:
            pass

        try:
            products = self.app.db.satis_rapor_list_products()
        except Exception:
            products = []
        try:
            self.cmb_urun.cmb["values"] = [""] + products
        except Exception:
            pass

        try:
            categories = self.app.db.satis_rapor_list_categories()
        except Exception:
            categories = []
        try:
            self.cmb_kategori.cmb["values"] = [""] + categories
        except Exception:
            pass

        try:
            subeler = self.app.db.satis_rapor_list_sube()
        except Exception:
            subeler = []
        try:
            self.cmb_sube.cmb["values"] = [""] + subeler
        except Exception:
            pass

        try:
            depolar = self.app.db.satis_rapor_list_depo()
        except Exception:
            depolar = []
        try:
            self.cmb_depo.cmb["values"] = [""] + depolar
        except Exception:
            pass

        try:
            odeme = self.app.db.list_payments()
        except Exception:
            odeme = []
        try:
            self.cmb_odeme.cmb["values"] = [""] + odeme
        except Exception:
            pass

        try:
            temsilciler = self.app.db.satis_rapor_list_temsilci()
        except Exception:
            temsilciler = []
        try:
            self.cmb_temsilci.cmb["values"] = [""] + temsilciler
        except Exception:
            pass

    def reset_filters(self):
        for w in (self.d_from, self.d_to, self.cmb_cari, self.cmb_urun, self.cmb_kategori,
                  self.cmb_sube, self.cmb_depo, self.cmb_odeme, self.cmb_temsilci):
            try:
                w.set("")
            except Exception:
                pass
        try:
            self.cmb_durum.set("Kesildi")
        except Exception:
            pass
        self._page = 0
        self.run_report()

    def _gather_filters(self) -> Dict[str, Any]:
        try:
            report_key = REPORT_TYPES.get(self.cmb_report.get(), "daily")
        except Exception:
            report_key = "daily"

        cari_name = ""
        try:
            cari_name = self.cmb_cari.get().strip()
        except Exception:
            cari_name = ""

        return {
            "report_key": report_key,
            "date_from": self.d_from.get(),
            "date_to": self.d_to.get(),
            "durum": self.cmb_durum.get(),
            "cari_id": self._cari_map.get(cari_name),
            "urun": self.cmb_urun.get(),
            "kategori": self.cmb_kategori.get(),
            "sube": self.cmb_sube.get(),
            "depo": self.cmb_depo.get(),
            "odeme": self.cmb_odeme.get(),
            "temsilci": self.cmb_temsilci.get(),
        }

    def _setup_tree(self, report_key: str):
        if report_key == "daily":
            cols = ("tarih", "satis_adet", "iade_adet", "ciro", "iskonto", "iade", "net", "tahsilat")
            headers = ["Tarih", "Satış", "İade", "Ciro", "İskonto", "İade Tutar", "Net Ciro", "Tahsilat"]
        elif report_key == "customer":
            cols = ("cari", "satis", "iade", "iskonto", "tahsilat", "net", "bakiye")
            headers = ["Müşteri", "Satış", "İade", "İskonto", "Tahsilat", "Net", "Bakiye"]
        elif report_key == "product":
            cols = ("urun", "kategori", "miktar", "ciro", "maliyet", "kar")
            headers = ["Ürün", "Kategori", "Miktar", "Ciro", "Maliyet", "Kâr"]
        else:
            cols = ("temsilci", "satis", "iade", "iskonto", "tahsilat", "net", "bakiye")
            headers = ["Temsilci", "Satış", "İade", "İskonto", "Tahsilat", "Net", "Bakiye"]

        self.tree.config(columns=cols)
        for col in cols:
            self.tree.heading(col, text=col.upper())
            self.tree.column(col, width=100)

        for col, header in zip(cols, headers):
            self.tree.heading(col, text=header)

        if report_key == "daily":
            self.tree.column("tarih", width=110)
            for col in ("satis_adet", "iade_adet"):
                self.tree.column(col, width=70, anchor="center")
        if report_key in ("customer", "temsilci"):
            self.tree.column(cols[0], width=220)
        if report_key == "product":
            self.tree.column("urun", width=220)
            self.tree.column("kategori", width=140)

    def run_report(self):
        if self._running:
            return
        self._page = 0
        self._fetch_report(reset_page=False)

    def prev_page(self):
        if self._page <= 0:
            return
        self._page -= 1
        self._fetch_report(reset_page=False)

    def next_page(self):
        self._page += 1
        self._fetch_report(reset_page=False)

    def _fetch_report(self, reset_page: bool):
        if self._running:
            return
        if reset_page:
            self._page = 0

        filters = self._gather_filters()
        report_key = filters.pop("report_key", "daily")
        self._report_key = report_key
        self._setup_tree(report_key)

        offset = self._page * self._page_size
        limit = self._page_size

        q: "queue.Queue[Tuple[str, Any]]" = queue.Queue()

        def worker():
            try:
                if report_key == "daily":
                    data = self.app.db.satis_rapor_gunluk(filters, limit, offset)
                elif report_key == "customer":
                    data = self.app.db.satis_rapor_musteri(filters, limit, offset)
                elif report_key == "product":
                    data = self.app.db.satis_rapor_urun(filters, limit, offset)
                else:
                    data = self.app.db.satis_rapor_temsilci(filters, limit, offset)

                kpis = self.app.db.satis_rapor_kpi(filters)
                warnings = self.app.db.satis_rapor_warnings()
                q.put(("done", data, kpis, warnings))
            except Exception as exc:
                q.put(("error", str(exc)))

        self._running = True
        self.pb.start(10)
        self.lbl_status.config(text="Rapor hazırlanıyor...")

        threading.Thread(target=worker, daemon=True).start()

        def poll():
            try:
                kind, *rest = q.get_nowait()
            except queue.Empty:
                if self._running:
                    self.after(100, poll)
                return

            self._running = False
            self.pb.stop()
            self.lbl_status.config(text="")

            if kind == "error":
                messagebox.showerror(APP_TITLE, f"Rapor alınamadı: {rest[0] if rest else ''}")
                return

            data, kpis, warnings = rest
            self._apply_report(data, kpis, warnings)

        poll()

    def _apply_report(self, data: Dict[str, Any], kpis: Dict[str, Any], warnings: List[str]):
        rows = data.get("rows", [])
        total = int(data.get("total") or 0)
        self._current_rows = rows
        self._current_title = self.cmb_report.get()

        children = self.tree.get_children()
        if children:
            self.tree.delete(*children)

        row_values = []
        if self._report_key == "daily":
            headers = ["Tarih", "Satış", "İade", "Ciro", "İskonto", "İade Tutar", "Net Ciro", "Tahsilat"]
            for r in rows:
                ciro = float(safe_float(r.get("ciro")))
                iade = float(safe_float(r.get("iade")))
                net = ciro - iade
                row_values.append((
                    fmt_tr_date(r.get("tarih")),
                    int(r.get("satis_adet") or 0),
                    int(r.get("iade_adet") or 0),
                    fmt_amount(ciro),
                    fmt_amount(r.get("iskonto")),
                    fmt_amount(iade),
                    fmt_amount(net),
                    fmt_amount(r.get("tahsilat")),
                ))
        elif self._report_key == "customer":
            headers = ["Müşteri", "Satış", "İade", "İskonto", "Tahsilat", "Net", "Bakiye"]
            for r in rows:
                row_values.append((
                    r.get("cari_ad"),
                    fmt_amount(r.get("satis")),
                    fmt_amount(r.get("iade")),
                    fmt_amount(r.get("iskonto")),
                    fmt_amount(r.get("tahsilat")),
                    fmt_amount(r.get("net")),
                    fmt_amount(r.get("bakiye")),
                ))
        elif self._report_key == "product":
            headers = ["Ürün", "Kategori", "Miktar", "Ciro", "Maliyet", "Kâr"]
            for r in rows:
                row_values.append((
                    r.get("urun"),
                    r.get("kategori"),
                    fmt_amount(r.get("miktar")),
                    fmt_amount(r.get("ciro")),
                    fmt_amount(r.get("maliyet")),
                    fmt_amount(r.get("kar")),
                ))
        else:
            headers = ["Temsilci", "Satış", "İade", "İskonto", "Tahsilat", "Net", "Bakiye"]
            for r in rows:
                row_values.append((
                    r.get("temsilci"),
                    fmt_amount(r.get("satis")),
                    fmt_amount(r.get("iade")),
                    fmt_amount(r.get("iskonto")),
                    fmt_amount(r.get("tahsilat")),
                    fmt_amount(r.get("net")),
                    fmt_amount(r.get("bakiye")),
                ))

        self._current_headers = headers
        self._update_kpis(kpis)
        self._update_warnings(warnings)

        if row_values:
            batch_size = 200
            total = len(row_values)
            tree = self.tree
            insert = tree.insert
            tk_end = tk.END

            def insert_batch(start: int = 0) -> None:
                end = min(start + batch_size, total)
                for values in row_values[start:end]:
                    insert("", tk_end, values=values)
                if end < total:
                    self.after(1, lambda: insert_batch(end))

            insert_batch()

        page_total = (total // self._page_size) + (1 if total % self._page_size else 0)
        self.lbl_page.config(text=f"Sayfa: {self._page + 1} / {max(page_total, 1)}  (Kayıt: {total})")

        if warnings:
            for w in warnings:
                try:
                    self.app.db.log("Satış Raporu Uyarı", w)
                except Exception:
                    pass

    def _update_kpis(self, kpis: Dict[str, Any]):
        self.txt_kpi.delete("1.0", tk.END)
        if not kpis:
            self.txt_kpi.insert(tk.END, "KPI bulunamadı.")
            return

        self.txt_kpi.insert(
            tk.END,
            "Özet\n"
            f"- Ciro: {fmt_amount(kpis.get('ciro'))}\n"
            f"- Net Ciro: {fmt_amount(kpis.get('net_ciro'))}\n"
            f"- İskonto: {fmt_amount(kpis.get('iskonto'))}\n"
            f"- İade: {fmt_amount(kpis.get('iade'))}\n"
            f"- İade Oranı: {fmt_amount(float(safe_float(kpis.get('iade_oran'))) * 100)} %\n"
            f"- Ortalama Sepet: {fmt_amount(kpis.get('ortalama_sepet'))}\n\n",
        )

        self.txt_kpi.insert(tk.END, "En Çok Satan 20 Ürün\n")
        self.txt_kpi.insert(tk.END, "-" * 32 + "\n")
        for r in kpis.get("top_products", []):
            self.txt_kpi.insert(
                tk.END,
                f"{r.get('urun')} | miktar={fmt_amount(r.get('miktar'))} | ciro={fmt_amount(r.get('ciro'))}\n",
            )

        self.txt_kpi.insert(tk.END, "\nEn İyi 20 Müşteri\n")
        self.txt_kpi.insert(tk.END, "-" * 32 + "\n")
        for r in kpis.get("top_customers", []):
            self.txt_kpi.insert(
                tk.END,
                f"{r.get('cari_ad')} | net={fmt_amount(r.get('net'))}\n",
            )

    def _update_warnings(self, warnings: List[str]):
        self.txt_warn.delete("1.0", tk.END)
        if not warnings:
            self.txt_warn.insert(tk.END, "Uyarı bulunamadı.")
            return
        for w in warnings:
            self.txt_warn.insert(tk.END, f"• {w}\n")

    def _export_data(self) -> Tuple[str, List[str], List[List[Any]]]:
        rows: List[List[Any]] = []
        for r in self._current_rows:
            if self._report_key == "daily":
                rows.append([
                    fmt_tr_date(r.get("tarih")),
                    int(r.get("satis_adet") or 0),
                    int(r.get("iade_adet") or 0),
                    float(safe_float(r.get("ciro"))),
                    float(safe_float(r.get("iskonto"))),
                    float(safe_float(r.get("iade"))),
                    float(safe_float(r.get("ciro"))) - float(safe_float(r.get("iade"))),
                    float(safe_float(r.get("tahsilat"))),
                ])
            elif self._report_key == "customer":
                rows.append([
                    r.get("cari_ad"),
                    float(safe_float(r.get("satis"))),
                    float(safe_float(r.get("iade"))),
                    float(safe_float(r.get("iskonto"))),
                    float(safe_float(r.get("tahsilat"))),
                    float(safe_float(r.get("net"))),
                    float(safe_float(r.get("bakiye"))),
                ])
            elif self._report_key == "product":
                rows.append([
                    r.get("urun"),
                    r.get("kategori"),
                    float(safe_float(r.get("miktar"))),
                    float(safe_float(r.get("ciro"))),
                    float(safe_float(r.get("maliyet"))),
                    float(safe_float(r.get("kar"))),
                ])
            else:
                rows.append([
                    r.get("temsilci"),
                    float(safe_float(r.get("satis"))),
                    float(safe_float(r.get("iade"))),
                    float(safe_float(r.get("iskonto"))),
                    float(safe_float(r.get("tahsilat"))),
                    float(safe_float(r.get("net"))),
                    float(safe_float(r.get("bakiye"))),
                ])

        return self._current_title or "Satış Raporu", self._current_headers, rows

    def export_csv(self):
        if not self._current_rows:
            messagebox.showinfo(APP_TITLE, "Dışa aktarılacak veri yok.")
            return
        path = filedialog.asksaveasfilename(
            title="CSV Kaydet",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("All", "*.*")],
        )
        if not path:
            return

        title, headers, rows = self._export_data()
        try:
            import csv

            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([title])
                writer.writerow(headers)
                writer.writerows(rows)
            messagebox.showinfo(APP_TITLE, "CSV oluşturuldu.")
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"CSV oluşturulamadı: {exc}")

    def export_excel(self):
        if not self._current_rows:
            messagebox.showinfo(APP_TITLE, "Dışa aktarılacak veri yok.")
            return
        if not HAS_OPENPYXL:
            messagebox.showerror(APP_TITLE, "openpyxl kurulu değil. Kur: pip install openpyxl")
            return
        path = filedialog.asksaveasfilename(
            title="Excel Kaydet",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx"), ("All", "*.*")],
        )
        if not path:
            return
        title, headers, rows = self._export_data()
        try:
            self.app.services.exporter.export_sales_report_excel(title, headers, rows, path)
            messagebox.showinfo(APP_TITLE, "Excel oluşturuldu.")
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Excel oluşturulamadı: {exc}")

    def export_pdf(self):
        if not self._current_rows:
            messagebox.showinfo(APP_TITLE, "Dışa aktarılacak veri yok.")
            return
        if not HAS_REPORTLAB:
            messagebox.showerror(APP_TITLE, "PDF için reportlab yok. Kur: pip install reportlab")
            return
        path = filedialog.asksaveasfilename(
            title="PDF Kaydet",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf"), ("All", "*.*")],
        )
        if not path:
            return
        title, headers, rows = self._export_data()
        try:
            self.app.services.exporter.export_sales_report_pdf(title, headers, rows, path)
            messagebox.showinfo(APP_TITLE, "PDF oluşturuldu.")
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"PDF oluşturulamadı: {exc}")
