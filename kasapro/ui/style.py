# -*- coding: utf-8 -*-
"""KasaPro v3 - ttk tema/stil ayarları"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .theme_tokens import DESIGN_TOKENS

def apply_modern_style(root: tk.Tk):
    """Tek noktadan modern/temiz bir görünüm uygular (ek bağımlılık yok)."""
    import sys as _sys
    import tkinter.font as _tkfont

    design_tokens = DESIGN_TOKENS
    components_layout = {
        "AppShell": {
            "description": "Uygulamanın ana kabuğu: Topbar + Sidebar + Content",
            "slots": ["TopBar", "SideBar", "ContentArea"],
            "behaviors": [
                "Responsive değil; desktop layout (fixed sidebar).",
                "ContentArea scrollable.",
            ],
        },
        "TopBar": {
            "parts": ["BrandMark", "GlobalSearch", "QuickActions", "UserMenu"],
            "states": {
                "notification_badge": [0, ">0"],
                "sync_state": ["idle", "syncing", "error"],
            },
        },
        "SideBar": {
            "parts": ["NavGroup(primary)", "NavItem(active/inactive/disabled)", "NavFooter(Settings, Import)"],
            "states": {
                "collapsed": False,
            },
        },
    }
    atoms = {
        "Icon": {
            "props": ["name", "size=24", "tone=default|accent|muted"],
        },
        "Badge": {
            "props": ["text|count", "variant=info|success|warning|danger|neutral"],
        },
        "PillStatus": {
            "props": ["label", "state=success|warning|danger|neutral"],
            "examples": ["Ödendi", "Ödenmedi", "Kısmi", "Acil Stok"],
        },
        "Divider": {
            "props": ["orientation=horizontal|vertical"],
        },
        "Avatar": {
            "props": ["image_url|initials", "size=28|36|48"],
        },
    }
    form_atoms = {
        "TextInput": {
            "props": ["label", "placeholder", "value", "leftIcon?", "rightIcon?", "state=default|focus|error|disabled"],
        },
        "PasswordInput": {
            "props": ["label", "placeholder", "value", "showToggle=true"],
        },
        "Select": {
            "props": ["label", "options", "value", "searchable=false"],
        },
        "DateRangePicker": {
            "props": ["start", "end"],
        },
        "Checkbox": {
            "props": ["label", "checked"],
        },
        "PrimaryButton": {
            "props": ["label", "iconLeft?", "loading=false", "disabled=false"],
        },
        "SecondaryButton": {
            "props": ["label", "iconLeft?", "disabled=false"],
        },
        "DangerButton": {
            "props": ["label", "iconLeft?", "disabled=false"],
        },
    }
    data_components = {
        "StatCard": {
            "description": "KPI kartı (başlık + değer + mini sparkline)",
            "props": ["title", "value", "delta?", "sparkline_data?", "accent=blue|teal|amber|green"],
            "states": ["normal", "hover"],
        },
        "ChartCard": {
            "description": "Başlık + legend + line chart (Gelir/Gider)",
            "props": ["title", "series[]", "legend=true", "rightChip?"],
            "behaviors": [
                "Hover tooltip",
                "Empty state: 'Veri yok'",
            ],
        },
        "WidgetCard": {
            "description": "Sağ sütundaki küçük kartlar (Kritik Stok, Ödenmemiş Faturalar, Hatırlatmalar)",
            "props": ["title", "rows[]", "action?", "iconRight?"],
        },
        "DataTable": {
            "description": "Zebra olmayan, ince çizgili tablo; satır hover + seçili satır",
            "props": ["columns[]", "rows[]", "rowActions?", "selectable=false"],
            "states": ["loading", "empty", "error"],
        },
        "RightDetailPanel": {
            "description": "Cariler ekranındaki sağ detay paneli",
            "props": ["header(avatar,name,subtitle)", "metaList[]", "actions[]"],
        },
    }
    overlays = {
        "Toast": {
            "props": ["title", "message?", "variant=success|info|warning|danger", "actionLabel?"],
            "behavior": "Auto-dismiss 3-4sn; sağ üstte stack",
        },
        "Modal": {
            "props": ["title", "body", "primaryAction", "secondaryAction"],
        },
        "InlineProgressChip": {
            "props": ["label='Senkronize ediliyor…'", "spinner=true"],
        },
    }
    screen_dashboard = {
        "layout": "AppShell",
        "topbar": [
            "TopBar(BrandMark, GlobalSearch, QuickActions, UserMenu)",
        ],
        "sidebar": [
            {
                "SideBar": {
                    "items": [
                        "NavItem: Dashboard (active)",
                        "NavItem: Kasa",
                        "NavItem: Cariler",
                        "NavItem: Cari Hareket/Ekstre",
                        "NavItem: Fatura",
                        "NavItem: Banka",
                        "NavItem: Maaş",
                        "NavItem: Raporlar",
                        "NavItem: Import",
                        "NavItem: Ayarlar",
                    ],
                },
            },
        ],
        "content": [
            {
                "PageGrid(columns=12, gap=24)": {
                    "row1": [
                        'StatCard(title="Günlük Ciro", value="₺12.450", sparkline=true)',
                        'StatCard(title="Tahsilat", value="₺8.950", sparkline=true)',
                        'StatCard(title="Borç / Alacak", value="₺15.200", delta="₺7.800")',
                        'StatCard(title="Kasa Bakiyesi", value="₺32.450", sparkline=true)',
                        'PrimaryButton(label="Yeni İşlem", iconLeft="plus")',
                    ],
                    "row2": [
                        (
                            'ChartCard(title="Son 30 Gün Nakit Akışı", series=[Gelir, Gider], '
                            'rightChip=InlineProgressChip("Senkronize ediliyor…"))'
                        ),
                        "RightColumn(col-span 3): WidgetCard(Kritik Stok/Ödenmemiş Faturalar/Hatırlatmalar)",
                    ],
                    "row3": [
                        (
                            'DataTable(title="Son İşlemler", columns=[Tarih, Tür, Açıklama, Tutar, Durum], '
                            "cellWidgets=[Durum: PillStatus(success|warning|danger)])"
                        ),
                        "Stack(col-span 3): WidgetCard(Kritik Stok mini + Ödenmemiş Faturalar mini)",
                    ],
                },
            },
        ],
    }
    screen_login = {
        "layout": "CenteredPanel",
        "background": "dark gradient + soft blur",
        "content": [
            (
                "AuthCard(radius=14, shadow=soft-lg): BrandMark + TextInput(E-posta) + "
                "PasswordInput(Şifre) + Checkbox(Beni hatırla) + PrimaryButton(Giriş Yap)"
            ),
            "InlineLoadingRow(visible=loading, text='Giriş Yap…')",
            "LinkButton(label='Şifremi unuttum')",
        ],
    }
    screen_kasa = {
        "layout": "AppShell",
        "content": [
            {
                "PageHeader": {
                    "title": "Kasa",
                    "leftActions": [
                        'PrimaryButton(label="Gelir Ekle", iconLeft="plus")',
                        'DangerButton(label="Gider Ekle", iconLeft="minus")',
                    ],
                    "rightAction": 'SecondaryButton(label="Fatura Oluştur", iconLeft="file-plus")',
                },
            },
            {
                "FilterBar": [
                    'DateRangePicker(start="01 Nisan 2024", end="21 Nisan 2024")',
                    'Select(label="İşlem Türü", options=[Tahsilat, Ödeme, Satış, ...])',
                    'Select(label="Kategori", options=[Satış, Ofis, ...])',
                    'Select(label="Hepsi", options=[...])',
                    'Select(label="Kullanıcı", options=[...])',
                    'IconButton(icon="plus")',
                ],
            },
            {
                "StatRow": [
                    'StatCard(title="Bugün", value="₺1.680", accent=green)',
                    'StatCard(title="Bu Hafta", value="₺8.450", accent=amber)',
                    'StatCard(title="Bu Ay", value="₺16.750", accent=blue)',
                ],
            },
            {
                "DataTable": {
                    "columns": ["Tarih", "Tür", "Açıklama", "Kategori", "Tutar(₺)", "Ödeme Tipi", "Etiket", "Durum"],
                    "rowWidgets": ["Durum: PillStatus", "Etiket: Badge"],
                },
            },
        ],
    }
    screen_banka = {
        "layout": "AppShell",
        "content": [
            {
                "PageHeader": {
                    "title": "Banka",
                },
            },
            {
                "ActionBar": [
                    'PrimaryButton(label="Ekstre İçe Aktar", iconLeft="upload")',
                    'SecondaryButton(label="Otomatik Eşleştir", iconLeft="sparkles")',
                    'SecondaryButton(label="Kural Oluştur", iconLeft="settings")',
                ],
            },
            {
                "ThreeColumnLayout": {
                    "left(col=3)": [
                        "AccountListCard(items=[BankAccountItem(bank='İş Bankası', iban_masked=true, active=true), ...])",
                    ],
                    "center(col=6)": [
                        (
                            "DataTable(columns=[Tarih, Açıklama, Borç, Alacak, Kategori, Cari, Eşleşme], "
                            "rowWidgets=[Eşleşme: PillStatus], highlight_row_when_matched=true)"
                        ),
                    ],
                    "right(col=3)": [
                        "SuggestionPanel(title='Eşleştirme Önerileri'): SuggestionCard(...)",
                        "RuleSuggestionBox(text='Bu tür işlemler için eşleşme kuralı oluştur', action='Kural oluştur')",
                    ],
                },
            },
        ],
    }
    screen_fatura = {
        "layout": "AppShell",
        "content": [
            {
                "PageHeader": {
                    "title": "Fatura",
                    "rightAction": 'PrimaryButton(label="Fatura Oluştur", iconLeft="plus")',
                },
            },
            {
                "Tabs": {
                    "items": ["Satış(active)", "Alış", "Taslak", "İade"],
                },
            },
            {
                "FilterBar": [
                    "DateRangePicker",
                    'Select(label="Tümü", options=[...])',
                    'FilterChips: Chip("Ödendi") + Chip("Ödenmedi") + Chip("Kısmi")',
                    'IconButton(icon="more")',
                ],
            },
            {
                "DataTable": {
                    "columns": ["Fatura No", "Tarih", "Cari", "Toplam", "KDV", "Durum", "Vade", "Aksiyonlar"],
                    "cellWidgets": [
                        "Durum: PillStatus(Ödendi/Ödenmedi/Kısmi/Gönderiliyor…)",
                        "Aksiyonlar: IconButton(PDF/Mail/WhatsApp/Sil)",
                    ],
                },
            },
            'Toast(variant=success, title="Gönderildi", actionLabel="Tamam")',
        ],
    }

    colors = {
        "bg": design_tokens["colors"]["bg_app"],
        "panel": design_tokens["colors"]["bg_surface"],
        "panel_alt": design_tokens["colors"]["bg_surface_2"],
        "panel_high": "#1C2538",
        "border": design_tokens["colors"]["border"],
        "text": design_tokens["colors"]["text_primary"],
        "text_secondary": design_tokens["colors"]["text_secondary"],
        "muted": design_tokens["colors"]["text_muted"],
        "accent": design_tokens["colors"]["accent_primary"],
        "accent_soft": "#1E3A8A",
        "success": design_tokens["colors"]["success"],
        "warning": design_tokens["colors"]["warning"],
        "danger": design_tokens["colors"]["danger"],
        "info": design_tokens["colors"]["info"],
    }
    spacing = {
        "xxs": 4,
        "xs": 8,
        "sm": 12,
        "md": 16,
        "lg": 24,
        "xl": 32,
        "2xl": 40,
        "3xl": 48,
    }
    radius = {
        "card": design_tokens["layout"]["card_radius"],
        "control": 12,
    }
    shadows = {
        "surface": (0, 8, 24, "#0B1220"),
        "elevated": (0, 16, 40, "#0B1220"),
    }

    try:
        root.configure(background=colors["bg"])
    except Exception:
        pass

    # Varsayılan fontları daha okunur yap
    base_family = "Segoe UI" if _sys.platform.startswith("win") else "Helvetica"
    base_size = design_tokens["typography"]["body"]
    for fname in (
        "TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont",
        "TkCaptionFont", "TkSmallCaptionFont", "TkIconFont", "TkTooltipFont"
    ):
        try:
            f = _tkfont.nametofont(fname)
            # TkHeadingFont bazı sistemlerde bold geliyor; onu bozmayalım
            if fname == "TkHeadingFont":
                f.configure(family=base_family, size=max(base_size, int(f.cget("size"))))
            else:
                f.configure(family=base_family, size=base_size)
        except Exception:
            pass

    # Klasik tk widget'lara da düzgün varsayılan renkler
    try:
        root.option_add("*Text.background", colors["panel"])
        root.option_add("*Text.foreground", colors["text"])
        root.option_add("*Text.insertBackground", colors["text"])
        root.option_add("*Listbox.background", colors["panel"])
        root.option_add("*Listbox.foreground", colors["text"])
        root.option_add("*Listbox.selectBackground", colors["accent_soft"])
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
        style.configure(".", font=(base_family, base_size))
    except Exception:
        pass
    style.configure("TFrame", background=colors["bg"])
    style.configure("TLabel", background=colors["bg"], foreground=colors["text"])
    style.configure("TSeparator", background=colors["border"])

    # Kart/panel görünümleri
    style.configure("Panel.TFrame", background=colors["panel"])
    style.configure("Topbar.TFrame", background=colors["panel"])
    style.configure(
        "TopTitle.TLabel",
        background=colors["panel"],
        foreground=colors["text"],
        font=(base_family, 20, "bold"),
    )
    style.configure("TopSub.TLabel", background=colors["panel"], foreground=colors["muted"])
    style.configure("Panel.TLabel", background=colors["panel"], foreground=colors["text"])
    style.configure("Muted.TLabel", background=colors["panel"], foreground=colors["muted"])
    style.configure(
        "H1.TLabel",
        background=colors["panel"],
        foreground=colors["text"],
        font=(base_family, design_tokens["typography"]["h1"], "bold"),
    )
    style.configure(
        "H2.TLabel",
        background=colors["panel"],
        foreground=colors["text"],
        font=(base_family, design_tokens["typography"]["h2"], "bold"),
    )
    style.configure(
        "Body.TLabel",
        background=colors["panel"],
        foreground=colors["text"],
        font=(base_family, design_tokens["typography"]["body"]),
    )

    # Sol menü
    style.configure("Sidebar.TFrame", background=colors["panel"])
    style.configure("SidebarTitle.TLabel", background=colors["panel"], foreground=colors["text"], font=(base_family, 18, "bold"))
    style.configure("SidebarSub.TLabel", background=colors["panel"], foreground=colors["muted"])
    style.configure("Sidebar.TButton", padding=(spacing["md"], spacing["sm"]), anchor="w", background=colors["panel"])
    style.configure("SidebarActive.TButton", padding=(spacing["md"], spacing["sm"]), anchor="w", background=colors["accent_soft"])
    style.map(
        "Sidebar.TButton",
        background=[("active", colors["panel_alt"]), ("!active", colors["panel"])],
        foreground=[("disabled", "#6B7280"), ("!disabled", colors["text"])],
    )
    style.map(
        "SidebarActive.TButton",
        background=[("active", colors["accent_soft"]), ("!active", colors["accent_soft"])],
        foreground=[("disabled", "#6B7280"), ("!disabled", colors["accent"])],
    )

    # Sol menü bölüm başlığı (Tanımlar/İşlemler gibi)
    style.configure(
        "SidebarSection.TLabel",
        background=colors["panel"],
        foreground=colors["muted"],
        font=(base_family, design_tokens["typography"]["small"], "bold"),
        padding=(spacing["md"], spacing["xs"]),
    )


    # Genel butonlar
    style.configure("TButton", padding=(spacing["md"], spacing["sm"]))
    style.map("TButton", foreground=[("disabled", "#6B7280")])

    # Buton varyantları
    style.configure("Primary.TButton", padding=(spacing["md"], spacing["sm"]), background=colors["accent"], foreground="#ffffff")
    style.map(
        "Primary.TButton",
        background=[("active", "#2563EB"), ("!active", colors["accent"])],
        foreground=[("disabled", "#E5E7EB"), ("!disabled", "#ffffff")],
    )
    style.configure(
        "Secondary.TButton",
        padding=(spacing["md"], spacing["sm"]),
        background=colors["panel_high"],
        foreground=colors["text"],
    )
    style.map(
        "Secondary.TButton",
        background=[("active", colors["panel_alt"]), ("!active", colors["panel_high"])],
        foreground=[("disabled", "#6B7280"), ("!disabled", colors["text"])],
    )
    style.configure("Danger.TButton", padding=(spacing["md"], spacing["sm"]), background=colors["danger"], foreground="#ffffff")
    style.map(
        "Danger.TButton",
        background=[("active", "#DC2626"), ("!active", colors["danger"])],
        foreground=[("disabled", "#FCA5A5"), ("!disabled", "#ffffff")],
    )

    # Giriş alanları
    style.configure("TEntry", padding=spacing["xs"], fieldbackground=colors["panel_high"], foreground=colors["text"])
    style.configure(
        "TCombobox",
        padding=spacing["xs"],
        fieldbackground=colors["panel_high"],
        foreground=colors["text"],
    )
    style.map("TCombobox", fieldbackground=[("readonly", colors["panel_high"])])
    style.configure("Error.TEntry", fieldbackground="#7F1D1D", foreground=colors["text"])
    style.configure("Error.TCombobox", fieldbackground="#7F1D1D", foreground=colors["text"])

    # LabelFrame
    style.configure("TLabelframe", background=colors["bg"])
    style.configure(
        "TLabelframe.Label",
        background=colors["bg"],
        foreground=colors["text"],
        font=(base_family, design_tokens["typography"]["small"], "bold"),
    )

    # Treeview
    style.configure(
        "Treeview",
        background=colors["panel"],
        fieldbackground=colors["panel"],
        foreground=colors["text"],
        rowheight=44,
        bordercolor=colors["border"],
        borderwidth=1,
        relief="flat",
    )
    style.configure(
        "Treeview.Heading",
        background=colors["panel_alt"],
        foreground=colors["text"],
        font=(base_family, design_tokens["typography"]["small"], "bold"),
        relief="flat",
        padding=(spacing["sm"], spacing["sm"]),
    )
    style.map(
        "Treeview",
        background=[("selected", colors["accent_soft"])],
        foreground=[("selected", colors["text"])],
    )

    # Notebook
    style.configure("TNotebook", background=colors["bg"], borderwidth=0)
    style.configure("TNotebook.Tab", padding=(spacing["md"], spacing["sm"]), background=colors["panel"])
    style.map(
        "TNotebook.Tab",
        background=[("selected", colors["panel_high"]), ("!selected", colors["panel"])],
        foreground=[("selected", colors["text"]), ("!selected", colors["muted"])],
    )

    # Status bar
    style.configure(
        "Status.TLabel",
        background=colors["panel"],
        foreground=colors["muted"],
        padding=(spacing["md"], spacing["xs"]),
    )

    return {
        "colors": colors,
        "spacing": spacing,
        "radius": radius,
        "shadows": shadows,
        "design_tokens": design_tokens,
        "components_layout": components_layout,
        "atoms": atoms,
        "form_atoms": form_atoms,
        "data_components": data_components,
        "overlays": overlays,
        "screen_dashboard": screen_dashboard,
        "screen_login": screen_login,
        "screen_kasa": screen_kasa,
        "screen_banka": screen_banka,
        "screen_fatura": screen_fatura,
    }
