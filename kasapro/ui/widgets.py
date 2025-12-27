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
        
        # Canvas boyutunu gölge için genişlet
        self.configure(width=width + 8, height=height + 8)
        
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
        """Butonu çiz - KasaPro UI stiline uygun ultra kaliteli görünüm."""
        self.delete("all")
        
        w, h = self.btn_width, self.btn_height
        ox, oy = 3, 3  # Gölge alanı
        radius = 8  # Daha yumuşak köşeler
        
        colors = self.colors
        
        # Durum bazlı renkler
        if self._state == "disabled":
            bg_top = "#2a2a2a"
            bg_mid = "#252525"
            bg_bottom = "#202020"
            fg = "#555555"
            border = "#333333"
            border_light = "#333333"
            glow = None
            inner_glow = None
        elif self._state == "pressed":
            bg_top = colors["bg_pressed_top"]
            bg_mid = self._blend_color(colors["bg_pressed_top"], colors["bg_pressed_bottom"], 0.5)
            bg_bottom = colors["bg_pressed_bottom"]
            fg = colors["fg"]
            border = colors["border"]
            border_light = self._blend_color(colors["border_light"], "#000000", 0.4)
            glow = None
            inner_glow = None
        elif self._state == "hover":
            bg_top = colors["bg_hover_top"]
            bg_mid = self._blend_color(colors["bg_hover_top"], colors["bg_hover_bottom"], 0.45)
            bg_bottom = colors["bg_hover_bottom"]
            fg = colors["fg"]
            border = colors["border"]
            border_light = colors["border_light"]
            glow = colors.get("glow")
            inner_glow = self._blend_color(colors["bg_hover_top"], "#ffffff", 0.15)
        else:
            bg_top = colors["bg_top"]
            bg_mid = self._blend_color(colors["bg_top"], colors["bg_bottom"], 0.45)
            bg_bottom = colors["bg_bottom"]
            fg = colors["fg"]
            border = colors["border"]
            border_light = colors["border_light"]
            glow = colors.get("glow")
            inner_glow = self._blend_color(colors["bg_top"], "#ffffff", 0.08)
        
        import math
        
        # ============================================
        # GÖLGE (Çok yumuşak, çok katmanlı)
        # ============================================
        if self._state not in ("pressed", "disabled"):
            # 5 katmanlı ultra yumuşak gölge
            for i in range(5):
                alpha = 0.08 - i * 0.012
                shadow_color = self._blend_color(self.canvas_bg, "#000000", alpha)
                offset = (5 - i) * 0.6
                blur = i * 0.4
                self._create_rounded_rect(
                    ox + blur, oy + offset + blur,
                    ox + w - blur, oy + h + offset,
                    radius + 2,
                    fill=shadow_color, outline=""
                )
        
        # ============================================
        # DIŞ GLOW (Hover efekti)
        # ============================================
        if glow and self._state == "hover":
            # 3 katmanlı glow
            for i in range(3):
                glow_alpha = 0.12 - i * 0.03
                glow_color = self._blend_color(self.canvas_bg, glow, glow_alpha)
                expand = 3 - i
                self._create_rounded_rect(
                    ox - expand, oy - expand + 1,
                    ox + w + expand, oy + h + expand,
                    radius + expand + 2,
                    fill=glow_color, outline=""
                )
        
        # ============================================
        # KENAR (Gradient border)
        # ============================================
        self._create_rounded_rect(
            ox, oy, ox + w, oy + h,
            radius,
            fill=border, outline=""
        )
        
        # ============================================
        # ÜST IŞIK KENARI (İnce highlight - bevel efekti)
        # ============================================
        if self._state != "pressed":
            # Üst kenar - açık çizgi
            self._create_rounded_rect(
                ox + 1, oy + 1, ox + w - 1, oy + 2,
                radius - 1,
                fill=border_light, outline=""
            )
        
        # ============================================
        # ANA YÜZEY (3 Noktalı Ultra Kalite Gradient)
        # ============================================
        surface_x1 = ox + 1
        surface_y1 = oy + 2 if self._state != "pressed" else oy + 1
        surface_x2 = ox + w - 1
        surface_y2 = oy + h - 1
        surface_h = surface_y2 - surface_y1
        
        # 3 noktalı gradient (üst -> orta -> alt)
        if surface_h > 0:
            mid_point = 0.35  # Orta renk %35'te
            
            for i in range(int(surface_h)):
                t = i / max(surface_h - 1, 1)
                
                # Ultra smooth 3-noktalı interpolasyon
                if t <= mid_point:
                    # Üst -> Orta
                    local_t = t / mid_point
                    smooth_t = self._smootherstep(local_t)
                    line_color = self._blend_color(bg_top, bg_mid, smooth_t)
                else:
                    # Orta -> Alt
                    local_t = (t - mid_point) / (1 - mid_point)
                    smooth_t = self._smootherstep(local_t)
                    line_color = self._blend_color(bg_mid, bg_bottom, smooth_t)
                
                y = surface_y1 + i
                
                # Köşe hesabı - daha düzgün
                r_inner = radius - 2
                if i < r_inner:
                    progress = (r_inner - i) / r_inner
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
        # İÇ KENAR PARLAMASI (Inner glow - edge highlight)
        # ============================================
        if self._state != "pressed" and inner_glow:
            # Üst kenar parlama (daha belirgin)
            gloss_height = min((h - 6) // 4, 10)
            
            for i in range(max(gloss_height, 1)):
                t = i / max(gloss_height - 1, 1)
                # Çok yumuşak düşüş
                falloff = (1 - self._smootherstep(t)) ** 1.5
                alpha = falloff * (0.18 if self._state == "hover" else 0.12)
                
                if alpha < 0.005:
                    continue
                
                line_color = self._blend_color(bg_top, "#ffffff", alpha)
                y = surface_y1 + i
                
                # Köşe
                r_inner = radius - 3
                if r_inner > 0 and i < r_inner:
                    corner_offset = r_inner - int(math.sqrt(max(0, r_inner**2 - (r_inner - i)**2)))
                else:
                    corner_offset = 0
                
                x1 = ox + 3 + corner_offset
                x2 = ox + w - 3 - corner_offset
                
                if x2 > x1:
                    self.create_line(x1, y, x2, y, fill=line_color)
            
            # Sol ve sağ kenar ince parlama
            edge_glow_width = 3
            for j in range(edge_glow_width):
                edge_alpha = (1 - j / edge_glow_width) * 0.04
                edge_color = self._blend_color(bg_mid, "#ffffff", edge_alpha)
                
                # Sol kenar
                for i in range(int(surface_h * 0.6)):
                    y = surface_y1 + gloss_height + i
                    if y < surface_y2 - radius:
                        self.create_line(
                            surface_x1 + 2 + j, y,
                            surface_x1 + 3 + j, y,
                            fill=edge_color
                        )
                
                # Sağ kenar
                for i in range(int(surface_h * 0.6)):
                    y = surface_y1 + gloss_height + i
                    if y < surface_y2 - radius:
                        self.create_line(
                            surface_x2 - 3 - j, y,
                            surface_x2 - 2 - j, y,
                            fill=edge_color
                        )
        
        # ============================================
        # ALT RIM LIGHT (İnce parlak çizgi)
        # ============================================
        if self._state not in ("pressed", "disabled"):
            # Gradient rim light
            rim_width = w - 2 * radius - 4
            rim_center = ox + w // 2
            
            for i in range(int(rim_width)):
                rx = rim_center - rim_width // 2 + i
                # Ortada parlak, kenarlarda sönük
                t = abs(i - rim_width / 2) / (rim_width / 2)
                rim_alpha = (1 - t ** 2) * 0.08
                rim_color = self._blend_color(bg_bottom, "#ffffff", rim_alpha)
                self.create_line(rx, oy + h - 3, rx + 1, oy + h - 3, fill=rim_color)
        
        # ============================================
        # METİN
        # ============================================
        text_x = ox + w // 2
        text_y = oy + h // 2
        
        if self._state == "pressed":
            text_y += 1
        
        # Metin gölgesi
        if self._state != "disabled":
            shadow_color = self._blend_color(bg_bottom, "#000000", 0.4)
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
