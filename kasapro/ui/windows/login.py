# -*- coding: utf-8 -*-
"""KasaPro v3 - Login penceresi (Toplevel) - Modern Dark Glass UI."""

from __future__ import annotations

import sqlite3
from typing import Optional

import tkinter as tk
from tkinter import ttk, messagebox

from ...config import APP_TITLE
from ...db.users_db import UsersDB
from ...utils import center_window


# ---- RENK PALETİ (Dark Glass Theme - Qt UI'dan uyarlama) ----
# Qt: rgba(20, 30, 50) -> rgba(10, 14, 24) -> rgba(6, 8, 14)
COLORS = {
    "bg_dark": "#060810",           # Ana arka plan (en koyu - stop:1)
    "bg_mid": "#0a0e18",            # Orta arka plan (stop:0.55)
    "card_bg": "#121a2a",           # Cam kart: rgba(18, 26, 42)
    "card_border": "#3a4a66",       # Kart kenarlık: rgba(255,255,255,30) ~ solid
    "input_bg": "#1a2030",          # Input: rgba(255,255,255,10) üzerine koyu
    "input_border": "#2a3548",      # Input kenarlık: rgba(255,255,255,22)
    "input_focus": "#4a7acc",       # Focus: rgba(90, 150, 255, 160) -> solid
    "input_focus_solid": "#4a7acc", # Focus solid
    "text_primary": "#f0f5ff",      # Ana metin: rgba(240,245,255,220)
    "text_secondary": "#c8d0e8",    # İkincil: rgba(230,235,255,190) -> solid
    "text_muted": "#8090a8",        # Soluk metin
    "text_placeholder": "#6a7a92",  # Placeholder
    "accent": "#378cff",            # Buton üst: rgba(55, 140, 255)
    "accent_dark": "#145ad2",       # Buton alt: rgba(20, 90, 210)
    "accent_hover": "#46a0ff",      # Hover: rgba(70, 160, 255)
    "accent_glow": "#5090ff",       # Glow: rgba(80,160,255,140)
    "btn_border": "#5a7aaa",        # Buton border: rgba(140, 190, 255, 90) -> solid
    "link": "#c8d7ff",              # Link: rgba(200,215,255,140)
    "link_hover": "#dceaff",        # Link hover: rgba(220,235,255,210)
    "divider": "#2a3548",           # Divider: rgba(255,255,255,18)
    "dropdown_bg": "#121a2a",       # Dropdown: rgba(18, 26, 42, 230) -> solid
    "selection": "#4682b4",         # Selection: rgba(70, 130, 255, 120) -> solid
}


