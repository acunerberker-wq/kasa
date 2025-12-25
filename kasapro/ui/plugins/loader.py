# -*- coding: utf-8 -*-
"""UI plugin keşfi ve yükleme.

Eklenti modülleri: kasapro.ui.plugins paketinin altındaki Python dosyalarıdır.

Her eklenti modülü şu iki parçayı sağlamalıdır:

- PLUGIN_META (dict):
    - key (str)        : benzersiz frame anahtarı
    - nav_text (str)   : sol menü buton metni
    - page_title (str) : üst başlık metni
    - order (int)      : (opsiyonel) menü sıralaması

- build(master, app) -> ttk.Frame : frame oluşturucu
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
import logging
import os
import pkgutil
from typing import Callable, Dict, List, Optional

from tkinter import ttk


def _ensure_plugin_logger() -> logging.Logger:
    logger = logging.getLogger("kasapro.ui.plugins")
    if any(isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", "").endswith("app.log") for h in logger.handlers):
        return logger
    log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "..", "logs", "app.log")
    log_path = os.path.abspath(log_path)
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    handler = logging.FileHandler(log_path)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


@dataclass(frozen=True)
class UIPlugin:
    key: str
    nav_text: str
    page_title: str
    build: Callable[[ttk.Frame, object], ttk.Frame]
    order: int = 100


def discover_ui_plugins() -> List[UIPlugin]:
    """kasapro.ui.plugins altındaki eklentileri keşfeder.

    Hatalı/eksik eklentiler uygulamayı düşürmez; sessizce atlanır.
    """
    logger = _ensure_plugin_logger()
    plugins: List[UIPlugin] = []
    try:
        pkg = import_module("kasapro.ui.plugins")
    except Exception:
        logger.exception("UI plugin package import failed")
        return []

    for modinfo in pkgutil.iter_modules(getattr(pkg, "__path__", []), pkg.__name__ + "."):
        name = modinfo.name
        # loader.py ve __init__.py gibi yardımcıları atla
        if name.endswith(".loader"):
            continue
        try:
            mod = import_module(name)
        except Exception:
            logger.exception("UI plugin import failed: %s", name)
            continue

        meta: Optional[Dict[str, object]] = getattr(mod, "PLUGIN_META", None)
        build = getattr(mod, "build", None)
        if not isinstance(meta, dict):
            continue
        if not callable(build):
            continue
        try:
            key = str(meta.get("key") or "").strip()
            nav_text = str(meta.get("nav_text") or "").strip()
            page_title = str(meta.get("page_title") or key).strip()
            enabled = bool(meta.get("enabled", True))
            name = str(meta.get("name") or key).strip()
            version = str(meta.get("version") or "0.1.0").strip()
            order_value = meta.get("order")
            if isinstance(order_value, (int, float, str)):
                order = int(order_value)
            else:
                order = 100
        except Exception:
            logger.exception("UI plugin metadata invalid: %s", name)
            continue
        if not enabled:
            logger.info("UI plugin disabled: %s", key)
            continue
        if not key or not nav_text:
            continue

        plugins.append(UIPlugin(key=key, nav_text=nav_text, page_title=page_title, build=build, order=order))
        logger.info("UI plugin loaded: %s (%s v%s)", key, name, version)

    plugins.sort(key=lambda p: (p.order, p.key))
    return plugins
