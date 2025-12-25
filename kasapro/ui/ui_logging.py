# -*- coding: utf-8 -*-
"""UI logging helpers."""

from __future__ import annotations

import logging
from typing import Any, Callable


def get_ui_logger() -> logging.Logger:
    return logging.getLogger("kasapro.ui")


def log_ui_event(event: str, **details: Any) -> None:
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
