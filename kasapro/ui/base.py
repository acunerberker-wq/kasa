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

    def build_ui(self) -> None:
        """Build UI elements (override in subclasses)."""

    def refresh(self, data: Optional[Any] = None) -> None:
        """Refresh UI state (override in subclasses)."""
