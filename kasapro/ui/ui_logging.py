# -*- coding: utf-8 -*-
"""UI logging helpers."""

from __future__ import annotations

import logging
import os
from typing import Any, Callable

from ..config import APP_BASE_DIR, APP_TITLE, LOG_DIRNAME

try:
    from tkinter import messagebox
except Exception:  # pragma: no cover - Tk import may fail in headless tests
    messagebox = None


def _ensure_ui_logger() -> None:
    logger = logging.getLogger("kasapro.ui")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return

    root = logging.getLogger()
    root_log_paths = {
        getattr(h, "baseFilename", "")
        for h in root.handlers
        if isinstance(h, logging.FileHandler)
    }
    desired_path = os.path.abspath(os.path.join(APP_BASE_DIR, LOG_DIRNAME, "app.log"))
    if desired_path in root_log_paths:
        logger.propagate = True
        return

    os.makedirs(os.path.dirname(desired_path), exist_ok=True)
    handler = logging.FileHandler(desired_path, encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False


def get_ui_logger() -> logging.Logger:
    _ensure_ui_logger()
    return logging.getLogger("kasapro.ui")


def log_ui_event(event: str, **details: Any) -> None:
    _ensure_ui_logger()
    logger = get_ui_logger()
    if details:
        detail_str = ", ".join(f"{k}={v!r}" for k, v in details.items())
        logger.info("UI %s | %s", event, detail_str)
    else:
        logger.info("UI %s", event)


def wrap_callback(name: str, func: Callable[..., Any]) -> Callable[..., Any]:
    log_ui_event("callback_bound", handler=name)

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        logger = get_ui_logger()
        logger.info("UI callback invoked: %s", name)
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            logger.exception("UI callback failed: %s", name)
            if messagebox is not None:
                try:
                    messagebox.showerror(APP_TITLE, "İşlem sırasında hata oluştu. Detaylar loglandı.")
                except Exception:
                    pass
            return None

    return wrapper
