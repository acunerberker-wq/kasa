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
import pkgutil
from typing import Callable, Dict, List, Optional

from tkinter import ttk


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
    logger = logging.getLogger("kasapro.ui.plugins")
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
            order_value = meta.get("order")
            if isinstance(order_value, (int, float, str)):
                order = int(order_value)
            else:
                order = 100
        except Exception:
            logger.exception("UI plugin metadata invalid: %s", name)
            continue
        if not key or not nav_text:
            continue

        plugins.append(UIPlugin(key=key, nav_text=nav_text, page_title=page_title, build=build, order=order))

    plugins.sort(key=lambda p: (p.order, p.key))
    return plugins
