# -*- coding: utf-8 -*-
"""Tanımlar Hub Frame

İstek:
- Cariler / Çalışanlar / Meslekler gibi "veri tanımı" ekranlarını tek bir menü altında topla.
- "Tanımlar" açılınca bu ekranlar aynı sayfada sekmeler (Notebook) halinde gelsin.

Not:
- Çalışanlar için Maaş Takibi eklentisinin "Çalışanlar" sekmesi kullanılabilir.
- Meslekler için Maaş Meslekler eklentisi kullanılır.
"""

from __future__ import annotations

from typing import Optional

import tkinter as tk
from tkinter import ttk

from .cariler import CarilerFrame


def _find_first_notebook(root: tk.Misc) -> Optional[ttk.Notebook]:
    """Çocuklar içinde ilk ttk.Notebook'u bulur."""
    try:
        if isinstance(root, ttk.Notebook):
            return root
    except Exception:
        pass
    try:
        for ch in root.winfo_children():
            nb = _find_first_notebook(ch)
            if nb is not None:
                return nb
    except Exception:
        return None
    return None


class TanimlarHubFrame(ttk.Frame):
    """Tanımlar tek ekranda: Cariler / Çalışanlar / Meslekler."""

    def __init__(self, master, app: "App"):
        super().__init__(master)
        self.app = app

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Tab konteynerleri
        self.tab_cariler = ttk.Frame(self.nb)
        self.tab_calisanlar = ttk.Frame(self.nb)
        self.tab_meslekler = ttk.Frame(self.nb)

        self.nb.add(self.tab_cariler, text="👥 Cariler")
        self.nb.add(self.tab_calisanlar, text="👷 Çalışanlar")
        self.nb.add(self.tab_meslekler, text="🧑‍🏭 Meslekler")

        # İçerikler
        self._build_cariler()
        self._build_calisanlar()
        self._build_meslekler()

        try:
            self.nb.bind("<<NotebookTabChanged>>", lambda _e: self._on_tab_change())
        except Exception:
            pass

    # -----------------
    # Builders
    # -----------------
    def _build_cariler(self):
        self.cariler_frame = CarilerFrame(self.tab_cariler, self.app)
        self.cariler_frame.pack(fill=tk.BOTH, expand=True)

    def _build_calisanlar(self):
        """Çalışanlar: Maaş Takibi eklentisinin Çalışanlar sekmesini kullan.

        Kullanıcı "Tanımlar" ekranında sadece çalışan tanımlarını görmek istiyor.
        Bu yüzden Maaş Takibi içindeki diğer sekmeler gizlenir.
        """

        try:
            # plugin iç sınıfı
            from ..plugins.maas_takibi import MaasTakibiFrame  # type: ignore

            self.calisanlar_frame = MaasTakibiFrame(self.tab_calisanlar, self.app)
            self.calisanlar_frame.pack(fill=tk.BOTH, expand=True)

            # Sadece "Çalışanlar" sekmesini göster
            try:
                nb = getattr(self.calisanlar_frame, "nb", None)
                tab_emp = getattr(self.calisanlar_frame, "tab_employees", None)
                if isinstance(nb, ttk.Notebook) and tab_emp is not None:
                    for tab_id in list(nb.tabs()):
                        if tab_id != str(tab_emp):
                            try:
                                nb.hide(tab_id)
                            except Exception:
                                pass
                    try:
                        nb.select(tab_emp)
                    except Exception:
                        pass
            except Exception:
                pass

        except Exception:
            ttk.Label(
                self.tab_calisanlar,
                text="Çalışanlar ekranı için 'Maaş Takibi' eklentisi bulunamadı.",
            ).pack(anchor="w", padx=12, pady=12)

    def _build_meslekler(self):
        """Meslekler: Maaş Meslekler eklentisini kullan.

        Tanımlar ekranında sade olması için sadece "Meslek Tanımları" sekmesi bırakılır.
        """

        try:
            from ..plugins.maas_meslekler import MaasMesleklerFrame  # type: ignore

            self.meslekler_frame = MaasMesleklerFrame(self.tab_meslekler, self.app)
            self.meslekler_frame.pack(fill=tk.BOTH, expand=True)

            # İç notebook'u bulup "Çalışana Meslek Ata" sekmesini gizle
            try:
                nb = _find_first_notebook(self.meslekler_frame)
                tab_atama = getattr(self.meslekler_frame, "tab_atama", None)
                tab_meslek = getattr(self.meslekler_frame, "tab_meslek", None)
                if isinstance(nb, ttk.Notebook):
                    if tab_atama is not None:
                        try:
                            nb.hide(str(tab_atama))
                        except Exception:
                            pass
                    if tab_meslek is not None:
                        try:
                            nb.select(str(tab_meslek))
                        except Exception:
                            pass
            except Exception:
                pass

        except Exception:
            ttk.Label(
                self.tab_meslekler,
                text="Meslekler ekranı için 'Maaş Meslekler' eklentisi bulunamadı.",
            ).pack(anchor="w", padx=12, pady=12)

    # -----------------
    # Public helpers
    # -----------------
    def select_tab(self, tab_key: str):
        """Hub içinde sekme seçimi (route ile kullanılabilir)."""
        m = {
            "cariler": self.tab_cariler,
            "calisanlar": self.tab_calisanlar,
            "meslekler": self.tab_meslekler,
        }
        target = m.get((tab_key or "").strip().lower())
        if target is None:
            target = self.tab_cariler
        try:
            self.nb.select(target)
        except Exception:
            pass

        # Sekme seçilince iç sekmeleri de doğru konuma al
        self._on_tab_change()

    def refresh(self):
        """Tanımlar ekranındaki alt ekranları tazeler."""
        try:
            if hasattr(self, "cariler_frame") and hasattr(self.cariler_frame, "refresh"):
                self.cariler_frame.refresh()  # type: ignore
        except Exception:
            pass
        try:
            if hasattr(self, "calisanlar_frame") and hasattr(self.calisanlar_frame, "refresh_all"):
                self.calisanlar_frame.refresh_all()  # type: ignore
        except Exception:
            pass
        try:
            if hasattr(self, "meslekler_frame") and hasattr(self.meslekler_frame, "refresh_all"):
                self.meslekler_frame.refresh_all()  # type: ignore
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
        """Seçili sekmeye göre alt notebook'u doğru yere al."""
        try:
            sel = self.nb.select()
        except Exception:
            sel = ""

        # Çalışanlar sekmesi seçilince çalışanlar alt sekmesini garanti et
        try:
            if sel == str(self.tab_calisanlar) and hasattr(self, "calisanlar_frame"):
                if hasattr(self.calisanlar_frame, "select_employees_tab"):
                    self.calisanlar_frame.select_employees_tab()  # type: ignore
        except Exception:
            pass
