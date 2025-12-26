# -*- coding: utf-8 -*-
"""KasaPro UI Widget'ları"""

import tkinter as tk
from tkinter import ttk
from typing import List, Optional, Callable, Any

# ✅ Tüm widget'ları export et
__all__ = [
    'SimpleField',
    'LabeledEntry',
    'LabeledCombo',
    'MoneyEntry',
    'StatusBar',  # ✅ Var olmalı
    'SearchEntry',
    'ButtonBar',
]


class SimpleField(ttk.Frame):
    """Basit metin giriş alanı (sadece entry, etiket yok)."""
    
    def __init__(self, master, **kwargs):
        super().__init__(master)
        self.entry = ttk.Entry(self, **kwargs)
        self.entry.pack(fill=tk.X)
    
    def get(self) -> str:
        """Değeri al."""
        return self.entry.get()
    
    def set(self, value: str) -> None:
        """Değeri ayarla."""
        self.entry.delete(0, tk.END)
        self.entry.insert(0, value)
    
    def clear(self) -> None:
        """Alanı temizle."""
        self.entry.delete(0, tk.END)
    
    def focus(self) -> None:
        """Odağı al."""
        self.entry.focus()


class LabeledEntry(ttk.Frame):
    """Etiket + Giriş alanı widget'ı."""
    
    def __init__(
        self,
        master,
        label_text: str,
        width: Optional[int] = None,
        **kwargs
    ):
        super().__init__(master)
        
        # Etiket
        self.label = ttk.Label(self, text=label_text)
        self.label.pack(anchor=tk.W, pady=(0, 5))
        
        # Giriş alanı
        entry_kwargs = kwargs.copy()
        if width:
            entry_kwargs['width'] = width
        
        self.entry = ttk.Entry(self, **entry_kwargs)
        self.entry.pack(fill=tk.X)
    
    def get(self) -> str:
        """Giriş değerini al."""
        return self.entry.get()
    
    def set(self, value: str) -> None:
        """Giriş değerini ayarla."""
        self.entry.delete(0, tk.END)
        self.entry.insert(0, value)
    
    def focus(self) -> None:
        """Odağı giriş alanına koy."""
        self.entry.focus()
    
    def clear(self) -> None:
        """Giriş alanını temizle."""
        self.entry.delete(0, tk.END)


class LabeledCombo(ttk.Frame):
    """Etiket + Açılır kutu widget'ı."""
    
    def __init__(
        self,
        master,
        label_text: str,
        values: Optional[List[str]] = None,
        width: Optional[int] = None,
        **kwargs
    ):
        super().__init__(master)
        
        # Etiket
        self.label = ttk.Label(self, text=label_text)
        self.label.pack(anchor=tk.W, pady=(0, 5))
        
        # Açılır kutu
        combo_kwargs = kwargs.copy()
        if width:
            combo_kwargs['width'] = width
        
        self.combo = ttk.Combobox(
            self,
            values=values or [],
            state='readonly',
            **combo_kwargs
        )
        self.combo.pack(fill=tk.X)
    
    def get(self) -> str:
        """Seçili değeri al."""
        return self.combo.get()
    
    def set(self, value: str) -> None:
        """Değeri ayarla."""
        if value in self.combo['values']:
            self.combo.set(value)
    
    def set_values(self, values: List[str]) -> None:
        """Seçenekleri güncelle."""
        self.combo['values'] = values


