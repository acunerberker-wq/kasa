# -*- coding: utf-8 -*-
"""KasaPro v3 - Login penceresi (Toplevel) - Modern Light UI."""

from __future__ import annotations

import sys
import sqlite3
from typing import Optional

import tkinter as tk
from tkinter import ttk, messagebox

from ...config import APP_TITLE
from ...db.users_db import UsersDB
from ...utils import center_window


# ---- RENK PALET (Qt Dark Glass theme - login_with_user_select.ui) ----
COLORS = {
    # Qt: qradialgradient - stop:0 rgba(20, 30, 50), stop:0.55 rgba(10, 14, 24), stop:1 rgba(6, 8, 14)
    "bg_dark": "#06080e",           # Ana arka plan (Qt: rgba(6, 8, 14))
    "bg_mid": "#0a0e18",            # Orta arka plan (Qt: rgba(10, 14, 24))
    "bg_glow": "#141e32",           # Glow efekt (Qt: rgba(20, 30, 50))
    # Qt: QFrame#Card - background: rgba(18, 26, 42, 165), border: rgba(255,255,255,30)
    "card_bg": "#121a2a",           # Kart zemini (Qt: rgba(18, 26, 42))
    "card_border": "#3a3a44",       # Kart kenarlik (simulated rgba(255,255,255,30))
    # Qt: QLineEdit/QComboBox - background: rgba(255,255,255,10), border: rgba(255,255,255,22)
    "input_bg": "#161a22",          # Input arka plan
    "input_border": "#2a2e38",      # Input kenarlik (simulated)
    # Qt: focus - border: rgba(90, 150, 255, 160), background: rgba(255,255,255,12)
    "input_focus": "#5a96ff",       # Focus rengi (Qt: rgba(90, 150, 255))
    "input_focus_solid": "#5a96ff", # Focus solid
    "input_focus_bg": "#14192a",    # Focus arka plan
    # Qt: color: rgba(240,245,255,220) / rgba(235,240,255,210)
    "text_primary": "#e8ecf5",      # Ana metin (Qt: rgba(240,245,255,220))
    "text_secondary": "#d0d6e2",    # Ikincil metin (Qt: rgba(235,240,255,210))
    "text_muted": "#8090aa",        # Soluk metin (Qt: rgba(180,200,255,120))
    "text_placeholder": "#7080a0",  # Placeholder
    # Qt: QPushButton#BtnLogin - gradient rgba(55, 140, 255) -> rgba(20, 90, 210)
    "accent": "#378cff",            # Aksan (Qt: rgba(55, 140, 255))
    "accent_dark": "#145ad2",       # Aksan koyu (Qt: rgba(20, 90, 210))
    "accent_hover": "#46a0ff",      # Hover (Qt: rgba(70, 160, 255))
    "accent_hover_dark": "#1969e6", # Hover koyu (Qt: rgba(25, 105, 230))
    # Qt: QFrame#GlowLine - gradient rgba(80,160,255,140)
    "accent_glow": "#3878b8",       # Glow line (simulated with dark bg blend)
    # Qt: border: 1px solid rgba(140, 190, 255, 90)
    "btn_border": "#5a7eb0",        # Buton kenarlik (simulated)
    # Qt: LblForgot - color: rgba(200,215,255,140), hover: rgba(220,235,255,210)
    "link": "#8898c0",              # Link (simulated)
    "link_hover": "#b8c8e8",        # Link hover (simulated)
    # Qt: Divider - background: rgba(255,255,255,18)
    "divider": "#282c36",           # Divider (simulated)
    # Qt: QAbstractItemView - background: rgba(18, 26, 42, 230), selection: rgba(70, 130, 255, 120)
    "dropdown_bg": "#101620",       # Dropdown
    "selection": "#2a4878",         # Selection (simulated)
    # Qt: QCheckBox indicator checked - background: rgba(70, 130, 255, 160), border: rgba(120, 170, 255, 200)
    "checkbox_checked": "#4682ff",  # Checkbox checked (Qt: rgba(70, 130, 255))
    "checkbox_border": "#78aaff",   # Checkbox border (Qt: rgba(120, 170, 255))
    # Qt: LblSpinner - border: 2px solid rgba(130, 170, 255, 90)
    "spinner_border": "#5878a8",    # Spinner border (simulated)
}