class ModernEntry(tk.Frame):
    """Modern görünümlü input widget - Qt QLineEdit stiline uygun."""
    
    def __init__(self, master, placeholder: str = "", show: str = "", **kwargs):
        super().__init__(master, bg=COLORS["card_bg"], **kwargs)
        
        self.placeholder = placeholder
        self._show = show
        self._has_focus = False
        
        # Dış çerçeve (border efekti için) - Qt: border-radius: 10px
        self.outer = tk.Frame(self, bg=COLORS["input_border"], padx=1, pady=1)
        self.outer.pack(fill=tk.X)
        
        # İç frame - Qt: padding: 10px 12px
        self.inner = tk.Frame(self.outer, bg=COLORS["input_bg"], padx=12, pady=10)
        self.inner.pack(fill=tk.X)
        
        # Entry widget - Qt: font-size: 14px, color: rgba(240,245,255,220)
        self.entry = tk.Entry(
            self.inner,
            font=("Inter", 14),
            bg=COLORS["input_bg"],
            fg=COLORS["text_placeholder"],
            insertbackground=COLORS["text_primary"],
            relief=tk.FLAT,
            highlightthickness=0,
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
        self.outer.configure(bg=COLORS["input_focus_solid"])
        self.inner.configure(bg="#1c2236")  # Biraz daha açık
        self.entry.configure(bg="#1c2236")
        if self.entry.get() == self.placeholder:
            self.entry.delete(0, tk.END)
            self.entry.configure(fg=COLORS["text_primary"])
            if self._show:
                self.entry.configure(show=self._show)
    
    def _on_focus_out(self, _event):
        self._has_focus = False
        self.outer.configure(bg=COLORS["input_border"])
        self.inner.configure(bg=COLORS["input_bg"])
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
            self.entry.configure(fg=COLORS["text_muted"], show="")


class ModernCombobox(tk.Frame):
    """Modern görünümlü combobox widget - Qt QComboBox stiline uygun."""
    
    def __init__(self, master, values: list, placeholder: str = "Seç...", **kwargs):
        super().__init__(master, bg=COLORS["card_bg"], **kwargs)
        
        # Dış çerçeve - Qt: border: 1px solid rgba(255,255,255,22), border-radius: 10px
        self.outer = tk.Frame(self, bg=COLORS["input_border"], padx=1, pady=1)
        self.outer.pack(fill=tk.X)
        
        # İç frame - Qt: padding: 10px 12px
        self.inner = tk.Frame(self.outer, bg=COLORS["input_bg"], padx=12, pady=10)
        self.inner.pack(fill=tk.X)
        
        # Dropdown listbox styling - Qt: QAbstractItemView
        # Qt: background: rgba(18, 26, 42, 230), selection-background-color: rgba(70, 130, 255, 120)
        root = self.winfo_toplevel()
        root.option_add("*TCombobox*Listbox.background", "#121a2a")
        root.option_add("*TCombobox*Listbox.foreground", "#f0f5ff")
        root.option_add("*TCombobox*Listbox.selectBackground", "#4682b4")
        root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
        
        # Style for combobox - Qt: font-size: 14px, color: rgba(240,245,255,220)
        style = ttk.Style()
        style.configure(
            "Modern.TCombobox",
            fieldbackground=COLORS["input_bg"],
            background=COLORS["input_bg"],
            foreground=COLORS["text_primary"],
            arrowcolor="#a0b8d8",    # Qt: rgba(210,225,255,160) -> solid
            borderwidth=0,
            padding=5,
        )
        style.map("Modern.TCombobox",
            fieldbackground=[("readonly", COLORS["input_bg"])],
            selectbackground=[("readonly", "#4682b4")],
            selectforeground=[("readonly", "#ffffff")],
        )
        
        self.combo = ttk.Combobox(
            self.inner,
            values=values,
            state="readonly",
            font=("Inter", 14),
            style="Modern.TCombobox",
        )
        self.combo.pack(fill=tk.X)
        
        if values:
            self.combo.set(placeholder)
        
        # Focus efektleri - Qt: border: 1px solid rgba(90, 150, 255, 160)
        self.combo.bind("<FocusIn>", lambda _: self.outer.configure(bg=COLORS["input_focus_solid"]))
        self.combo.bind("<FocusOut>", lambda _: self.outer.configure(bg=COLORS["input_border"]))
    
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
            bg=COLORS["input_bg"],
            highlightthickness=1,
            highlightbackground="#4a5a72",  # rgba(255,255,255,30)
        )
        self.indicator.pack(side=tk.LEFT, padx=(0, 10))
        
        # Label - Qt: color: rgba(230,235,255,190), font-size: 13px
        self.label = tk.Label(
            self,
            text=text,
            font=("Inter", 13),
            bg=COLORS["card_bg"],
            fg="#c8d0e8",    # rgba(230,235,255,190) -> solid
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
        self.indicator.delete("check")
        if self.var.get():
            # Qt checked: background: rgba(70, 130, 255, 160), border: 1px solid rgba(120, 170, 255, 200)
            self.indicator.configure(bg="#4682b4", highlightbackground="#78aacc")
            # Draw checkmark
            self.indicator.create_line(4, 9, 7, 13, fill="white", width=2, tags="check")
            self.indicator.create_line(7, 13, 14, 5, fill="white", width=2, tags="check")
        else:
            self.indicator.configure(bg=COLORS["input_bg"], highlightbackground="#4a5a72")
    
    def get(self) -> bool:
        return self.var.get()


class ModernButton(tk.Frame):
    """Modern gradient button widget - Qt QPushButton#BtnLogin stiline uygun."""
    
    def __init__(self, master, text: str, command=None, **kwargs):
        super().__init__(master, bg=COLORS["card_bg"], **kwargs)
        
        self.command = command
        
        # Border frame - Qt: border: 1px solid rgba(140, 190, 255, 90), border-radius: 10px
        self.border = tk.Frame(self, bg="#5a7aaa", padx=1, pady=1)
        self.border.pack(fill=tk.X)
        
        # Button - Qt: background gradient rgba(55, 140, 255) -> rgba(20, 90, 210)
        # Qt: font-size: 18px, padding: 12px 14px, color: rgba(255,255,255,240)
        self.btn = tk.Label(
            self.border,
            text=text,
            font=("Inter", 18, "bold"),
            bg="#378cff",
            fg="#ffffff",
            padx=14,
            pady=12,
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
        self.btn.configure(bg="#46a0ff")
    
    def _on_leave(self, _event):
        self.btn.configure(bg="#378cff")
    
    def _on_click(self, _event):
        # Qt pressed: rgba(20, 90, 210)
        self.btn.configure(bg="#145ad2")
    
    def _on_release(self, _event):
        self.btn.configure(bg="#378cff")
        if self.command:
            self.command()


class LoginWindow(tk.Toplevel):
    """Modern Dark Glass Login Window."""
    
    def __init__(self, root: tk.Tk, usersdb: UsersDB):
        super().__init__(root)
        self.usersdb = usersdb
        self.user: Optional[sqlite3.Row] = None
        
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
        # Ana container (merkeze hizalama için)
        main_container = tk.Frame(self, bg=COLORS["bg_dark"])
        main_container.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        # Glass Card - Qt: minimumSize 720x460, padding 48/42/48/34, spacing 16
        # Qt: background: rgba(18, 26, 42, 165), border: 1px solid rgba(255,255,255,30), border-radius: 16px
        card_border = tk.Frame(main_container, bg="#4a5a72", padx=1, pady=1)  # border
        card_border.pack()
        
        card = tk.Frame(
            card_border,
            bg=COLORS["card_bg"],
            padx=48,
            pady=42,
        )
        card.pack()
        
        # ---- BRAND ROW ---- Qt: spacing 12
        brand_frame = tk.Frame(card, bg=COLORS["card_bg"])
        brand_frame.pack(fill=tk.X, pady=(0, 16))
        
        # Logo - Qt: 36x36, gradient mavi, border-radius: 10px
        logo = tk.Canvas(brand_frame, width=36, height=36, bg=COLORS["card_bg"], highlightthickness=0)
        logo.pack(side=tk.LEFT, padx=(0, 12))
        # Gradient simulation - Qt: rgba(70,160,255) -> rgba(30,110,230)
        logo.create_rectangle(0, 0, 36, 36, fill="#1e6ee6", outline="")
        logo.create_rectangle(3, 3, 33, 18, fill="#46a0ff", outline="")
        logo.create_rectangle(3, 3, 18, 33, fill="#3890ff", outline="")
        
        # App name - Qt: font-size: 22px, font-weight: 700, color: rgba(240,245,255,220)
        app_name = tk.Label(
            brand_frame,
            text=APP_TITLE,
            font=("Inter", 22, "bold"),
            bg=COLORS["card_bg"],
            fg="#d8e0f0",
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
        
        # Glow line - Qt: GlowLine, height 4, gradient glow
        glow_canvas = tk.Canvas(form_frame, height=4, bg=COLORS["card_bg"], highlightthickness=0)
        glow_canvas.pack(fill=tk.X, pady=(0, 10))
        # Gradient glow simulation - Qt: rgba(80,160,255,140) ortada
        glow_canvas.update_idletasks()
        glow_canvas.create_rectangle(80, 0, 340, 4, fill="#5090ff", outline="")
        glow_canvas.create_rectangle(120, 0, 300, 4, fill="#60a0ff", outline="")
        
        # Loading satırı - Qt: LoadingRow, spacing 10 (başlangıçta gizli)
        self.loading_frame = tk.Frame(form_frame, bg=COLORS["card_bg"])
        self.loading_frame.pack(fill=tk.X, pady=4)
        
        # Spinner - Qt: LblSpinner 18x18, border: 2px solid rgba(130, 170, 255, 90)
        self.lbl_spinner = tk.Label(
            self.loading_frame,
            text="◐",
            font=("Inter", 14),
            bg=COLORS["card_bg"],
            fg="#82aaff",
        )
        self.lbl_spinner.pack(side=tk.LEFT, padx=(0, 10))
        
        # Loading text - Qt: LblLoading, color: rgba(180,200,255,120), font-size: 13px
        self.lbl_loading = tk.Label(
            self.loading_frame,
            text="Giriş Yap...",
            font=("Inter", 13),
            bg=COLORS["card_bg"],
            fg="#8090a8",
        )
        self.lbl_loading.pack(side=tk.LEFT)
        self.loading_frame.pack_forget()  # Başlangıçta gizle
        
        # Spacer
        tk.Frame(form_frame, bg=COLORS["card_bg"], height=28).pack()
        
        # Divider - Qt: Divider, height 1, background: rgba(255,255,255,18)
        divider = tk.Frame(form_frame, bg="#3a4a5a", height=1)
        divider.pack(fill=tk.X)
        
        # Şifremi unuttum linki - Qt: LblForgot, color: rgba(200,215,255,140), font-size: 14px
        self.lbl_forgot = tk.Label(
            form_frame,
            text="Şifremi unuttum",
            font=("Inter", 14),
            bg=COLORS["card_bg"],
            fg="#8a9ab8",
            cursor="hand2",
        )
        self.lbl_forgot.pack(pady=(16, 0))
        # Hover - Qt: color: rgba(220,235,255,210), text-decoration: underline
        self.lbl_forgot.bind("<Enter>", lambda _: self.lbl_forgot.configure(fg="#c8d8f0", font=("Inter", 14, "underline")))
        self.lbl_forgot.bind("<Leave>", lambda _: self.lbl_forgot.configure(fg="#8a9ab8", font=("Inter", 14)))
        self.lbl_forgot.bind("<Button-1>", self._on_forgot_password)
        
        # İlk kurulum notu
        note_label = tk.Label(
            form_frame,
            text="İlk kurulum: admin / admin",
            font=("Inter", 11),
            bg=COLORS["card_bg"],
            fg=COLORS["text_muted"],
        )
        note_label.pack(pady=(16, 0))
    
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
