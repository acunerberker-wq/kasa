# -*- coding: utf-8 -*-
"""KasaPro v4 - Premium Dark Glass Theme

Qt UI tasarımından alınan modern dark glass tema.
Referans: login_with_user_select.ui, banka_hareketleri_advanced_designer_ok_v2.ui

Tasarım Dili:
- Koyu radial gradient arka plan
- Glassmorphism kartlar (yarı saydam)
- Gradient mavi aksan butonları
- Yumuşak border-radius (10-16px)
- Inter/Segoe UI fontları
"""

from __future__ import annotations

import sys
from typing import Dict, Optional

import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont


# ============================================================================
# RENK PALETİ (Qt .ui dosyalarından çıkarıldı)
# ============================================================================

# Light theme (varsayılan - legacy uyumluluk için korunuyor)
COLORS_LIGHT: Dict[str, str] = {
    "bg": "#F5F6FA",
    "panel": "#FFFFFF",
    "border": "#E5E7EB",
    "text": "#111827",
    "muted": "#6B7280",
    "accent": "#2563EB",
    "accent_light": "#DBEAFE",
    "danger": "#DC2626",
    "success": "#16A34A",
    "warning": "#F59E0B",
}

# Premium Dark Glass Theme (Qt UI'dan alındı)
# NOT: Tkinter alpha desteklemez, tüm renkler koyu arka plana göre blend edildi
COLORS_DARK: Dict[str, str] = {
    # Ana arka planlar (Qt: qradialgradient)
    "bg": "#0a0e18",                # Ana arka plan (Qt: rgba(10, 14, 24))
    "bg_glow": "#141e32",           # Glow efekt alanı (Qt: rgba(20, 30, 50))
    "bg_dark": "#06080e",           # En koyu arka plan (Qt: rgba(6, 8, 14))
    
    # Panel/Kart renkleri (Qt: QFrame#Card, QFrame.Card)
    "panel": "#121a2a",             # Kart zemini (Qt: rgba(18, 26, 42))
    "panel_border": "#3a3e48",      # Kart kenarı (blend: #ffffff @ 19% on dark)
    "sidebar": "#0e1422",           # Sidebar (Qt: rgba(14, 20, 34))
    
    # Kenar renkleri
    "border": "#2a2e38",            # Genel kenar (blend: #ffffff @ 10% on dark)
    "border_light": "#1e222c",      # Hafif kenar (blend: #ffffff @ 7% on dark)
    
    # Metin renkleri (Qt: color: rgba(...))
    "text": "#f0f5ff",              # Ana metin (Qt: rgba(240,245,255,220))
    "text_secondary": "#dce5ff",    # İkincil (Qt: rgba(220,225,255,175))
    "muted": "#8090aa",             # Soluk (Qt: rgba(180,200,255,120))
    "placeholder": "#7080a0",       # Placeholder
    
    # Aksan renkleri (Qt: QPushButton.Primary gradient)
    "accent": "#378cff",            # Ana aksan (Qt: rgba(55, 140, 255))
    "accent_dark": "#145ad2",       # Koyu aksan (Qt: rgba(20, 90, 210))
    "accent_light": "#1e3a5f",      # Açık aksan (blend: #5a8cff @ 47% on dark)
    "accent_hover": "#46a0ff",      # Hover (Qt: rgba(70, 160, 255))
    "accent_glow": "#50a0ff",       # Glow efekt
    
    # Input stilleri (Qt: QLineEdit, QCombobox)
    "input_bg": "#151923",          # Input arka plan (blend: #ffffff @ 4% on dark)
    "input_border": "#1e222c",      # Input kenar (blend: #ffffff @ 9% on dark)
    "input_focus": "#3a5a8a",       # Focus kenar (blend: #5a96ff @ 63% on dark)
    
    # Durum renkleri
    "danger": "#ff5a5a",            # Tehlike (Qt: rgba(255,90,90))
    "danger_bg": "#2a1a1a",         # Tehlike arka plan (blend on dark)
    "success": "#23aa5f",           # Başarı (Qt: rgba(35,170,95))
    "success_bg": "#142a1f",        # Başarı arka plan (blend on dark)
    "warning": "#f5a623",           # Uyarı
    "warning_bg": "#2a2214",        # Uyarı arka plan (blend on dark)
    
    # Tablo/Treeview
    "table_header": "#14181f",      # Header arka plan (blend: #ffffff @ 3% on dark)
    "table_row_alt": "#0e1218",     # Alternatif satır (blend: #ffffff @ 2% on dark)
    "selection": "#1e3a5f",         # Seçim (blend: #5a8cff @ 47% on dark)
    "gridline": "#1e222c",          # Tablo çizgileri (blend: #ffffff @ 7% on dark)
    
    # Badge/Etiket renkleri
    "badge_in_bg": "#142a1f",       # Giriş badge (blend: #23aa5f @ 18% on dark)
    "badge_in_border": "#1a4030",   # Giriş kenar (blend: #23aa5f @ 35% on dark)
    "badge_in_text": "#aaf0c8",     # Giriş metin (Qt: rgba(170,240,200,235))
    "badge_out_bg": "#2a1a1a",      # Çıkış badge (blend: #ff5a5a @ 18% on dark)
    "badge_out_border": "#4a2828",  # Çıkış kenar (blend: #ff7878 @ 35% on dark)
    "badge_out_text": "#ffd2d2",    # Çıkış metin (Qt: rgba(255,210,210,235))
    
    # Buton stilleri
    "btn_primary_bg": "#378cff",    # Primary arka plan
    "btn_primary_border": "#5a8ccc",# Primary kenar (blend: #8cbeff @ 56% on dark)
    "btn_ghost_bg": "#151923",      # Ghost arka plan (blend: #ffffff @ 4% on dark)
    "btn_ghost_border": "#1e222c",  # Ghost kenar (blend: #ffffff @ 9% on dark)
}

