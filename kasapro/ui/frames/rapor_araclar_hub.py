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

from ..base import BaseView
from ..ui_logging import log_ui_event, wrap_callback
from .raporlar import RaporlarFrame
from .global_search import GlobalSearchFrame
from .logs import LogsFrame
from .satin_alma_raporlar import SatinAlmaRaporlarFrame
from ...modules.notes_reminders.ui import NotesRemindersFrame

if TYPE_CHECKING:
    from ...app import App

if TYPE_CHECKING:
    from ...app import App


class RaporAraclarHubFrame(BaseView):
    """Rapor & Araçlar tek ekranda: Raporlar / Global Arama / Log."""

    def __init__(self, master, app: "App"):
        self.app = app
        super().__init__(master, app)

        self.build_ui()

    def build_ui(self) -> None:
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Tab konteynerleri
        self.tab_raporlar = ttk.Frame(self.nb)
        self.tab_search = ttk.Frame(self.nb)
        self.tab_loglar = ttk.Frame(self.nb)
        self.tab_satin_alma = ttk.Frame(self.nb)
        self.tab_notes_reminders = ttk.Frame(self.nb)

        self.nb.add(self.tab_raporlar, text="📊 Raporlar")
        log_ui_event("tab_added", tab="raporlar", container="rapor_araclar")
        self.nb.add(self.tab_search, text="🔎 Global Arama")
        log_ui_event("tab_added", tab="search", container="rapor_araclar")
        self.nb.add(self.tab_loglar, text="🧾 Log")
        log_ui_event("tab_added", tab="loglar", container="rapor_araclar")
        self.nb.add(self.tab_satin_alma, text="📦 Satın Alma Sipariş Raporları")
        self._notes_tab_base_text = "🗒️ Notlar & Hatırlatmalar"
        self.nb.add(self.tab_notes_reminders, text=self._notes_tab_base_text)

        # İçerikler
        self.raporlar_frame = RaporlarFrame(self.tab_raporlar, self.app)
        self.raporlar_frame.pack(fill=tk.BOTH, expand=True)

        self.search_frame = GlobalSearchFrame(self.tab_search, self.app)
        self.search_frame.pack(fill=tk.BOTH, expand=True)

        self.loglar_frame = LogsFrame(self.tab_loglar, self.app)
        self.loglar_frame.pack(fill=tk.BOTH, expand=True)

        self.satin_alma_frame = SatinAlmaRaporlarFrame(self.tab_satin_alma, self.app)
        self.satin_alma_frame.pack(fill=tk.BOTH, expand=True)

        self.notes_reminders_frame = NotesRemindersFrame(self.tab_notes_reminders, self.app)
        self.notes_reminders_frame.pack(fill=tk.BOTH, expand=True)

        try:
            self.nb.bind(
                "<<NotebookTabChanged>>",
                wrap_callback("rapor_araclar_tab_change", lambda _e: self._on_tab_change()),
            )
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
            "search": self.tab_search,
            "arama": self.tab_search,
            "loglar": self.tab_loglar,
            "log": self.tab_loglar,
            "satin_alma": self.tab_satin_alma,
            "satin_alma_rapor": self.tab_satin_alma,
            "notlar_hatirlatmalar": self.tab_notes_reminders,
            "notlar": self.tab_notes_reminders,
            "hatirlatmalar": self.tab_notes_reminders,
        }
        target = m.get(k, self.tab_raporlar)
        try:
            self.nb.select(target)
        except Exception:
            pass

        self._on_tab_change()

    def refresh(self, data=None):
        """Alt ekranları tazeler."""
        try:
            if hasattr(self, "raporlar_frame") and hasattr(self.raporlar_frame, "refresh"):
                self.raporlar_frame.refresh()  # type: ignore
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
        try:
            if hasattr(self, "notes_reminders_frame") and hasattr(self.notes_reminders_frame, "refresh"):
                self.notes_reminders_frame.refresh()  # type: ignore
        except Exception:
            pass

    def refresh_notes_reminders_badge(self, count: int) -> None:
        try:
            text = self._notes_tab_base_text
            if count and count > 0:
                text = f"{text} ({count})"
            self.nb.tab(self.tab_notes_reminders, text=text)
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

        # Notlar & Hatırlatmalar sekmesi aktifse tazele
        try:
            if sel == str(self.tab_notes_reminders) and hasattr(self, "notes_reminders_frame"):
                if hasattr(self.notes_reminders_frame, "refresh"):
                    self.notes_reminders_frame.refresh()  # type: ignore
        except Exception:
            pass
