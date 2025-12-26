# -*- coding: utf-8 -*-
"""UI tema tokenleri.

Tek merkezden yönetilen renk, spacing, radius ve typography değerleri.
"""

from __future__ import annotations

DESIGN_TOKENS = {
    "layout": {
        "grid": 8,
        "app_max_width": 1440,
        "topbar_height": 64,
        "sidebar_width": 240,
        "page_padding": 24,
        "card_radius": 14,
        "input_height": 40,
        "button_height": 44,
    },
    "colors": {
        "bg_app": "#0B0F1A",
        "bg_surface": "#111827",
        "bg_surface_2": "#161E2E",
        "border": "#334155",
        "text_primary": "#F8FAFC",
        "text_secondary": "#CBD5E1",
        "text_muted": "#94A3B8",
        "accent_primary": "#3B82F6",
        "accent_secondary": "#14B8A6",
        "success": "#22C55E",
        "warning": "#F59E0B",
        "danger": "#EF4444",
        "info": "#06B6D4",
    },
    "effects": {
        "shadow_card": "soft-lg",
        "blur_glass": "8-12px",
    },
    "typography": {
        "font_family": "Inter/SFPro",
        "h1": 26,
        "h2": 18,
        "body": 14,
        "small": 12,
        "weight_normal": 400,
        "weight_semibold": 600,
        "weight_bold": 700,
    },
    "iconography": {
        "size": 24,
        "style": "outline duotone",
    },
}