# Aktif tema (varsayılan: dark)
_active_theme: str = "dark"


def get_colors() -> Dict[str, str]:
    """Aktif tema renklerini döndür."""
    return COLORS_DARK if _active_theme == "dark" else COLORS_LIGHT


def set_theme(theme: str) -> None:
    """Tema değiştir: 'dark' veya 'light'."""
    global _active_theme
    _active_theme = theme if theme in ("dark", "light") else "dark"


# ============================================================================
# FONT YAPISI
# ============================================================================

def get_base_font() -> str:
    """Platform için en uygun sans-serif fontu döndür."""
    preferred = ["Inter", "Segoe UI", "SF Pro Display", "Helvetica Neue", "Arial"]
    try:
        available = tkfont.families()
        for font in preferred:
            if font in available:
                return font
    except Exception:
        pass
    
    if sys.platform.startswith("win"):
        return "Segoe UI"
    elif sys.platform == "darwin":
        return "SF Pro Display"
    return "DejaVu Sans"


# ============================================================================
# TEMA UYGULAMA FONKSİYONLARI
# ============================================================================

def apply_dark_glass_theme(root: tk.Tk) -> Dict[str, str]:
    """Premium Dark Glass temasını uygula.
    
    Qt UI dosyalarından alınan modern koyu cam efektli tema.
    """
    colors = COLORS_DARK
    base_font = get_base_font()
    
    # Root pencere arka planı
    try:
        root.configure(background=colors["bg"])
    except Exception:
        pass
    
    # Varsayılan fontları ayarla
    for fname in (
        "TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont",
        "TkCaptionFont", "TkSmallCaptionFont", "TkIconFont", "TkTooltipFont"
    ):
        try:
            f = tkfont.nametofont(fname)
            if fname == "TkHeadingFont":
                f.configure(family=base_font, size=11, weight="bold")
            else:
                f.configure(family=base_font, size=10)
        except Exception:
            pass
    
    # Klasik tk widget renkleri (Text, Listbox vs.)
    try:
        root.option_add("*Text.background", colors["panel"])
        root.option_add("*Text.foreground", colors["text"])
        root.option_add("*Text.insertBackground", colors["accent"])
        root.option_add("*Text.selectBackground", colors["selection"])
        root.option_add("*Text.selectForeground", colors["text"])
        root.option_add("*Listbox.background", colors["panel"])
        root.option_add("*Listbox.foreground", colors["text"])
        root.option_add("*Listbox.selectBackground", colors["selection"])
        root.option_add("*Listbox.selectForeground", colors["text"])
        # Combobox dropdown stilleri
        root.option_add("*TCombobox*Listbox.background", colors["panel"])
        root.option_add("*TCombobox*Listbox.foreground", colors["text"])
        root.option_add("*TCombobox*Listbox.selectBackground", colors["accent_light"])
        root.option_add("*TCombobox*Listbox.selectForeground", colors["text"])
    except Exception:
        pass
    
    style = ttk.Style(root)
    
    # Tema seçimi (clam en iyi özelleştirme desteği sağlar)
    try:
        style.theme_use("clam")
    except Exception:
        try:
            style.theme_use("default")
        except Exception:
            pass
    
    # ========================================
    # GLOBAL STILLER
    # ========================================
    style.configure(".", 
        font=(base_font, 10),
        background=colors["bg"],
        foreground=colors["text"],
        borderwidth=0,
        focuscolor=colors["accent"],
    )
    
    # ========================================
    # FRAME STİLLERİ
    # ========================================
    style.configure("TFrame", background=colors["bg"])
    style.configure("Panel.TFrame", background=colors["panel"])
    style.configure("Card.TFrame", background=colors["panel"])
    style.configure("Sidebar.TFrame", background=colors["sidebar"])
    style.configure("Topbar.TFrame", background=colors["panel"])
    
    # ========================================
    # SEPARATOR
    # ========================================
    style.configure("TSeparator", background=colors["border"])
    
    # ========================================
    # LABEL STİLLERİ
    # ========================================
    style.configure("TLabel", 
        background=colors["bg"], 
        foreground=colors["text"],
    )
    style.configure("Panel.TLabel",
        background=colors["panel"],
        foreground=colors["text"],
    )
    style.configure("TopTitle.TLabel", 
        background=colors["panel"], 
        foreground=colors["text"], 
        font=(base_font, 18, "bold"),
    )
    style.configure("TopSub.TLabel", 
        background=colors["panel"], 
        foreground=colors["muted"],
        font=(base_font, 10),
    )
    
    # Sidebar Labels
    style.configure("SidebarTitle.TLabel", 
        background=colors["sidebar"], 
        foreground=colors["text"], 
        font=(base_font, 16, "bold"),
    )
    style.configure("SidebarSub.TLabel", 
        background=colors["sidebar"], 
        foreground=colors["muted"],
        font=(base_font, 9),
    )
    style.configure("SidebarSection.TLabel",
        background=colors["sidebar"],
        foreground=colors["muted"],
        font=(base_font, 9, "bold"),
        padding=(12, 6),
    )
    
    # Status bar
    style.configure("Status.TLabel", 
        background=colors["panel"], 
        foreground=colors["muted"], 
        padding=(12, 6),
    )
    
    # Badge stilleri
    style.configure("Badge.TLabel",
        background=colors["accent_light"],
        foreground=colors["accent"],
        font=(base_font, 9, "bold"),
        padding=(6, 3),
    )
    style.configure("BadgeSuccess.TLabel",
        background=colors["success_bg"],
        foreground=colors["success"],
        font=(base_font, 9, "bold"),
        padding=(6, 3),
    )
    style.configure("BadgeDanger.TLabel",
        background=colors["danger_bg"],
        foreground=colors["danger"],
        font=(base_font, 9, "bold"),
        padding=(6, 3),
    )
    style.configure("BadgeIn.TLabel",
        background=colors["badge_in_bg"],
        foreground=colors["badge_in_text"],
        font=(base_font, 9, "bold"),
        padding=(6, 3),
    )
    style.configure("BadgeOut.TLabel",
        background=colors["badge_out_bg"],
        foreground=colors["badge_out_text"],
        font=(base_font, 9, "bold"),
        padding=(6, 3),
    )
    
    # ========================================
    # BUTTON STİLLERİ
    # ========================================
    
    # Genel buton
    style.configure("TButton", 
        padding=(14, 10),
        font=(base_font, 10),
        background=colors["btn_ghost_bg"],
        foreground=colors["text"],
        borderwidth=1,
        relief="flat",
    )
    style.map("TButton",
        background=[
            ("active", colors["accent_light"]),
            ("pressed", colors["accent_dark"]),
            ("!active", colors["btn_ghost_bg"]),
        ],
        foreground=[
            ("disabled", colors["muted"]),
            ("!disabled", colors["text"]),
        ],
    )
    
    # Primary Button (Ana aksiyon)
    style.configure("Primary.TButton", 
        padding=(14, 10),
        font=(base_font, 10, "bold"),
        background=colors["accent"],
        foreground="#ffffff",
        borderwidth=1,
    )
    style.map("Primary.TButton",
        background=[
            ("active", colors["accent_hover"]),
            ("pressed", colors["accent_dark"]),
            ("!active", colors["accent"]),
        ],
        foreground=[
            ("disabled", "#888888"),
            ("!disabled", "#ffffff"),
        ],
    )
    
    # Secondary Button (İkincil aksiyon)
    style.configure("Secondary.TButton", 
        padding=(14, 10),
        font=(base_font, 10),
        background=colors["panel"],
        foreground=colors["text"],
        borderwidth=1,
    )
    style.map("Secondary.TButton",
        background=[
            ("active", colors["accent_light"]),
            ("!active", colors["panel"]),
        ],
        foreground=[
            ("disabled", colors["muted"]),
            ("!disabled", colors["text"]),
        ],
    )
    
    # Ghost Button (Saydam)
    style.configure("Ghost.TButton", 
        padding=(14, 10),
        font=(base_font, 10),
        background=colors["btn_ghost_bg"],
        foreground=colors["text_secondary"],
        borderwidth=1,
    )
    style.map("Ghost.TButton",
        background=[
            ("active", colors["accent_light"]),
            ("!active", colors["btn_ghost_bg"]),
        ],
    )
    
    # Danger Button (Tehlikeli aksiyon)
    style.configure("Danger.TButton", 
        padding=(14, 10),
        font=(base_font, 10, "bold"),
        background=colors["danger"],
        foreground="#ffffff",
    )
    style.map("Danger.TButton",
        background=[
            ("active", "#ff4040"),
            ("pressed", "#cc4040"),
            ("!active", colors["danger"]),
        ],
        foreground=[
            ("disabled", "#aaaaaa"),
            ("!disabled", "#ffffff"),
        ],
    )
    
    # Success Button
    style.configure("Success.TButton", 
        padding=(14, 10),
        font=(base_font, 10, "bold"),
        background=colors["success"],
        foreground="#ffffff",
    )
    style.map("Success.TButton",
        background=[
            ("active", "#2bc96e"),
            ("pressed", "#1a8a4a"),
            ("!active", colors["success"]),
        ],
    )
    
    # Sidebar Buttons
    style.configure("Sidebar.TButton", 
        padding=(14, 10), 
        anchor="w",
        font=(base_font, 10),
        background=colors["sidebar"],
        foreground=colors["text_secondary"],
    )
    style.map("Sidebar.TButton",
        background=[
            ("active", colors["accent_light"]),
            ("!active", colors["sidebar"]),
        ],
        foreground=[
            ("disabled", colors["muted"]),
            ("!disabled", colors["text_secondary"]),
        ],
    )
    
    style.configure("SidebarActive.TButton", 
        padding=(14, 10), 
        anchor="w",
        font=(base_font, 10, "bold"),
        background=colors["accent_light"],
        foreground=colors["accent"],
    )
    style.map("SidebarActive.TButton",
        background=[
            ("active", colors["accent_light"]),
            ("!active", colors["accent_light"]),
        ],
        foreground=[
            ("!disabled", colors["accent"]),
        ],
    )
    
    # ========================================
    # INPUT STİLLERİ (Entry, Combobox)
    # ========================================
    style.configure("TEntry",
        padding=8,
        fieldbackground=colors["panel"],
        foreground=colors["text"],
        insertcolor=colors["accent"],
        borderwidth=1,
    )
    style.map("TEntry",
        fieldbackground=[
            ("focus", colors["panel"]),
            ("!focus", colors["panel"]),
        ],
    )
    
    style.configure("TCombobox",
        padding=6,
        fieldbackground=colors["panel"],
        foreground=colors["text"],
        arrowcolor=colors["text_secondary"],
    )
    style.map("TCombobox",
        fieldbackground=[
            ("readonly", colors["panel"]),
        ],
        selectbackground=[
            ("readonly", colors["accent_light"]),
        ],
    )
    
    # Error variants
    style.configure("Error.TEntry", 
        fieldbackground=colors["danger_bg"], 
        foreground=colors["text"],
    )
    style.configure("Error.TCombobox", 
        fieldbackground=colors["danger_bg"], 
        foreground=colors["text"],
    )
    
    # ========================================
    # SPINBOX
    # ========================================
    style.configure("TSpinbox",
        padding=6,
        fieldbackground=colors["panel"],
        foreground=colors["text"],
        arrowcolor=colors["text_secondary"],
    )
    
    # ========================================
    # LABELFRAME
    # ========================================
    style.configure("TLabelframe", 
        background=colors["bg"],
        borderwidth=1,
        relief="solid",
    )
    style.configure("TLabelframe.Label", 
        background=colors["bg"], 
        foreground=colors["text"], 
        font=(base_font, 10, "bold"),
    )
    style.configure("Card.TLabelframe",
        background=colors["panel"],
    )
    style.configure("Card.TLabelframe.Label",
        background=colors["panel"],
        foreground=colors["text"],
        font=(base_font, 10, "bold"),
    )
    
    # ========================================
    # TREEVIEW (Tablo)
    # ========================================
    style.configure("Treeview",
        background=colors["panel"],
        fieldbackground=colors["panel"],
        foreground=colors["text"],
        rowheight=28,
        borderwidth=0,
        relief="flat",
    )
    style.configure("Treeview.Heading",
        background=colors["table_header"],
        foreground=colors["text_secondary"],
        font=(base_font, 10, "bold"),
        relief="flat",
        padding=(10, 8),
    )
    style.map("Treeview",
        background=[
            ("selected", colors["selection"]),
        ],
        foreground=[
            ("selected", colors["text"]),
        ],
    )
    style.map("Treeview.Heading",
        background=[
            ("active", colors["accent_light"]),
        ],
    )
    
    # ========================================
    # NOTEBOOK (Tabs)
    # ========================================
    style.configure("TNotebook", 
        background=colors["bg"], 
        borderwidth=0,
        tabmargins=[0, 0, 0, 0],
    )
    style.configure("TNotebook.Tab", 
        padding=(16, 10),
        font=(base_font, 10),
        background=colors["panel"],
        foreground=colors["muted"],
    )
    style.map("TNotebook.Tab",
        background=[
            ("selected", colors["accent_light"]),
            ("!selected", colors["panel"]),
        ],
        foreground=[
            ("selected", colors["accent"]),
            ("!selected", colors["muted"]),
        ],
    )
    
    # ========================================
    # PROGRESSBAR
    # ========================================
    style.configure("TProgressbar",
        background=colors["accent"],
        troughcolor=colors["panel"],
        borderwidth=0,
        thickness=6,
    )
    
    # ========================================
    # SCALE (Slider)
    # ========================================
    style.configure("TScale",
        background=colors["bg"],
        troughcolor=colors["panel"],
        sliderrelief="flat",
    )
    
    # ========================================
    # CHECKBUTTON & RADIOBUTTON
    # ========================================
    style.configure("TCheckbutton",
        background=colors["bg"],
        foreground=colors["text"],
        focuscolor=colors["accent"],
    )
    style.map("TCheckbutton",
        background=[
            ("active", colors["bg"]),
        ],
    )
    
    style.configure("TRadiobutton",
        background=colors["bg"],
        foreground=colors["text"],
        focuscolor=colors["accent"],
    )
    style.map("TRadiobutton",
        background=[
            ("active", colors["bg"]),
        ],
    )
    
    # Panel üzerindeki checkbox/radio
    style.configure("Panel.TCheckbutton",
        background=colors["panel"],
        foreground=colors["text"],
    )
    style.configure("Panel.TRadiobutton",
        background=colors["panel"],
        foreground=colors["text"],
    )
    
    # ========================================
    # SCROLLBAR
    # ========================================
    style.configure("TScrollbar",
        background=colors["panel"],
        troughcolor=colors["bg"],
        arrowcolor=colors["text_secondary"],
        borderwidth=0,
    )
    style.map("TScrollbar",
        background=[
            ("active", colors["accent_light"]),
            ("!active", colors["panel"]),
        ],
    )
    
    # ========================================
    # MENUBUTTON
    # ========================================
    style.configure("TMenubutton",
        background=colors["panel"],
        foreground=colors["text"],
        padding=(10, 6),
    )
    
    return colors


def apply_modern_style(root: tk.Tk) -> Dict[str, str]:
    """Modern tema uygula (legacy uyumluluk için).
    
    Bu fonksiyon geriye uyumluluk için korunmuştur.
    Yeni kod için apply_dark_glass_theme() kullanın.
    """
    return apply_dark_glass_theme(root)