class MoneyEntry(ttk.Frame):
    """Para giriş alanı (₺ ile, otomatik format)."""
    
    def __init__(self, master, label_text: str = "Tutar", **kwargs):
        super().__init__(master)
        
        # Etiket
        self.label = ttk.Label(self, text=label_text)
        self.label.pack(anchor=tk.W, pady=(0, 5))
        
        # Container
        container = ttk.Frame(self)
        container.pack(fill=tk.X)
        
        # Para giriş
        self.entry = ttk.Entry(container, **kwargs)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Para sembolü
        self.symbol = ttk.Label(container, text="₺")
        self.symbol.pack(side=tk.LEFT, padx=(5, 0))
        
        # Event binding
        self.entry.bind('<KeyRelease>', self._on_change)
    
    def _on_change(self, event=None) -> None:
        """Giriş değiştiğinde otomatik format et."""
        value = self.entry.get()
        # Sadece sayı ve nokta/virgülü tut
        cleaned = ''.join(c for c in value if c.isdigit() or c in '.,')
        if cleaned != value:
            self.entry.delete(0, tk.END)
            self.entry.insert(0, cleaned)
    
    def get(self) -> float:
        """Para değerini float olarak al."""
        value = self.entry.get().replace(',', '.')
        try:
            return float(value) if value else 0.0
        except ValueError:
            return 0.0
    
    def set(self, value: float) -> None:
        """Para değerini ayarla."""
        self.entry.delete(0, tk.END)
        self.entry.insert(0, f"{value:.2f}")
    
    def clear(self) -> None:
        """Alanı temizle."""
        self.entry.delete(0, tk.END)


class StatusBar(ttk.Frame):
    """Alt durum çubuğu."""
    
    def __init__(self, master):
        super().__init__(master, relief=tk.SUNKEN, borderwidth=1)
        self.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_lbl = ttk.Label(self, text="✅ Hazır")
        self.status_lbl.pack(side=tk.LEFT, padx=5, pady=2)
        
        self._clear_timer = None
    
    def set_status(
        self,
        text: str,
        clear_after_ms: int = 0,
        status_type: str = "info"
    ) -> None:
        """Durum mesajı ayarla.
        
        Args:
            text: Gösterilecek mesaj
            clear_after_ms: Belirtilen ms sonra temizle (0 = temizleme)
            status_type: "info", "success", "warning", "error"
        """
        # İkon seç
        icons = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "❌",
        }
        icon = icons.get(status_type, "")
        
        full_text = f"{icon} {text}" if icon else text
        self.status_lbl.config(text=full_text)
        
        # Önceki timer'ı iptal et
        if self._clear_timer:
            self.after_cancel(self._clear_timer)
        
        # Yeni timer ayarla
        if clear_after_ms > 0:
            self._clear_timer = self.after(
                clear_after_ms,
                lambda: self.status_lbl.config(text="✅ Hazır")
            )


class SearchEntry(ttk.Frame):
    """Arama giriş alanı (lup ikonu ile)."""
    
    def __init__(self, master, **kwargs):
        super().__init__(master)
        
        container = ttk.Frame(self)
        container.pack(fill=tk.X)
        
        # Arama ikonu
        lbl_icon = ttk.Label(container, text="🔍")
        lbl_icon.pack(side=tk.LEFT, padx=(0, 5))
        
        # Giriş alanı
        self.entry = ttk.Entry(container, **kwargs)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    def get(self) -> str:
        """Arama metnini al."""
        return self.entry.get()
    
    def clear(self) -> None:
        """Arama alanını temizle."""
        self.entry.delete(0, tk.END)


class ButtonBar(ttk.Frame):
    """Buton çubuğu (standart layout)."""
    
    def __init__(self, master):
        super().__init__(master)
        self.pack(fill=tk.X, padx=10, pady=10)
        
        self.buttons = {}
    
    def add_button(
        self,
        key: str,
        text: str,
        command: Optional[Callable] = None,
        icon: str = ""
    ) -> ttk.Button:
        """Buton ekle."""
        label = f"{icon} {text}" if icon else text
        btn = ttk.Button(
            self,
            text=label,
            command=command,
        )
        btn.pack(side=tk.LEFT, padx=5)
        self.buttons[key] = btn
        return btn
    
    def get_button(self, key: str) -> Optional[ttk.Button]:
        """Buton al."""
        return self.buttons.get(key)