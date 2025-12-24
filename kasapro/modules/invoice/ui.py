# -*- coding: utf-8 -*-
"""UI for the advanced invoice module."""

from __future__ import annotations

import logging
import os
import queue
import threading
from datetime import date
from typing import Any, Dict, List, Optional

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from ...config import APP_TITLE
from ...utils import fmt_amount, fmt_tr_date, parse_date_smart
from .calculator import calculate_totals
from .export import export_csv, export_pdf
from .security import can_create_document, can_manage_payments, can_void_document

logger = logging.getLogger(__name__)

STATUS_OPTIONS = ["DRAFT", "POSTED", "VOID"]


def _today_str() -> str:
    try:
        return date.today().strftime("%d.%m.%Y")
    except Exception:
        return ""


class InvoiceModuleFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.repo = app.db.invoice_adv
        self.company_id = int(getattr(app, "active_company_id", None) or 1)
        self._build()

    def _build(self) -> None:
        header = ttk.Frame(self)
        header.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(header, text="Gelişmiş Fatura Sistemi", style="TopTitle.TLabel").pack(side=tk.LEFT)

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.tabs: Dict[str, InvoiceListTab] = {}
        for key, title, doc_type in (
            ("sales", "Satış Faturası", "sales"),
            ("purchase", "Alış Faturası", "purchase"),
            ("returns", "İade İşlemleri", None),
            ("payments", "Tahsilat / Ödeme", "payments"),
        ):
            tab = ttk.Frame(self.nb)
            self.nb.add(tab, text=title)
            if key == "payments":
                frame = PaymentsTab(tab, self.app, self.repo, self.company_id)
            else:
                frame = InvoiceListTab(tab, self.app, self.repo, self.company_id, doc_type=doc_type)
            frame.pack(fill=tk.BOTH, expand=True)
            self.tabs[key] = frame

    def refresh(self) -> None:
        for tab in self.tabs.values():
            tab.refresh()


