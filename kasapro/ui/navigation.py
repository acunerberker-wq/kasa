# -*- coding: utf-8 -*-
"""Navigation registry for UI screens."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

import tkinter as tk
from tkinter import ttk

from .ui_logging import get_ui_logger, log_ui_event


Factory = Callable[[ttk.Frame, Any], ttk.Frame]


@dataclass
class ScreenSpec:
    key: str
    factory: Factory
    title: str = ""


class ScreenRegistry:
    def __init__(self, container: ttk.Frame, controller: Any) -> None:
        self.container = container
        self.controller = controller
        self.frames: Dict[str, ttk.Frame] = {}
        self._specs: Dict[str, ScreenSpec] = {}
        self._logger = get_ui_logger()

    def register(self, key: str, factory: Factory, title: str = "") -> None:
        if key in self._specs:
            self._logger.warning("UI screen already registered: %s", key)
            return
        spec = ScreenSpec(key=key, factory=factory, title=title)
        self._specs[key] = spec
        log_ui_event("screen_registered", key=key, title=title)
        self._create_frame(spec)

    def _create_frame(self, spec: ScreenSpec) -> Optional[ttk.Frame]:
        if spec.key in self.frames:
            return self.frames[spec.key]
        try:
            frame = spec.factory(self.container, self.controller)
            self.frames[spec.key] = frame
            log_ui_event("screen_created", key=spec.key, view=frame.__class__.__name__)
            return frame
        except Exception:
            self._logger.exception("Failed to build screen: %s", spec.key)
            return None

    def show(self, key: str) -> None:
        if key not in self.frames:
            self._logger.warning("UI screen missing: %s", key)
            return
        for k, f in self.frames.items():
            if k == key:
                f.pack(fill=tk.BOTH, expand=True)
            else:
                f.pack_forget()
        log_ui_event("screen_shown", key=key)
