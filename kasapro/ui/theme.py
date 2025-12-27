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
# RENK PALETİ - KasaPro Tasarım Sistemi
# ============================================================================

# Light theme (Ana tema - yeni renk paleti)
COLORS_LIGHT: Dict[str, str] = {
    # Arkaplan / Yüzeyler
    "bg": "#F8F7FA",                # App arkaplan (çok açık soğuk gri)
    "bg_workspace": "#FFFFFF",      # Çalışma alanı (okunurluk için beyaz)
    "panel": "#F3F1F7",             # Card / panel yüzeyi
    "panel_hover": "#EBE9F2",       # Panel hover
    "muted_surface": "#EBE9F2",     # Muted yüzey (toolbar/şerit)
    
    # Sidebar / Koyu Alanlar
    "sidebar": "#111125",           # Sidebar BG
    "sidebar_hover": "#242545",     # Sidebar hover
    "sidebar_active": "#242545",    # Koyu üst bar / panel
    
    # Metin
    "text": "#181839",              # Text Primary
    "text_secondary": "#4A4A6D",    # Text Muted
    "text_on_dark": "#EDEBF3",      # Text on Dark
    "muted": "#4A4A6D",             # Muted text
    "placeholder": "#888AA2",       # Placeholder
    
    # Border / Ayraçlar
    "border": "#CBCADA",            # Border
    "border_strong": "#A6AABE",     # Border Strong
    "border_light": "#DBDAE8",      # Hafif border
    
    # Marka / Accent
    "accent": "#02095B",            # Primary Accent
    "accent_hover": "#20276F",      # Hover
    "accent_pressed": "#020854",    # Pressed
    "accent_disabled": "#898CB2",   # Disabled
    "accent_light": "#DBDAE8",      # Açık aksan (selection)
    
    # Secondary (Deep)
    "secondary": "#000537",         # Secondary
    "secondary_hover": "#1F234F",   # Secondary Hover
    "secondary_pressed": "#000533", # Secondary Pressed
    "secondary_disabled": "#888AA2",# Secondary Disabled
    
    # Pill / Sekme (açık gri butonlar)
    "pill_bg": "#DBDAE8",           # Pill BG
    "pill_hover": "#DFDEEA",        # Pill Hover
    "pill_pressed": "#CECDDA",      # Pill Pressed
    "pill_disabled": "#ECEBF3",     # Pill Disabled
    "pill_border": "#C9C8D9",       # Pill Border
    "pill_text": "#181839",         # Pill Text
    
    # Durum renkleri
    "success": "#16A34A",           # Success
    "success_bg": "#e8f5ec",        # Success arka plan
    "warning": "#F59E0B",           # Warning
    "warning_bg": "#fef3e0",        # Warning arka plan
    "danger": "#EF4444",            # Danger
    "danger_bg": "#fde8e8",         # Danger arka plan
    "info": "#3B82F6",              # Info
    "info_bg": "#e8f0fe",           # Info arka plan
    
    # Input stilleri
    "input_bg": "#FFFFFF",          # Input arka plan
    "input_border": "#CBCADA",      # Input kenar
    "input_focus": "#02095B",       # Focus kenar
    
    # Tablo/Treeview
    "table_header": "#EBE9F2",      # Header arka plan
    "table_header_border": "#CBCADA", # Header alt border
    "table_row": "#FFFFFF",         # Normal satır
    "table_row_alt": "#F8F7FA",     # Alternatif satır
    "selection": "#DBDAE8",         # Seçim
    "gridline": "#CBCADA",          # Tablo çizgileri
    
    # Tab stilleri
    "tab_bg": "#EBE9F2",            # Pasif tab
    "tab_active_bg": "#02095B",     # Aktif tab arka plan
    "tab_active_text": "#EDEBF3",   # Aktif tab metin
    "tab_border": "#CBCADA",        # Tab border
    
    # Buton stilleri
    "btn_primary_bg": "#02095B",    # Primary arka plan
    "btn_primary_hover": "#20276F", # Primary hover
    "btn_primary_border": "#010538",# Primary kenar
    "btn_secondary_bg": "#000537",  # Secondary arka plan
    "btn_secondary_border": "#000320", # Secondary kenar
    "btn_ghost_bg": "#F3F1F7",      # Ghost arka plan
    "btn_ghost_border": "#CBCADA",  # Ghost kenar
    "btn_ghost_hover": "#EBE9F2",   # Ghost hover
}

