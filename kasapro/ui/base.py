# -*- coding: utf-8 -*-
"""Base UI classes."""

from __future__ import annotations

from typing import Any, Optional

from tkinter import ttk

from .ui_logging import log_ui_event


class BaseView(ttk.Frame):
    """Common base for UI screens."""

    def __init__(self, parent: ttk.Frame, controller: Any, **kwargs: Any) -> None:
        super().__init__(parent, **kwargs)
        self.controller = controller
        self._view_name = self.__class__.__name__
        log_ui_event("frame_created", view=self._view_name)
        self._refresh_scheduled = False

    def build_ui(self) -> None:
        """Build UI elements (override in subclasses)."""

    def refresh(self, data: Optional[Any] = None) -> None:
        """Refresh UI state (override in subclasses)."""
        if self._refresh_scheduled:
            return  # Önceki refresh henüz devam ediyor

        self._refresh_scheduled = True
        try:
            # ...existing code...
        except Exception as e:
            print(f"Refresh hatası: {e}")
        finally:
            self._refresh_scheduled = False

    def schedule_refresh(self, delay_ms: int = 100, data=None) -> None:
        """Refresh'i geciktir (UI güncelleme sırasında çakışmayı önle)."""
        if hasattr(self, '_refresh_id') and self._refresh_id:
            self.after_cancel(self._refresh_id)

        self._refresh_id = self.after(
            delay_ms,
            lambda: self.refresh(data)
        )
