# -*- coding: utf-8 -*-
"""Base UI classes."""

from __future__ import annotations

from typing import Any, Optional

from tkinter import ttk
import tkinter as tk

from .ui_logging import log_ui_event


class BaseView(ttk.Frame):
    """Common base for UI screens."""

    def __init__(self, parent: ttk.Frame, controller: Any, **kwargs: Any) -> None:
        super().__init__(parent, **kwargs)
        self.controller = controller
        self._view_name = self.__class__.__name__
        log_ui_event("frame_created", view=self._view_name)
        self._refresh_scheduled = False
        self._refresh_id = None

        # ✅ Stil ayarları
        self.style = ttk.Style()
        self.setup_styles()

    def setup_styles(self) -> None:
        """UI bileşenlerin stilini ayarla."""
        # Override et gerekirse
        pass

    def create_header(self, title: str, subtitle: str = "") -> ttk.Frame:
        """Başlık çerçevesi oluştur."""
        header = ttk.Frame(self)
        header.pack(fill=tk.X, padx=15, pady=10)

        title_lbl = ttk.Label(
            header,
            text=title,
            font=self.controller.font_heading if hasattr(self.controller, 'font_heading') else ("Segoe UI", 14, "bold"),
        )
        title_lbl.pack(anchor=tk.W)

        if subtitle:
            subtitle_lbl = ttk.Label(
                header,
                text=subtitle,
                font=("Segoe UI", 9),
            )
            subtitle_lbl.pack(anchor=tk.W, pady=(5, 0))

        return header

    def create_button_bar(self) -> ttk.Frame:
        """Buton çubuğu oluştur."""
        bar = ttk.Frame(self)
        bar.pack(fill=tk.X, padx=15, pady=10)
        return bar

    def create_content_frame(self) -> ttk.Frame:
        """İçerik çerçevesi oluştur."""
        content = ttk.Frame(self)
        content.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        return content

    def build_ui(self) -> None:
        """Build UI elements (override in subclasses)."""

    def refresh(self, data: Optional[Any] = None) -> None:
        """Refresh UI state (override in subclasses)."""
        if self._refresh_scheduled:
            return  # Önceki refresh henüz devam ediyor

        self._refresh_scheduled = True
        try:
            self._do_refresh(data)
        except Exception as e:
            import logging
            logging.exception("Refresh hatası")
        finally:
            self._refresh_scheduled = False

    def _do_refresh(self, data: Optional[Any] = None) -> None:
        """Gerçek refresh işlemini yap (override etmek için)."""
        pass

    def schedule_refresh(self, delay_ms: int = 100, data=None) -> None:
        """Refresh'i geciktir (UI güncelleme sırasında çakışmayı önle)."""
        if hasattr(self, '_refresh_id') and self._refresh_id:
            self.after_cancel(self._refresh_id)

        self._refresh_id = self.after(
            delay_ms,
            lambda: self.refresh(data)
        )