class InvoiceListTab(ttk.Frame):
    def __init__(self, master, app, repo, company_id: int, doc_type: Optional[str]):
        super().__init__(master)
        self.app = app
        self.repo = repo
        self.company_id = company_id
        self.doc_type = doc_type
        self.page = 0
        self.limit = 20
        self.customer_map: Dict[str, int] = {}
        self._build()
        self.refresh()

    def _build(self) -> None:
        filters = ttk.LabelFrame(self, text="Filtre")
        filters.pack(fill=tk.X, padx=6, pady=6)

        row = ttk.Frame(filters)
        row.pack(fill=tk.X, pady=4)

        ttk.Label(row, text="Ara:").pack(side=tk.LEFT)
        self.q_entry = ttk.Entry(row, width=20)
        self.q_entry.pack(side=tk.LEFT, padx=4)

        ttk.Label(row, text="Durum:").pack(side=tk.LEFT, padx=(10, 2))
        self.status_combo = ttk.Combobox(row, values=[""] + STATUS_OPTIONS, width=10)
        self.status_combo.pack(side=tk.LEFT)

        ttk.Label(row, text="Başlangıç:").pack(side=tk.LEFT, padx=(10, 2))
        self.date_from_entry = ttk.Entry(row, width=12)
        self.date_from_entry.pack(side=tk.LEFT)

        ttk.Label(row, text="Bitiş:").pack(side=tk.LEFT, padx=(10, 2))
        self.date_to_entry = ttk.Entry(row, width=12)
        self.date_to_entry.pack(side=tk.LEFT)

        ttk.Label(row, text="Cari:").pack(side=tk.LEFT, padx=(10, 2))
        self.customer_combo = ttk.Combobox(row, values=[], width=24)
        self.customer_combo.pack(side=tk.LEFT)

        ttk.Button(row, text="Yenile", command=self.refresh).pack(side=tk.LEFT, padx=6)

        if self.doc_type is None:
            ttk.Label(row, text="İade Türü:").pack(side=tk.LEFT, padx=(10, 2))
            self.return_combo = ttk.Combobox(row, values=["", "sales_return", "purchase_return"], width=14)
            self.return_combo.pack(side=tk.LEFT)
        else:
            self.return_combo = None

        action_row = ttk.Frame(self)
        action_row.pack(fill=tk.X, padx=6, pady=(2, 6))

        ttk.Button(action_row, text="Yeni", command=self._new_doc).pack(side=tk.LEFT)
        ttk.Button(action_row, text="Detay", command=self._open_selected).pack(side=tk.LEFT, padx=4)
        ttk.Button(action_row, text="İptal", command=self._void_selected).pack(side=tk.LEFT, padx=4)

        cols = ("id", "doc_no", "doc_date", "customer", "status", "total", "remaining")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=14)
        for col in cols:
            self.tree.heading(col, text=col.upper())
        self.tree.column("id", width=60, anchor="center")
        self.tree.column("doc_no", width=150)
        self.tree.column("doc_date", width=90)
        self.tree.column("customer", width=220)
        self.tree.column("status", width=90, anchor="center")
        self.tree.column("total", width=120, anchor="e")
        self.tree.column("remaining", width=120, anchor="e")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=6)

        pager = ttk.Frame(self)
        pager.pack(fill=tk.X, padx=6, pady=6)
        ttk.Button(pager, text="◀", command=self._prev_page).pack(side=tk.LEFT)
        ttk.Button(pager, text="▶", command=self._next_page).pack(side=tk.LEFT, padx=4)
        self.page_label = ttk.Label(pager, text="Sayfa 1")
        self.page_label.pack(side=tk.LEFT, padx=6)

        try:
            self.tree.bind("<Double-1>", lambda _e: self._open_selected())
        except Exception:
            pass

    def _load_customers(self) -> None:
        try:
            rows = self.app.db.cari_list(q="")
            self.customer_map = {str(r["ad"]): int(r["id"]) for r in rows}
            self.customer_combo["values"] = [""] + list(self.customer_map.keys())
        except Exception:
            logger.exception("Failed to load customers")

    def _selected_doc_id(self) -> Optional[int]:
        sel = self.tree.selection()
        if not sel:
            return None
        try:
            return int(self.tree.item(sel[0], "values")[0])
        except Exception:
            return None

    def _new_doc(self) -> None:
        if not can_create_document(self.app.user["role"]):
            messagebox.showwarning(APP_TITLE, "Yetkiniz yok")
            return
        doc_type = self.doc_type
        if doc_type is None and self.return_combo:
            doc_type = self.return_combo.get() or "sales_return"
        InvoiceEditorWindow(self, self.app, self.repo, self.company_id, doc_type, on_saved=self.refresh)

    def _void_selected(self) -> None:
        if not can_void_document(self.app.user["role"]):
            messagebox.showwarning(APP_TITLE, "İptal için yetkiniz yok")
            return
        doc_id = self._selected_doc_id()
        if not doc_id:
            return
        if not messagebox.askyesno(APP_TITLE, "Faturayı iptal etmek istiyor musunuz?"):
            return
        try:
            self.repo.void_doc(doc_id, user_id=self.app.data_owner_user_id, username=self.app.data_owner_username)
            self.refresh()
        except Exception as exc:
            logger.exception("Void failed")
            messagebox.showerror(APP_TITLE, f"İptal sırasında hata: {exc}")

    def _open_selected(self) -> None:
        doc_id = self._selected_doc_id()
        if not doc_id:
            return
        InvoiceDetailWindow(self, self.app, self.repo, doc_id)

    def _prev_page(self) -> None:
        if self.page > 0:
            self.page -= 1
            self.refresh()

    def _next_page(self) -> None:
        self.page += 1
        self.refresh()

    def refresh(self) -> None:
        self._load_customers()
        try:
            query = self.q_entry.get().strip()
            status = self.status_combo.get().strip() or None
            date_from = self.date_from_entry.get().strip()
            date_to = self.date_to_entry.get().strip()
            customer_name = self.customer_combo.get().strip()
            customer_id = self.customer_map.get(customer_name) if customer_name else None
            doc_type = self.doc_type
            if doc_type is None and self.return_combo:
                doc_type = self.return_combo.get().strip() or None

            rows, total = self.repo.list_docs(
                company_id=self.company_id,
                doc_type=doc_type,
                status=status,
                query=query,
                date_from=date_from,
                date_to=date_to,
                customer_id=customer_id,
                limit=self.limit,
                offset=self.page * self.limit,
            )
            for item in self.tree.get_children():
                self.tree.delete(item)
            for r in rows:
                self.tree.insert(
                    "",
                    tk.END,
                    values=(
                        r["id"],
                        r["doc_no"],
                        fmt_tr_date(r["doc_date"]),
                        r["customer_name"],
                        r["status"],
                        fmt_amount(r["grand_total"]),
                        fmt_amount(r["remaining"]),
                    ),
                )
            page_count = max(1, (total + self.limit - 1) // self.limit)
            self.page = min(self.page, page_count - 1)
            self.page_label.configure(text=f"Sayfa {self.page + 1} / {page_count}")
        except Exception as exc:
            logger.exception("Failed to refresh list")
            messagebox.showerror(APP_TITLE, f"Liste yüklenemedi: {exc}")


class InvoiceEditorWindow(tk.Toplevel):
    def __init__(self, master, app, repo, company_id: int, doc_type: str, on_saved=None):
        super().__init__(master)
        self.app = app
        self.repo = repo
        self.company_id = company_id
        self.doc_type = doc_type
        self.on_saved = on_saved
        self.lines: List[Dict[str, Any]] = []
        self.customer_map: Dict[str, int] = {}
        self.title("Fatura Oluştur")
        self.geometry("860x620")
        self._build()

    def _build(self) -> None:
        form = ttk.Frame(self)
        form.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(form, text=f"Tür: {self.doc_type}").grid(row=0, column=0, sticky="w")
        ttk.Label(form, text="Tarih").grid(row=0, column=1, sticky="w")
        self.date_entry = ttk.Entry(form, width=12)
        self.date_entry.grid(row=0, column=2, sticky="w")
        self.date_entry.insert(0, _today_str())

        ttk.Label(form, text="Vade").grid(row=0, column=3, sticky="w")
        self.due_entry = ttk.Entry(form, width=12)
        self.due_entry.grid(row=0, column=4, sticky="w")

        ttk.Label(form, text="Seri").grid(row=1, column=0, sticky="w")
        self.series_entry = ttk.Entry(form, width=8)
        self.series_entry.grid(row=1, column=1, sticky="w")
        self.series_entry.insert(0, "A")

        ttk.Label(form, text="Cari").grid(row=1, column=2, sticky="w")
        self.customer_combo = ttk.Combobox(form, width=28)
        self.customer_combo.grid(row=1, column=3, columnspan=2, sticky="w")

        ttk.Label(form, text="Para").grid(row=2, column=0, sticky="w")
        self.currency_entry = ttk.Entry(form, width=8)
        self.currency_entry.grid(row=2, column=1, sticky="w")
        self.currency_entry.insert(0, "TL")

        self.vat_included_var = tk.IntVar(value=0)
        ttk.Checkbutton(form, text="KDV Dahil", variable=self.vat_included_var).grid(row=2, column=2, sticky="w")

        ttk.Label(form, text="Genel İskonto").grid(row=2, column=3, sticky="w")
        self.inv_discount_entry = ttk.Entry(form, width=10)
        self.inv_discount_entry.grid(row=2, column=4, sticky="w")
        self.inv_discount_entry.insert(0, "0")

        self.inv_discount_type = ttk.Combobox(form, values=["amount", "percent"], width=8)
        self.inv_discount_type.grid(row=2, column=5, sticky="w")
        self.inv_discount_type.set("amount")

        self.proforma_var = tk.IntVar(value=0)
        ttk.Checkbutton(form, text="Proforma", variable=self.proforma_var).grid(row=3, column=0, sticky="w")

        ttk.Label(form, text="Not").grid(row=3, column=1, sticky="w")
        self.notes_entry = ttk.Entry(form, width=48)
        self.notes_entry.grid(row=3, column=2, columnspan=4, sticky="w")

        line_box = ttk.LabelFrame(self, text="Satırlar")
        line_box.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        line_form = ttk.Frame(line_box)
        line_form.pack(fill=tk.X, pady=4)

        self.line_desc = ttk.Entry(line_form, width=30)
        self.line_desc.pack(side=tk.LEFT, padx=4)
        self.line_qty = ttk.Entry(line_form, width=6)
        self.line_qty.pack(side=tk.LEFT)
        self.line_qty.insert(0, "1")
        self.line_unit = ttk.Entry(line_form, width=6)
        self.line_unit.pack(side=tk.LEFT, padx=4)
        self.line_unit.insert(0, "Adet")
        self.line_price = ttk.Entry(line_form, width=10)
        self.line_price.pack(side=tk.LEFT)
        self.line_price.insert(0, "0")
        self.line_vat = ttk.Entry(line_form, width=6)
        self.line_vat.pack(side=tk.LEFT, padx=4)
        self.line_vat.insert(0, "20")
        self.line_discount = ttk.Entry(line_form, width=8)
        self.line_discount.pack(side=tk.LEFT)
        self.line_discount.insert(0, "0")
        self.line_discount_type = ttk.Combobox(line_form, values=["amount", "percent"], width=8)
        self.line_discount_type.pack(side=tk.LEFT, padx=4)
        self.line_discount_type.set("amount")

        ttk.Button(line_form, text="Satır Ekle", command=self._add_line).pack(side=tk.LEFT, padx=4)
        ttk.Button(line_form, text="Satır Sil", command=self._remove_line).pack(side=tk.LEFT, padx=4)

        cols = ("line_no", "description", "qty", "unit", "unit_price", "vat_rate", "line_discount_value", "line_total")
        self.line_tree = ttk.Treeview(line_box, columns=cols, show="headings", height=8)
        for col in cols:
            self.line_tree.heading(col, text=col)
        self.line_tree.column("description", width=220)
        self.line_tree.column("line_total", width=110, anchor="e")
        self.line_tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        footer = ttk.Frame(self)
        footer.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(footer, text="Kaydet", command=self._save).pack(side=tk.LEFT)
        ttk.Button(footer, text="Kapat", command=self.destroy).pack(side=tk.LEFT, padx=6)
        self.total_label = ttk.Label(footer, text="Toplam: 0")
        self.total_label.pack(side=tk.RIGHT)

        self._load_customers()

    def _load_customers(self) -> None:
        try:
            rows = self.app.db.cari_list(q="")
            self.customer_map = {str(r["ad"]): int(r["id"]) for r in rows}
            self.customer_combo["values"] = list(self.customer_map.keys())
        except Exception:
            logger.exception("Customer load failed")

    def _add_line(self) -> None:
        try:
            line = {
                "description": self.line_desc.get().strip(),
                "qty": self.line_qty.get().strip(),
                "unit": self.line_unit.get().strip(),
                "unit_price": self.line_price.get().strip(),
                "vat_rate": self.line_vat.get().strip(),
                "line_discount_value": self.line_discount.get().strip(),
                "line_discount_type": self.line_discount_type.get().strip() or "amount",
            }
            self.lines.append(line)
            self._render_lines()
        except Exception:
            logger.exception("Failed to add line")

    def _remove_line(self) -> None:
        sel = self.line_tree.selection()
        if not sel:
            return
        idx = self.line_tree.index(sel[0])
        if 0 <= idx < len(self.lines):
            self.lines.pop(idx)
            self._render_lines()

    def _render_lines(self) -> None:
        totals = calculate_totals(
            self.lines,
            invoice_discount_value=self.inv_discount_entry.get().strip(),
            invoice_discount_type=self.inv_discount_type.get().strip(),
            vat_included=bool(self.vat_included_var.get()),
            sign=1,
        )
        for item in self.line_tree.get_children():
            self.line_tree.delete(item)
        for line in totals.lines:
            self.line_tree.insert(
                "",
                tk.END,
                values=(
                    line.get("line_no"),
                    line.get("description"),
                    line.get("qty"),
                    line.get("unit"),
                    line.get("unit_price"),
                    line.get("vat_rate"),
                    line.get("line_discount_value"),
                    fmt_amount(line.get("line_total")),
                ),
            )
        self.total_label.configure(text=f"Toplam: {fmt_amount(totals.grand_total)}")

    def _save(self) -> None:
        if not self.lines:
            messagebox.showwarning(APP_TITLE, "En az bir satır ekleyin")
            return
        try:
            customer_name = self.customer_combo.get().strip()
            header = {
                "company_id": self.company_id,
                "doc_type": self.doc_type,
                "doc_date": parse_date_smart(self.date_entry.get().strip()),
                "due_date": parse_date_smart(self.due_entry.get().strip()) if self.due_entry.get().strip() else "",
                "customer_id": self.customer_map.get(customer_name),
                "customer_name": customer_name,
                "currency": self.currency_entry.get().strip() or "TL",
                "vat_included": int(self.vat_included_var.get()),
                "invoice_discount_type": self.inv_discount_type.get().strip() or "amount",
                "invoice_discount_value": self.inv_discount_entry.get().strip(),
                "series": self.series_entry.get().strip() or "A",
                "status": "POSTED",
                "is_proforma": int(self.proforma_var.get()),
                "notes": self.notes_entry.get().strip(),
            }
            doc_id = self.repo.create_doc(
                header,
                self.lines,
                user_id=self.app.data_owner_user_id,
                username=self.app.data_owner_username,
            )
            messagebox.showinfo(APP_TITLE, f"Fatura oluşturuldu (ID: {doc_id})")
            if self.on_saved:
                self.on_saved()
            self.destroy()
        except Exception as exc:
            logger.exception("Save invoice failed")
            messagebox.showerror(APP_TITLE, f"Fatura kaydedilemedi: {exc}")


class InvoiceDetailWindow(tk.Toplevel):
    def __init__(self, master, app, repo, doc_id: int):
        super().__init__(master)
        self.app = app
        self.repo = repo
        self.doc_id = doc_id
        self.queue: queue.Queue = queue.Queue()
        self.title("Fatura Detayı")
        self.geometry("780x520")
        self._build()
        self._load()

    def _build(self) -> None:
        self.header_label = ttk.Label(self, text="")
        self.header_label.pack(fill=tk.X, padx=10, pady=6)

        self.tree = ttk.Treeview(self, columns=("desc", "qty", "unit", "total"), show="headings", height=12)
        for col in ("desc", "qty", "unit", "total"):
            self.tree.heading(col, text=col)
        self.tree.column("desc", width=320)
        self.tree.column("total", width=120, anchor="e")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        self.total_label = ttk.Label(self, text="")
        self.total_label.pack(fill=tk.X, padx=10)

        buttons = ttk.Frame(self)
        buttons.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(buttons, text="PDF", command=self._export_pdf).pack(side=tk.LEFT)
        ttk.Button(buttons, text="CSV", command=self._export_csv).pack(side=tk.LEFT, padx=6)
        ttk.Button(buttons, text="Kapat", command=self.destroy).pack(side=tk.RIGHT)

    def _load(self) -> None:
        try:
            payload = self.repo.get_doc(self.doc_id)
            if not payload:
                messagebox.showwarning(APP_TITLE, "Fatura bulunamadı")
                self.destroy()
                return
            header = payload["header"]
            self.header = header
            self.lines = payload["lines"]

            totals = {
                "subtotal": header["subtotal"],
                "discount_total": header["discount_total"],
                "vat_total": header["vat_total"],
                "grand_total": header["grand_total"],
            }
            self.totals = totals
            self.header_label.configure(text=f"{header['doc_no']} • {header['customer_name']} • {fmt_tr_date(header['doc_date'])}")

            for item in self.tree.get_children():
                self.tree.delete(item)
            for line in self.lines:
                self.tree.insert(
                    "",
                    tk.END,
                    values=(line["description"], line["qty"], line["unit"], fmt_amount(line["line_total"]))
                )
            self.total_label.configure(text=f"Genel Toplam: {fmt_amount(header['grand_total'])}")
        except Exception as exc:
            logger.exception("Failed to load invoice detail")
            messagebox.showerror(APP_TITLE, f"Detay yüklenemedi: {exc}")

    def _export_pdf(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        self._export_async(path, "pdf")

    def _export_csv(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        self._export_async(path, "csv")

    def _export_async(self, path: str, kind: str) -> None:
        def worker():
            try:
                if kind == "pdf":
                    export_pdf(path, dict(self.header), [dict(l) for l in self.lines], dict(self.totals), self._company_info())
                else:
                    export_csv(path, dict(self.header), [dict(l) for l in self.lines], dict(self.totals))
                self.queue.put(("ok", path))
            except Exception as exc:
                logger.exception("Export failed")
                self.queue.put(("err", str(exc)))

        threading.Thread(target=worker, daemon=True).start()
        self.after(150, self._poll_queue)

    def _poll_queue(self) -> None:
        try:
            status, payload = self.queue.get_nowait()
        except queue.Empty:
            self.after(150, self._poll_queue)
            return
        if status == "ok":
            messagebox.showinfo(APP_TITLE, f"Export tamamlandı: {os.path.basename(payload)}")
        else:
            messagebox.showerror(APP_TITLE, f"Export hatası: {payload}")

    def _company_info(self) -> Dict[str, str]:
        return {
            "name": getattr(self.app, "active_company_name", ""),
            "address": "",
            "tax": "",
        }


class PaymentsTab(ttk.Frame):
    def __init__(self, master, app, repo, company_id: int):
        super().__init__(master)
        self.app = app
        self.repo = repo
        self.company_id = company_id
        self._build()
        self.refresh()

    def _build(self) -> None:
        header = ttk.Frame(self)
        header.pack(fill=tk.X, padx=6, pady=6)
        ttk.Button(header, text="Ödeme Ekle", command=self._add_payment).pack(side=tk.LEFT)
        ttk.Button(header, text="Yenile", command=self.refresh).pack(side=tk.LEFT, padx=6)

        cols = ("id", "doc_no", "customer", "total", "remaining")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=14)
        for col in cols:
            self.tree.heading(col, text=col)
        self.tree.column("id", width=60, anchor="center")
        self.tree.column("doc_no", width=150)
        self.tree.column("customer", width=220)
        self.tree.column("total", width=120, anchor="e")
        self.tree.column("remaining", width=120, anchor="e")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=6)

    def _selected_doc_id(self) -> Optional[int]:
        sel = self.tree.selection()
        if not sel:
            return None
        try:
            return int(self.tree.item(sel[0], "values")[0])
        except Exception:
            return None

    def refresh(self) -> None:
        try:
            rows, _ = self.repo.list_docs(company_id=self.company_id, limit=200, offset=0)
            for item in self.tree.get_children():
                self.tree.delete(item)
            for r in rows:
                if r["remaining"] <= 0:
                    continue
                self.tree.insert(
                    "",
                    tk.END,
                    values=(r["id"], r["doc_no"], r["customer_name"], fmt_amount(r["grand_total"]), fmt_amount(r["remaining"])),
                )
        except Exception:
            logger.exception("Failed to refresh payments")

    def _add_payment(self) -> None:
        if not can_manage_payments(self.app.user["role"]):
            messagebox.showwarning(APP_TITLE, "Tahsilat için yetkiniz yok")
            return
        doc_id = self._selected_doc_id()
        if not doc_id:
            return
        PaymentWindow(self, self.app, self.repo, doc_id, on_saved=self.refresh)


class PaymentWindow(tk.Toplevel):
    def __init__(self, master, app, repo, doc_id: int, on_saved=None):
        super().__init__(master)
        self.app = app
        self.repo = repo
        self.doc_id = doc_id
        self.on_saved = on_saved
        self.title("Tahsilat / Ödeme")
        self.geometry("420x220")
        self._build()

    def _build(self) -> None:
        form = ttk.Frame(self)
        form.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(form, text="Tarih").grid(row=0, column=0, sticky="w")
        self.date_entry = ttk.Entry(form, width=12)
        self.date_entry.grid(row=0, column=1, sticky="w")
        self.date_entry.insert(0, _today_str())

        ttk.Label(form, text="Tutar").grid(row=1, column=0, sticky="w")
        self.amount_entry = ttk.Entry(form, width=12)
        self.amount_entry.grid(row=1, column=1, sticky="w")

        ttk.Label(form, text="Para").grid(row=2, column=0, sticky="w")
        self.currency_entry = ttk.Entry(form, width=8)
        self.currency_entry.grid(row=2, column=1, sticky="w")
        self.currency_entry.insert(0, "TL")

        ttk.Label(form, text="Yöntem").grid(row=3, column=0, sticky="w")
        self.method_entry = ttk.Entry(form, width=12)
        self.method_entry.grid(row=3, column=1, sticky="w")
        self.method_entry.insert(0, "Kasa")

        ttk.Button(form, text="Kaydet", command=self._save).grid(row=4, column=0, pady=10)
        ttk.Button(form, text="Kapat", command=self.destroy).grid(row=4, column=1, pady=10)

    def _save(self) -> None:
        try:
            self.repo.add_payment(
                self.doc_id,
                self.date_entry.get().strip(),
                float(self.amount_entry.get().strip() or 0),
                self.currency_entry.get().strip() or "TL",
                self.method_entry.get().strip(),
                user_id=self.app.data_owner_user_id,
                username=self.app.data_owner_username,
            )
            if self.on_saved:
                self.on_saved()
            self.destroy()
        except Exception as exc:
            logger.exception("Payment failed")
            messagebox.showerror(APP_TITLE, f"Ödeme kaydedilemedi: {exc}")
