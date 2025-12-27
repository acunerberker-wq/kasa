# -*- coding: utf-8 -*-
"""KasaPro UI Theme Smoke Test

Bu modül, yeni Premium Dark Glass temasının düzgün çalıştığını doğrular.
"""

from __future__ import annotations

import sys
import time
from typing import List, Tuple

import tkinter as tk
from tkinter import ttk


def run_theme_smoke_test() -> Tuple[bool, List[str]]:
    """Tema smoke testini çalıştır.
    
    Returns:
        (success, messages) tuple'ı
    """
    messages: List[str] = []
    success = True
    
    try:
        # Tema modülünü import et
        from kasapro.ui.theme import (
            apply_dark_glass_theme,
            get_colors,
            get_base_font,
            COLORS_DARK,
            COLORS_LIGHT,
        )
        messages.append("✓ Tema modülü import edildi")
    except ImportError as e:
        messages.append(f"✗ Tema modülü import hatası: {e}")
        return False, messages
    
    try:
        # Legacy style modülü kontrolü
        from kasapro.ui.style import apply_modern_style
        messages.append("✓ Style modülü (legacy) import edildi")
    except ImportError as e:
        messages.append(f"✗ Style modülü import hatası: {e}")
        return False, messages
    
    # Renk paleti kontrolleri
    required_colors = [
        "bg", "panel", "text", "accent", "danger", "success",
        "sidebar", "border", "muted", "selection"
    ]
    
    missing_colors = [c for c in required_colors if c not in COLORS_DARK]
    if missing_colors:
        messages.append(f"✗ Eksik renkler: {missing_colors}")
        success = False
    else:
        messages.append(f"✓ Tüm gerekli renkler mevcut ({len(COLORS_DARK)} adet)")
    
    # Font kontrolü
    font = get_base_font()
    if font:
        messages.append(f"✓ Base font: {font}")
    else:
        messages.append("✗ Base font bulunamadı")
        success = False
    
    # Tkinter testi
    try:
        root = tk.Tk()
        root.withdraw()
        messages.append("✓ Tkinter root oluşturuldu")
    except tk.TclError as e:
        messages.append(f"✗ Tkinter başlatılamadı: {e}")
        return False, messages
    
    try:
        # Tema uygula
        colors = apply_dark_glass_theme(root)
        messages.append("✓ Dark glass tema uygulandı")
        
        # Renklerin döndüğünü kontrol et
        if colors and "accent" in colors:
            messages.append(f"✓ Aksan rengi: {colors['accent']}")
        else:
            messages.append("✗ Tema renkleri döndürülmedi")
            success = False
        
    except Exception as e:
        messages.append(f"✗ Tema uygulama hatası: {e}")
        success = False
    
    # Stil kontrolleri
    style = ttk.Style(root)
    
    required_styles = [
        "TFrame", "Panel.TFrame", "Sidebar.TFrame",
        "TLabel", "TopTitle.TLabel", "SidebarTitle.TLabel",
        "TButton", "Primary.TButton", "Ghost.TButton", "Danger.TButton",
        "Sidebar.TButton", "SidebarActive.TButton",
        "TEntry", "TCombobox",
        "Treeview", "Treeview.Heading",
        "TNotebook", "TNotebook.Tab",
    ]
    
    missing_styles = []
    for s in required_styles:
        try:
            # Stil var mı kontrol et
            style.configure(s)
        except tk.TclError:
            missing_styles.append(s)
    
    if missing_styles:
        messages.append(f"✗ Eksik stiller: {missing_styles}")
        success = False
    else:
        messages.append(f"✓ Tüm stiller mevcut ({len(required_styles)} adet)")
    
    # Widget oluşturma testleri
    try:
        frame = ttk.Frame(root, style="Panel.TFrame")
        messages.append("✓ Panel.TFrame oluşturuldu")
    except Exception as e:
        messages.append(f"✗ Panel.TFrame hatası: {e}")
        success = False
    
    try:
        label = ttk.Label(root, text="Test", style="TopTitle.TLabel")
        messages.append("✓ TopTitle.TLabel oluşturuldu")
    except Exception as e:
        messages.append(f"✗ TopTitle.TLabel hatası: {e}")
        success = False
    
    try:
        btn = ttk.Button(root, text="Test", style="Primary.TButton")
        messages.append("✓ Primary.TButton oluşturuldu")
    except Exception as e:
        messages.append(f"✗ Primary.TButton hatası: {e}")
        success = False
    
    try:
        tree = ttk.Treeview(root, columns=("col1",), show="headings")
        messages.append("✓ Treeview oluşturuldu")
    except Exception as e:
        messages.append(f"✗ Treeview hatası: {e}")
        success = False
    
    try:
        nb = ttk.Notebook(root)
        messages.append("✓ Notebook oluşturuldu")
    except Exception as e:
        messages.append(f"✗ Notebook hatası: {e}")
        success = False
    
    # Badge stilleri kontrolü
    badge_styles = ["Badge.TLabel", "BadgeSuccess.TLabel", "BadgeDanger.TLabel", 
                    "BadgeIn.TLabel", "BadgeOut.TLabel"]
    for bs in badge_styles:
        try:
            ttk.Label(root, text="Badge", style=bs)
        except Exception:
            messages.append(f"✗ {bs} oluşturulamadı")
            success = False
    
    messages.append("✓ Badge stilleri kontrol edildi")
    
    # Temizlik
    try:
        root.destroy()
        messages.append("✓ Tkinter root temizlendi")
    except Exception:
        pass
    
    return success, messages


def main():
    """Test runner."""
    print("=" * 60)
    print("KasaPro Premium Dark Theme - Smoke Test")
    print("=" * 60)
    print()
    
    success, messages = run_theme_smoke_test()
    
    for msg in messages:
        print(msg)
    
    print()
    print("=" * 60)
    if success:
        print("SONUÇ: ✓ TÜM TESTLER GEÇTİ")
    else:
        print("SONUÇ: ✗ BAZI TESTLER BAŞARISIZ")
    print("=" * 60)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
