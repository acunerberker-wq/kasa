# -*- coding: utf-8 -*-
"""KasaPro v3 - ttk tema/stil ayarları"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

def apply_modern_style(root: tk.Tk):
    """Tek noktadan daha modern/temiz bir görünüm uygular (ek bağımlılık yok)."""
    import sys as _sys
    import tkinter.font as _tkfont

    colors = {
        "bg": "#F5F6FA",
        "panel": "#FFFFFF",
        "border": "#E5E7EB",
        "text": "#111827",
        "muted": "#6B7280",
        "accent": "#2563EB",
        "accent_light": "#DBEAFE",
        "danger": "#DC2626",
    }

    try:
        root.configure(background=colors["bg"])
    except Exception:
        pass

    # Varsayılan fontları daha okunur yap
    base_family = "Segoe UI" if _sys.platform.startswith("win") else "Calibri"
    for fname in (
        "TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont",
        "TkCaptionFont", "TkSmallCaptionFont", "TkIconFont", "TkTooltipFont"
    ):
        try:
            f = _tkfont.nametofont(fname)
            # TkHeadingFont bazı sistemlerde bold geliyor; onu bozmayalım
            if fname == "TkHeadingFont":
                f.configure(family=base_family, size=max(10, int(f.cget("size"))))
            else:
                f.configure(family=base_family, size=10)
        except Exception:
            pass

    # Klasik tk widget'lara da düzgün varsayılan renkler
    try:
        root.option_add("*Text.background", colors["panel"])
        root.option_add("*Text.foreground", colors["text"])
        root.option_add("*Text.insertBackground", colors["text"])
        root.option_add("*Listbox.background", colors["panel"])
        root.option_add("*Listbox.foreground", colors["text"])
        root.option_add("*Listbox.selectBackground", colors["accent_light"])
        root.option_add("*Listbox.selectForeground", colors["text"])
    except Exception:
        pass

    style = ttk.Style(root)

    # Tema seçimi
    for t in (("vista" if _sys.platform.startswith("win") else ""), "clam", "default"):
        if not t:
            continue
        try:
            style.theme_use(t)
            break
        except Exception:
            pass

    # Global stil
    try:
        style.configure(".", font=(base_family, 10))
    except Exception:
        pass
    style.configure("TFrame", background=colors["bg"])
    style.configure("TLabel", background=colors["bg"], foreground=colors["text"])
    style.configure("TSeparator", background=colors["border"])

    # Kart/panel görünümleri
    style.configure("Panel.TFrame", background=colors["panel"])
    style.configure("Topbar.TFrame", background=colors["panel"])
    style.configure("TopTitle.TLabel", background=colors["panel"], foreground=colors["text"], font=(base_family, 15, "bold"))
    style.configure("TopSub.TLabel", background=colors["panel"], foreground=colors["muted"])

    # Sol menü
    style.configure("Sidebar.TFrame", background=colors["panel"])
    style.configure("SidebarTitle.TLabel", background=colors["panel"], foreground=colors["text"], font=(base_family, 18, "bold"))
    style.configure("SidebarSub.TLabel", background=colors["panel"], foreground=colors["muted"])
    style.configure("Sidebar.TButton", padding=(12, 10), anchor="w", background=colors["panel"])
    style.configure("SidebarActive.TButton", padding=(12, 10), anchor="w", background=colors["accent_light"])
    style.map(
        "Sidebar.TButton",
        background=[("active", "#F3F4F6"), ("!active", colors["panel"])],
        foreground=[("disabled", "#9CA3AF"), ("!disabled", colors["text"])],
    )
    style.map(
        "SidebarActive.TButton",
        background=[("active", colors["accent_light"]), ("!active", colors["accent_light"])],
        foreground=[("disabled", "#9CA3AF"), ("!disabled", colors["accent"])],
    )

    # Sol menü bölüm başlığı (Tanımlar/İşlemler gibi)
    style.configure(
        "SidebarSection.TLabel",
        background=colors["panel"],
        foreground=colors["muted"],
        font=(base_family, 9, "bold"),
        padding=(12, 6),
    )


    # Genel butonlar
    style.configure("TButton", padding=(12, 8))
    style.map("TButton", foreground=[("disabled", "#9CA3AF")])

    # Buton varyantları
    style.configure("Primary.TButton", padding=(12, 8), background=colors["accent"], foreground="#ffffff")
    style.map(
        "Primary.TButton",
        background=[("active", "#1D4ED8"), ("!active", colors["accent"])],
        foreground=[("disabled", "#E5E7EB"), ("!disabled", "#ffffff")],
    )
    style.configure("Secondary.TButton", padding=(12, 8), background=colors["panel"], foreground=colors["text"])
    style.map(
        "Secondary.TButton",
        background=[("active", "#F3F4F6"), ("!active", colors["panel"])],
        foreground=[("disabled", "#9CA3AF"), ("!disabled", colors["text"])],
    )
    style.configure("Danger.TButton", padding=(12, 8), background=colors["danger"], foreground="#ffffff")
    style.map(
        "Danger.TButton",
        background=[("active", "#B91C1C"), ("!active", colors["danger"])],
        foreground=[("disabled", "#FCA5A5"), ("!disabled", "#ffffff")],
    )

    # Giriş alanları
    style.configure("TEntry", padding=6)
    style.configure("TCombobox", padding=4)
    style.configure("Error.TEntry", fieldbackground="#FEE2E2", foreground=colors["text"])
    style.configure("Error.TCombobox", fieldbackground="#FEE2E2", foreground=colors["text"])

    # LabelFrame
    style.configure("TLabelframe", background=colors["bg"])
    style.configure("TLabelframe.Label", background=colors["bg"], foreground=colors["text"], font=(base_family, 10, "bold"))

    # Treeview
    style.configure(
        "Treeview",
        background=colors["panel"],
        fieldbackground=colors["panel"],
        foreground=colors["text"],
        rowheight=26,
        bordercolor=colors["border"],
        borderwidth=1,
        relief="flat",
    )
    style.configure(
        "Treeview.Heading",
        background="#F3F4F6",
        foreground=colors["text"],
        font=(base_family, 10, "bold"),
        relief="flat",
        padding=(8, 8),
    )
    style.map(
        "Treeview",
        background=[("selected", colors["accent_light"])],
        foreground=[("selected", colors["text"])],
    )

    # Notebook
    style.configure("TNotebook", background=colors["bg"], borderwidth=0)
    style.configure("TNotebook.Tab", padding=(12, 8))
    style.map("TNotebook.Tab", foreground=[("selected", colors["text"]), ("!selected", colors["muted"])])

    # Status bar
    style.configure("Status.TLabel", background=colors["panel"], foreground=colors["muted"], padding=(12, 6))

    return colors