# Qt: font-family: "Inter","Segoe UI","SF Pro Display" - sans-serif fontlar
# Tkinter için platform bazlı sans-serif font seçimi
import tkinter.font as tkfont

def _get_sans_serif_font() -> str:
    """Sistemde mevcut olan ilk sans-serif fontu döndür."""
    # Tercih sırası: Inter > Segoe UI > SF Pro Display > Helvetica Neue > Arial
    preferred = ["Inter", "Segoe UI", "SF Pro Display", "Helvetica Neue", "Arial", "Helvetica"]
    try:
        available = tkfont.families()
        for font in preferred:
            if font in available:
                return font
    except Exception:
        pass
    # Windows için varsayılan
    if sys.platform.startswith("win"):
        return "Segoe UI"
    # macOS için varsayılan
    elif sys.platform == "darwin":
        return "SF Pro Display"
    # Linux için varsayılan
    return "DejaVu Sans"

# Lazy initialization - font ailesi ilk kullanımda belirlenir
_BASE_FONT_CACHE: Optional[str] = None

def get_base_font() -> str:
    """Sans-serif base font döndür (lazy loaded)."""
    global _BASE_FONT_CACHE
    if _BASE_FONT_CACHE is None:
        _BASE_FONT_CACHE = _get_sans_serif_font()
    return _BASE_FONT_CACHE

# Eski kod ile uyumluluk için
BASE_FONT = "Segoe UI"  # Varsayılan, runtime'da güncellenir


def _round_rect_points(x1: float, y1: float, x2: float, y2: float, r: float) -> list[float]:
    return [
        x1 + r, y1,
        x2 - r, y1,
        x2, y1,
        x2, y1 + r,
        x2, y2 - r,
        x2, y2,
        x2 - r, y2,
        x1 + r, y2,
        x1, y2,
        x1, y2 - r,
        x1, y1 + r,
        x1, y1,
    ]


class RoundedBox(tk.Canvas):
    def __init__(
        self,
        master: tk.Misc,
        radius: int,
        bg_color: str,
        border_color: str,
        border_width: int = 1,
        padding: int = 0,
        **kwargs,
    ):
        super().__init__(
            master,
            highlightthickness=0,
            bd=0,
            bg=master.cget("bg"),
            **kwargs,
        )
        self.radius = radius
        self.bg_color = bg_color
        self.border_color = border_color
        self.border_width = border_width
        self.padding = padding

        self.inner = tk.Frame(self, bg=self.bg_color)
        self._window = self.create_window(0, 0, anchor="nw", window=self.inner)
        self.bind("<Configure>", self._redraw)

    def _redraw(self, _event=None):
        self.delete("round")
        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 2 or h <= 2:
            return
        bw = max(0, int(self.border_width))
        half = bw / 2 if bw else 0
        r = min(self.radius, (w - bw) / 2, (h - bw) / 2)
        if r < 0:
            r = 0
        points = _round_rect_points(half, half, w - half, h - half, r)
        self.create_polygon(
            points,
            smooth=True,
            fill=self.bg_color,
            outline=self.border_color if bw else self.bg_color,
            width=bw,
            tags="round",
        )
        inner_pad = self.padding + bw
        inner_w = max(1, w - 2 * inner_pad)
        inner_h = max(1, h - 2 * inner_pad)
        self.coords(self._window, inner_pad, inner_pad)
        self.itemconfigure(self._window, width=inner_w, height=inner_h)

    def set_colors(self, bg_color: Optional[str] = None, border_color: Optional[str] = None) -> None:
        if bg_color is not None:
            self.bg_color = bg_color
            self.inner.configure(bg=bg_color)
        if border_color is not None:
            self.border_color = border_color
        self._redraw()

    def fit_to_inner(self) -> None:
        self.update_idletasks()
        w = self.inner.winfo_reqwidth() + 2 * (self.padding + self.border_width)
        h = self.inner.winfo_reqheight() + 2 * (self.padding + self.border_width)
        self.configure(width=w, height=h)
        self._redraw()


