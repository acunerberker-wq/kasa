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

from kasapro.ui.widgets import Button3D
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
