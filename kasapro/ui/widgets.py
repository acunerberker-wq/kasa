# -*- coding: utf-8 -*-
"""KasaPro v3 - Ortak UI widget'ları"""

from __future__ import annotations

from typing import Any, List, Callable, Optional

import re
import tkinter as tk
from tkinter import ttk

from ..utils import safe_float, fmt_amount, parse_number_smart


class Button3D(tk.Canvas):
    """Modern 3D buton - KasaPro UI stiline uygun.
    
    Kullanım:
        btn = Button3D(parent, text="Kaydet", command=save_func, style="primary")
        btn.pack()
    
    Stiller: "primary", "secondary", "pill", "danger", "success", "ghost", "toolbar"
    """
    
    STYLES = {
        "primary": {
            # Primary Accent - Koyu lacivert
            "bg_top": "#0a1268",       # Biraz açık üst
            "bg_bottom": "#02095B",    # Ana primary
            "bg_hover_top": "#252c78",
            "bg_hover_bottom": "#20276F",
            "bg_pressed_top": "#020854",
            "bg_pressed_bottom": "#010745",
            "fg": "#EDEBF3",           # Text on Dark
            "fg_disabled": "#898CB2",
            "border": "#010538",
            "border_light": "#3a4088",
            "glow": "#20276F",
        },
        "secondary": {
            # Secondary Deep - Çok koyu lacivert
            "bg_top": "#0a0c45",
            "bg_bottom": "#000537",
            "bg_hover_top": "#252858",
            "bg_hover_bottom": "#1F234F",
            "bg_pressed_top": "#000533",
            "bg_pressed_bottom": "#000428",
            "fg": "#EDEBF3",
            "fg_disabled": "#888AA2",
            "border": "#000320",
            "border_light": "#2a2d55",
            "glow": None,
        },
        "pill": {
            # Pill / Sekme - Açık gri butonlar
            "bg_top": "#e2e1ed",
            "bg_bottom": "#DBDAE8",
            "bg_hover_top": "#e5e4ef",
            "bg_hover_bottom": "#DFDEEA",
            "bg_pressed_top": "#CECDDA",
            "bg_pressed_bottom": "#c5c4d2",
            "fg": "#181839",           # Pill Text
            "fg_disabled": "#888AA2",
            "border": "#C9C8D9",        # Pill Border
            "border_light": "#e8e7f0",
            "glow": None,
        },
        "danger": {
            # Danger - Kırmızı
            "bg_top": "#f55555",
            "bg_bottom": "#EF4444",
            "bg_hover_top": "#f76666",
            "bg_hover_bottom": "#f55555",
            "bg_pressed_top": "#dc3333",
            "bg_pressed_bottom": "#cc2222",
            "fg": "#ffffff",
            "fg_disabled": "#888888",
            "border": "#cc3333",
            "border_light": "#ff7777",
            "glow": "#EF4444",
        },
        "success": {
            # Success - Yeşil
            "bg_top": "#1cb855",
            "bg_bottom": "#16A34A",
            "bg_hover_top": "#22c85f",
            "bg_hover_bottom": "#1cb855",
            "bg_pressed_top": "#128a3d",
            "bg_pressed_bottom": "#0e7533",
            "fg": "#ffffff",
            "fg_disabled": "#888888",
            "border": "#0e7533",
            "border_light": "#40d875",
            "glow": "#16A34A",
        },
        "warning": {
            # Warning - Turuncu
            "bg_top": "#f7ab20",
            "bg_bottom": "#F59E0B",
            "bg_hover_top": "#f8b535",
            "bg_hover_bottom": "#f7ab20",
            "bg_pressed_top": "#e08a00",
            "bg_pressed_bottom": "#cc7a00",
            "fg": "#181839",
            "fg_disabled": "#888888",
            "border": "#cc7a00",
            "border_light": "#ffc040",
            "glow": "#F59E0B",
        },
        "info": {
            # Info - Mavi
            "bg_top": "#4a90f8",
            "bg_bottom": "#3B82F6",
            "bg_hover_top": "#5a9af9",
            "bg_hover_bottom": "#4a90f8",
            "bg_pressed_top": "#2a70e5",
            "bg_pressed_bottom": "#2060d5",
            "fg": "#ffffff",
            "fg_disabled": "#888888",
            "border": "#2060d5",
            "border_light": "#70a8fa",
            "glow": "#3B82F6",
        },
        "ghost": {
            # Ghost - Sidebar/koyu alanda kullanım (Yeni Sipariş butonu gibi)
            "bg_top": "#1e1e45",       # Daha açık üst
            "bg_bottom": "#141432",    # Koyu alt
            "bg_hover_top": "#2a2a58", # Hover üst
            "bg_hover_bottom": "#1e1e45", # Hover alt
            "bg_pressed_top": "#0f0f28",
            "bg_pressed_bottom": "#0a0a1e",
            "fg": "#c8c8e8",           # Açık metin
            "fg_disabled": "#4A4A6D",
            "border": "#2a2a55",       # Görünür kenar
            "border_light": "#3a3a68", # Üst highlight
            "glow": "#3535a0",         # Mavi-mor glow
        },
        "toolbar": {
            # Toolbar - Muted yüzeyde kullanım
            "bg_top": "#f0eff5",
            "bg_bottom": "#EBE9F2",
            "bg_hover_top": "#f5f4f8",
            "bg_hover_bottom": "#f0eff5",
            "bg_pressed_top": "#e0dfe8",
            "bg_pressed_bottom": "#d8d7e2",
            "fg": "#181839",
            "fg_disabled": "#888AA2",
            "border": "#CBCADA",
            "border_light": "#f5f4f8",
            "glow": None,
        },
    }
    
    # Varsayılan arka plan rengi (tema ile uyumlu - sidebar)
    DEFAULT_BG = "#111125"
    
    def __init__(
        self, 
        parent, 
        text: str = "", 
        command: Optional[Callable] = None,
        style: str = "primary",
        width: int = 120,
        height: int = 36,
        font: Optional[tuple] = None,
        bg: str = None,  # Arka plan rengi
        **kwargs
    ):
        # Arka plan rengini belirle
        if bg is None:
            # Parent'tan almayı dene
            try:
                bg = parent.cget("background")
            except:
                bg = self.DEFAULT_BG
        
        super().__init__(
            parent, 
            width=width, 
            height=height, 
            highlightthickness=0,
            background=bg,
            **kwargs
        )
        
        self.text = text
        self.command = command
        self.btn_width = width
        self.btn_height = height
        self.btn_font = font or ("Segoe UI", 10, "bold")
        self.canvas_bg = bg
        
        # Stil ayarları
        self.style_name = style if style in self.STYLES else "primary"
        self.colors = self.STYLES[self.style_name].copy()
        
        self._state = "normal"  # normal, hover, pressed, disabled
        self._pressed = False
        
        # Canvas boyutunu gölge için genişlet (ince gölge alanı)
        self.configure(width=width + 6, height=height + 6)
        
        # Çiz
        self._draw()
        
        # Olaylar
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
    
    def _blend_color(self, color1: str, color2: str, ratio: float) -> str:
        """İki rengi karıştır - Gamma-corrected blending için."""
        # Gamma correction için (daha doğru renk geçişi)
        gamma = 2.2
        
        r1, g1, b1 = int(color1[1:3], 16), int(color1[3:5], 16), int(color1[5:7], 16)
        r2, g2, b2 = int(color2[1:3], 16), int(color2[3:5], 16), int(color2[5:7], 16)
        
        # Linear space'e çevir
        r1_lin = (r1 / 255) ** gamma
        g1_lin = (g1 / 255) ** gamma
        b1_lin = (b1 / 255) ** gamma
        r2_lin = (r2 / 255) ** gamma
        g2_lin = (g2 / 255) ** gamma
        b2_lin = (b2 / 255) ** gamma
        
        # Linear interpolation
        r_lin = r1_lin + (r2_lin - r1_lin) * ratio
        g_lin = g1_lin + (g2_lin - g1_lin) * ratio
        b_lin = b1_lin + (b2_lin - b1_lin) * ratio
        
        # Gamma space'e geri çevir
        r = int((r_lin ** (1/gamma)) * 255)
        g = int((g_lin ** (1/gamma)) * 255)
        b = int((b_lin ** (1/gamma)) * 255)
        
        # Clamp
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def _blend_multi(self, colors: list, ratios: list) -> str:
        """Birden fazla rengi karıştır (smooth gradient için)."""
        if len(colors) < 2:
            return colors[0] if colors else "#000000"
        
        result = colors[0]
        for i in range(1, len(colors)):
            result = self._blend_color(result, colors[i], ratios[i-1] if i-1 < len(ratios) else 0.5)
        return result
    
    def _ease_out_quad(self, t: float) -> float:
        """Quadratic ease-out."""
        return 1 - (1 - t) ** 2
    
    def _ease_out_cubic(self, t: float) -> float:
        """Cubic ease-out (daha yumuşak)."""
        return 1 - (1 - t) ** 3
    
    def _ease_out_quart(self, t: float) -> float:
        """Quartic ease-out (en yumuşak)."""
        return 1 - (1 - t) ** 4
    
    def _ease_in_out_sine(self, t: float) -> float:
        """Sinusoidal ease-in-out."""
        import math
        return -(math.cos(math.pi * t) - 1) / 2
    
    def _ease_in_out_cubic(self, t: float) -> float:
        """Cubic ease-in-out (smooth S-curve)."""
        if t < 0.5:
            return 4 * t * t * t
        else:
            return 1 - ((-2 * t + 2) ** 3) / 2
    
    def _smoothstep(self, t: float) -> float:
        """Hermite smoothstep (en kaliteli geçiş)."""
        t = max(0, min(1, t))
        return t * t * (3 - 2 * t)
    
    def _smootherstep(self, t: float) -> float:
        """Ken Perlin's smootherstep (ultra kalite)."""
        t = max(0, min(1, t))
        return t * t * t * (t * (t * 6 - 15) + 10)
    
    def _create_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        """Yuvarlatılmış köşeli dikdörtgen."""
        r = min(radius, (x2 - x1) // 2, (y2 - y1) // 2)
        if r < 1:
            return self.create_rectangle(x1, y1, x2, y2, **kwargs)
        
        import math
        points = []
        segments = 6
        
        # Sağ üst köşe
        for i in range(segments + 1):
            angle = math.pi / 2 * (1 - i / segments)
            px = x2 - r + r * math.cos(angle)
            py = y1 + r - r * math.sin(angle)
            points.extend([px, py])
        
        # Sağ alt köşe
        for i in range(segments + 1):
            angle = math.pi / 2 * i / segments
            px = x2 - r + r * math.cos(angle)
            py = y2 - r + r * math.sin(angle)
            points.extend([px, py])
        
        # Sol alt köşe
        for i in range(segments + 1):
            angle = math.pi / 2 + math.pi / 2 * i / segments
            px = x1 + r + r * math.cos(angle)
            py = y2 - r + r * math.sin(angle)
            points.extend([px, py])
        
        # Sol üst köşe
        for i in range(segments + 1):
            angle = math.pi + math.pi / 2 * i / segments
            px = x1 + r + r * math.cos(angle)
            py = y1 + r + r * math.sin(angle)
            points.extend([px, py])
        
        return self.create_polygon(points, smooth=False, **kwargs)
    
    def _draw(self):
        """Butonu çiz - Ultra gerçekçi profesyonel görünüm.
        
        Özellikler:
        - 5 noktalı gradient geçişi (2x artırılmış)
        - 10 katmanlı gölge sistemi (2x artırılmış)
        - 6 katmanlı glow efekti
        - Çoklu iç kenar parlaması
        - Fresnel rim light efekti
        - Ambient occlusion simülasyonu
        """
        self.delete("all")
        
        w, h = self.btn_width, self.btn_height
        ox, oy = 2, 2  # İnce gölge alanı
        radius = 6  # Daha kompakt köşeler
        
        colors = self.colors
        
        # Durum bazlı renkler - 5 noktalı gradient için
        if self._state == "disabled":
            bg_colors = ["#2e2e2e", "#2a2a2a", "#262626", "#222222", "#1e1e1e"]
            fg = "#555555"
            border = "#333333"
            border_light = "#3a3a3a"
            glow = None
            inner_glow = None
            ambient = 0.0
        elif self._state == "pressed":
            # Pressed için daha koyu tonlar
            c_top = colors["bg_pressed_top"]
            c_bot = colors["bg_pressed_bottom"]
            bg_colors = [
                self._blend_color(c_top, "#000000", 0.1),
                c_top,
                self._blend_color(c_top, c_bot, 0.4),
                self._blend_color(c_top, c_bot, 0.7),
                c_bot,
            ]
            fg = colors["fg"]
            border = colors["border"]
            border_light = self._blend_color(colors["border_light"], "#000000", 0.5)
            glow = None
            inner_glow = None
            ambient = 0.02
        elif self._state == "hover":
            c_top = colors["bg_hover_top"]
            c_bot = colors["bg_hover_bottom"]
            bg_colors = [
                self._blend_color(c_top, "#ffffff", 0.08),  # En parlak
                c_top,
                self._blend_color(c_top, c_bot, 0.35),
                self._blend_color(c_top, c_bot, 0.65),
                c_bot,
            ]
            fg = colors["fg"]
            border = colors["border"]
            border_light = self._blend_color(colors["border_light"], "#ffffff", 0.1)
            glow = colors.get("glow")
            inner_glow = self._blend_color(c_top, "#ffffff", 0.2)
            ambient = 0.06
        else:
            c_top = colors["bg_top"]
            c_bot = colors["bg_bottom"]
            bg_colors = [
                self._blend_color(c_top, "#ffffff", 0.04),  # Hafif parlak
                c_top,
                self._blend_color(c_top, c_bot, 0.35),
                self._blend_color(c_top, c_bot, 0.65),
                c_bot,
            ]
            fg = colors["fg"]
            border = colors["border"]
            border_light = colors["border_light"]
            glow = colors.get("glow")
            inner_glow = self._blend_color(c_top, "#ffffff", 0.1)
            ambient = 0.04
        
        import math
        
        # ============================================
        # GÖLGE (5 katmanlı kompakt yumuşak)
        # ============================================
        if self._state not in ("pressed", "disabled"):
            shadow_layers = 5
            for i in range(shadow_layers):
                # Üstel düşüş ile yumuşak gölge
                t = i / shadow_layers
                alpha = 0.15 * ((1 - t) ** 2.5)
                if alpha < 0.008:
                    continue
                shadow_color = self._blend_color(self.canvas_bg, "#000000", alpha)
                offset_y = (shadow_layers - i) * 0.25
                blur = i * 0.15
                self._create_rounded_rect(
                    ox + blur * 0.3, oy + offset_y + blur * 0.2,
                    ox + w - blur * 0.3, oy + h + offset_y * 0.5,
                    radius + 1 + blur * 0.15,
                    fill=shadow_color, outline=""
                )
        
        # ============================================
        # DIŞ GLOW (4 katmanlı kompakt)
        # ============================================
        if glow and self._state == "hover":
            glow_layers = 4
            for i in range(glow_layers):
                t = i / glow_layers
                glow_alpha = 0.20 * ((1 - t) ** 2)
                if glow_alpha < 0.015:
                    continue
                glow_color = self._blend_color(self.canvas_bg, glow, glow_alpha)
                expand = (glow_layers - i) * 0.4
                self._create_rounded_rect(
                    ox - expand, oy - expand * 0.4,
                    ox + w + expand, oy + h + expand * 0.4,
                    radius + expand + 1,
                    fill=glow_color, outline=""
                )
        
        # ============================================
        # AMBIENT OCCLUSION (Kenar karartma - kompakt)
        # ============================================
        if ambient > 0 and self._state != "pressed":
            ao_layers = 3
            for i in range(ao_layers):
                ao_alpha = ambient * (1 - i / ao_layers)
                ao_color = self._blend_color(self.canvas_bg, "#000000", ao_alpha)
                inset = i * 0.2
                self._create_rounded_rect(
                    ox + inset, oy + inset,
                    ox + w - inset, oy + h - inset,
                    radius - inset * 0.3,
                    fill=ao_color, outline=""
                )
        
        # ============================================
        # KENAR (Gradient border - çok katmanlı)
        # ============================================
        # Dış kenar (koyu)
        self._create_rounded_rect(
            ox, oy, ox + w, oy + h,
            radius,
            fill=border, outline=""
        )
        
        # ============================================
        # ÜST IŞIK KENARI (Bevel highlight - kompakt)
        # ============================================
        if self._state != "pressed":
            # Ana highlight (ince)
            self._create_rounded_rect(
                ox + 1, oy + 1, ox + w - 1, oy + 2,
                radius - 1,
                fill=border_light, outline=""
            )
            # Parlak çizgi (çok ince)
            highlight_bright = self._blend_color(border_light, "#ffffff", 0.18)
            self._create_rounded_rect(
                ox + 2, oy + 1, ox + w - 2, oy + 1.5,
                radius - 2,
                fill=highlight_bright, outline=""
            )
        
        # ============================================
        # ANA YÜZEY (5 Noktalı Ultra Kalite Gradient - kompakt)
        # ============================================
        surface_x1 = ox + 1
        surface_y1 = oy + 2 if self._state != "pressed" else oy + 1.5
        surface_x2 = ox + w - 1
        surface_y2 = oy + h - 0.5
        surface_h = surface_y2 - surface_y1
        
        # 5 noktalı gradient (5 renk arası 4 geçiş bölgesi)
        if surface_h > 0:
            # Geçiş noktaları (normalize edilmiş)
            stops = [0.0, 0.15, 0.40, 0.70, 1.0]
            
            for i in range(int(surface_h)):
                t = i / max(surface_h - 1, 1)
                
                # Hangi renk aralığında olduğunu bul
                segment = 0
                for s in range(len(stops) - 1):
                    if t >= stops[s] and t <= stops[s + 1]:
                        segment = s
                        break
                
                # Segment içindeki pozisyon
                seg_start = stops[segment]
                seg_end = stops[segment + 1]
                local_t = (t - seg_start) / (seg_end - seg_start) if seg_end > seg_start else 0
                
                # Ultra smooth interpolasyon
                smooth_t = self._smootherstep(local_t)
                
                # Renk blend
                c1 = bg_colors[segment]
                c2 = bg_colors[segment + 1]
                line_color = self._blend_color(c1, c2, smooth_t)
                
                y = surface_y1 + i
                
                # Köşe hesabı
                r_inner = radius - 2
                if i < r_inner:
                    corner_offset = r_inner - int(math.sqrt(max(0, r_inner**2 - (r_inner - i)**2)))
                elif i > surface_h - r_inner - 1:
                    remaining = surface_h - 1 - i
                    corner_offset = r_inner - int(math.sqrt(max(0, r_inner**2 - (r_inner - remaining)**2)))
                else:
                    corner_offset = 0
                
                x1 = surface_x1 + corner_offset + 1
                x2 = surface_x2 - corner_offset - 1
                
                if x2 > x1:
                    self.create_line(x1, y, x2, y, fill=line_color)
        
        # ============================================
        # ÜST PARLAKLIK (Glass/Gloss efekti - kompakt)
        # ============================================
        if self._state != "pressed" and inner_glow:
            # Ana gloss (üst yarıda - daha kısa)
            gloss_height = min((h - 4) // 4, 10)
            
            for i in range(max(gloss_height, 1)):
                t = i / max(gloss_height - 1, 1)
                # Çift eğri ile ultra yumuşak düşüş
                falloff = (1 - self._smootherstep(t)) ** 2
                alpha = falloff * (0.28 if self._state == "hover" else 0.18)
                
                if alpha < 0.01:
                    continue
                
                line_color = self._blend_color(bg_colors[0], "#ffffff", alpha)
                y = surface_y1 + i
                
                r_inner = radius - 2
                if r_inner > 0 and i < r_inner:
                    corner_offset = r_inner - int(math.sqrt(max(0, r_inner**2 - (r_inner - i)**2)))
                else:
                    corner_offset = 0
                
                x1 = ox + 2 + corner_offset
                x2 = ox + w - 2 - corner_offset
                
                if x2 > x1:
                    self.create_line(x1, y, x2, y, fill=line_color)
            
            # İkinci gloss katmanı (çok ince, daha parlak)
            gloss2_height = gloss_height // 3
            for i in range(max(gloss2_height, 1)):
                t = i / max(gloss2_height - 1, 1)
                falloff = (1 - t) ** 3
                alpha = falloff * 0.10
                
                if alpha < 0.008:
                    continue
                
                line_color = self._blend_color(bg_colors[0], "#ffffff", alpha)
                y = surface_y1 + i
                
                x1 = ox + w // 4
                x2 = ox + w * 3 // 4
                
                if x2 > x1:
                    self.create_line(x1, y, x2, y, fill=line_color)
        
        # ============================================
        # KENAR PARLAMASI (Edge highlights - kompakt)
        # ============================================
        if self._state not in ("pressed", "disabled"):
            edge_glow_width = 3  # Kompakt
            
            for j in range(edge_glow_width):
                t = j / edge_glow_width
                edge_alpha = (1 - self._smootherstep(t)) * 0.08
                edge_color = self._blend_color(bg_colors[2], "#ffffff", edge_alpha)
                
                # Sol kenar
                start_y = surface_y1 + (h // 8)
                end_y = surface_y2 - radius - 1
                for y in range(int(start_y), int(min(end_y, surface_y2))):
                    self.create_line(
                        surface_x1 + 1 + j, y,
                        surface_x1 + 2 + j, y,
                        fill=edge_color
                    )
                
                # Sağ kenar
                for y in range(int(start_y), int(min(end_y, surface_y2))):
                    self.create_line(
                        surface_x2 - 2 - j, y,
                        surface_x2 - 1 - j, y,
                        fill=edge_color
                    )
        
        # ============================================
        # ALT RIM LIGHT (Fresnel efekti - kompakt)
        # ============================================
        if self._state not in ("pressed", "disabled"):
            rim_width = w - 2 * radius - 3
            rim_center = ox + w // 2
            rim_height = 2  # Kompakt rim light
            
            for row in range(rim_height):
                row_alpha = (1 - row / rim_height) * 0.8
                
                for i in range(int(rim_width)):
                    rx = rim_center - rim_width // 2 + i
                    # Gauss dağılımı ile ortada parlak
                    t = (i - rim_width / 2) / (rim_width / 2)
                    gauss = math.exp(-4 * t * t)
                    rim_alpha = gauss * 0.14 * row_alpha
                    
                    if rim_alpha < 0.008:
                        continue
                    
                    rim_color = self._blend_color(bg_colors[-1], "#ffffff", rim_alpha)
                    y = oy + h - 2 - row
                    self.create_line(rx, y, rx + 1, y, fill=rim_color)
        
        # ============================================
        # İÇ GÖLGE (Depth efekti - kompakt)
        # ============================================
        if self._state not in ("disabled",):
            inner_shadow_height = 2
            for i in range(inner_shadow_height):
                t = i / inner_shadow_height
                shadow_alpha = (1 - t) * 0.10
                shadow_color = self._blend_color(bg_colors[-1], "#000000", shadow_alpha)
                y = surface_y2 - inner_shadow_height + i
                
                if y > surface_y1:
                    r_inner = radius - 1
                    remaining = surface_h - 1 - (y - surface_y1)
                    if remaining < r_inner and remaining >= 0:
                        corner_offset = r_inner - int(math.sqrt(max(0, r_inner**2 - remaining**2)))
                    else:
                        corner_offset = 0
                    
                    x1 = surface_x1 + corner_offset + 1
                    x2 = surface_x2 - corner_offset - 1
                    if x2 > x1:
                        self.create_line(x1, y, x2, y, fill=shadow_color)
        
        # ============================================
        # METİN
        # ============================================
        text_x = ox + w // 2
        text_y = oy + h // 2
        
        if self._state == "pressed":
            text_y += 0.5
        
        # Metin gölgesi (tek katman - kompakt)
        if self._state != "disabled":
            shadow_color = self._blend_color(bg_colors[-1], "#000000", 0.45)
            self.create_text(
                text_x, text_y + 1,
                text=self.text,
                fill=shadow_color,
                font=self.btn_font,
                anchor="center"
            )
        
        # Ana metin
        self.create_text(
            text_x, text_y,
            text=self.text,
            fill=fg,
            font=self.btn_font,
            anchor="center"
        )
    
    def _on_enter(self, event):
        if self._state != "disabled":
            self._state = "hover"
            self._draw()
    
    def _on_leave(self, event):
        if self._state != "disabled":
            self._state = "normal"
            self._pressed = False
            self._draw()
    
    def _on_press(self, event):
        if self._state != "disabled":
            self._state = "pressed"
            self._pressed = True
            self._draw()
    
    def _on_release(self, event):
        if self._state != "disabled" and self._pressed:
            self._state = "hover"
            self._pressed = False
            self._draw()
            if self.command:
                self.command()
    
    def configure(self, **kwargs):
        """Buton yapılandırması."""
        if "text" in kwargs:
            self.text = kwargs.pop("text")
        if "command" in kwargs:
            self.command = kwargs.pop("command")
        if "state" in kwargs:
            state = kwargs.pop("state")
            self._state = "disabled" if state == "disabled" else "normal"
        if kwargs:
            super().configure(**kwargs)
        self._draw()
    
    config = configure
    
    def cget(self, key):
        if key == "text":
            return self.text
        if key == "command":
            return self.command
        if key == "state":
            return self._state
        return super().cget(key)


class Checkbox3D(tk.Canvas):
    """
    3D görünümlü özel checkbox widget'ı.
    Koyu mavi arka plan, yeşil tik işareti.
    """
    
    STYLES = {
        "default": {
            "bg_top": "#1a1a3a",
            "bg_bottom": "#0d0d25",
            "border": "#2a2a5a",
            "border_light": "#3a3a7a",
            "check_color": "#22c55e",
            "check_glow": "#4ade80",
            "fg": "#e0e0e0",
        },
        "primary": {
            "bg_top": "#02095B",
            "bg_bottom": "#000537",
            "border": "#1a1a6a",
            "border_light": "#3a3a8a",
            "check_color": "#22c55e",
            "check_glow": "#4ade80",
            "fg": "#ffffff",
        },
        "success": {
            "bg_top": "#064e3b",
            "bg_bottom": "#022c22",
            "border": "#065f46",
            "border_light": "#10b981",
            "check_color": "#34d399",
            "check_glow": "#6ee7b7",
            "fg": "#ffffff",
        },
    }
    
    def __init__(
        self,
        parent,
        text: str = "",
        variable: tk.BooleanVar = None,
        command: Callable = None,
        style: str = "default",
        size: int = 20,
        bg: str = None,
        **kwargs
    ):
        self.text = text
        self.variable = variable or tk.BooleanVar(value=False)
        self.command = command
        self.style_name = style
        self.box_size = size
        self._state = "normal"
        self._hover = False
        
        # Arka plan rengi
        if bg:
            self.canvas_bg = bg
        else:
            try:
                self.canvas_bg = parent.cget("bg")
            except:
                self.canvas_bg = "#111125"
        
        # Font
        self.label_font = kwargs.pop("font", ("Segoe UI", 9))
        
        # Canvas boyutu (text genişliği için tahmin)
        text_width = len(text) * 7 + 10 if text else 0
        canvas_width = size + 6 + text_width
        canvas_height = size + 4
        
        super().__init__(
            parent,
            width=canvas_width,
            height=canvas_height,
            bg=self.canvas_bg,
            highlightthickness=0,
            **kwargs
        )
        
        # Variable trace
        self.variable.trace_add("write", self._on_var_change)
        
        # Event bindings
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        
        self._draw()
    
    def _blend_color(self, c1: str, c2: str, t: float) -> str:
        """Gamma-corrected renk karışımı."""
        gamma = 2.2
        
        def hex_to_rgb(h):
            h = h.lstrip('#')
            return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        
        def rgb_to_hex(r, g, b):
            return f"#{int(r):02x}{int(g):02x}{int(b):02x}"
        
        r1, g1, b1 = hex_to_rgb(c1)
        r2, g2, b2 = hex_to_rgb(c2)
        
        # Gamma space'e çevir
        r1, g1, b1 = (r1/255)**gamma, (g1/255)**gamma, (b1/255)**gamma
        r2, g2, b2 = (r2/255)**gamma, (g2/255)**gamma, (b2/255)**gamma
        
        # Blend
        r = r1 * (1-t) + r2 * t
        g = g1 * (1-t) + g2 * t
        b = b1 * (1-t) + b2 * t
        
        # Geri çevir
        r = int((r ** (1/gamma)) * 255)
        g = int((g ** (1/gamma)) * 255)
        b = int((b ** (1/gamma)) * 255)
        
        return rgb_to_hex(
            max(0, min(255, r)),
            max(0, min(255, g)),
            max(0, min(255, b))
        )
    
    def _create_rounded_rect(self, x1, y1, x2, y2, r, **kwargs):
        """Yuvarlatılmış dikdörtgen çiz."""
        points = [
            x1+r, y1, x2-r, y1,
            x2, y1, x2, y1+r,
            x2, y2-r, x2, y2,
            x2-r, y2, x1+r, y2,
            x1, y2, x1, y2-r,
            x1, y1+r, x1, y1,
            x1+r, y1
        ]
        return self.create_polygon(points, smooth=True, **kwargs)
    
    def _draw(self):
        """Checkbox'ı çiz."""
        self.delete("all")
        
        colors = self.STYLES.get(self.style_name, self.STYLES["default"])
        size = self.box_size
        ox, oy = 2, 2
        checked = self.variable.get()
        
        import math
        
        # Gölge
        if self._state != "disabled":
            for i in range(3):
                t = i / 3
                alpha = 0.12 * (1 - t)
                shadow_color = self._blend_color(self.canvas_bg, "#000000", alpha)
                offset = (3 - i) * 0.3
                self._create_rounded_rect(
                    ox + offset * 0.2, oy + offset,
                    ox + size - offset * 0.2, oy + size + offset * 0.3,
                    4,
                    fill=shadow_color, outline=""
                )
        
        # Dış border
        self._create_rounded_rect(
            ox, oy, ox + size, oy + size,
            4,
            fill=colors["border"], outline=""
        )
        
        # İç gradient yüzey
        c_top = colors["bg_top"]
        c_bot = colors["bg_bottom"]
        
        if self._hover:
            c_top = self._blend_color(c_top, "#ffffff", 0.08)
            c_bot = self._blend_color(c_bot, "#ffffff", 0.04)
        
        # 3 katmanlı gradient
        for i in range(int(size - 2)):
            t = i / max(size - 3, 1)
            line_color = self._blend_color(c_top, c_bot, t)
            y = oy + 1 + i
            
            r = 3
            if i < r:
                corner = r - int(math.sqrt(max(0, r**2 - (r-i)**2)))
            elif i > size - 3 - r:
                remaining = size - 3 - i
                corner = r - int(math.sqrt(max(0, r**2 - (r-remaining)**2)))
            else:
                corner = 0
            
            x1 = ox + 1 + corner
            x2 = ox + size - 1 - corner
            if x2 > x1:
                self.create_line(x1, y, x2, y, fill=line_color)
        
        # Üst highlight
        highlight = self._blend_color(colors["border_light"], "#ffffff", 0.15)
        self._create_rounded_rect(
            ox + 1, oy + 1, ox + size - 1, oy + 2,
            3,
            fill=highlight, outline=""
        )
        
        # Tik işareti
        if checked:
            check_color = colors["check_color"]
            glow_color = colors["check_glow"]
            
            # Tik glow
            if self._hover:
                for i in range(2):
                    glow_alpha = 0.3 * (1 - i/2)
                    g_color = self._blend_color(c_bot, glow_color, glow_alpha)
                    expand = 2 - i
                    cx, cy = ox + size//2, oy + size//2
                    self.create_oval(
                        cx - size//3 - expand, cy - size//4 - expand,
                        cx + size//3 + expand, cy + size//4 + expand,
                        fill=g_color, outline=""
                    )
            
            # Tik çizimi (kalın çizgiler)
            cx = ox + size // 2
            cy = oy + size // 2
            
            # Tik noktaları
            p1 = (cx - size//4, cy)
            p2 = (cx - size//10, cy + size//4)
            p3 = (cx + size//3, cy - size//4)
            
            # Gölge
            self.create_line(
                p1[0], p1[1]+1, p2[0], p2[1]+1, p3[0], p3[1]+1,
                fill=self._blend_color(check_color, "#000000", 0.4),
                width=2.5, capstyle="round", joinstyle="round"
            )
            
            # Ana tik
            self.create_line(
                p1[0], p1[1], p2[0], p2[1], p3[0], p3[1],
                fill=check_color,
                width=2.5, capstyle="round", joinstyle="round"
            )
            
            # Parlak highlight
            self.create_line(
                p1[0]+0.5, p1[1]-0.5, p2[0]+0.5, p2[1]-0.5, p3[0]+0.5, p3[1]-0.5,
                fill=glow_color,
                width=1, capstyle="round", joinstyle="round"
            )
        
        # Label text
        if self.text:
            text_x = ox + size + 6
            text_y = oy + size // 2
            
            fg = colors["fg"]
            if self._state == "disabled":
                fg = self._blend_color(fg, self.canvas_bg, 0.5)
            
            # Text shadow
            self.create_text(
                text_x, text_y + 1,
                text=self.text,
                fill=self._blend_color(self.canvas_bg, "#000000", 0.3),
                font=self.label_font,
                anchor="w"
            )
            
            # Main text
            self.create_text(
                text_x, text_y,
                text=self.text,
                fill=fg,
                font=self.label_font,
                anchor="w"
            )
    
    def _on_var_change(self, *args):
        self._draw()
    
    def _on_enter(self, event):
        if self._state != "disabled":
            self._hover = True
            self._draw()
    
    def _on_leave(self, event):
        if self._state != "disabled":
            self._hover = False
            self._draw()
    
    def _on_click(self, event):
        if self._state != "disabled":
            self.variable.set(not self.variable.get())
            if self.command:
                self.command()
    
    def get(self) -> bool:
        return self.variable.get()
    
    def set(self, value: bool):
        self.variable.set(value)
    
    def configure(self, **kwargs):
        if "text" in kwargs:
            self.text = kwargs.pop("text")
        if "state" in kwargs:
            self._state = kwargs.pop("state")
        self._draw()
    
    config = configure


class IconButton3D(tk.Canvas):
    """
    3D görünümlü icon buton widget'ı.
    Üst menü çubuğu için: mail, bildirim, ayarlar, profil vb.
    """
    
    # Unicode/Emoji iconları
    ICONS = {
        "mail": "✉",
        "notification": "🔔",
        "bell": "🔔",
        "screen": "🖥",
        "monitor": "🖥",
        "settings": "⚙",
        "gear": "⚙",
        "profile": "👤",
        "user": "👤",
        "search": "🔍",
        "home": "🏠",
        "plus": "+",
        "minus": "−",
        "close": "✕",
        "check": "✓",
        "arrow_left": "◀",
        "arrow_right": "▶",
        "arrow_up": "▲",
        "arrow_down": "▼",
        "refresh": "⟳",
        "edit": "✎",
        "delete": "🗑",
        "save": "💾",
        "folder": "📁",
        "file": "📄",
        "calendar": "📅",
        "clock": "🕐",
        "star": "★",
        "heart": "♥",
        "info": "ℹ",
        "warning": "⚠",
        "error": "⊘",
    }
    
    STYLES = {
        "header": {
            "bg": "#111125",
            "bg_hover": "#1a1a3a",
            "fg": "#8888aa",
            "fg_hover": "#ffffff",
            "border": "#2a2a4a",
            "glow": "#4a4a8a",
        },
        "dark": {
            "bg": "#0d0d20",
            "bg_hover": "#1a1a35",
            "fg": "#6a6a8a",
            "fg_hover": "#e0e0f0",
            "border": "#252545",
            "glow": "#3a3a6a",
        },
        "light": {
            "bg": "#e8e8f0",
            "bg_hover": "#d8d8e8",
            "fg": "#4a4a6a",
            "fg_hover": "#1a1a3a",
            "border": "#c0c0d0",
            "glow": "#a0a0c0",
        },
        "danger": {
            "bg": "#2a1a1a",
            "bg_hover": "#3a2020",
            "fg": "#ff6b6b",
            "fg_hover": "#ff8888",
            "border": "#4a2a2a",
            "glow": "#ff4444",
        },
        "success": {
            "bg": "#1a2a1a",
            "bg_hover": "#203a20",
            "fg": "#6bff6b",
            "fg_hover": "#88ff88",
            "border": "#2a4a2a",
            "glow": "#44ff44",
        },
    }
    
    def __init__(
        self,
        parent,
        icon: str = "settings",
        command: Callable = None,
        style: str = "header",
        size: int = 32,
        badge: int = 0,
        badge_color: str = "#ef4444",
        image_path: str = None,
        bg: str = None,
        **kwargs
    ):
        self.icon_name = icon
        self.icon_char = self.ICONS.get(icon, icon)  # Özel karakter de kabul et
        self.command = command
        self.style_name = style
        self.btn_size = size
        self.badge_count = badge
        self.badge_color = badge_color
        self.image_path = image_path
        self._photo_image = None
        self._state = "normal"
        self._hover = False
        
        # Arka plan rengi
        if bg:
            self.canvas_bg = bg
        else:
            try:
                self.canvas_bg = parent.cget("bg")
            except:
                self.canvas_bg = "#111125"
        
        # Font boyutu icon için
        icon_font_size = max(10, size // 2)
        self.icon_font = kwargs.pop("font", ("Segoe UI Emoji", icon_font_size))
        
        # Canvas boyutu
        canvas_size = size + 4
        
        super().__init__(
            parent,
            width=canvas_size,
            height=canvas_size,
            bg=self.canvas_bg,
            highlightthickness=0,
            **kwargs
        )
        
        # Resim yükle
        if image_path:
            self._load_image()
        
        # Event bindings
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self.bind("<ButtonRelease-1>", self._on_release)
        
        self._draw()
    
    def _load_image(self):
        """Resim dosyasını yükle."""
        try:
            from PIL import Image, ImageTk
            img = Image.open(self.image_path)
            # Yuvarlak kırpma için boyutlandır
            img = img.resize((self.btn_size - 4, self.btn_size - 4), Image.Resampling.LANCZOS)
            self._photo_image = ImageTk.PhotoImage(img)
        except Exception as e:
            print(f"Image load error: {e}")
            self._photo_image = None
    
    def _blend_color(self, c1: str, c2: str, t: float) -> str:
        """Gamma-corrected renk karışımı."""
        gamma = 2.2
        
        def hex_to_rgb(h):
            h = h.lstrip('#')
            return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        
        def rgb_to_hex(r, g, b):
            return f"#{int(r):02x}{int(g):02x}{int(b):02x}"
        
        r1, g1, b1 = hex_to_rgb(c1)
        r2, g2, b2 = hex_to_rgb(c2)
        
        r1, g1, b1 = (r1/255)**gamma, (g1/255)**gamma, (b1/255)**gamma
        r2, g2, b2 = (r2/255)**gamma, (g2/255)**gamma, (b2/255)**gamma
        
        r = r1 * (1-t) + r2 * t
        g = g1 * (1-t) + g2 * t
        b = b1 * (1-t) + b2 * t
        
        r = int((r ** (1/gamma)) * 255)
        g = int((g ** (1/gamma)) * 255)
        b = int((b ** (1/gamma)) * 255)
        
        return rgb_to_hex(
            max(0, min(255, r)),
            max(0, min(255, g)),
            max(0, min(255, b))
        )
    
    def _draw(self):
        """Icon butonunu çiz."""
        self.delete("all")
        
        colors = self.STYLES.get(self.style_name, self.STYLES["header"])
        size = self.btn_size
        ox, oy = 2, 2
        cx, cy = ox + size // 2, oy + size // 2
        r = size // 2
        
        # Renkleri belirle
        if self._hover:
            bg = colors["bg_hover"]
            fg = colors["fg_hover"]
        else:
            bg = colors["bg"]
            fg = colors["fg"]
        
        border = colors["border"]
        
        # Gölge
        if self._state != "disabled":
            for i in range(3):
                t = i / 3
                alpha = 0.10 * (1 - t)
                shadow_color = self._blend_color(self.canvas_bg, "#000000", alpha)
                offset = (3 - i) * 0.2
                self.create_oval(
                    cx - r - 1 + offset, cy - r + offset,
                    cx + r + 1 + offset, cy + r + 1 + offset,
                    fill=shadow_color, outline=""
                )
        
        # Dış border (ince)
        self.create_oval(
            cx - r, cy - r,
            cx + r, cy + r,
            fill=border, outline=""
        )
        
        # İç yüzey (gradient efekti için 2 oval)
        bg_light = self._blend_color(bg, "#ffffff", 0.08)
        bg_dark = self._blend_color(bg, "#000000", 0.1)
        
        # Alt yarı (koyu)
        self.create_arc(
            cx - r + 1, cy - r + 1,
            cx + r - 1, cy + r - 1,
            start=-180, extent=180,
            fill=bg_dark, outline=""
        )
        
        # Üst yarı (açık)
        self.create_arc(
            cx - r + 1, cy - r + 1,
            cx + r - 1, cy + r - 1,
            start=0, extent=180,
            fill=bg_light, outline=""
        )
        
        # Ana yüzey
        self.create_oval(
            cx - r + 2, cy - r + 2,
            cx + r - 2, cy + r - 2,
            fill=bg, outline=""
        )
        
        # Üst highlight
        if self._hover:
            highlight = self._blend_color(bg, "#ffffff", 0.15)
            self.create_arc(
                cx - r + 3, cy - r + 3,
                cx + r - 3, cy - r//2,
                start=0, extent=180,
                fill=highlight, outline=""
            )
        
        # Icon veya resim
        if self._photo_image:
            self.create_image(cx, cy, image=self._photo_image, anchor="center")
        else:
            # Icon text
            self.create_text(
                cx, cy,
                text=self.icon_char,
                fill=fg,
                font=self.icon_font,
                anchor="center"
            )
        
        # Badge (bildirim sayısı)
        if self.badge_count > 0:
            badge_r = 7
            badge_x = cx + r - 4
            badge_y = cy - r + 4
            
            # Badge glow
            glow = self._blend_color(self.badge_color, "#ffffff", 0.3)
            self.create_oval(
                badge_x - badge_r - 1, badge_y - badge_r - 1,
                badge_x + badge_r + 1, badge_y + badge_r + 1,
                fill=glow, outline=""
            )
            
            # Badge arka plan
            self.create_oval(
                badge_x - badge_r, badge_y - badge_r,
                badge_x + badge_r, badge_y + badge_r,
                fill=self.badge_color, outline=""
            )
            
            # Badge sayı
            badge_text = str(self.badge_count) if self.badge_count < 10 else "9+"
            self.create_text(
                badge_x, badge_y,
                text=badge_text,
                fill="#ffffff",
                font=("Segoe UI", 7, "bold"),
                anchor="center"
            )
    
    def _on_enter(self, event):
        if self._state != "disabled":
            self._hover = True
            self._draw()
    
    def _on_leave(self, event):
        if self._state != "disabled":
            self._hover = False
            self._draw()
    
    def _on_click(self, event):
        if self._state != "disabled":
            self._state = "pressed"
            self._draw()
    
    def _on_release(self, event):
        if self._state != "disabled":
            self._state = "normal"
            self._draw()
            if self.command:
                self.command()
    
    def set_badge(self, count: int):
        """Badge sayısını güncelle."""
        self.badge_count = count
        self._draw()
    
    def configure(self, **kwargs):
        if "icon" in kwargs:
            self.icon_name = kwargs.pop("icon")
            self.icon_char = self.ICONS.get(self.icon_name, self.icon_name)
        if "badge" in kwargs:
            self.badge_count = kwargs.pop("badge")
        if "state" in kwargs:
            self._state = kwargs.pop("state")
        self._draw()
    
    config = configure


class SimpleField:
    """Basit get/set alanı (LabeledEntry yerine)"""
    def __init__(self, value: str = ""):
        self._v = "" if value is None else str(value)
    def get(self) -> str:
        return self._v
    def set(self, v: str):
        self._v = "" if v is None else str(v)

class LabeledEntry(ttk.Frame):
    def __init__(self, master, label: str, width: int = 18):
        super().__init__(master)
        ttk.Label(self, text=label).pack(side=tk.LEFT, padx=(0,6))
        self.ent = ttk.Entry(self, width=width)
        self.ent.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def get(self) -> str:
        return self.ent.get()

    def set(self, v: str):
        self.ent.delete(0, tk.END)
        self.ent.insert(0, v)

class LabeledCombo(ttk.Frame):
    def __init__(self, master, label: str, values: List[str], width: int = 18, state: str="readonly"):
        super().__init__(master)
        ttk.Label(self, text=label).pack(side=tk.LEFT, padx=(0,6))
        self.var = tk.StringVar()
        self.cmb = ttk.Combobox(self, textvariable=self.var, values=values, width=width, state=state)
        self.cmb.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def get(self) -> str:
        return self.var.get()

    def set(self, v: str):
        self.var.set(v)

class MoneyEntry(ttk.Frame):
    """Para/tutar girişi için Entry (TR).
    - Yazarken maskeleme: 1111111 -> 1.111.111,00
    - ',' veya '.' basınca imleç küsurat kısmına geçer (virgülden sonraki 2 hane).
    - FocusOut / Enter'da kesin TR formatına çevirir (fmt_amount).
    """
    _IGNORE_KEYS = {
        "Left","Right","Up","Down","Home","End","Tab",
        "Shift_L","Shift_R","Control_L","Control_R","Alt_L","Alt_R",
        "Caps_Lock","Escape","Prior","Next"
    }

    def __init__(self, master, label: str, width: int = 12):
        super().__init__(master)
        ttk.Label(self, text=label).pack(side=tk.LEFT, padx=(0,6))
        self.var = tk.StringVar()
        self.ent = ttk.Entry(self, width=width, textvariable=self.var)
        self.ent.pack(side=tk.LEFT)

        self._formatting = False

        # Canlı maskeleme + çıkınca/enter'da kesin format
        self.ent.bind("<KeyRelease>", self._on_key_release)
        self.ent.bind("<FocusOut>", lambda _e: self.format_now())
        self.ent.bind("<Return>", self._on_return)

    @staticmethod
    def _group_tr(digits: str) -> str:
        # "1234567" -> "1.234.567"
        if not digits:
            return "0"
        rev = digits[::-1]
        parts = [rev[i:i+3] for i in range(0, len(rev), 3)]
        return ".".join(p[::-1] for p in parts[::-1])

    def _mask_tr(self, s: str) -> tuple[str, int]:
        """Girilen metni TR para biçimine maskele.
        Dönüş: (formatted, typed_dec_len)
        typed_dec_len: kullanıcının küsurat kısmında yazdığı hane sayısı (0-2).
        """
        s = (s or "").strip()
        if not s:
            return ("", 0)

        # işaret
        sign = ""
        if s.startswith("-"):
            sign = "-"
            s = s[1:].lstrip()

        # yalnızca rakam + ayırıcılar
        s = re.sub(r"[^\d,\.]", "", s)

        # Ondalık ayracı belirle:
        # - Virgül varsa onu kullan
        # - Virgül yoksa ve tek nokta + en fazla 2 hane ile bitiyorsa onu ondalık say
        dec_sep = None
        if "," in s:
            dec_sep = ","
        elif "." in s and s.count(".") == 1 and re.fullmatch(r"\d+\.\d{0,2}", s):
            dec_sep = "."

        if dec_sep:
            ip, dp = s.split(dec_sep, 1)
            ip_digits = re.sub(r"\D", "", ip)
            dp_digits = re.sub(r"\D", "", dp)[:2]
            typed_dec_len = len(dp_digits)
        else:
            ip_digits = re.sub(r"\D", "", s)
            dp_digits = ""
            typed_dec_len = 0

        if ip_digits == "" and dp_digits == "":
            return ("", 0)

        ip_digits = ip_digits.lstrip("0") or "0"
        grouped = self._group_tr(ip_digits)
        dp_show = (dp_digits or "").ljust(2, "0")[:2] if (dp_digits or "") else "00"
        return (f"{sign}{grouped},{dp_show}", typed_dec_len)

    def _on_return(self, _e):
        self.format_now()
        return "break"

    def _on_key_release(self, e: tk.Event):
        if self._formatting:
            return
        if getattr(e, "keysym", "") in self._IGNORE_KEYS:
            return
        # Enter zaten ayrı handler
        if getattr(e, "keysym", "") in ("Return", "KP_Enter"):
            return

        raw = self.var.get()
        # imleç konumu: küsurata mı yazıyor?
        try:
            cur = int(self.ent.index(tk.INSERT))
        except Exception:
            cur = len(raw)

        comma_pos_raw = raw.find(",")
        dot_pos_raw = raw.rfind(".")
        in_dec = False
        if comma_pos_raw != -1 and cur > comma_pos_raw:
            in_dec = True
        elif comma_pos_raw == -1 and dot_pos_raw != -1 and re.fullmatch(r".*\.\d{0,2}", raw):
            if cur > dot_pos_raw:
                in_dec = True

        # ',' veya '.' tuşu basıldıysa küsurata geç
        if getattr(e, "char", "") in (",", "."):
            in_dec = True

        formatted, typed_dec_len = self._mask_tr(raw)

        # tamamen boşsa boş bırak
        if formatted == "":
            return

        # Yeniden yaz
        self._formatting = True
        try:
            if formatted != raw:
                self.var.set(formatted)
        finally:
            self._formatting = False

        # imleci ayarla
        comma_pos = formatted.find(",")
        try:
            if in_dec:
                if getattr(e, "char", "") in (",", "."):
                    # küsurat kısmını seç ki direkt yazılabilsin
                    self.ent.icursor(comma_pos + 1)
                    self.ent.selection_range(comma_pos + 1, tk.END)
                else:
                    newpos = min(len(formatted), comma_pos + 1 + min(typed_dec_len, 2))
                    self.ent.icursor(newpos)
            else:
                # sürekli rakam girerken virgülden önce kalsın
                self.ent.icursor(comma_pos)
        except Exception:
            pass

    def format_now(self):
        s = (self.var.get() or "").strip()
        if not s:
            return
        val = parse_number_smart(s)
        self._formatting = True
        try:
            self.var.set(fmt_amount(val))
        finally:
            self._formatting = False

    def get_float(self) -> float:
        return safe_float(self.var.get())

    def set(self, v: Any):
        self._formatting = True
        try:
            self.var.set("" if (v is None or v == "") else fmt_amount(parse_number_smart(v)))
        finally:
            self._formatting = False
