# -*- coding: utf-8 -*-
"""KasaPro v4 - ttk tema/stil ayarları

Bu modül geriye uyumluluk için korunmuştur.
Yeni tema sistemi için kasapro.ui.theme modülünü kullanın.
"""

from __future__ import annotations

from typing import Dict

import tkinter as tk

# Yeni tema modülünden import
from .theme import (
    apply_dark_glass_theme,
    apply_modern_style as _apply_modern_style,
    get_colors,
    get_base_font,
    COLORS_DARK,
    COLORS_LIGHT,
)


def apply_modern_style(root: tk.Tk) -> Dict[str, str]:
    """Modern tema uygula.
    
    Bu fonksiyon artık Premium Dark Glass temasını uygular.
    Legacy uyumluluk için korunmuştur.
    """
    return apply_dark_glass_theme(root)


# Legacy exports
__all__ = [
    "apply_modern_style",
    "apply_dark_glass_theme", 
    "get_colors",
    "get_base_font",
    "COLORS_DARK",
    "COLORS_LIGHT",
]
