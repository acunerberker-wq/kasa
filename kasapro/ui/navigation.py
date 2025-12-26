# -*- coding: utf-8 -*-
"""Navigation registry for UI screens."""

from __future__ import annotations

from dataclasses import dataclass
import time
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

    def register(self, key: str, factory: Factory, title: str = "", create: bool = True) -> None:
        if key in self._specs:
            self._logger.warning("UI screen already registered: %s", key)
            return
        spec = ScreenSpec(key=key, factory=factory, title=title)
        self._specs[key] = spec
        log_ui_event("screen_registered", key=key, title=title)
        if create:
            self._create_frame(spec)

    def has_spec(self, key: str) -> bool:
        return key in self._specs

    def _create_frame(self, spec: ScreenSpec) -> Optional[ttk.Frame]:
        if spec.key in self.frames:
            return self.frames[spec.key]
        try:
            started = time.perf_counter()
            frame = spec.factory(self.container, self.controller)
            elapsed = time.perf_counter() - started
            self.frames[spec.key] = frame
            log_ui_event(
                "screen_created",
                key=spec.key,
                view=frame.__class__.__name__,
                elapsed_s=round(elapsed, 4),
            )
            return frame
        except Exception:
            self._logger.exception("Failed to build screen: %s", spec.key)
            return None

    def show(self, key: str) -> None:
        if key not in self.frames:
            spec = self._specs.get(key)
            if not spec:
                self._logger.warning("UI screen missing: %s", key)
                return
            frame = self._create_frame(spec)
            if frame is None:
                return
        for k, f in self.frames.items():
            if k == key:
                f.pack(fill=tk.BOTH, expand=True)
            else:
                f.pack_forget()
        log_ui_event("screen_shown", key=key)
