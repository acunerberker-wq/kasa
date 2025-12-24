# -*- coding: utf-8 -*-
"""Satın Alma İşlemleri Hareketleri raporu."""

from __future__ import annotations

import csv
import logging
import queue
import threading
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional, TYPE_CHECKING

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from ...config import APP_TITLE, HAS_OPENPYXL, HAS_REPORTLAB
from ...utils import fmt_amount, fmt_tr_date, safe_float
from ..widgets import LabeledCombo, LabeledEntry

if TYPE_CHECKING:
    from ...app import App

logger = logging.getLogger(__name__)


PERIOD_LABELS = {
    "Günlük": "gunluk",
    "Haftalık": "haftalik",
    "Aylık": "aylik",
}


class PurchaseReportFrame(ttk.Frame):
    def __init__(self, master, app: "App"):
        super().__init__(master)
        self.app = app
        self._report_queue: Optional["queue.Queue[tuple]"] = None
        self._report_running = False
        self._last_report: Optional[Dict[str, Any]] = None
        self._last_schedule_day: Optional[str] = None

        self.var_schedule = tk.BooleanVar(value=False)
        self.var_include_stock = tk.BooleanVar(value=True)

        self._build()
        self._load_settings()
        self.reload_filters()
        self.last30()
        self.after(120, lambda: self.run_report(auto=True))
        self.after(500, self._schedule_tick)

    # -----------------
    # UI
    # -----------------
    def _build(self):
        filters = ttk.LabelFrame(self, text="Filtreler")
        filters.pack(fill=tk.X, padx=10, pady=(10, 6))

        row1 = ttk.Frame(filters)
        row1.pack(fill=tk.X, pady=4)
        self.in_from = LabeledEntry(row1, "Başlangıç:", 12)
        self.in_from.pack(side=tk.LEFT, padx=6)
        self.in_to = LabeledEntry(row1, "Bitiş:", 12)
        self.in_to.pack(side=tk.LEFT, padx=6)
        self.in_period = LabeledCombo(row1, "Periyot:", list(PERIOD_LABELS.keys()), 12)
        self.in_period.pack(side=tk.LEFT, padx=6)
        self.in_period.set("Günlük")
        try:
            self.in_period.cmb.bind("<<ComboboxSelected>>", lambda _e: self._refresh_summary_only())
        except Exception:
            pass

        ttk.Button(row1, text="Son 30 gün", command=self.last30).pack(side=tk.LEFT, padx=6)
        ttk.Button(row1, text="Raporu Oluştur", command=self.run_report).pack(side=tk.LEFT, padx=6)

        row2 = ttk.Frame(filters)
        row2.pack(fill=tk.X, pady=4)
        self.in_supplier = LabeledCombo(row2, "Tedarikçi:", ["(Tümü)"], 26)
        self.in_supplier.pack(side=tk.LEFT, padx=6)
        self.in_supplier.set("(Tümü)")

        self.in_product = LabeledCombo(row2, "Ürün/Kalem:", ["(Tümü)"], 22)
        self.in_product.pack(side=tk.LEFT, padx=6)
        self.in_product.set("(Tümü)")

        self.in_category = LabeledCombo(row2, "Kategori:", ["(Tümü)"], 16)
        self.in_category.pack(side=tk.LEFT, padx=6)
        self.in_category.set("(Tümü)")

        row3 = ttk.Frame(filters)
        row3.pack(fill=tk.X, pady=4)
        self.in_payment = LabeledCombo(row3, "Ödeme Tipi:", ["(Tümü)"] + self.app.db.list_payments(), 16)
        self.in_payment.pack(side=tk.LEFT, padx=6)
        self.in_payment.set("(Tümü)")

        self.in_location = LabeledCombo(row3, "Depo:", ["(Tümü)"], 16)
        self.in_location.pack(side=tk.LEFT, padx=6)
        self.in_location.set("(Tümü)")

        self.in_user = LabeledCombo(row3, "Kullanıcı:", ["(Tümü)"], 16)
        self.in_user.pack(side=tk.LEFT, padx=6)
        self.in_user.set("(Tümü)")
        try:
            self.in_user.cmb.configure(state="disabled")
        except Exception:
            pass

        ttk.Checkbutton(row3, text="Stok girişlerini dahil et", variable=self.var_include_stock).pack(side=tk.LEFT, padx=6)

        row4 = ttk.Frame(filters)
        row4.pack(fill=tk.X, pady=(2, 6))
        ttk.Checkbutton(row4, text="Planlı Rapor (her gün 18:00)", variable=self.var_schedule, command=self._save_settings).pack(
            side=tk.LEFT, padx=6
        )
        self.lbl_schedule = ttk.Label(row4, text="")
        self.lbl_schedule.pack(side=tk.LEFT, padx=6)

        self.lbl_status = ttk.Label(filters, text="")
        self.lbl_status.pack(anchor="w", padx=8, pady=(4, 6))

        export = ttk.Frame(self)
        export.pack(fill=tk.X, padx=10, pady=(0, 6))
        ttk.Button(export, text="📄 CSV", command=self.export_csv).pack(side=tk.LEFT, padx=6)
        self.btn_excel = ttk.Button(export, text="📊 Excel", command=self.export_excel)
        self.btn_excel.pack(side=tk.LEFT, padx=6)
        self.btn_pdf = ttk.Button(export, text="🧾 PDF", command=self.export_pdf)
        self.btn_pdf.pack(side=tk.LEFT, padx=6)
        self.btn_pdf_print = ttk.Button(export, text="🖨️ Yazdırılabilir PDF", command=lambda: self.export_pdf(printable=True))
        self.btn_pdf_print.pack(side=tk.LEFT, padx=6)

        if not HAS_OPENPYXL:
            try:
                self.btn_excel.config(state="disabled")
            except Exception:
                pass
        if not HAS_REPORTLAB:
            try:
                self.btn_pdf.config(state="disabled")
                self.btn_pdf_print.config(state="disabled")
            except Exception:
                pass

        kpi = ttk.LabelFrame(self, text="KPI")
        kpi.pack(fill=tk.X, padx=10, pady=(0, 6))
        krow = ttk.Frame(kpi)
        krow.pack(fill=tk.X, padx=6, pady=6)

        self.lbl_total = ttk.Label(krow, text="Toplam Satın Alma: 0")
        self.lbl_total.pack(side=tk.LEFT, padx=8)
        self.lbl_kdv = ttk.Label(krow, text="KDV: 0")
        self.lbl_kdv.pack(side=tk.LEFT, padx=8)
        self.lbl_iskonto = ttk.Label(krow, text="İskonto: 0")
        self.lbl_iskonto.pack(side=tk.LEFT, padx=8)
        self.lbl_avg_cost = ttk.Label(krow, text="Ort. Birim Maliyet: 0")
        self.lbl_avg_cost.pack(side=tk.LEFT, padx=8)

        lists = ttk.Frame(self)
        lists.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 6))

        box_prod = ttk.LabelFrame(lists, text="En Çok Alınan 20 Ürün")
        box_prod.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        self.tree_products = ttk.Treeview(box_prod, columns=("urun", "qty", "total"), show="headings", height=6)
        for c in ("urun", "qty", "total"):
            self.tree_products.heading(c, text=c.upper())
        self.tree_products.column("urun", width=220)
        self.tree_products.column("qty", width=90, anchor="e")
        self.tree_products.column("total", width=120, anchor="e")
        self.tree_products.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        box_sup = ttk.LabelFrame(lists, text="En Çok Çalışılan 20 Tedarikçi")
        box_sup.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))
        self.tree_suppliers = ttk.Treeview(box_sup, columns=("tedarikci", "total"), show="headings", height=6)
        for c in ("tedarikci", "total"):
            self.tree_suppliers.heading(c, text=c.upper())
        self.tree_suppliers.column("tedarikci", width=220)
        self.tree_suppliers.column("total", width=120, anchor="e")
        self.tree_suppliers.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        summary = ttk.LabelFrame(self, text="Özet")
        summary.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 6))
        self.tree_summary = ttk.Treeview(
            summary,
            columns=("period", "alis", "iade", "gider", "odeme", "net"),
            show="headings",
            height=6,
        )
        for c in ("period", "alis", "iade", "gider", "odeme", "net"):
            self.tree_summary.heading(c, text=c.upper())
        self.tree_summary.column("period", width=110)
        self.tree_summary.column("alis", width=120, anchor="e")
        self.tree_summary.column("iade", width=120, anchor="e")
        self.tree_summary.column("gider", width=120, anchor="e")
        self.tree_summary.column("odeme", width=120, anchor="e")
        self.tree_summary.column("net", width=120, anchor="e")
        self.tree_summary.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        movements = ttk.LabelFrame(self, text="Hareketler")
        movements.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        cols = (
            "tarih",
            "hareket",
            "kaynak",
            "belge",
            "tedarikci",
            "urun",
            "kategori",
            "depo",
            "odeme",
            "miktar",
            "birim",
            "tutar",
            "kdv",
            "iskonto",
            "para",
        )
        self.tree_movements = ttk.Treeview(movements, columns=cols, show="headings", height=10)
        for c in cols:
            self.tree_movements.heading(c, text=c.upper())
        self.tree_movements.column("tarih", width=95)
        self.tree_movements.column("hareket", width=90)
        self.tree_movements.column("kaynak", width=80)
        self.tree_movements.column("belge", width=110)
        self.tree_movements.column("tedarikci", width=180)
        self.tree_movements.column("urun", width=180)
        self.tree_movements.column("kategori", width=120)
        self.tree_movements.column("depo", width=120)
        self.tree_movements.column("odeme", width=120)
        self.tree_movements.column("miktar", width=90, anchor="e")
        self.tree_movements.column("birim", width=70, anchor="center")
        self.tree_movements.column("tutar", width=110, anchor="e")
        self.tree_movements.column("kdv", width=90, anchor="e")
        self.tree_movements.column("iskonto", width=90, anchor="e")
        self.tree_movements.column("para", width=60, anchor="center")
        self.tree_movements.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

    def reload_settings(self):
        try:
            self.in_payment.cmb["values"] = ["(Tümü)"] + self.app.db.list_payments()
        except Exception:
            pass

    def reload_filters(self):
        try:
            suppliers = ["(Tümü)"]
            for r in self.app.db.purchase_report_suppliers():
                suppliers.append(f"{r['id']} - {r['ad']}")
            self.in_supplier.cmb["values"] = suppliers
        except Exception:
            pass

        try:
            products = ["(Tümü)"] + self.app.db.purchase_report_products()
            self.in_product.cmb["values"] = products
        except Exception:
            pass

        try:
            categories = ["(Tümü)"] + self.app.db.purchase_report_categories()
            self.in_category.cmb["values"] = categories
        except Exception:
            pass

        try:
            locations = ["(Tümü)"]
            for r in self.app.db.purchase_report_locations():
                locations.append(f"{r['id']} - {r['ad']}")
            self.in_location.cmb["values"] = locations
        except Exception:
            pass

        try:
            users = ["(Tümü)"]
            for r in self.app.db.purchase_report_users():
                users.append(f"{r['id']} - {r['username']}")
            self.in_user.cmb["values"] = users
        except Exception:
            pass

    def last30(self):
        d_to = date.today()
        d_from = d_to - timedelta(days=30)
        self.in_from.set(d_from.strftime("%d.%m.%Y"))
        self.in_to.set(d_to.strftime("%d.%m.%Y"))

    # -----------------
    # Report
    # -----------------
    def run_report(self, auto: bool = False):
        if self._report_running:
            return
        self._report_running = True
        self.lbl_status.config(text="Rapor hazırlanıyor…")

        filters = self._collect_filters()
        q: "queue.Queue[tuple]" = queue.Queue()
        self._report_queue = q

        def worker():
            try:
                data = self.app.db.purchase_report_fetch(**filters)
                q.put(("ok", data))
            except Exception as exc:
                logger.exception("Satın alma raporu oluşturulamadı")
                q.put(("err", exc))

        threading.Thread(target=worker, daemon=True).start()
        self.after(80, self._poll_queue)

    def _poll_queue(self):
        if not self._report_queue:
            return
        try:
            status, payload = self._report_queue.get_nowait()
        except queue.Empty:
            self.after(120, self._poll_queue)
            return

        self._report_running = False
        if status == "ok":
            self._apply_report(payload)
            self.lbl_status.config(text="Rapor hazır.")
        else:
            msg = str(payload)
            messagebox.showerror(APP_TITLE, "Rapor oluşturulamadı. Lütfen filtreleri kontrol edin.")
            self.lbl_status.config(text=f"Hata: {msg}")

    def _apply_report(self, data: Dict[str, Any]):
        self._last_report = data
        self._render_kpis(data.get("kpis") or {})
        self._render_products(data.get("kpis", {}).get("top_products") or [])
        self._render_suppliers(data.get("kpis", {}).get("top_suppliers") or [])
        self._render_summary(data.get("summary") or [])
        self._render_movements(data.get("movements") or [])

    def _render_kpis(self, kpis: Dict[str, Any]):
        total = safe_float(kpis.get("toplam"))
        kdv = safe_float(kpis.get("kdv"))
        iskonto = safe_float(kpis.get("iskonto"))
        avg = safe_float(kpis.get("avg_birim_maliyet"))
        qty = safe_float(kpis.get("qty"))
        self.lbl_total.config(text=f"Toplam Satın Alma: {fmt_amount(total)}")
        self.lbl_kdv.config(text=f"KDV: {fmt_amount(kdv)}")
        self.lbl_iskonto.config(text=f"İskonto: {fmt_amount(iskonto)}")
        self.lbl_avg_cost.config(text=f"Ort. Birim Maliyet: {fmt_amount(avg)} (adet={fmt_amount(qty)})")

    def _render_products(self, rows: List[Dict[str, Any]]):
        self.tree_products.delete(*self.tree_products.get_children())
        for r in rows:
            self.tree_products.insert(
                "",
                tk.END,
                values=(r.get("urun") or "", fmt_amount(safe_float(r.get("qty"))), fmt_amount(safe_float(r.get("total")))),
            )

    def _render_suppliers(self, rows: List[Dict[str, Any]]):
        self.tree_suppliers.delete(*self.tree_suppliers.get_children())
        for r in rows:
            self.tree_suppliers.insert(
                "",
                tk.END,
                values=(r.get("tedarikci") or "", fmt_amount(safe_float(r.get("total")))),
            )

    def _render_summary(self, rows: List[Dict[str, Any]]):
        self.tree_summary.delete(*self.tree_summary.get_children())
        period_label = PERIOD_LABELS.get(self.in_period.get(), "gunluk")
        filtered = [r for r in rows if r.get("period") == period_label]
        filtered.sort(key=lambda r: r.get("key") or "")
        for r in filtered:
            self.tree_summary.insert(
                "",
                tk.END,
                values=(
                    r.get("key") or "",
                    fmt_amount(safe_float(r.get("alis"))),
                    fmt_amount(safe_float(r.get("iade"))),
                    fmt_amount(safe_float(r.get("gider"))),
                    fmt_amount(safe_float(r.get("odeme"))),
                    fmt_amount(safe_float(r.get("net"))),
                ),
            )

    def _render_movements(self, rows: List[Dict[str, Any]]):
        self.tree_movements.delete(*self.tree_movements.get_children())
        for r in rows:
            self.tree_movements.insert(
                "",
                tk.END,
                values=(
                    fmt_tr_date(r.get("tarih") or ""),
                    r.get("hareket") or "",
                    r.get("kaynak") or "",
                    r.get("belge") or "",
                    r.get("tedarikci") or "",
                    r.get("urun") or "",
                    r.get("kategori") or "",
                    r.get("depo") or "",
                    r.get("odeme") or "",
                    fmt_amount(safe_float(r.get("miktar"))),
                    r.get("birim") or "",
                    fmt_amount(safe_float(r.get("tutar"))),
                    fmt_amount(safe_float(r.get("kdv"))),
                    fmt_amount(safe_float(r.get("iskonto"))),
                    r.get("para") or "",
                ),
            )

    def _refresh_summary_only(self):
        if self._last_report:
            self._render_summary(self._last_report.get("summary") or [])

    def _collect_filters(self) -> Dict[str, Any]:
        supplier_id = self._parse_id(self.in_supplier.get())
        location_id = self._parse_id(self.in_location.get())
        product = self.in_product.get()
        category = self.in_category.get()
        payment = self.in_payment.get()

        return {
            "date_from": self.in_from.get(),
            "date_to": self.in_to.get(),
            "supplier_id": supplier_id,
            "product_name": "" if product == "(Tümü)" else product,
            "category": "" if category == "(Tümü)" else category,
            "payment_type": "" if payment == "(Tümü)" else payment,
            "location_id": location_id,
            "include_stock_entries": bool(self.var_include_stock.get()),
        }

    def _parse_id(self, value: str) -> Optional[int]:
        if not value or value == "(Tümü)":
            return None
        if " - " in value:
            try:
                return int(value.split(" - ", 1)[0])
            except Exception:
                return None
        return None

    # -----------------
    # Export
    # -----------------
    def export_csv(self):
        if not self._last_report:
            messagebox.showinfo(APP_TITLE, "Önce rapor oluşturun.")
            return
        p = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            title="Satın Alma Raporu CSV Kaydet",
        )
        if not p:
            return
        try:
            rows = self._last_report.get("movements") or []
            with open(p, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "tarih",
                        "hareket",
                        "kaynak",
                        "belge",
                        "tedarikci",
                        "urun",
                        "kategori",
                        "depo",
                        "odeme",
                        "miktar",
                        "birim",
                        "tutar",
                        "kdv",
                        "iskonto",
                        "para",
                    ]
                )
                for r in rows:
                    writer.writerow(
                        [
                            r.get("tarih"),
                            r.get("hareket"),
                            r.get("kaynak"),
                            r.get("belge"),
                            r.get("tedarikci"),
                            r.get("urun"),
                            r.get("kategori"),
                            r.get("depo"),
                            r.get("odeme"),
                            r.get("miktar"),
                            r.get("birim"),
                            r.get("tutar"),
                            r.get("kdv"),
                            r.get("iskonto"),
                            r.get("para"),
                        ]
                    )
            messagebox.showinfo(APP_TITLE, f"CSV kaydedildi:\n{p}")
        except Exception as exc:
            logger.exception("CSV export başarısız")
            messagebox.showerror(APP_TITLE, f"CSV export hatası: {exc}")

    def export_excel(self):
        if not self._last_report:
            messagebox.showinfo(APP_TITLE, "Önce rapor oluşturun.")
            return
        if not HAS_OPENPYXL:
            messagebox.showerror(APP_TITLE, "openpyxl kurulu değil. Kur: pip install openpyxl")
            return
        p = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            title="Satın Alma Raporu Excel Kaydet",
        )
        if not p:
            return
        try:
            self.app.services.exporter.export_purchase_report_excel(self._last_report, p)
            messagebox.showinfo(APP_TITLE, f"Excel kaydedildi:\n{p}")
        except Exception as exc:
            logger.exception("Excel export başarısız")
            messagebox.showerror(APP_TITLE, f"Excel export hatası: {exc}")

    def export_pdf(self, printable: bool = False):
        if not self._last_report:
            messagebox.showinfo(APP_TITLE, "Önce rapor oluşturun.")
            return
        if not HAS_REPORTLAB:
            messagebox.showerror(APP_TITLE, "reportlab kurulu değil. Kur: pip install reportlab")
            return
        p = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            title="Satın Alma Raporu PDF Kaydet",
        )
        if not p:
            return
        try:
            self.app.services.exporter.export_purchase_report_pdf(self._last_report, p, printable=printable)
            messagebox.showinfo(APP_TITLE, f"PDF kaydedildi:\n{p}")
        except Exception as exc:
            logger.exception("PDF export başarısız")
            messagebox.showerror(APP_TITLE, f"PDF export hatası: {exc}")

    # -----------------
    # Planlı rapor
    # -----------------
    def _load_settings(self):
        try:
            enabled = self.app.db.get_setting("purchase_report_schedule_enabled")
            self.var_schedule.set(enabled == "1")
        except Exception:
            pass
        try:
            self._last_schedule_day = self.app.db.get_setting("purchase_report_last_run") or None
            if self._last_schedule_day:
                self.lbl_schedule.config(text=f"Son planlı rapor: {self._last_schedule_day}")
        except Exception:
            self._last_schedule_day = None

    def _save_settings(self):
        try:
            self.app.db.set_setting("purchase_report_schedule_enabled", "1" if self.var_schedule.get() else "0")
        except Exception:
            pass

    def _schedule_tick(self):
        try:
            if self.var_schedule.get():
                now = datetime.now()
                target = datetime.combine(now.date(), time(hour=18, minute=0))
                if now >= target:
                    today_key = now.date().isoformat()
                    if self._last_schedule_day != today_key:
                        self._last_schedule_day = today_key
                        try:
                            self.app.db.set_setting("purchase_report_last_run", today_key)
                        except Exception:
                            pass
                        self.run_report(auto=True)
                        self.lbl_schedule.config(text=f"Son planlı rapor: {today_key}")
        except Exception as exc:
            logger.exception("Planlı rapor tetiklenemedi")
            self.lbl_schedule.config(text=f"Planlı rapor hatası: {exc}")
        finally:
            self.after(60000, self._schedule_tick)