class ModernEntry(tk.Frame):
    """Modern görünümlü input widget - Qt QLineEdit stiline uygun."""
    
    def __init__(self, master, placeholder: str = "", show: str = "", **kwargs):
        super().__init__(master, bg=COLORS["card_bg"], **kwargs)
        
        self.placeholder = placeholder
        self._show = show
        self._has_focus = False
        
        self.box = RoundedBox(
            self,
            radius=14,
            bg_color=COLORS["input_bg"],
            border_color=COLORS["input_border"],
            border_width=1,
            padding=10,
            height=44,
        )
        self.box.pack(fill=tk.X)
        
        # Entry widget - Qt: font-size: 14px, color: rgba(240,245,255,220)
        self.entry = tk.Entry(
            self.box.inner,
            font=(BASE_FONT, 12),
            bg=COLORS["input_bg"],
            fg=COLORS["text_placeholder"],
            insertbackground=COLORS["text_primary"],
            relief=tk.FLAT,
            highlightthickness=0,
            bd=0,
            show="" if not show else "",
        )
        self.entry.pack(fill=tk.X)
        self.entry.insert(0, placeholder)
        
        # Event bindings
        self.entry.bind("<FocusIn>", self._on_focus_in)
        self.entry.bind("<FocusOut>", self._on_focus_out)
    
    def _on_focus_in(self, _event):
        self._has_focus = True
        # Qt: border: 1px solid rgba(90, 150, 255, 160), background: rgba(255,255,255,12)
        self.box.set_colors(bg_color=COLORS["input_focus_bg"], border_color=COLORS["input_focus_solid"])
        self.entry.configure(bg=COLORS["input_focus_bg"])
        if self.entry.get() == self.placeholder:
            self.entry.delete(0, tk.END)
            self.entry.configure(fg=COLORS["text_primary"])
            if self._show:
                self.entry.configure(show=self._show)
    
    def _on_focus_out(self, _event):
        self._has_focus = False
        self.box.set_colors(bg_color=COLORS["input_bg"], border_color=COLORS["input_border"])
        self.entry.configure(bg=COLORS["input_bg"])
        if not self.entry.get():
            self.entry.insert(0, self.placeholder)
            self.entry.configure(fg=COLORS["text_placeholder"], show="")
    
    def get(self) -> str:
        val = self.entry.get()
        return "" if val == self.placeholder else val
    
    def set(self, value: str):
        self.entry.delete(0, tk.END)
        if value:
            self.entry.insert(0, value)
            self.entry.configure(fg=COLORS["text_primary"])
            if self._show:
                self.entry.configure(show=self._show)
        else:
            self.entry.insert(0, self.placeholder)
            self.entry.configure(fg=COLORS["text_placeholder"], show="")


