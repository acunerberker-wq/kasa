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
# Görsel referanslar: 15 ekran görüntüsünden analiz edildi
COLORS_DARK: Dict[str, str] = {
    # Ana arka planlar - daha derin lacivert tonları
    "bg": "#080c14",                # Ana arka plan (daha koyu)
    "bg_glow": "#101828",           # Glow efekt alanı
    "bg_dark": "#050810",           # En koyu arka plan
    
    # Panel/Kart renkleri - görsellerle uyumlu
    "panel": "#0f1520",             # Kart zemini (daha koyu)
    "panel_hover": "#141c2a",       # Kart hover
    "panel_border": "#243040",      # Kart kenarı (mavi tonlu)
    "sidebar": "#0a1018",           # Sidebar (en koyu)
    "sidebar_active": "#0f1828",    # Aktif sidebar item arka planı
    
    # Kenar renkleri - mavi tonlu
    "border": "#1a2535",            # Genel kenar (mavi tonlu)
    "border_light": "#141c28",      # Hafif kenar
    "border_accent": "#2a4a6a",     # Vurgulu kenar (aktif tab gibi)
    
    # Metin renkleri
    "text": "#e8f0ff",              # Ana metin (biraz daha açık)
    "text_secondary": "#b8c8e0",    # İkincil
    "muted": "#6080a0",             # Soluk (daha mavi)
    "placeholder": "#506080",       # Placeholder
    
    # Aksan renkleri - parlak mavi
    "accent": "#3a8fff",            # Ana aksan (daha parlak)
    "accent_dark": "#1a5cc0",       # Koyu aksan
    "accent_light": "#1a3050",      # Açık aksan (hover/selection)
    "accent_bright": "#50a0ff",     # En parlak (aktif tab)
    "accent_hover": "#4a9fff",      # Hover
    "accent_glow": "#5ab0ff",       # Glow efekt
    
    # Input stilleri - daha belirgin
    "input_bg": "#0c1018",          # Input arka plan (koyu)
    "input_border": "#1a2838",      # Input kenar
    "input_focus": "#2a5080",       # Focus kenar (mavi)
    
    # Durum renkleri
    "danger": "#ff5a5a",            # Tehlike
    "danger_bg": "#201418",         # Tehlike arka plan
    "success": "#20c060",           # Başarı (daha parlak)
    "success_bg": "#102018",        # Başarı arka plan
    "warning": "#f5a020",           # Uyarı
    "warning_bg": "#201810",        # Uyarı arka plan
    
    # Tablo/Treeview - görsellerle uyumlu
    "table_header": "#0c1420",      # Header arka plan
    "table_header_border": "#1a2838", # Header alt border
    "table_row": "#0f1520",         # Normal satır
    "table_row_alt": "#0a1018",     # Alternatif satır
    "selection": "#1a3858",         # Seçim
    "gridline": "#141c28",          # Tablo çizgileri
    
    # Tab stilleri - görsellerle uyumlu
    "tab_bg": "#0c1420",            # Pasif tab
    "tab_active_bg": "#1a3858",     # Aktif tab arka plan
    "tab_active_text": "#50a0ff",   # Aktif tab metin
    "tab_border": "#1a2838",        # Tab border
    
    # Badge/Etiket renkleri
    "badge_in_bg": "#102820",       # Giriş badge
    "badge_in_border": "#184030",   # Giriş kenar
    "badge_in_text": "#80e0a0",     # Giriş metin
    "badge_out_bg": "#281418",      # Çıkış badge
    "badge_out_border": "#402028",  # Çıkış kenar
    "badge_out_text": "#ffa0a0",    # Çıkış metin
    
    # Buton stilleri - görsellerle uyumlu
    "btn_primary_bg": "#3a8fff",    # Primary arka plan
    "btn_primary_hover": "#4a9fff", # Primary hover
    "btn_primary_border": "#5aafff",# Primary kenar
    "btn_secondary_bg": "#141c28",  # Secondary arka plan
    "btn_secondary_border": "#1a2838", # Secondary kenar
    "btn_ghost_bg": "#0c1420",      # Ghost arka plan
    "btn_ghost_border": "#1a2838",  # Ghost kenar
    "btn_ghost_hover": "#141c30",   # Ghost hover
    
    # Pagination stilleri
    "pager_bg": "#0c1420",          # Sayfalama buton bg
    "pager_border": "#1a2838",      # Sayfalama border
    "pager_text": "#6080a0",        # Sayfalama metin
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
    style.configure("FilterBar.TFrame", background=colors["panel"])  # Filtre alanı
    style.configure("FormSection.TFrame", background=colors["panel"]) # Form bölümü
    
    # ========================================
    # SEPARATOR
    # ========================================
    style.configure("TSeparator", background=colors["border"])
    style.configure("Accent.TSeparator", background=colors["accent"])  # Aktif sidebar indicator
    
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
        background=colors["bg"], 
        foreground=colors["text"], 
        font=(base_font, 20, "bold"),  # Daha büyük başlık
    )
    style.configure("TopSub.TLabel", 
        background=colors["bg"], 
        foreground=colors["muted"],
        font=(base_font, 10),
    )
    style.configure("PageTitle.TLabel",  # Sayfa başlığı (ör: "Banka Hareketleri")
        background=colors["bg"],
        foreground=colors["text"],
        font=(base_font, 18, "bold"),
    )
    style.configure("SectionTitle.TLabel",  # Bölüm başlığı (ör: "Filtre")
        background=colors["panel"],
        foreground=colors["text"],
        font=(base_font, 11, "bold"),
    )
    style.configure("FormLabel.TLabel",  # Form etiketleri
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
        padding=(12, 8),
    )
    
    # Status bar
    style.configure("Status.TLabel", 
        background=colors["panel"], 
        foreground=colors["muted"], 
        padding=(12, 6),
    )
    
    # Pagination label
    style.configure("Pager.TLabel",
        background=colors["panel"],
        foreground=colors["muted"],
        font=(base_font, 10),
    )
    
    # Summary/Info labels (ör: "Toplam: Giriş 0,00 - Çıkış 0,00")
    style.configure("Summary.TLabel",
        background=colors["panel"],
        foreground=colors["text_secondary"],
        font=(base_font, 10),
    )
    
    # Badge stilleri
    style.configure("Badge.TLabel",
        background=colors["accent_light"],
        foreground=colors["accent"],
        font=(base_font, 9, "bold"),
        padding=(8, 4),
    )
    style.configure("BadgeSuccess.TLabel",
        background=colors["success_bg"],
        foreground=colors["success"],
        font=(base_font, 9, "bold"),
        padding=(8, 4),
    )
    style.configure("BadgeDanger.TLabel",
        background=colors["danger_bg"],
        foreground=colors["danger"],
        font=(base_font, 9, "bold"),
        padding=(8, 4),
    )
    style.configure("BadgeWarning.TLabel",
        background=colors["warning_bg"],
        foreground=colors["warning"],
        font=(base_font, 9, "bold"),
        padding=(8, 4),
    )
    style.configure("BadgeIn.TLabel",
        background=colors["badge_in_bg"],
        foreground=colors["badge_in_text"],
        font=(base_font, 9, "bold"),
        padding=(8, 4),
    )
    style.configure("BadgeOut.TLabel",
        background=colors["badge_out_bg"],
        foreground=colors["badge_out_text"],
        font=(base_font, 9, "bold"),
        padding=(8, 4),
    )
    
    # ========================================
    # BUTTON STİLLERİ - Görsellerden
    # ========================================
    
    # Genel buton (Ghost tarzı)
    style.configure("TButton", 
        padding=(16, 8),
        font=(base_font, 10),
        background=colors["btn_ghost_bg"],
        foreground=colors["text_secondary"],
        borderwidth=1,
        relief="flat",
    )
    style.map("TButton",
        background=[
            ("active", colors["btn_ghost_hover"]),
            ("pressed", colors["accent_light"]),
            ("!active", colors["btn_ghost_bg"]),
        ],
        foreground=[
            ("disabled", colors["muted"]),
            ("!disabled", colors["text_secondary"]),
        ],
    )
    
    # Primary Button (Parlak mavi - "Yeni", "Kaydet + Yeni", "Yenile")
    style.configure("Primary.TButton", 
        padding=(16, 8),
        font=(base_font, 10, "bold"),
        background=colors["btn_primary_bg"],
        foreground="#ffffff",
        borderwidth=0,
    )
    style.map("Primary.TButton",
        background=[
            ("active", colors["btn_primary_hover"]),
            ("pressed", colors["accent_dark"]),
            ("disabled", colors["muted"]),
            ("!active", colors["btn_primary_bg"]),
        ],
        foreground=[
            ("disabled", "#666666"),
            ("!disabled", "#ffffff"),
        ],
    )
    
    # Secondary Button (Koyu arka plan, açık kenar - "Detay", "İptal")
    style.configure("Secondary.TButton", 
        padding=(16, 8),
        font=(base_font, 10),
        background=colors["btn_secondary_bg"],
        foreground=colors["text"],
        borderwidth=1,
    )
    style.map("Secondary.TButton",
        background=[
            ("active", colors["accent_light"]),
            ("!active", colors["btn_secondary_bg"]),
        ],
        foreground=[
            ("disabled", colors["muted"]),
            ("!disabled", colors["text"]),
        ],
    )
    
    # Ghost Button (Tamamen saydam görünüm)
    style.configure("Ghost.TButton", 
        padding=(16, 8),
        font=(base_font, 10),
        background=colors["btn_ghost_bg"],
        foreground=colors["text_secondary"],
        borderwidth=1,
    )
    style.map("Ghost.TButton",
        background=[
            ("active", colors["btn_ghost_hover"]),
            ("!active", colors["btn_ghost_bg"]),
        ],
        foreground=[
            ("disabled", colors["muted"]),
            ("!disabled", colors["text_secondary"]),
        ],
    )
    
    # Toolbar Button (Araç çubuğu - "Excel ile Aktar", "PDF", "Sil")
    style.configure("Toolbar.TButton", 
        padding=(12, 6),
        font=(base_font, 10),
        background=colors["btn_secondary_bg"],
        foreground=colors["text_secondary"],
        borderwidth=1,
    )
    style.map("Toolbar.TButton",
        background=[
            ("active", colors["accent_light"]),
            ("!active", colors["btn_secondary_bg"]),
        ],
    )
    
    # Danger Button (Sil, İptal gibi)
    style.configure("Danger.TButton", 
        padding=(16, 8),
        font=(base_font, 10, "bold"),
        background=colors["danger"],
        foreground="#ffffff",
    )
    style.map("Danger.TButton",
        background=[
            ("active", "#ff4040"),
            ("pressed", "#cc3030"),
            ("!active", colors["danger"]),
        ],
        foreground=[
            ("disabled", "#888888"),
            ("!disabled", "#ffffff"),
        ],
    )
    
    # Success Button
    style.configure("Success.TButton", 
        padding=(16, 8),
        font=(base_font, 10, "bold"),
        background=colors["success"],
        foreground="#ffffff",
    )
    style.map("Success.TButton",
        background=[
            ("active", "#30d070"),
            ("pressed", "#18a050"),
            ("!active", colors["success"]),
        ],
    )
    
    # Pagination Buttons (◄ ►)
    style.configure("Pager.TButton", 
        padding=(12, 6),
        font=(base_font, 10),
        background=colors["pager_bg"],
        foreground=colors["pager_text"],
        borderwidth=1,
    )
    style.map("Pager.TButton",
        background=[
            ("active", colors["accent_light"]),
            ("!active", colors["pager_bg"]),
        ],
    )
    
    # Sidebar Buttons
    style.configure("Sidebar.TButton", 
        padding=(14, 10), 
        anchor="w",
        font=(base_font, 10),
        background=colors["sidebar"],
        foreground=colors["text_secondary"],
        borderwidth=0,
    )
    style.map("Sidebar.TButton",
        background=[
            ("active", colors["sidebar_active"]),
            ("!active", colors["sidebar"]),
        ],
        foreground=[
            ("disabled", colors["muted"]),
            ("!disabled", colors["text_secondary"]),
        ],
    )
    
    # Active Sidebar Button (Sol mavi çizgi efekti simülasyonu)
    style.configure("SidebarActive.TButton", 
        padding=(14, 10), 
        anchor="w",
        font=(base_font, 10, "bold"),
        background=colors["sidebar_active"],
        foreground=colors["accent_bright"],
        borderwidth=0,
    )
    style.map("SidebarActive.TButton",
        background=[
            ("active", colors["sidebar_active"]),
            ("!active", colors["sidebar_active"]),
        ],
        foreground=[
            ("!disabled", colors["accent_bright"]),
        ],
    )
    
    # ========================================
    # INPUT STİLLERİ (Entry, Combobox) - Görsellerden
    # ========================================
    style.configure("TEntry",
        padding=10,
        fieldbackground=colors["input_bg"],
        foreground=colors["text"],
        insertcolor=colors["accent"],
        borderwidth=1,
    )
    style.map("TEntry",
        fieldbackground=[
            ("focus", colors["input_bg"]),
            ("!focus", colors["input_bg"]),
        ],
        bordercolor=[
            ("focus", colors["input_focus"]),
        ],
    )
    
    style.configure("TCombobox",
        padding=8,
        fieldbackground=colors["input_bg"],
        foreground=colors["text"],
        arrowcolor=colors["text_secondary"],
        borderwidth=1,
    )
    style.map("TCombobox",
        fieldbackground=[
            ("readonly", colors["input_bg"]),
            ("!readonly", colors["input_bg"]),
        ],
        selectbackground=[
            ("readonly", colors["accent_light"]),
        ],
        arrowcolor=[
            ("disabled", colors["muted"]),
        ],
    )
    
    # Search Entry (Arama kutusu - üst barda)
    style.configure("Search.TEntry",
        padding=10,
        fieldbackground=colors["panel"],
        foreground=colors["text"],
        insertcolor=colors["accent"],
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
        padding=8,
        fieldbackground=colors["input_bg"],
        foreground=colors["text"],
        arrowcolor=colors["text_secondary"],
        borderwidth=1,
    )
    
    # ========================================
    # LABELFRAME - Kart stili
    # ========================================
    style.configure("TLabelframe", 
        background=colors["panel"],
        borderwidth=1,
        relief="solid",
    )
    style.configure("TLabelframe.Label", 
        background=colors["panel"], 
        foreground=colors["text"], 
        font=(base_font, 11, "bold"),
    )
    style.configure("Card.TLabelframe",
        background=colors["panel"],
        bordercolor=colors["border"],
    )
    style.configure("Card.TLabelframe.Label",
        background=colors["panel"],
        foreground=colors["text"],
        font=(base_font, 11, "bold"),
    )
    
    # ========================================
    # TREEVIEW (Tablo) - Görsellerden
    # ========================================
    style.configure("Treeview",
        background=colors["table_row"],
        fieldbackground=colors["table_row"],
        foreground=colors["text"],
        rowheight=32,  # Daha yüksek satırlar
        borderwidth=0,
        relief="flat",
    )
    style.configure("Treeview.Heading",
        background=colors["table_header"],
        foreground=colors["text_secondary"],
        font=(base_font, 10, "bold"),
        relief="flat",
        padding=(12, 10),
        borderwidth=1,
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
            ("!active", colors["table_header"]),
        ],
    )
    
    # ========================================
    # NOTEBOOK (Tabs) - Görsellerden
    # ========================================
    style.configure("TNotebook", 
        background=colors["bg"], 
        borderwidth=0,
        tabmargins=[0, 0, 0, 0],
    )
    style.configure("TNotebook.Tab", 
        padding=(18, 10),
        font=(base_font, 10),
        background=colors["tab_bg"],
        foreground=colors["muted"],
        borderwidth=0,
    )
    style.map("TNotebook.Tab",
        background=[
            ("selected", colors["tab_active_bg"]),
            ("!selected", colors["tab_bg"]),
        ],
        foreground=[
            ("selected", colors["tab_active_text"]),
            ("!selected", colors["muted"]),
        ],
    )
    
    # Alt Tab stili (nested tabs için - ör: Fatura içindeki tabs)
    style.configure("Inner.TNotebook", 
        background=colors["panel"], 
        borderwidth=0,
    )
    style.configure("Inner.TNotebook.Tab", 
        padding=(14, 8),
        font=(base_font, 10),
        background=colors["panel"],
        foreground=colors["muted"],
    )
    style.map("Inner.TNotebook.Tab",
        background=[
            ("selected", colors["accent_light"]),
            ("!selected", colors["panel"]),
        ],
        foreground=[
            ("selected", colors["accent_bright"]),
            ("!selected", colors["muted"]),
        ],
    )
    
    # ========================================
    # PROGRESSBAR
    # ========================================
    style.configure("TProgressbar",
        background=colors["accent"],
        troughcolor=colors["input_bg"],
        borderwidth=0,
        thickness=8,
    )
    
    # ========================================
    # SCALE (Slider)
    # ========================================
    style.configure("TScale",
        background=colors["bg"],
        troughcolor=colors["input_bg"],
        sliderrelief="flat",
    )
    
    # ========================================
    # CHECKBUTTON & RADIOBUTTON
    # ========================================
    style.configure("TCheckbutton",
        background=colors["bg"],
        foreground=colors["text"],
        focuscolor=colors["accent"],
        indicatorcolor=colors["input_bg"],
    )
    style.map("TCheckbutton",
        background=[
            ("active", colors["bg"]),
        ],
        indicatorcolor=[
            ("selected", colors["accent"]),
            ("!selected", colors["input_bg"]),
        ],
    )
    
    style.configure("TRadiobutton",
        background=colors["bg"],
        foreground=colors["text"],
        focuscolor=colors["accent"],
        indicatorcolor=colors["input_bg"],
    )
    style.map("TRadiobutton",
        background=[
            ("active", colors["bg"]),
        ],
        indicatorcolor=[
            ("selected", colors["accent"]),
            ("!selected", colors["input_bg"]),
        ],
    )
    
    # Panel üzerindeki checkbox/radio
    style.configure("Panel.TCheckbutton",
        background=colors["panel"],
        foreground=colors["text"],
    )
    style.map("Panel.TCheckbutton",
        background=[
            ("active", colors["panel"]),
        ],
    )
    style.configure("Panel.TRadiobutton",
        background=colors["panel"],
        foreground=colors["text"],
    )
    style.map("Panel.TRadiobutton",
        background=[
            ("active", colors["panel"]),
        ],
    )
    
    # ========================================
    # SCROLLBAR - İnce modern scrollbar
    # ========================================
    style.configure("TScrollbar",
        background=colors["border"],
        troughcolor=colors["bg"],
        arrowcolor=colors["muted"],
        borderwidth=0,
        width=10,
    )
    style.map("TScrollbar",
        background=[
            ("active", colors["accent_light"]),
            ("!active", colors["border"]),
        ],
    )
    
    # ========================================
    # MENUBUTTON
    # ========================================
    style.configure("TMenubutton",
        background=colors["btn_secondary_bg"],
        foreground=colors["text"],
        padding=(12, 8),
        borderwidth=1,
    )
    style.map("TMenubutton",
        background=[
            ("active", colors["accent_light"]),
            ("!active", colors["btn_secondary_bg"]),
        ],
    )
    
    # ========================================
    # SIZEGRIP
    # ========================================
    style.configure("TSizegrip",
        background=colors["bg"],
    )
    
    return colors


def apply_modern_style(root: tk.Tk) -> Dict[str, str]:
    """Modern tema uygula (legacy uyumluluk için).
    
    Bu fonksiyon geriye uyumluluk için korunmuştur.
    Yeni kod için apply_dark_glass_theme() kullanın.
    """
    return apply_dark_glass_theme(root)
