# -*- coding: utf-8 -*-
"""UI Plugin: Satış Sipariş Raporları."""

from __future__ import annotations

from datetime import date, timedelta
import queue
import threading
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from ...config import APP_TITLE, HAS_OPENPYXL
from ...db.main_db import DB
from ...utils import fmt_amount, fmt_tr_date, safe_float
from ..base import BaseView
from ..widgets import LabeledEntry, LabeledCombo

if TYPE_CHECKING:
    from ...app import App

PLUGIN_META = {
    "key": "satis_siparis_rapor",
    "nav_text": "🧾 Satış Siparişleri",
    "page_title": "Satış Sipariş Raporları",
    "order": 24,
}

STATUSES = ["Açık", "Hazırlanıyor", "Kısmi Sevk", "Sevk Edildi", "Faturalandı", "İptal"]
OPEN_STATUSES = ["Açık", "Hazırlanıyor", "Kısmi Sevk"]


def build(master, app: "App") -> ttk.Frame:
    return SatisSiparisRaporFrame(master, app)


class SatisSiparisRaporFrame(BaseView):
    def __init__(self, master, app: "App"):
        self.app = app
        super().__init__(master, app)
        self.company_map: Dict[str, int] = {}
        self.depo_map: Dict[str, Optional[int]] = {}
        self._report_data: Dict[str, Dict[str, Any]] = {}
        self._running = False
        self.build_ui()

    def build_ui(self) -> None:
        self._build()

    def _build(self):
        filters = ttk.LabelFrame(self, text="Filtreler")
        filters.pack(fill=tk.X, padx=10, pady=10)

        row1 = ttk.Frame(filters)
        row1.pack(fill=tk.X, pady=6)
        self.f_customer = LabeledEntry(row1, "Müşteri:", 24)
        self.f_customer.pack(side=tk.LEFT, padx=6)
        self.f_rep = LabeledEntry(row1, "Temsilci:", 18)
        self.f_rep.pack(side=tk.LEFT, padx=6)
        self.f_status = LabeledCombo(row1, "Durum:", ["(Tümü)"] + STATUSES, 16)
        self.f_status.pack(side=tk.LEFT, padx=6)
        self.f_status.set("(Tümü)")
        self.f_depo = LabeledCombo(row1, "Depo:", ["(Tümü)"], 18)
        self.f_depo.pack(side=tk.LEFT, padx=6)

        row2 = ttk.Frame(filters)
        row2.pack(fill=tk.X, pady=6)
        self.f_from = LabeledEntry(row2, "Başlangıç:", 12)
        self.f_from.pack(side=tk.LEFT, padx=6)
        self.f_to = LabeledEntry(row2, "Bitiş:", 12)
        self.f_to.pack(side=tk.LEFT, padx=6)
        self.f_company = LabeledCombo(row2, "Şirket:", ["(Aktif)"], 22)
        self.f_company.pack(side=tk.LEFT, padx=6)

        btns = ttk.Frame(row2)
        btns.pack(side=tk.RIGHT)
        self.btn_refresh = ttk.Button(btns, text="Yenile", command=self.run_active_report)
        self.btn_refresh.pack(side=tk.LEFT, padx=4)
        self.btn_csv = ttk.Button(btns, text="CSV", command=self.export_csv)
        self.btn_csv.pack(side=tk.LEFT, padx=4)
        self.btn_excel = ttk.Button(btns, text="Excel", command=self.export_excel)
        self.btn_excel.pack(side=tk.LEFT, padx=4)
        if not HAS_OPENPYXL:
            try:
                self.btn_excel.config(state="disabled")
            except Exception:
                pass

        self.lbl_status = ttk.Label(filters, text="")
        self.lbl_status.pack(anchor="w", padx=10, pady=(0, 6))

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.tab_open = ttk.Frame(self.nb)
        self.tab_ready = ttk.Frame(self.nb)
        self.tab_partial = ttk.Frame(self.nb)
        self.tab_conv = ttk.Frame(self.nb)

        self.nb.add(self.tab_open, text="Açık Siparişler")
        self.nb.add(self.tab_ready, text="Sevkiyata Hazır")
        self.nb.add(self.tab_partial, text="Kısmi Sevk")
        self.nb.add(self.tab_conv, text="Dönüşüm")

        self.tree_open = self._build_tree(self.tab_open, ("cari", "adet", "toplam"))
        self.tree_ready = self._build_tree(
            self.tab_ready,
            ("siparis_no", "tarih", "cari", "temsilci", "depo", "durum", "kalan", "para", "toplam", "stok_durum"),
        )
        self.tree_partial = self._build_tree(
            self.tab_partial,
            ("siparis_no", "tarih", "cari", "urun", "miktar", "sevk", "kalan", "birim", "durum"),
        )
        self.tree_conv = self._build_tree(
            self.tab_conv,
            ("siparis_no", "tarih", "cari", "temsilci", "depo", "durum", "sevk_no", "sevk_tarih", "fatura_no", "fatura_tarih", "para", "toplam"),
        )

        self._configure_tree_columns()
        self.reload_filters()
        self.last30()

        try:
            self.nb.bind("<<NotebookTabChanged>>", lambda _e: self.run_active_report())
        except Exception:
            pass

    def _build_tree(self, parent: ttk.Frame, cols: Tuple[str, ...]) -> ttk.Treeview:
        tree = ttk.Treeview(parent, columns=cols, show="headings", height=18)
        for c in cols:
            tree.heading(c, text=c.upper())
            tree.column(c, anchor="w")
        tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        scr = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        scr.place(in_=tree, relx=1.0, rely=0, relheight=1.0, x=0)
        tree.configure(yscrollcommand=scr.set)
        return tree

    def _configure_tree_columns(self) -> None:
        self.tree_open.column("cari", width=260)
        self.tree_open.column("adet", width=70, anchor="center")
        self.tree_open.column("toplam", width=140, anchor="e")

        for tree in (self.tree_ready, self.tree_conv):
            tree.column("siparis_no", width=120)
            tree.column("tarih", width=95)
            tree.column("cari", width=220)
            tree.column("temsilci", width=120)
            tree.column("depo", width=120)
            tree.column("durum", width=110)
            tree.column("para", width=55, anchor="center")
            tree.column("toplam", width=120, anchor="e")

        self.tree_ready.column("kalan", width=90, anchor="e")
        self.tree_ready.column("stok_durum", width=120, anchor="center")

        self.tree_partial.column("siparis_no", width=120)
        self.tree_partial.column("tarih", width=95)
        self.tree_partial.column("cari", width=220)
        self.tree_partial.column("urun", width=220)
        self.tree_partial.column("miktar", width=90, anchor="e")
        self.tree_partial.column("sevk", width=90, anchor="e")
        self.tree_partial.column("kalan", width=90, anchor="e")
        self.tree_partial.column("birim", width=70, anchor="center")
        self.tree_partial.column("durum", width=110, anchor="center")

        self.tree_conv.column("sevk_no", width=120)
        self.tree_conv.column("sevk_tarih", width=95)
        self.tree_conv.column("fatura_no", width=120)
        self.tree_conv.column("fatura_tarih", width=95)

    def reload_filters(self) -> None:
        self._load_companies()
        self._load_depos()

    def last30(self):
        d_to = date.today()
        d_from = d_to - timedelta(days=30)
        self.f_from.set(d_from.strftime("%d.%m.%Y"))
        self.f_to.set(d_to.strftime("%d.%m.%Y"))

    def _load_companies(self) -> None:
        self.company_map.clear()
        try:
            urow = self.app.get_active_user_row()
            uid = int(urow["id"]) if urow else None
        except Exception:
            uid = None
        companies = []
        if uid:
            companies = self.app.usersdb.list_companies(uid)
        values = []
        active_name = getattr(self.app, "active_company_name", "") or ""
        for c in companies:
            name = str(c["name"])
            values.append(name)
            try:
                self.company_map[name] = int(c["id"])
            except Exception:
                continue
        if not values and active_name:
            values = [active_name]
        try:
            self.f_company.cmb.configure(values=values)
        except Exception:
            pass
        if active_name and active_name in values:
            self.f_company.set(active_name)
        elif values:
            self.f_company.set(values[0])

    def _load_depos(self) -> None:
        self.depo_map = {"(Tümü)": None}
        values = ["(Tümü)"]
        try:
            rows = self.app.db.stok_lokasyon_list(only_active=True)
        except Exception:
            rows = []
        for r in rows:
            name = str(r["ad"])
            values.append(name)
            try:
                self.depo_map[name] = int(r["id"])
            except Exception:
                self.depo_map[name] = None
        try:
            self.f_depo.cmb.configure(values=values)
        except Exception:
            pass
        self.f_depo.set("(Tümü)")

    def _filters_payload(self) -> Dict[str, Any]:
        depo_name = self.f_depo.get()
        depot_id = self.depo_map.get(depo_name)
        return {
            "customer": (self.f_customer.get() or "").strip(),
            "representative": (self.f_rep.get() or "").strip(),
            "depot_id": depot_id,
            "status": self.f_status.get(),
            "date_from": self.f_from.get(),
            "date_to": self.f_to.get(),
        }

    def _selected_company_db_path(self) -> str:
        name = self.f_company.get()
        cid = self.company_map.get(name)
        if cid:
            c = self.app.usersdb.get_company_by_id(int(cid))
            if c:
                return self.app.usersdb.get_company_db_path(c)
        return self.app.db.path

    def run_active_report(self) -> None:
        tab = self.nb.select()
        key = {
            str(self.tab_open): "open",
            str(self.tab_ready): "ready",
            str(self.tab_partial): "partial",
            str(self.tab_conv): "conversion",
        }.get(str(tab), "open")
        self._run_report(key)

    def _set_status(self, text: str) -> None:
        try:
            self.lbl_status.config(text=text)
        except Exception:
            pass

    def _run_report(self, key: str) -> None:
        if self._running:
            return
        filters = self._filters_payload()
        db_path = self._selected_company_db_path()
        self._running = True
        self._set_status("Rapor hazırlanıyor...")
        try:
            self.btn_refresh.config(state="disabled")
        except Exception:
            pass
        q: "queue.Queue[tuple]" = queue.Queue()

        def worker():
            try:
                db = DB(db_path)
                # Tabloları kontrol et
                cursor = db.conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('satis_siparis', 'satis_siparis_kalem')"
                )
                tables = [row[0] for row in cursor.fetchall()]
                if 'satis_siparis' not in tables or 'satis_siparis_kalem' not in tables:
                    db.close()
                    q.put(("warn", "Satış sipariş tabloları henüz oluşturulmamış. Lütfen önce satış siparişi oluşturun."))
                    return
                
                if key == "open":
                    data = db.satis_siparis_rapor_acik(filters, OPEN_STATUSES)
                elif key == "ready":
                    data = db.satis_siparis_rapor_sevkiyata_hazir(filters, OPEN_STATUSES)
                elif key == "partial":
                    data = db.satis_siparis_rapor_kismi_sevk(filters)
                else:
                    data = db.satis_siparis_rapor_donusum(filters)
                db.close()
                q.put(("ok", data))
            except AttributeError as exc:
                if "satis_siparis" in str(exc).lower():
                    q.put(("warn", "Satış sipariş fonksiyonları henüz etkin değil. Lütfen önce satış siparişi oluşturun."))
                else:
                    q.put(("err", exc))
            except Exception as exc:
                q.put(("err", exc))

        threading.Thread(target=worker, daemon=True).start()

        def poll():
            try:
                status, payload = q.get_nowait()
            except queue.Empty:
                self.after(80, poll)
                return
            self._running = False
            try:
                self.btn_refresh.config(state="normal")
            except Exception:
                pass
            if status == "err":
                messagebox.showerror(APP_TITLE, f"Rapor oluşturulamadı: {payload}")
                self._set_status("Rapor hatası.")
                return
            elif status == "warn":
                messagebox.showwarning(APP_TITLE, str(payload))
                self._set_status("Rapor yok.")
                return
            self._render_report(key, payload)

        self.after(60, poll)

    def _clear_tree(self, tree: ttk.Treeview) -> None:
        for item in tree.get_children():
            tree.delete(item)

    def _render_report(self, key: str, data: Dict[str, Any]) -> None:
        self._report_data[key] = data
        if key == "open":
            self._render_open(data)
        elif key == "ready":
            self._render_ready(data)
        elif key == "partial":
            self._render_partial(data)
        else:
            self._render_conversion(data)

    def _render_open(self, data: Dict[str, Any]) -> None:
        self._clear_tree(self.tree_open)
        rows = []
        for r in data.get("rows", []):
            rows.append((r["cari"], r["adet"], fmt_amount(r["toplam"])))
            self.tree_open.insert("", tk.END, values=rows[-1])
        total = fmt_amount(data.get("total", 0.0))
        self._set_status(f"Açık sipariş müşteri: {len(rows)} • Toplam: {total}")

    def _render_ready(self, data: Dict[str, Any]) -> None:
        self._clear_tree(self.tree_ready)
        rows = []
        for r in data.get("rows", []):
            rows.append((
                r["siparis_no"],
                fmt_tr_date(r["tarih"]),
                r["cari"],
                r["temsilci"],
                r["depo"],
                r["durum"],
                fmt_amount(r["kalan"]),
                r["para"],
                fmt_amount(r["toplam"]),
                r["stok_durum"],
            ))
            self.tree_ready.insert("", tk.END, values=rows[-1])
        self._set_status(f"Sevkiyata hazır sipariş: {data.get('order_count', 0)}")

    def _render_partial(self, data: Dict[str, Any]) -> None:
        self._clear_tree(self.tree_partial)
        rows = []
        for r in data.get("rows", []):
            rows.append((
                r["siparis_no"],
                fmt_tr_date(r["tarih"]),
                r["cari"],
                r["urun"],
                fmt_amount(r["miktar"]),
                fmt_amount(r["sevk"]),
                fmt_amount(r["kalan"]),
                r["birim"],
                r["durum"],
            ))
            self.tree_partial.insert("", tk.END, values=rows[-1])
        self._set_status(f"Kısmi sevk kalem: {data.get('order_count', 0)}")

    def _render_conversion(self, data: Dict[str, Any]) -> None:
        self._clear_tree(self.tree_conv)
        rows = []
        for r in data.get("rows", []):
            rows.append((
                r["siparis_no"],
                fmt_tr_date(r["tarih"]),
                r["cari"],
                r["temsilci"],
                r["depo"],
                r["durum"],
                r["sevk_no"],
                fmt_tr_date(r["sevk_tarih"]) if r["sevk_tarih"] else "",
                r["fatura_no"],
                fmt_tr_date(r["fatura_tarih"]) if r["fatura_tarih"] else "",
                r["para"],
                fmt_amount(r["toplam"]),
            ))
            self.tree_conv.insert("", tk.END, values=rows[-1])
        self._set_status(f"Dönüşüm kayıt: {data.get('order_count', 0)}")

    def _export_payload(self) -> Optional[Tuple[List[str], List[List[Any]]]]:
        tab = self.nb.select()
        key = {
            str(self.tab_open): "open",
            str(self.tab_ready): "ready",
            str(self.tab_partial): "partial",
            str(self.tab_conv): "conversion",
        }.get(str(tab), "open")
        data = self._report_data.get(key)
        if not data:
            return None
        if key == "open":
            headers = ["Müşteri", "Adet", "Toplam"]
            rows = [[r["cari"], r["adet"], safe_float(r["toplam"])] for r in data.get("rows", [])]
        elif key == "ready":
            headers = ["Sipariş No", "Tarih", "Cari", "Temsilci", "Depo", "Durum", "Kalan", "Para", "Toplam", "Stok Durum"]
            rows = [[
                r["siparis_no"],
                r["tarih"],
                r["cari"],
                r["temsilci"],
                r["depo"],
                r["durum"],
                safe_float(r["kalan"]),
                r["para"],
                safe_float(r["toplam"]),
                r["stok_durum"],
            ] for r in data.get("rows", [])]
        elif key == "partial":
            headers = ["Sipariş No", "Tarih", "Cari", "Ürün", "Miktar", "Sevk", "Kalan", "Birim", "Durum"]
            rows = [[
                r["siparis_no"],
                r["tarih"],
                r["cari"],
                r["urun"],
                safe_float(r["miktar"]),
                safe_float(r["sevk"]),
                safe_float(r["kalan"]),
                r["birim"],
                r["durum"],
            ] for r in data.get("rows", [])]
        else:
            headers = ["Sipariş No", "Tarih", "Cari", "Temsilci", "Depo", "Durum", "Sevk No", "Sevk Tarih", "Fatura No", "Fatura Tarih", "Para", "Toplam"]
            rows = [[
                r["siparis_no"],
                r["tarih"],
                r["cari"],
                r["temsilci"],
                r["depo"],
                r["durum"],
                r["sevk_no"],
                r["sevk_tarih"],
                r["fatura_no"],
                r["fatura_tarih"],
                r["para"],
                safe_float(r["toplam"]),
            ] for r in data.get("rows", [])]
        return headers, rows

    def export_csv(self) -> None:
        payload = self._export_payload()
        if not payload:
            messagebox.showinfo(APP_TITLE, "Önce raporu oluşturun.")
            return
        headers, rows = payload
        path = filedialog.asksaveasfilename(
            title="CSV Kaydet",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
        )
        if not path:
            return
        try:
            self.app.services.exporter.export_table_csv(headers, rows, path)
            messagebox.showinfo(APP_TITLE, "CSV oluşturuldu.")
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"CSV yazılamadı: {exc}")

    def export_excel(self) -> None:
        if not HAS_OPENPYXL:
            messagebox.showerror(APP_TITLE, "Excel için openpyxl yok.")
            return
        payload = self._export_payload()
        if not payload:
            messagebox.showinfo(APP_TITLE, "Önce raporu oluşturun.")
            return
        headers, rows = payload
        path = filedialog.asksaveasfilename(
            title="Excel Kaydet",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
        )
        if not path:
            return
        try:
            self.app.services.exporter.export_table_excel(headers, rows, path)
            messagebox.showinfo(APP_TITLE, "Excel oluşturuldu.")
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Excel yazılamadı: {exc}")

    def refresh(self, data=None):
        self.reload_filters()
        self.run_active_report()