class ModernCombobox(tk.Frame):
    """Modern görünümlü combobox widget - Qt QComboBox stiline uygun."""
    
    def __init__(self, master, values: list, placeholder: str = "Seç...", **kwargs):
        super().__init__(master, bg=COLORS["card_bg"], **kwargs)
        
        self.box = RoundedBox(
            self,
            radius=14,
            bg_color=COLORS["input_bg"],
            border_color=COLORS["input_border"],
            border_width=1,
            padding=8,
            height=44,
        )
        self.box.pack(fill=tk.X)
        
        # Dropdown listbox styling - Qt: QAbstractItemView
        # Qt: background: rgba(18, 26, 42, 230), selection-background-color: rgba(70, 130, 255, 120)
        root = self.winfo_toplevel()
        root.option_add("*TCombobox*Listbox.background", COLORS["dropdown_bg"])
        root.option_add("*TCombobox*Listbox.foreground", COLORS["text_primary"])
        root.option_add("*TCombobox*Listbox.selectBackground", COLORS["selection"])
        root.option_add("*TCombobox*Listbox.selectForeground", COLORS["text_primary"])
        
        # Style for combobox - Qt: font-size: 14px, color: rgba(240,245,255,220)
        style = ttk.Style()
        style.configure(
            "Modern.TCombobox",
            fieldbackground=COLORS["input_bg"],
            background=COLORS["input_bg"],
            foreground=COLORS["text_primary"],
            arrowcolor=COLORS["text_muted"],
            borderwidth=0,
            relief="flat",
            padding=4,
        )
        style.map("Modern.TCombobox",
            fieldbackground=[("readonly", COLORS["input_bg"])],
            selectbackground=[("readonly", COLORS["selection"])],
            selectforeground=[("readonly", COLORS["text_primary"])],
        )
        
        self.combo = ttk.Combobox(
            self.box.inner,
            values=values,
            state="readonly",
            font=(BASE_FONT, 12),
            style="Modern.TCombobox",
        )
        self.combo.pack(fill=tk.X)
        
        if values:
            self.combo.set(placeholder)
        
        # Focus efektleri - Qt: border: 1px solid rgba(90, 150, 255, 160)
        self.combo.bind("<FocusIn>", lambda _: self.box.set_colors(border_color=COLORS["input_focus_solid"]))
        self.combo.bind("<FocusOut>", lambda _: self.box.set_colors(border_color=COLORS["input_border"]))
    
    def get(self) -> str:
        return self.combo.get()
    
    def set(self, value: str):
        self.combo.set(value)
    
    def bind_selection(self, callback):
        self.combo.bind("<<ComboboxSelected>>", callback)


class ModernCheckbox(tk.Frame):
    """Modern görünümlü checkbox widget - Qt QCheckBox stiline uygun."""
    
    def __init__(self, master, text: str = "", **kwargs):
        super().__init__(master, bg=COLORS["card_bg"], **kwargs)
        
        self.var = tk.BooleanVar(value=False)
        
        # Checkbox frame
        self.check_frame = tk.Frame(self, bg=COLORS["card_bg"], cursor="hand2")
        self.check_frame.pack(side=tk.LEFT)
        
        # Checkbox indicator - Qt: width/height: 18px, border-radius: 6px
        # Qt unchecked: border: 1px solid rgba(255,255,255,30), background: rgba(255,255,255,10)
        self.indicator = tk.Canvas(
            self.check_frame,
            width=18, height=18,
            bg=COLORS["card_bg"],
            highlightthickness=0,
        )
        self.indicator.pack(side=tk.LEFT, padx=(0, 10))
        
        # Label - Qt: color: rgba(230,235,255,190), font-size: 13px
        self.label = tk.Label(
            self,
            text=text,
            font=(BASE_FONT, 11),
            bg=COLORS["card_bg"],
            fg=COLORS["text_secondary"],
            cursor="hand2",
        )
        self.label.pack(side=tk.LEFT)
        
        # Click bindings
        self.indicator.bind("<Button-1>", self._toggle)
        self.label.bind("<Button-1>", self._toggle)
        self.check_frame.bind("<Button-1>", self._toggle)
        
        self._update_indicator()
    
    def _toggle(self, _event=None):
        self.var.set(not self.var.get())
        self._update_indicator()
    
    def _update_indicator(self):
        self.indicator.delete("all")
        if self.var.get():
            # Qt: checked - background: rgba(70, 130, 255, 160), border: rgba(120, 170, 255, 200)
            border = COLORS["checkbox_border"]
            fill = COLORS["checkbox_checked"]
            # Draw checkmark
            self.indicator.create_oval(1, 1, 17, 17, outline=border, width=1, fill=fill, tags="box")
            self.indicator.create_line(4, 9, 7, 13, fill="white", width=2, tags="check")
            self.indicator.create_line(7, 13, 14, 5, fill="white", width=2, tags="check")
        else:
            # Qt: unchecked - border: rgba(255,255,255,30), background: rgba(255,255,255,10)
            border = COLORS["input_border"]
            fill = COLORS["input_bg"]
            self.indicator.create_oval(1, 1, 17, 17, outline=border, width=1, fill=fill, tags="box")
    
    def get(self) -> bool:
        return self.var.get()


