# -*- coding: utf-8 -*-
"""UI logging helpers."""

from __future__ import annotations

import logging
import os
from typing import Any, Callable


def _ensure_ui_logger() -> None:
    logger = logging.getLogger("kasapro.ui")
    if any(isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", "").endswith("app.log") for h in logger.handlers):
        return
    log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "logs", "app.log")
    log_path = os.path.abspath(log_path)
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    handler = logging.FileHandler(log_path)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


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
        return func(*args, **kwargs)

    return wrapper
