# -*- coding: utf-8 -*-
"""Base classes for Create Center forms."""

from __future__ import annotations

import logging
import queue
import threading
from typing import Any, Callable, Dict, Optional

import tkinter as tk
from tkinter import ttk, messagebox

from ..ui_logging import log_ui_event


class BaseCreateForm(ttk.Frame):
    """Standard base form for Create Center."""

    def __init__(self, master: tk.Misc, app: Any) -> None:
        super().__init__(master)
        self.app = app
        self._logger = logging.getLogger(__name__)
        self._error_widgets: Dict[tk.Widget, str] = {}
        self._message_var = tk.StringVar(value="")
        self._background_queue: queue.Queue = queue.Queue()
        self._context: Dict[str, Any] = {}
        self.build_ui()
        self._build_message_area()

    def build_ui(self) -> None:
        """Builds form UI (override in subclasses)."""

    def _build_message_area(self) -> None:
        msg = ttk.Label(self, textvariable=self._message_var, style="SidebarSub.TLabel")
        msg.pack(fill=tk.X, padx=6, pady=(6, 0))

    def set_context(self, ctx: Optional[Dict[str, Any]] = None) -> None:
        self._context = ctx or {}

    def validate_form(self) -> bool:
        self.clear_errors()
        return True

    def collect_data(self) -> Dict[str, Any]:
        return {}

    def perform_save(self) -> bool:
        return True

    def save(self) -> bool:
        if not self.validate_form():
            self._set_message("Eksik alanlar var. Lütfen işaretli alanları kontrol edin.")
            return False
        try:
            ok = self.perform_save()
        except Exception as exc:
            self._logger.exception("Create form save failed")
            messagebox.showerror("KasaPro", f"Kayıt başarısız: {exc}")
            return False
        if ok:
            log_ui_event("create_form_saved", form=self.__class__.__name__)
            self._set_message("Kayıt başarılı.")
        return bool(ok)

    def save_draft(self) -> bool:
        self._set_message("Taslak desteği bu formda yok.")
        return False

    def reset_form(self) -> None:
        """Reset form state (override in subclasses)."""

    def on_show(self) -> None:
        """Hook when form is shown."""

    def focus_first(self) -> None:
        """Override to focus first input widget."""

    def _set_message(self, text: str) -> None:
        try:
            self._message_var.set(text)
        except Exception:
            pass

    def clear_errors(self) -> None:
        for widget, style in list(self._error_widgets.items()):
            try:
                if isinstance(widget, ttk.Entry):
                    widget.configure(style=style or "TEntry")
                elif isinstance(widget, ttk.Combobox):
                    widget.configure(style=style or "TCombobox")
                elif isinstance(widget, tk.Text):
                    widget.configure(background="white")
            except Exception:
                continue
        self._error_widgets.clear()

    def mark_error(self, widget: tk.Widget, message: str) -> None:
        if widget not in self._error_widgets:
            try:
                if isinstance(widget, ttk.Entry):
                    self._error_widgets[widget] = widget.cget("style")
                    widget.configure(style="Error.TEntry")
                elif isinstance(widget, ttk.Combobox):
                    self._error_widgets[widget] = widget.cget("style")
                    widget.configure(style="Error.TCombobox")
                elif isinstance(widget, tk.Text):
                    self._error_widgets[widget] = ""
                    widget.configure(background="#FEE2E2")
            except Exception:
                pass
        self._set_message(message)

    def run_in_background(self, task: Callable[[], Any], on_done: Callable[[Any], None]) -> None:
        def worker() -> None:
            try:
                result = task()
                self._background_queue.put(("ok", result))
            except Exception as exc:
                self._background_queue.put(("err", exc))

        threading.Thread(target=worker, daemon=True).start()

        def poll() -> None:
            try:
                status, payload = self._background_queue.get_nowait()
            except queue.Empty:
                self.after(80, poll)
                return
            if status == "err":
                self._logger.exception("Background task failed", exc_info=payload)
                return
            on_done(payload)

        self.after(80, poll)

    def _ensure_recent_bucket(self, key: str) -> None:
        if not hasattr(self.app, "_create_center_recent_entities"):
            self.app._create_center_recent_entities = {}
        if key not in self.app._create_center_recent_entities:
            self.app._create_center_recent_entities[key] = []

    def add_recent_entity(self, key: str, value: str) -> None:
        if not value:
            return
        self._ensure_recent_bucket(key)
        items = self.app._create_center_recent_entities[key]
        if value in items:
            items.remove(value)
        items.insert(0, value)
        del items[5:]

    def get_recent_entities(self, key: str) -> list[str]:
        self._ensure_recent_bucket(key)
        return list(self.app._create_center_recent_entities.get(key, []))