class ModernButton(tk.Frame):
    """Modern gradient button widget - Qt QPushButton#BtnLogin stiline uygun."""
    
    def __init__(self, master, text: str, command=None, **kwargs):
        super().__init__(master, bg=COLORS["card_bg"], **kwargs)
        
        self.command = command
        
        self.box = RoundedBox(
            self,
            radius=14,
            bg_color=COLORS["accent"],
            border_color=COLORS["btn_border"],
            border_width=1,
            padding=1,
            height=48,
        )
        self.box.pack(fill=tk.X)
        
        # Button - Qt: background gradient rgba(55, 140, 255) -> rgba(20, 90, 210)
        # Qt: font-size: 18px, padding: 12px 14px, color: rgba(255,255,255,240)
        self.btn = tk.Label(
            self.box.inner,
            text=text,
            font=(BASE_FONT, 13, "bold"),
            bg=COLORS["accent"],
            fg="#ffffff",
            padx=14,
            pady=10,
            cursor="hand2",
        )
        self.btn.pack(fill=tk.X)
        
        # Hover effects
        self.btn.bind("<Enter>", self._on_enter)
        self.btn.bind("<Leave>", self._on_leave)
        self.btn.bind("<Button-1>", self._on_click)
        self.btn.bind("<ButtonRelease-1>", self._on_release)
    
    def _on_enter(self, _event):
        # Qt hover: rgba(70, 160, 255) -> rgba(25, 105, 230)
        self._set_state(COLORS["accent_hover"])
    
    def _on_leave(self, _event):
        self._set_state(COLORS["accent"])
    
    def _on_click(self, _event):
        # Qt pressed: rgba(20, 90, 210)
        self._set_state(COLORS["accent_dark"])
    
    def _on_release(self, _event):
        self._set_state(COLORS["accent"])
        if self.command:
            self.command()

    def _set_state(self, bg_color: str) -> None:
        self.box.set_colors(bg_color=bg_color)
        self.btn.configure(bg=bg_color)


