# -*- coding: utf-8 -*-
"""3D Buton Demo - KasaPro

Bu dosyayı çalıştırarak 3D butonları test edebilirsiniz:
    python tools/demo_3d_buttons.py

Özellikler:
- Tüm buton stilleri (primary, secondary, ghost, pill, danger, success, warning, info, toolbar)
- Güncel renk paleti (Primary #02095B, Secondary #000537, vs.)
- 3 noktalı gradient geçişleri
- Hover/pressed efektleri
- Koyu ve açık tema örnekleri
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
from tkinter import ttk

from kasapro.ui.widgets import Button3D, Checkbox3D, IconButton3D
from kasapro.ui.theme import apply_dark_glass_theme, COLORS_LIGHT, COLORS_DARK


class Button3DDemo:
    """3D Buton Demo Uygulaması."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("KasaPro - 3D Buton Demo")
        self.root.geometry("850x750")
        self.root.configure(bg="#0a0a18")
        
        # Tema uygula
        apply_dark_glass_theme(self.root)
        
        self._build_ui()
    
    def _build_ui(self):
        """UI'ı oluştur."""
        # Ana container - scrollable
        canvas = tk.Canvas(self.root, bg="#0a0a18", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        
        main_frame = tk.Frame(canvas, bg="#0a0a18", padx=30, pady=30)
        
        canvas.create_window((0, 0), window=main_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        
        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        main_frame.bind("<Configure>", on_frame_configure)
        
        # Mouse scroll
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        # ========================================
        # BAŞLIK
        # ========================================
        header = tk.Frame(main_frame, bg="#0a0a18")
        header.pack(fill="x", pady=(0, 30))
        
        tk.Label(
            header,
            text="🎨 KasaPro Button3D Stilleri",
            font=("Segoe UI", 20, "bold"),
            fg="#EDEBF3",
            bg="#0a0a18"
        ).pack(anchor="w")
        
        tk.Label(
            header,
            text="Tüm buton stilleri ve renk paleti demo'su",
            font=("Segoe UI", 11),
            fg="#888AA2",
            bg="#0a0a18"
        ).pack(anchor="w", pady=(5, 0))
        
        # ========================================
        # KOYU TEMA BÖLÜMÜ
        # ========================================
        dark_section = tk.Frame(main_frame, bg="#111125", padx=20, pady=20)
        dark_section.pack(fill="x", pady=(0, 20))
        
        self._add_section_title(dark_section, "🌙 Koyu Tema Butonları", "#111125")
        
        # Ghost - Sidebar butonları
        self._add_button_row(
            dark_section,
            "Ghost (Sidebar / Yeni Sipariş stili)",
            [
                ("+ Yeni Sipariş", "ghost", 140, 38),
                ("Önceki", "ghost", 90, 38),
                ("Sonraki", "ghost", 90, 38),
                ("<", "ghost", 45, 38),
                (">", "ghost", 45, 38),
            ],
            bg="#111125"
        )
        
        # Primary - Ana aksiyon
        self._add_button_row(
            dark_section,
            "Primary (Ana aksiyonlar - #02095B)",
            [
                ("Kaydet", "primary", 100, 38),
                ("Ara", "primary", 80, 38),
                ("Durum Güncelle", "primary", 145, 38),
                ("Gönder", "primary", 90, 38),
            ],
            bg="#111125"
        )
        
        # Secondary - İkincil aksiyon
        self._add_button_row(
            dark_section,
            "Secondary (İkincil aksiyonlar - #000537)",
            [
                ("İptal", "secondary", 85, 36),
                ("Kapat", "secondary", 85, 36),
                ("Geri", "secondary", 75, 36),
                ("Vazgeç", "secondary", 90, 36),
            ],
            bg="#111125"
        )
        
        # Durum butonları
        self._add_button_row(
            dark_section,
            "Durum Butonları (Danger, Success, Warning, Info)",
            [
                ("Sil", "danger", 75, 36),
                ("Onayla", "success", 90, 36),
                ("Uyarı", "warning", 85, 36),
                ("Bilgi", "info", 80, 36),
            ],
            bg="#111125"
        )
        
        # ========================================
        # AÇIK TEMA BÖLÜMÜ
        # ========================================
        light_section = tk.Frame(main_frame, bg="#F8F7FA", padx=20, pady=20)
        light_section.pack(fill="x", pady=(0, 20))
        
        self._add_section_title(light_section, "☀️ Açık Tema Butonları", "#F8F7FA", fg="#181839")
        
        # Pill - Tab/Sekme stili
        self._add_button_row(
            light_section,
            "Pill (Tab/Sekme stili - #DBDAE8)",
            [
                ("Tümü", "pill", 80, 34),
                ("Aktif", "pill", 80, 34),
                ("Beklemede", "pill", 100, 34),
                ("Tamamlandı", "pill", 110, 34),
            ],
            bg="#F8F7FA",
            label_fg="#4A4A6D"
        )
        
        # Toolbar
        self._add_button_row(
            light_section,
            "Toolbar (Araç çubuğu - #EBE9F2)",
            [
                ("Excel", "toolbar", 80, 32),
                ("PDF", "toolbar", 70, 32),
                ("Yazdır", "toolbar", 85, 32),
                ("Kopyala", "toolbar", 90, 32),
            ],
            bg="#F8F7FA",
            label_fg="#4A4A6D"
        )
        
        # Primary on light
        self._add_button_row(
            light_section,
            "Primary (Açık temada)",
            [
                ("Yeni Kayıt", "primary", 110, 36),
                ("Düzenle", "primary", 95, 36),
                ("Filtrele", "primary", 95, 36),
            ],
            bg="#F8F7FA",
            label_fg="#4A4A6D"
        )
        
        # ========================================
        # BOYUT KARŞILAŞTIRMASI
        # ========================================
        size_section = tk.Frame(main_frame, bg="#1a1a35", padx=20, pady=20)
        size_section.pack(fill="x", pady=(0, 20))
        
        self._add_section_title(size_section, "📏 Boyut Karşılaştırması", "#1a1a35")
        
        size_frame = tk.Frame(size_section, bg="#1a1a35")
        size_frame.pack(fill="x", pady=10)
        
        sizes = [
            ("Küçük", 70, 28),
            ("Normal", 100, 36),
            ("Orta", 130, 42),
            ("Büyük", 160, 48),
        ]
        
        for text, w, h in sizes:
            btn = Button3D(
                size_frame,
                text=f"{text} ({w}x{h})",
                style="primary",
                width=w,
                height=h,
                bg="#1a1a35"
            )
            btn.pack(side="left", padx=8, pady=5)
        
        # ========================================
        # RENK PALETİ GÖSTERİMİ
        # ========================================
        palette_section = tk.Frame(main_frame, bg="#0f0f22", padx=20, pady=20)
        palette_section.pack(fill="x", pady=(0, 20))
        
        self._add_section_title(palette_section, "🎨 Renk Paleti", "#0f0f22")
        
        # Renk kutuları
        colors_frame = tk.Frame(palette_section, bg="#0f0f22")
        colors_frame.pack(fill="x", pady=10)
        
        palette = [
            ("Primary", "#02095B", "#EDEBF3"),
            ("Secondary", "#000537", "#EDEBF3"),
            ("Sidebar", "#111125", "#EDEBF3"),
            ("Pill BG", "#DBDAE8", "#181839"),
            ("Success", "#16A34A", "#ffffff"),
            ("Danger", "#EF4444", "#ffffff"),
            ("Warning", "#F59E0B", "#181839"),
            ("Info", "#3B82F6", "#ffffff"),
        ]
        
        for name, bg_color, fg_color in palette:
            color_box = tk.Frame(colors_frame, bg=bg_color, padx=15, pady=10)
            color_box.pack(side="left", padx=5)
            tk.Label(
                color_box,
                text=f"{name}\n{bg_color}",
                font=("Consolas", 9),
                fg=fg_color,
                bg=bg_color,
                justify="center"
            ).pack()
        
        # ========================================
        # ICON BUTTON BÖLÜMÜ (Header Bar)
        # ========================================
        icon_section = tk.Frame(main_frame, bg="#111125", padx=20, pady=20)
        icon_section.pack(fill="x", pady=(0, 20))
        
        self._add_section_title(icon_section, "🔘 Header Icon Butonları", "#111125")
        
        # Header bar simülasyonu
        header_bar = tk.Frame(icon_section, bg="#0d0d20", padx=15, pady=10)
        header_bar.pack(fill="x", pady=10)
        
        tk.Label(
            header_bar,
            text="Header Bar Örneği:",
            font=("Segoe UI", 10),
            fg="#6a6a8a",
            bg="#0d0d20"
        ).pack(side="left", padx=(0, 20))
        
        # Mail butonu
        mail_btn = IconButton3D(
            header_bar,
            icon="mail",
            style="header",
            size=32,
            bg="#0d0d20",
            command=lambda: print("📧 Mail tıklandı!")
        )
        mail_btn.pack(side="left", padx=5)
        
        # Bildirim butonu (badge ile)
        notif_btn = IconButton3D(
            header_bar,
            icon="bell",
            style="header",
            size=32,
            badge=3,
            bg="#0d0d20",
            command=lambda: print("🔔 Bildirim tıklandı!")
        )
        notif_btn.pack(side="left", padx=5)
        
        # Ekran butonu
        screen_btn = IconButton3D(
            header_bar,
            icon="monitor",
            style="header",
            size=32,
            bg="#0d0d20",
            command=lambda: print("🖥 Ekran tıklandı!")
        )
        screen_btn.pack(side="left", padx=5)
        
        # Ayarlar butonu
        settings_btn = IconButton3D(
            header_bar,
            icon="settings",
            style="header",
            size=32,
            bg="#0d0d20",
            command=lambda: print("⚙ Ayarlar tıklandı!")
        )
        settings_btn.pack(side="left", padx=5)
        
        # Profil butonu
        profile_btn = IconButton3D(
            header_bar,
            icon="user",
            style="header",
            size=32,
            bg="#0d0d20",
            command=lambda: print("👤 Profil tıklandı!")
        )
        profile_btn.pack(side="left", padx=5)
        
        # Tüm icon'lar
        tk.Label(
            icon_section,
            text="Tüm Icon'lar:",
            font=("Segoe UI", 10),
            fg="#888AA2",
            bg="#111125"
        ).pack(anchor="w", pady=(15, 5))
        
        icons_row = tk.Frame(icon_section, bg="#111125")
        icons_row.pack(fill="x", pady=5)
        
        all_icons = [
            "mail", "bell", "monitor", "settings", "user", "search", 
            "home", "plus", "close", "check", "refresh", "edit", 
            "save", "folder", "calendar", "star", "info", "warning"
        ]
        
        for icon_name in all_icons:
            btn = IconButton3D(
                icons_row,
                icon=icon_name,
                style="header",
                size=28,
                bg="#111125"
            )
            btn.pack(side="left", padx=3)
        
        # Farklı stiller
        tk.Label(
            icon_section,
            text="Farklı Stiller (dark, light, danger, success):",
            font=("Segoe UI", 10),
            fg="#888AA2",
            bg="#111125"
        ).pack(anchor="w", pady=(15, 5))
        
        styles_row = tk.Frame(icon_section, bg="#111125")
        styles_row.pack(fill="x", pady=5)
        
        style_demos = [
            ("header", "settings"),
            ("dark", "settings"),
            ("danger", "close"),
            ("success", "check"),
        ]
        
        for style, icon in style_demos:
            frame = tk.Frame(styles_row, bg="#111125")
            frame.pack(side="left", padx=10)
            
            btn = IconButton3D(
                frame,
                icon=icon,
                style=style,
                size=36,
                bg="#111125"
            )
            btn.pack()
            
            tk.Label(
                frame,
                text=style,
                font=("Segoe UI", 8),
                fg="#6a6a8a",
                bg="#111125"
            ).pack(pady=(3, 0))
        
        # Light tema örneği
        light_bar = tk.Frame(icon_section, bg="#e8e8f0", padx=15, pady=10)
        light_bar.pack(fill="x", pady=(15, 5))
        
        tk.Label(
            light_bar,
            text="Light Tema:",
            font=("Segoe UI", 10),
            fg="#4a4a6a",
            bg="#e8e8f0"
        ).pack(side="left", padx=(0, 20))
        
        for icon_name in ["mail", "bell", "settings", "user", "search"]:
            btn = IconButton3D(
                light_bar,
                icon=icon_name,
                style="light",
                size=32,
                bg="#e8e8f0"
            )
            btn.pack(side="left", padx=5)
        
        # ========================================
        # CHECKBOX BÖLÜMÜ
        # ========================================
        checkbox_section = tk.Frame(main_frame, bg="#111125", padx=20, pady=20)
        checkbox_section.pack(fill="x", pady=(0, 20))
        
        self._add_section_title(checkbox_section, "☑️ 3D Checkbox Stilleri", "#111125")
        
        # Default style checkboxes
        cb_row1 = tk.Frame(checkbox_section, bg="#111125")
        cb_row1.pack(fill="x", pady=5)
        
        tk.Label(
            cb_row1,
            text="Default (Koyu mavi):",
            font=("Segoe UI", 10),
            fg="#888AA2",
            bg="#111125",
            width=18,
            anchor="w"
        ).pack(side="left")
        
        for i in range(8):
            var = tk.BooleanVar(value=True)
            cb = Checkbox3D(
                cb_row1,
                text="",
                variable=var,
                style="default",
                size=22,
                bg="#111125"
            )
            cb.pack(side="left", padx=3)
        
        # Primary style with labels
        cb_row2 = tk.Frame(checkbox_section, bg="#111125")
        cb_row2.pack(fill="x", pady=10)
        
        tk.Label(
            cb_row2,
            text="Primary (Etiketli):",
            font=("Segoe UI", 10),
            fg="#888AA2",
            bg="#111125",
            width=18,
            anchor="w"
        ).pack(side="left")
        
        labels = ["Aktif", "Onaylandı", "Tamamlandı", "Seçili"]
        for label in labels:
            var = tk.BooleanVar(value=True)
            cb = Checkbox3D(
                cb_row2,
                text=label,
                variable=var,
                style="primary",
                size=20,
                bg="#111125"
            )
            cb.pack(side="left", padx=8)
        
        # Success style - Başarılı durumlar
        cb_row3 = tk.Frame(checkbox_section, bg="#111125")
        cb_row3.pack(fill="x", pady=10)
        
        tk.Label(
            cb_row3,
            text="Success (Başarılı):",
            font=("Segoe UI", 10),
            fg="#888AA2",
            bg="#111125",
            width=18,
            anchor="w"
        ).pack(side="left")
        
        success_labels = ["Başarılı", "Başarılı", "Başarılı", "Başarılı", "Başarılı"]
        for label in success_labels:
            var = tk.BooleanVar(value=True)
            cb = Checkbox3D(
                cb_row3,
                text=label,
                variable=var,
                style="success",
                size=20,
                bg="#111125"
            )
            cb.pack(side="left", padx=6)
        
        # Mixed states
        cb_row4 = tk.Frame(checkbox_section, bg="#111125")
        cb_row4.pack(fill="x", pady=10)
        
        tk.Label(
            cb_row4,
            text="Karışık durumlar:",
            font=("Segoe UI", 10),
            fg="#888AA2",
            bg="#111125",
            width=18,
            anchor="w"
        ).pack(side="left")
        
        states = [True, False, True, False, True, True, False, True]
        for checked in states:
            var = tk.BooleanVar(value=checked)
            cb = Checkbox3D(
                cb_row4,
                text="",
                variable=var,
                style="default",
                size=22,
                bg="#111125"
            )
            cb.pack(side="left", padx=3)
        
        # ========================================
        # PROJE BUTONLARI - CRUD AKSIYONLAR
        # ========================================
        crud_section = tk.Frame(main_frame, bg="#111125", padx=20, pady=20)
        crud_section.pack(fill="x", pady=(0, 20))
        
        self._add_section_title(crud_section, "💼 Proje Butonları - CRUD Aksiyonlar", "#111125")
        
        # Kaydet/Sil/Düzenle grubu
        self._add_button_row(
            crud_section,
            "Temel CRUD (Kaydet, Sil, Düzenle, Yeni)",
            [
                ("💾 Kaydet", "primary", 100, 36),
                ("🗑️ Sil", "danger", 80, 36),
                ("✏️ Düzenle", "secondary", 100, 36),
                ("➕ Yeni", "ghost", 80, 36),
            ],
            bg="#111125"
        )
        
        # Ekleme butonları
        self._add_button_row(
            crud_section,
            "Ekleme Butonları (➕ prefix)",
            [
                ("➕ Yeni Fatura", "primary", 120, 36),
                ("➕ Kalem Ekle", "ghost", 110, 36),
                ("➕ Poz Ekle", "ghost", 100, 36),
                ("➕ Dönem Ekle", "ghost", 110, 36),
            ],
            bg="#111125"
        )
        
        # Kaydetme varyasyonları
        self._add_button_row(
            crud_section,
            "Kaydetme Varyasyonları",
            [
                ("💾 Proje Kaydet", "primary", 130, 36),
                ("💾 Rol Kaydet", "primary", 110, 36),
                ("💾 Metraj Kaydet", "primary", 130, 36),
                ("💾 Seçimleri Kaydet", "primary", 140, 36),
            ],
            bg="#111125"
        )
        
        # ========================================
        # PROJE BUTONLARI - NAVİGASYON
        # ========================================
        nav_section = tk.Frame(main_frame, bg="#1a1a35", padx=20, pady=20)
        nav_section.pack(fill="x", pady=(0, 20))
        
        self._add_section_title(nav_section, "🧭 Navigasyon Butonları", "#1a1a35")
        
        # Sayfalama
        self._add_button_row(
            nav_section,
            "Sayfalama (Önceki/Sonraki)",
            [
                ("◀ Önceki", "secondary", 100, 36),
                ("Sonraki ▶", "secondary", 100, 36),
                ("<", "ghost", 45, 36),
                (">", "ghost", 45, 36),
            ],
            bg="#1a1a35"
        )
        
        # Yenileme butonları
        self._add_button_row(
            nav_section,
            "Yenileme Butonları",
            [
                ("🔄 Yenile", "secondary", 100, 36),
                ("Yenile", "ghost", 80, 36),
                ("🔄 Filtreleri Yenile", "ghost", 140, 36),
                ("Listeleri Yenile", "ghost", 130, 36),
            ],
            bg="#1a1a35"
        )
        
        # ========================================
        # PROJE BUTONLARI - FİLTRE & RAPOR
        # ========================================
        filter_section = tk.Frame(main_frame, bg="#111125", padx=20, pady=20)
        filter_section.pack(fill="x", pady=(0, 20))
        
        self._add_section_title(filter_section, "📊 Filtre & Rapor Butonları", "#111125")
        
        # Tarih filtreleri
        self._add_button_row(
            filter_section,
            "Tarih Filtreleri",
            [
                ("Bugün", "pill", 80, 34),
                ("Bu Ay", "pill", 80, 34),
                ("Son 30 gün", "pill", 100, 34),
                ("Filtrele", "secondary", 90, 34),
            ],
            bg="#111125"
        )
        
        # Export butonları
        self._add_button_row(
            filter_section,
            "Export Butonları",
            [
                ("📥 Excel İçe Aktar", "toolbar", 140, 34),
                ("📤 Excel Export", "toolbar", 120, 34),
                ("📥 CSV", "toolbar", 80, 34),
                ("🖨️ Yazdır/PDF", "toolbar", 110, 34),
            ],
            bg="#111125"
        )
        
        # Rapor butonları
        self._add_button_row(
            filter_section,
            "Rapor Butonları",
            [
                ("Hesapla", "primary", 90, 36),
                ("📊 Raporu Çalıştır", "primary", 140, 36),
                ("📤 Rapor Üret", "primary", 120, 36),
                ("Rapor", "secondary", 80, 36),
            ],
            bg="#111125"
        )
        
        # ========================================
        # PROJE BUTONLARI - ONAY & İPTAL
        # ========================================
        confirm_section = tk.Frame(main_frame, bg="#1a1a35", padx=20, pady=20)
        confirm_section.pack(fill="x", pady=(0, 20))
        
        self._add_section_title(confirm_section, "✅ Onay & İptal Butonları", "#1a1a35")
        
        # Dialog butonları
        self._add_button_row(
            confirm_section,
            "Dialog Butonları",
            [
                ("Tamam", "primary", 85, 36),
                ("İptal", "secondary", 85, 36),
                ("Uygula", "success", 90, 36),
                ("Uygula & Kapat", "success", 120, 36),
                ("Kapat", "ghost", 80, 36),
            ],
            bg="#1a1a35"
        )
        
        # Onay/Red butonları
        self._add_button_row(
            confirm_section,
            "Onay/Red Butonları (HR, İzin, vs.)",
            [
                ("Onay", "success", 75, 36),
                ("Onayla", "success", 85, 36),
                ("Reddet", "danger", 85, 36),
                ("Yönetici Onayı", "success", 130, 36),
                ("İK Onayı", "success", 100, 36),
            ],
            bg="#1a1a35"
        )
        
        # ========================================
        # PROJE BUTONLARI - ÖZEL AKSIYONLAR
        # ========================================
        special_section = tk.Frame(main_frame, bg="#111125", padx=20, pady=20)
        special_section.pack(fill="x", pady=(0, 20))
        
        self._add_section_title(special_section, "🔧 Özel Aksiyon Butonları", "#111125")
        
        # Seçim butonları
        self._add_button_row(
            special_section,
            "Seçim Butonları",
            [
                ("✅ Seç / Aç", "primary", 100, 36),
                ("Seçiliyi Aç", "secondary", 100, 36),
                ("Tümünü Seç", "ghost", 100, 36),
                ("Tümünü Kaldır", "ghost", 110, 36),
            ],
            bg="#111125"
        )
        
        # Mesaj butonları
        self._add_button_row(
            special_section,
            "Mesaj & İletişim",
            [
                ("➕ Yeni Mesaj", "primary", 120, 36),
                ("Gönder", "success", 85, 36),
                ("Taslak Kaydet", "secondary", 120, 36),
                ("🗑 Kaldır", "danger", 90, 36),
            ],
            bg="#111125"
        )
        
        # HR butonları
        self._add_button_row(
            special_section,
            "İK / HR Butonları",
            [
                ("Pasife Al", "warning", 100, 36),
                ("Talep Oluştur", "primary", 115, 36),
                ("Talep", "ghost", 75, 36),
                ("Kilitle", "danger", 85, 36),
                ("Dönem Oluştur", "primary", 120, 36),
            ],
            bg="#111125"
        )
        
        # Şirket butonları
        self._add_button_row(
            special_section,
            "Şirket Yönetimi",
            [
                ("➕ Yeni Şirket", "primary", 120, 36),
                ("✏️ Yeniden Adlandır", "secondary", 145, 36),
                ("🗑️ Sil", "danger", 80, 36),
                ("🔑 Şifre", "warning", 90, 36),
            ],
            bg="#111125"
        )
        
        # Stok/Fatura butonları
        self._add_button_row(
            special_section,
            "Stok & Fatura",
            [
                ("Yeni Ürün", "primary", 100, 36),
                ("Yeni Hareket", "ghost", 110, 36),
                ("🧾 PDF", "toolbar", 80, 34),
                ("📎 Ataşman Ekle", "ghost", 120, 36),
            ],
            bg="#111125"
        )
        
        # Diğer aksiyonlar
        self._add_button_row(
            special_section,
            "Diğer Aksiyonlar",
            [
                ("🔄 Endeksleri Çek", "info", 130, 36),
                ("Kalem Ekle", "ghost", 100, 36),
                ("Varsayılan Seri Oluştur", "secondary", 160, 36),
            ],
            bg="#111125"
        )
        
        # ========================================
        # EKSİK BUTONLAR - BANKA & FİNANS
        # ========================================
        finance_section = tk.Frame(main_frame, bg="#1a1a35", padx=20, pady=20)
        finance_section.pack(fill="x", pady=(0, 20))
        
        self._add_section_title(finance_section, "🏦 Banka & Finans Butonları", "#1a1a35")
        
        # Tahsilat/Ödeme
        self._add_button_row(
            finance_section,
            "Tahsilat & Ödeme",
            [
                ("➕ Tahsilat/Ödeme Ekle", "primary", 165, 36),
                ("Tahsilat", "success", 95, 36),
                ("Ödeme", "warning", 85, 36),
                ("Ödeme Ekle", "ghost", 105, 36),
            ],
            bg="#1a1a35"
        )
        
        # Banka işlemleri
        self._add_button_row(
            finance_section,
            "Banka İşlemleri",
            [
                ("💼 Maaşları Bul", "primary", 130, 36),
                ("📊 Analiz Raporu", "info", 130, 36),
                ("💼 Aç + Maaşları Bul", "primary", 160, 36),
            ],
            bg="#1a1a35"
        )
        
        # ========================================
        # EKSİK BUTONLAR - ARAMA & TARAMA
        # ========================================
        search_section = tk.Frame(main_frame, bg="#111125", padx=20, pady=20)
        search_section.pack(fill="x", pady=(0, 20))
        
        self._add_section_title(search_section, "🔍 Arama & Tarama Butonları", "#111125")
        
        # Arama butonları
        self._add_button_row(
            search_section,
            "Arama & Filtreleme",
            [
                ("Ara", "primary", 70, 36),
                ("🔍 Bul", "primary", 80, 36),
                ("Tara", "secondary", 75, 36),
                ("🔎 Global Arama", "info", 130, 36),
            ],
            bg="#111125"
        )
        
        # Eşleştirme butonları
        self._add_button_row(
            search_section,
            "Eşleştirme & Doğrulama",
            [
                ("Eşleştir", "primary", 95, 36),
                ("Doğrula", "success", 90, 36),
                ("Kolon Eşleştir", "secondary", 120, 36),
            ],
            bg="#111125"
        )
        
        # ========================================
        # EKSİK BUTONLAR - YEDEKLEME & GERİ YÜKLEME
        # ========================================
        backup_section = tk.Frame(main_frame, bg="#1a1a35", padx=20, pady=20)
        backup_section.pack(fill="x", pady=(0, 20))
        
        self._add_section_title(backup_section, "💾 Yedekleme & Geri Yükleme", "#1a1a35")
        
        self._add_button_row(
            backup_section,
            "Yedekleme İşlemleri",
            [
                ("♻️ Yedek Seç ve Geri Yükle", "warning", 180, 36),
                ("Yükle", "primary", 80, 36),
                ("Sürüm Yükle", "ghost", 110, 36),
                ("📥 İndir", "toolbar", 90, 34),
            ],
            bg="#1a1a35"
        )
        
        # ========================================
        # EKSİK BUTONLAR - NAKLİYE & LOJİSTİK
        # ========================================
        logistics_section = tk.Frame(main_frame, bg="#111125", padx=20, pady=20)
        logistics_section.pack(fill="x", pady=(0, 20))
        
        self._add_section_title(logistics_section, "🚚 Nakliye & Lojistik", "#111125")
        
        self._add_button_row(
            logistics_section,
            "Nakliye Butonları",
            [
                ("Firma Ekle", "primary", 100, 36),
                ("Araç Ekle", "ghost", 95, 36),
                ("Rota Ekle", "ghost", 95, 36),
                ("İşlem Kaydet", "success", 115, 36),
            ],
            bg="#111125"
        )
        
        # ========================================
        # EKSİK BUTONLAR - TAB STİLLERİ
        # ========================================
        tab_section = tk.Frame(main_frame, bg="#1a1a35", padx=20, pady=20)
        tab_section.pack(fill="x", pady=(0, 20))
        
        self._add_section_title(tab_section, "📑 Tab / Sekme Stilleri", "#1a1a35")
        
        # Notebook tab simülasyonu
        tab_demo = tk.Frame(tab_section, bg="#0d0d20", padx=5, pady=5)
        tab_demo.pack(fill="x", pady=10)
        
        tabs = [
            ("📁 Proje/Sözleşme", "pill", 140, 34),
            ("📌 Poz/Birim Fiyat", "pill", 130, 34),
            ("🧾 Hakediş Dönemi", "pill", 140, 34),
            ("📈 Endeks", "pill", 100, 34),
            ("📄 Rapor", "pill", 90, 34),
        ]
        
        for text, style, w, h in tabs:
            btn = Button3D(
                tab_demo,
                text=text,
                style=style,
                width=w,
                height=h,
                bg="#0d0d20"
            )
            btn.pack(side="left", padx=3)
        
        # Daha fazla tab örneği
        self._add_button_row(
            tab_section,
            "Fatura Modülü Sekmeleri",
            [
                ("➕ İşlem Ekle", "pill", 110, 34),
                ("🗂️ Geçmiş", "pill", 100, 34),
                ("📊 Raporlar", "pill", 105, 34),
                ("Tahsilat / Ödeme", "pill", 130, 34),
            ],
            bg="#1a1a35"
        )
        
        # ========================================
        # EKSİK BUTONLAR - ÇOKLU SEÇİM
        # ========================================
        multi_section = tk.Frame(main_frame, bg="#111125", padx=20, pady=20)
        multi_section.pack(fill="x", pady=(0, 20))
        
        self._add_section_title(multi_section, "☑️ Çoklu Seçim & Toggle", "#111125")
        
        self._add_button_row(
            multi_section,
            "Toggle Butonları",
            [
                ("Çoklu Seçim: Kapalı", "secondary", 145, 36),
                ("Çoklu Seçim: Açık", "primary", 140, 36),
                ("Sadece aktif", "pill", 110, 34),
                ("Sadece okunmamış", "pill", 135, 34),
            ],
            bg="#111125"
        )
        
        # ========================================
        # EKSİK BUTONLAR - LOG & DİAGNOSTİK
        # ========================================
        diag_section = tk.Frame(main_frame, bg="#1a1a35", padx=20, pady=20)
        diag_section.pack(fill="x", pady=(0, 20))
        
        self._add_section_title(diag_section, "🔧 Log & Diagnostik", "#1a1a35")
        
        self._add_button_row(
            diag_section,
            "Log İşlemleri",
            [
                ("Logu TXT Dışa Aktar", "toolbar", 150, 34),
                ("Demo Stok Fişleri Oluştur", "ghost", 175, 36),
                ("Açılışta otomatik çalıştır", "pill", 170, 34),
            ],
            bg="#1a1a35"
        )
        
        # ========================================
        # PROJE BUTONLARI - SİDEBAR NAVİGASYON
        # ========================================
        sidebar_section = tk.Frame(main_frame, bg="#0d0d20", padx=20, pady=20)
        sidebar_section.pack(fill="x", pady=(0, 20))
        
        self._add_section_title(sidebar_section, "📌 Sidebar Navigasyon", "#0d0d20")
        
        # Sidebar menü simülasyonu
        sidebar_demo = tk.Frame(sidebar_section, bg="#111125", padx=10, pady=10)
        sidebar_demo.pack(fill="x", pady=10)
        
        sidebar_items = [
            ("🏠 Kasa", "ghost", 150, 38),
            ("👥 Cariler", "ghost", 150, 38),
            ("🧾 Fatura", "ghost", 150, 38),
            ("📊 Raporlar", "ghost", 150, 38),
            ("⚙️ Ayarlar", "ghost", 150, 38),
        ]
        
        for text, style, w, h in sidebar_items:
            btn = Button3D(
                sidebar_demo,
                text=text,
                style=style,
                width=w,
                height=h,
                bg="#111125"
            )
            btn.pack(anchor="w", pady=3)
        
        # Alt butonlar
        self._add_button_row(
            sidebar_section,
            "Alt Navigasyon",
            [
                ("🚪 Çıkış", "danger", 100, 36),
                ("❓ Yardım", "info", 90, 36),
                ("⚙️ Ayarlar", "ghost", 100, 36),
            ],
            bg="#0d0d20"
        )
        
        # ========================================
        # İNTERAKTİF TEST
        # ========================================
        test_section = tk.Frame(main_frame, bg="#111125", padx=20, pady=20)
        test_section.pack(fill="x", pady=(0, 20))
        
        self._add_section_title(test_section, "🖱️ İnteraktif Test", "#111125")
        
        tk.Label(
            test_section,
            text="Butonlara tıklayın ve konsolu kontrol edin:",
            font=("Segoe UI", 10),
            fg="#888AA2",
            bg="#111125"
        ).pack(anchor="w", pady=(0, 10))
        
        test_frame = tk.Frame(test_section, bg="#111125")
        test_frame.pack(fill="x", pady=10)
        
        for style in ["primary", "secondary", "ghost", "danger", "success"]:
            btn = Button3D(
                test_frame,
                text=style.capitalize(),
                style=style,
                width=100,
                height=36,
                bg="#111125",
                command=lambda s=style: self._on_button_click(s)
            )
            btn.pack(side="left", padx=5)
        
        # ========================================
        # FOOTER
        # ========================================
        footer = tk.Frame(main_frame, bg="#0a0a18")
        footer.pack(fill="x", pady=(20, 0))
        
        tk.Label(
            footer,
            text="KasaPro UI Components • Button3D Widget",
            font=("Segoe UI", 9),
            fg="#4A4A6D",
            bg="#0a0a18"
        ).pack()
    
    def _add_section_title(self, parent, text, bg, fg="#EDEBF3"):
        """Bölüm başlığı ekle."""
        tk.Label(
            parent,
            text=text,
            font=("Segoe UI", 13, "bold"),
            fg=fg,
            bg=bg
        ).pack(anchor="w", pady=(0, 15))
    
    def _add_button_row(self, parent, label, buttons, bg="#111125", label_fg="#888AA2"):
        """Etiketli buton satırı ekle."""
        tk.Label(
            parent,
            text=label,
            font=("Segoe UI", 10),
            fg=label_fg,
            bg=bg
        ).pack(anchor="w", pady=(10, 5))
        
        row = tk.Frame(parent, bg=bg)
        row.pack(fill="x", pady=5)
        
        for text, style, width, height in buttons:
            btn = Button3D(
                row,
                text=text,
                style=style,
                width=width,
                height=height,
                bg=bg
            )
            btn.pack(side="left", padx=5)
    
    def _on_button_click(self, style):
        """Buton tıklama olayı."""
        print(f"✓ '{style}' butonuna tıklandı!")
    
    def run(self):
        """Uygulamayı çalıştır."""
        self.root.mainloop()


def main():
    demo = Button3DDemo()
    demo.run()


if __name__ == "__main__":
    main()