# Dark theme (Sidebar ve koyu alanlar için)
COLORS_DARK: Dict[str, str] = {
    # Ana arka planlar - Sidebar/Koyu alanlar
    "bg": "#111125",                # Sidebar BG
    "bg_glow": "#1a1a35",           # Glow efekt alanı
    "bg_dark": "#0a0a18",           # En koyu arka plan
    
    # Panel/Kart renkleri
    "panel": "#1a1a35",             # Kart zemini
    "panel_hover": "#242545",       # Kart hover
    "panel_border": "#303055",      # Kart kenarı
    "sidebar": "#111125",           # Sidebar
    "sidebar_active": "#242545",    # Aktif sidebar item
    
    # Kenar renkleri
    "border": "#303055",            # Genel kenar
    "border_light": "#242545",      # Hafif kenar
    "border_accent": "#02095B",     # Vurgulu kenar
    
    # Metin renkleri
    "text": "#EDEBF3",              # Ana metin (Text on Dark)
    "text_secondary": "#b8b8d0",    # İkincil
    "muted": "#4A4A6D",             # Soluk
    "placeholder": "#606080",       # Placeholder
    
    # Aksan renkleri - Primary
    "accent": "#02095B",            # Ana aksan
    "accent_dark": "#000537",       # Koyu aksan
    "accent_light": "#20276F",      # Açık aksan
    "accent_bright": "#3a4088",     # En parlak
    "accent_hover": "#20276F",      # Hover
    "accent_glow": "#02095B",       # Glow efekt
    
    # Input stilleri
    "input_bg": "#1a1a35",          # Input arka plan
    "input_border": "#303055",      # Input kenar
    "input_focus": "#02095B",       # Focus kenar
    
    # Durum renkleri
    "danger": "#EF4444",            # Tehlike
    "danger_bg": "#2a1a1a",         # Tehlike arka plan
    "success": "#16A34A",           # Başarı
    "success_bg": "#1a2a1a",        # Başarı arka plan
    "warning": "#F59E0B",           # Uyarı
    "warning_bg": "#2a2518",        # Uyarı arka plan
    "info": "#3B82F6",              # Info
    "info_bg": "#1a2035",           # Info arka plan
    
    # Tablo/Treeview
    "table_header": "#1a1a35",      # Header arka plan
    "table_header_border": "#303055", # Header alt border
    "table_row": "#111125",         # Normal satır
    "table_row_alt": "#0a0a18",     # Alternatif satır
    "selection": "#242545",         # Seçim
    "gridline": "#242545",          # Tablo çizgileri
    
    # Tab stilleri
    "tab_bg": "#1a1a35",            # Pasif tab
    "tab_active_bg": "#02095B",     # Aktif tab arka plan
    "tab_active_text": "#EDEBF3",   # Aktif tab metin
    "tab_border": "#303055",        # Tab border
    
    # Badge/Etiket renkleri
    "badge_in_bg": "#1a2a1a",       # Giriş badge
    "badge_in_border": "#16A34A",   # Giriş kenar
    "badge_in_text": "#16A34A",     # Giriş metin
    "badge_out_bg": "#2a1a1a",      # Çıkış badge
    "badge_out_border": "#EF4444",  # Çıkış kenar
    "badge_out_text": "#EF4444",    # Çıkış metin
    
    # Buton stilleri
    "btn_primary_bg": "#02095B",    # Primary arka plan
    "btn_primary_hover": "#20276F", # Primary hover
    "btn_primary_border": "#3a4088",# Primary kenar
    "btn_secondary_bg": "#1a1a35",  # Secondary arka plan
    "btn_secondary_border": "#303055", # Secondary kenar
    "btn_ghost_bg": "#1a1a35",      # Ghost arka plan
    "btn_ghost_border": "#303055",  # Ghost kenar
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
    
    # Genel buton (3D görünüm)
    style.configure("TButton", 
        padding=(16, 8),
        font=(base_font, 10),
        background=colors["btn_ghost_bg"],
        foreground=colors["text_secondary"],
        borderwidth=2,
        relief="raised",
        lightcolor=colors["border_accent"],
        darkcolor=colors["bg_dark"],
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
        relief=[
            ("pressed", "sunken"),
            ("!pressed", "raised"),
        ],
    )
    
    # Primary Button (Parlak mavi - "Yeni", "Kaydet + Yeni", "Yenile")
    style.configure("Primary.TButton", 
        padding=(16, 8),
        font=(base_font, 10, "bold"),
        background=colors["btn_primary_bg"],
        foreground="#ffffff",
        borderwidth=2,
        relief="raised",
        lightcolor=colors["accent_glow"],
        darkcolor=colors["accent_dark"],
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
        relief=[
            ("pressed", "sunken"),
            ("!pressed", "raised"),
        ],
    )
    
    # Secondary Button (Koyu arka plan, açık kenar - "Detay", "İptal")
    style.configure("Secondary.TButton", 
        padding=(16, 8),
        font=(base_font, 10),
        background=colors["btn_secondary_bg"],
        foreground=colors["text"],
        borderwidth=2,
        relief="raised",
        lightcolor=colors["border_accent"],
        darkcolor=colors["bg_dark"],
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
        relief=[
            ("pressed", "sunken"),
            ("!pressed", "raised"),
        ],
    )
    
    # Ghost Button (Hafif 3D görünüm)
    style.configure("Ghost.TButton", 
        padding=(16, 8),
        font=(base_font, 10),
        background=colors["btn_ghost_bg"],
        foreground=colors["text_secondary"],
        borderwidth=2,
        relief="raised",
        lightcolor=colors["border"],
        darkcolor=colors["bg_dark"],
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
        relief=[
            ("pressed", "sunken"),
            ("!pressed", "raised"),
        ],
    )
    
    # Toolbar Button (Araç çubuğu - "Excel ile Aktar", "PDF", "Sil")
    style.configure("Toolbar.TButton", 
        padding=(12, 6),
        font=(base_font, 10),
        background=colors["btn_secondary_bg"],
        foreground=colors["text_secondary"],
        borderwidth=2,
        relief="raised",
        lightcolor=colors["border"],
        darkcolor=colors["bg_dark"],
    )
    style.map("Toolbar.TButton",
        background=[
            ("active", colors["accent_light"]),
            ("!active", colors["btn_secondary_bg"]),
        ],
        relief=[
            ("pressed", "sunken"),
            ("!pressed", "raised"),
        ],
    )
    
    # Danger Button (Sil, İptal gibi)
    style.configure("Danger.TButton", 
        padding=(16, 8),
        font=(base_font, 10, "bold"),
        background=colors["danger"],
        foreground="#ffffff",
        borderwidth=2,
        relief="raised",
        lightcolor="#ff8080",
        darkcolor="#aa2020",
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
        relief=[
            ("pressed", "sunken"),
            ("!pressed", "raised"),
        ],
    )
    
    # Success Button
    style.configure("Success.TButton", 
        padding=(16, 8),
        font=(base_font, 10, "bold"),
        background=colors["success"],
        foreground="#ffffff",
        borderwidth=2,
        relief="raised",
        lightcolor="#40e080",
        darkcolor="#108040",
    )
    style.map("Success.TButton",
        background=[
            ("active", "#30d070"),
            ("pressed", "#18a050"),
            ("!active", colors["success"]),
        ],
        relief=[
            ("pressed", "sunken"),
            ("!pressed", "raised"),
        ],
    )
    
    # Pagination Buttons (◄ ►)
    style.configure("Pager.TButton", 
        padding=(12, 6),
        font=(base_font, 10),
        background=colors["pager_bg"],
        foreground=colors["pager_text"],
        borderwidth=2,
        relief="raised",
        lightcolor=colors["border"],
        darkcolor=colors["bg_dark"],
    )
    style.map("Pager.TButton",
        background=[
            ("active", colors["accent_light"]),
            ("!active", colors["pager_bg"]),
        ],
        relief=[
            ("pressed", "sunken"),
            ("!pressed", "raised"),
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