class LoginWindow(tk.Toplevel):
    """Modern Dark Glass Login Window."""
    
    def __init__(self, root: tk.Tk, usersdb: UsersDB):
        super().__init__(root)
        self.usersdb = usersdb
        self.user: Optional[sqlite3.Row] = None
        
        # Sans-serif font'u runtime'da belirle
        global BASE_FONT
        BASE_FONT = get_base_font()
        
        # Pencere ayarları
        self.title("Giriş")
        self.geometry("980x620")
        self.resizable(False, False)
        self.configure(bg=COLORS["bg_dark"])
        
        # Root ile ilişki
        try:
            if bool(root.winfo_viewable()):
                self.transient(root)
        except Exception:
            pass
        self.protocol("WM_DELETE_WINDOW", self.do_exit)
        
        self._build_ui()
        self._setup_events()
        self._post_init()
    
    def _build_ui(self):
        """Ana UI yapısını oluştur - Qt LoginWindow stiline uygun."""
        # Background glow
        self._bg_canvas = tk.Canvas(self, bg=COLORS["bg_dark"], highlightthickness=0, bd=0)
        self._bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        tk.Misc.lower(self._bg_canvas)
        self.bind("<Configure>", self._draw_background)
        self._draw_background()

        # Ana container (merkeze hizalama için)
        main_container = tk.Frame(self, bg=COLORS["bg_dark"])
        main_container.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        # Glass Card - Qt: minimumSize 720x460, padding 48/42/48/34, spacing 16
        # Qt: background: rgba(18, 26, 42, 165), border: 1px solid rgba(255,255,255,30), border-radius: 16px
        card_box = RoundedBox(
            main_container,
            radius=16,
            bg_color=COLORS["card_bg"],
            border_color=COLORS["card_border"],  # Simulated rgba(255,255,255,30)
            border_width=1,
            padding=32,
        )
        card_box.pack()
        card = card_box.inner
        
        # ---- BRAND ROW ---- Qt: spacing 12
        brand_frame = tk.Frame(card, bg=COLORS["card_bg"])
        brand_frame.pack(fill=tk.X, pady=(0, 16))
        
        # Logo - Qt: 36x36, gradient mavi, border-radius: 10px
        # Qt: qlineargradient rgba(70,160,255) -> rgba(30,110,230)
        logo = tk.Canvas(brand_frame, width=36, height=36, bg=COLORS["card_bg"], highlightthickness=0)
        logo.pack(side=tk.LEFT, padx=(0, 12))
        # Gradient simulation - Qt: rgba(70,160,255) -> rgba(30,110,230)
        logo.create_rectangle(0, 0, 36, 36, fill=COLORS["accent"], outline="")
        logo.create_rectangle(3, 3, 33, 18, fill="#46a0ff", outline="")  # rgba(70,160,255)
        logo.create_rectangle(3, 3, 18, 33, fill="#1e6ee6", outline="")  # rgba(30,110,230)
        
        # App name - Qt: font-size: 22px, font-weight: 700, color: rgba(240,245,255,220)
        app_name = tk.Label(
            brand_frame,
            text=APP_TITLE,
            font=(BASE_FONT, 20, "bold"),
            bg=COLORS["card_bg"],
            fg=COLORS["text_primary"],
        )
        app_name.pack(side=tk.LEFT)
        
        # Spacer
        tk.Frame(card, bg=COLORS["card_bg"], height=8).pack()
        
        # ---- FORM CONTAINER ---- Qt: FormStack spacing 12
        form_frame = tk.Frame(card, bg=COLORS["card_bg"], width=420)
        form_frame.pack(pady=8)
        form_frame.pack_propagate(False)
        form_frame.configure(width=420, height=400)
        
        # Kullanıcı seçimi - Qt: CmbUser, minimumSize 420x44
        self.cmb_user = ModernCombobox(
            form_frame,
            values=["Kullanıcı seç"] + self.usersdb.list_usernames(),
            placeholder="Kullanıcı seç",
        )
        self.cmb_user.pack(fill=tk.X, pady=6)
        
        # E-posta alanı - Qt: EdtEmail, minimumSize 420x44, placeholder "E-posta"
        self.edt_email = ModernEntry(form_frame, placeholder="E-posta")
        self.edt_email.pack(fill=tk.X, pady=6)
        
        # Şifre alanı - Qt: EdtPassword, minimumSize 420x44, echoMode Password
        self.edt_password = ModernEntry(form_frame, placeholder="Şifre", show="•")
        self.edt_password.pack(fill=tk.X, pady=6)
        
        # Beni hatırla checkbox - Qt: ChkRemember
        self.chk_remember = ModernCheckbox(form_frame, text="Beni hatırla")
        self.chk_remember.pack(anchor=tk.W, pady=(12, 6))
        
        # Spacer
        tk.Frame(form_frame, bg=COLORS["card_bg"], height=6).pack()
        
        # Giriş butonu - Qt: BtnLogin, minimumSize 420x54, text "Giriş Yap.."
        self.btn_login = ModernButton(form_frame, text="Giriş Yap..", command=self.do_login)
        self.btn_login.pack(fill=tk.X, pady=(0, 4))
        
        # Glow line - Qt: GlowLine, height 4
        # Qt: qlineargradient stop:0.3/0.7 rgba(80,160,255,140)
        glow_line = tk.Frame(form_frame, bg="#50a0ff", height=4)
        glow_line.pack(fill=tk.X, pady=(0, 12))
        
        # Loading satırı - Qt: LoadingRow, spacing 10 (başlangıçta gizli)
        self.loading_frame = tk.Frame(form_frame, bg=COLORS["card_bg"])
        self.loading_frame.pack(fill=tk.X, pady=4)
        
        # Spinner - Qt: LblSpinner 18x18, border: 2px solid rgba(130, 170, 255, 90)
        self.lbl_spinner = tk.Label(
            self.loading_frame,
            text="◐",
            font=(BASE_FONT, 12),
            bg=COLORS["card_bg"],
            fg=COLORS["accent"],  # Qt: rgba(55, 140, 255)
        )
        self.lbl_spinner.pack(side=tk.LEFT, padx=(0, 10))
        
        # Loading text - Qt: LblLoading, color: rgba(180,200,255,120), font-size: 13px
        self.lbl_loading = tk.Label(
            self.loading_frame,
            text="Giriş Yap...",
            font=(BASE_FONT, 11),
            bg=COLORS["card_bg"],
            fg=COLORS["text_muted"],
        )
        self.lbl_loading.pack(side=tk.LEFT)
        self.loading_frame.pack_forget()  # Başlangıçta gizle
        
        # Spacer
        tk.Frame(form_frame, bg=COLORS["card_bg"], height=28).pack()
        
        # Divider - Qt: Divider, height 1, background: rgba(255,255,255,18)
        divider = tk.Frame(form_frame, bg=COLORS["divider"], height=1)
        divider.pack(fill=tk.X)
        
        # Şifremi unuttum linki - Qt: LblForgot, color: rgba(200,215,255,140), font-size: 14px
        self.lbl_forgot = tk.Label(
            form_frame,
            text="Şifremi unuttum",
            bg=COLORS["card_bg"],
            cursor="hand2",
        )
        self.lbl_forgot.pack(pady=(16, 0))
        self.lbl_forgot.configure(font=(BASE_FONT, 11), fg=COLORS["link"])
        # Hover - Qt: color: rgba(220,235,255,210), text-decoration: underline
        self.lbl_forgot.bind("<Enter>", lambda _: self.lbl_forgot.configure(fg=COLORS["link_hover"], font=(BASE_FONT, 11, "underline")))
        self.lbl_forgot.bind("<Leave>", lambda _: self.lbl_forgot.configure(fg=COLORS["link"], font=(BASE_FONT, 11)))
        self.lbl_forgot.bind("<Button-1>", self._on_forgot_password)
        
        # İlk kurulum notu
        note_label = tk.Label(
            form_frame,
            text="İlk kurulum: admin / admin",
            font=(BASE_FONT, 10),
            bg=COLORS["card_bg"],
            fg=COLORS["text_muted"],
        )
        note_label.pack(pady=(16, 0))
        card_box.fit_to_inner()

    def _draw_background(self, _event=None):
        """Qt radial gradient simulation - cx:0.5, cy:0.35, radius:0.95"""
        canvas = getattr(self, "_bg_canvas", None)
        if not canvas:
            return
        w = max(1, self.winfo_width())
        h = max(1, self.winfo_height())
        canvas.delete("bg")
        # Qt: stop:1 rgba(6, 8, 14) - ana arka plan
        canvas.create_rectangle(0, 0, w, h, fill=COLORS["bg_dark"], outline="", tags="bg")
        # Qt: stop:0.55 rgba(10, 14, 24) - orta katman
        glow_w = int(w * 0.85)
        glow_h = int(h * 0.75)
        canvas.create_oval(
            int(w * 0.5 - glow_w * 0.5),
            int(h * 0.35 - glow_h * 0.5),
            int(w * 0.5 + glow_w * 0.5),
            int(h * 0.35 + glow_h * 0.5),
            fill=COLORS["bg_mid"],
            outline="",
            tags="bg",
        )
        # Qt: stop:0 rgba(20, 30, 50) - merkez glow
        inner_w = int(w * 0.5)
        inner_h = int(h * 0.45)
        canvas.create_oval(
            int(w * 0.5 - inner_w * 0.5),
            int(h * 0.35 - inner_h * 0.5),
            int(w * 0.5 + inner_w * 0.5),
            int(h * 0.35 + inner_h * 0.5),
            fill=COLORS["bg_glow"],
            outline="",
            tags="bg",
        )
    
    def _setup_events(self):
        """Event bindings."""
        self.cmb_user.bind_selection(lambda _e: self._on_pick_user())
        self.bind("<Return>", lambda _e: self.do_login())
        
        # Varsayılan kullanıcı seçimi
        try:
            vals = self.usersdb.list_usernames()
            if vals:
                self.cmb_user.set(vals[0])
                self._on_pick_user()
        except Exception:
            pass
    
    def _post_init(self):
        """Pencere gösterimi sonrası işlemler."""
        center_window(self)
        
        try:
            self.deiconify()
        except Exception:
            pass
        
        def _post_show():
            try:
                self.lift()
                self.focus_force()
            except Exception:
                pass
            try:
                self.attributes("-topmost", True)
                self.after(300, lambda: self.attributes("-topmost", False))
            except Exception:
                pass
            try:
                self.grab_set()
            except Exception:
                pass
            try:
                self.edt_email.entry.focus_set()
            except Exception:
                pass
        
        self.after(50, _post_show)
    
    def _on_pick_user(self):
        """Kullanıcı seçildiğinde."""
        u = self.cmb_user.get().strip()
        if u and u != "Kullanıcı seç":
            self.edt_email.set(u)
            try:
                self.edt_password.entry.focus_set()
            except Exception:
                pass
    
    def _on_forgot_password(self, _event=None):
        """Şifremi unuttum tıklandığında."""
        messagebox.showinfo(APP_TITLE, "Şifre sıfırlama için sistem yöneticinizle iletişime geçin.")
    
    def _show_loading(self, message: str = "Giriş yapılıyor..."):
        """Loading göster."""
        self.lbl_loading.configure(text=message)
        self.loading_frame.pack(fill=tk.X, pady=4)
        self.btn_login.btn.configure(state=tk.DISABLED)
        self._animate_spinner()
    
    def _hide_loading(self):
        """Loading gizle."""
        self.loading_frame.pack_forget()
        self.btn_login.btn.configure(state=tk.NORMAL)
    
    def _animate_spinner(self):
        """Spinner animasyonu."""
        if not self.loading_frame.winfo_ismapped():
            return
        spinners = ["◐", "◓", "◑", "◒"]
        current = self.lbl_spinner.cget("text")
        try:
            idx = spinners.index(current)
            next_idx = (idx + 1) % len(spinners)
        except ValueError:
            next_idx = 0
        self.lbl_spinner.configure(text=spinners[next_idx])
        self.after(150, self._animate_spinner)
    
    def do_login(self):
        """Giriş işlemi."""
        u = self.edt_email.get().strip()
        p = self.edt_password.get()
        
        if not u:
            messagebox.showwarning(APP_TITLE, "Lütfen kullanıcı adı girin.")
            return
        if not p:
            messagebox.showwarning(APP_TITLE, "Lütfen şifre girin.")
            return
        
        user = self.usersdb.auth(u, p)
        if not user:
            messagebox.showerror(APP_TITLE, "Hatalı kullanıcı/şifre.")
            return
        
        self.user = user
        # Login başarılı (log, kullanıcı DB'si açıldıktan sonra App içinde yazılır)
        self.destroy()
    
    def do_exit(self):
        """Çıkış işlemi."""
        self.user = None
        self.destroy()
