# -*- coding: utf-8 -*-

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from ..base import BaseView
from ..ui_logging import log_ui_event, wrap_callback


class StockWmsFrame(BaseView):
    """Stok/Depo/WMS ana ekranı (fazlar için yerleşim)."""

    def __init__(self, master, app):
        self.app = app
        super().__init__(master, app)
        self.build_ui()

    def build_ui(self) -> None:
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.tab_card = ttk.Frame(self.nb)
        self.tab_doc = ttk.Frame(self.nb)
        self.tab_warehouse = ttk.Frame(self.nb)
        self.tab_count = ttk.Frame(self.nb)
        self.tab_pick = ttk.Frame(self.nb)
        self.tab_reports = ttk.Frame(self.nb)

        self.nb.add(self.tab_card, text="📦 Stok Kartı")
        self.nb.add(self.tab_doc, text="🧾 Stok Hareket Fişi")
        self.nb.add(self.tab_warehouse, text="🏭 Depo Yönetimi")
        self.nb.add(self.tab_count, text="📋 Sayım")
        self.nb.add(self.tab_pick, text="🧭 Toplama")
        self.nb.add(self.tab_reports, text="📈 Rapor Merkezi")

        self._build_stock_card()
        self._build_doc()
        self._build_warehouse()
        self._build_count()
        self._build_pick()
        self._build_reports()

    def _build_stock_card(self) -> None:
        nb = ttk.Notebook(self.tab_card)
        nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        tabs = {
            "Genel": "Genel kart bilgileri.",
            "Barkod": "Barkod yönetimi.",
            "Depo-Lokasyon": "Depo/lokasyon görünümü.",
            "Seri-Lot": "Seri/Lot takibi.",
            "Fiyat-Maliyet": "Maliyet ve fiyat bilgisi.",
            "Kurallar": "Negatif stok ve doğrulamalar.",
            "Ekler": "Doküman ekleri.",
        }
        for title, desc in tabs.items():
            frame = ttk.Frame(nb)
            nb.add(frame, text=title)
            ttk.Label(frame, text=desc).pack(anchor="w", padx=12, pady=12)
        log_ui_event("tab_added", tab="stock_card", container="stock_wms")

    def _build_doc(self) -> None:
        ttk.Label(
            self.tab_doc,
            text="Hızlı giriş, barkod ve satır kopyalama akışları burada yönetilir.",
        ).pack(anchor="w", padx=12, pady=12)

        btn = ttk.Button(
            self.tab_doc,
            text="Demo Stok Fişleri Oluştur",
            command=wrap_callback("wms_demo_docs", self._seed_demo),
        )
        btn.pack(anchor="w", padx=12, pady=(0, 12))

    def _build_warehouse(self) -> None:
        ttk.Label(
            self.tab_warehouse,
            text="Depo/Lokasyon ağacı + doluluk/kapasite alanları.",
        ).pack(anchor="w", padx=12, pady=12)

    def _build_count(self) -> None:
        ttk.Label(
            self.tab_count,
            text="Sayım akışı: görev → sayım → fark → tolerans → onay.",
        ).pack(anchor="w", padx=12, pady=12)

    def _build_pick(self) -> None:
        ttk.Label(
            self.tab_pick,
            text="Wave/rota → doğrulama → paketleme akışı.",
        ).pack(anchor="w", padx=12, pady=12)

    def _build_reports(self) -> None:
        ttk.Label(
            self.tab_reports,
            text="Stok raporları, KPI ve otomasyon kuralları.",
        ).pack(anchor="w", padx=12, pady=12)

    def _seed_demo(self) -> None:
        try:
            company_id = int(getattr(self.app, "active_company_id", 1) or 1)
            branch_id = 1
            if hasattr(self.app, "services") and hasattr(self.app.services, "wms"):
                self.app.services.wms.seed_demo_data(company_id, branch_id)
                messagebox.showinfo("Demo", "Demo stok verisi oluşturuldu.")
            else:
                messagebox.showwarning("Demo", "WMS servisi bulunamadı.")
        except Exception as exc:
            messagebox.showerror("Demo", f"Hata: {exc}")

