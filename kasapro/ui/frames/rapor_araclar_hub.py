# -*- coding: utf-8 -*-
"""Rapor & Araçlar Hub Frame

İstek:
- Raporlar / Global Arama / Log gibi "araç" ekranlarını tek bir menü altında topla.
- "Rapor & Araçlar" açılınca bu ekranlar aynı sayfada sekmeler (Notebook) halinde gelsin.

Bu frame; mevcut ekranları (RaporlarFrame / GlobalSearchFrame / LogsFrame) değiştirmez,
aynı sayfada sekmeler halinde gösterir.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import tkinter as tk
from tkinter import ttk

from .raporlar import RaporlarFrame
from .purchase_report import PurchaseReportFrame
from .global_search import GlobalSearchFrame
from .logs import LogsFrame
from .satin_alma_raporlar import SatinAlmaRaporlarFrame

if TYPE_CHECKING:
    from ...app import App


class RaporAraclarHubFrame(ttk.Frame):
    """Rapor & Araçlar tek ekranda: Raporlar / Global Arama / Log."""

    def __init__(self, master, app: "App"):
        super().__init__(master)
        self.app = app

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Tab konteynerleri
        self.tab_raporlar = ttk.Frame(self.nb)
        self.tab_purchase = ttk.Frame(self.nb)
        self.tab_search = ttk.Frame(self.nb)
        self.tab_loglar = ttk.Frame(self.nb)
        self.tab_satin_alma = ttk.Frame(self.nb)

        self.nb.add(self.tab_raporlar, text="📊 Raporlar")
        self.nb.add(self.tab_purchase, text="🧾 Satın Alma Raporu")
        self.nb.add(self.tab_search, text="🔎 Global Arama")
        self.nb.add(self.tab_loglar, text="🧾 Log")
        self.nb.add(self.tab_satin_alma, text="📦 Satın Alma Sipariş Raporları")

        # İçerikler
        self.raporlar_frame = RaporlarFrame(self.tab_raporlar, self.app)
        self.raporlar_frame.pack(fill=tk.BOTH, expand=True)

        self.purchase_frame = PurchaseReportFrame(self.tab_purchase, self.app)
        self.purchase_frame.pack(fill=tk.BOTH, expand=True)

        self.search_frame = GlobalSearchFrame(self.tab_search, self.app)
        self.search_frame.pack(fill=tk.BOTH, expand=True)

        self.loglar_frame = LogsFrame(self.tab_loglar, self.app)
        self.loglar_frame.pack(fill=tk.BOTH, expand=True)

        self.satin_alma_frame = SatinAlmaRaporlarFrame(self.tab_satin_alma, self.app)
        self.satin_alma_frame.pack(fill=tk.BOTH, expand=True)

        try:
            self.nb.bind("<<NotebookTabChanged>>", lambda _e: self._on_tab_change())
        except Exception:
            pass

    # -----------------
    # Public helpers
    # -----------------
    def select_tab(self, tab_key: str):
        """Hub içinde sekme seçimi (route ile kullanılabilir)."""
        k = (tab_key or "").strip().lower()
        m = {
            "raporlar": self.tab_raporlar,
            "rapor": self.tab_raporlar,
            "purchase": self.tab_purchase,
            "satinalma": self.tab_purchase,
            "search": self.tab_search,
            "arama": self.tab_search,
            "loglar": self.tab_loglar,
            "log": self.tab_loglar,
            "satin_alma": self.tab_satin_alma,
            "satin_alma_rapor": self.tab_satin_alma,
        }
        target = m.get(k, self.tab_raporlar)
        try:
            self.nb.select(target)
        except Exception:
            pass

        self._on_tab_change()

    def refresh(self):
        """Alt ekranları tazeler."""
        try:
            if hasattr(self, "raporlar_frame") and hasattr(self.raporlar_frame, "refresh"):
                self.raporlar_frame.refresh()  # type: ignore
        except Exception:
            pass
        try:
            if hasattr(self, "purchase_frame") and hasattr(self.purchase_frame, "reload_filters"):
                self.purchase_frame.reload_filters()  # type: ignore
        except Exception:
            pass
        try:
            if hasattr(self, "loglar_frame") and hasattr(self.loglar_frame, "refresh"):
                self.loglar_frame.refresh()  # type: ignore
        except Exception:
            pass
        try:
            if hasattr(self, "satin_alma_frame") and hasattr(self.satin_alma_frame, "refresh"):
                self.satin_alma_frame.refresh()  # type: ignore
        except Exception:
            pass

    def reload_settings(self):
        """App.reload_settings() çağrısında uyumlu olsun."""
        try:
            self.refresh()
        except Exception:
            pass

    # -----------------
    # Internal
    # -----------------
    def _on_tab_change(self):
        """Seçili sekmeye göre gerekli refreshleri tetikler."""
        try:
            sel = self.nb.select()
        except Exception:
            sel = ""

        # Raporlar sekmesi aktifse raporu yenile (DB değişimi vs. sonrası)
        try:
            if sel == str(self.tab_raporlar) and hasattr(self, "raporlar_frame"):
                if hasattr(self.raporlar_frame, "refresh"):
                    self.raporlar_frame.refresh()  # type: ignore
        except Exception:
            pass

        try:
            if sel == str(self.tab_purchase) and hasattr(self, "purchase_frame"):
                if hasattr(self.purchase_frame, "reload_filters"):
                    self.purchase_frame.reload_filters()  # type: ignore
        except Exception:
            pass

        # Log sekmesi aktifse logu yenile
        try:
            if sel == str(self.tab_loglar) and hasattr(self, "loglar_frame"):
                if hasattr(self.loglar_frame, "refresh"):
                    self.loglar_frame.refresh()  # type: ignore
        except Exception:
            pass

        # Satın alma rapor sekmesi aktifse tazele
        try:
            if sel == str(self.tab_satin_alma) and hasattr(self, "satin_alma_frame"):
                if hasattr(self.satin_alma_frame, "refresh"):
                    self.satin_alma_frame.refresh()  # type: ignore
        except Exception:
            pass
