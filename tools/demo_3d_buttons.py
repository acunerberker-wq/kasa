# -*- coding: utf-8 -*-
"""3D Buton Demo - KasaPro

Bu dosyayı çalıştırarak 3D butonları test edebilirsiniz:
    python tools/demo_3d_buttons.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
from tkinter import ttk

from kasapro.ui.widgets import Button3D
from kasapro.ui.theme import apply_dark_glass_theme


def main():
    root = tk.Tk()
    root.title("3D Buton Demo - KasaPro")
    root.geometry("600x500")
    
    # Tema uygula
    apply_dark_glass_theme(root)
    
    # Ana frame
    main_frame = ttk.Frame(root, padding=20)
    main_frame.pack(fill="both", expand=True)
    
    # Başlık
    ttk.Label(
        main_frame, 
        text="KasaPro Buton Stilleri",
        style="PageTitle.TLabel"
    ).pack(pady=(0, 20))
    
    # Primary butonlar
    ttk.Label(main_frame, text="Primary (Yeni Sipariş, Kaydet):").pack(anchor="w", pady=(10, 5))
    btn_frame1 = ttk.Frame(main_frame)
    btn_frame1.pack(fill="x", pady=5)
    
    Button3D(
        btn_frame1, 
        text="+ Yeni Sipariş", 
        style="primary",
        width=130,
        height=34,
        command=lambda: print("Yeni Sipariş!")
    ).pack(side="left", padx=5)
    
    Button3D(
        btn_frame1, 
        text="Kaydet", 
        style="primary",
        width=90,
        height=34,
    ).pack(side="left", padx=5)
    
    Button3D(
        btn_frame1, 
        text="Ara", 
        style="primary",
        width=70,
        height=34,
    ).pack(side="left", padx=5)
    
    # Secondary butonlar
    ttk.Label(main_frame, text="Secondary (Ara, Durum Güncelle):").pack(anchor="w", pady=(20, 5))
    btn_frame2 = ttk.Frame(main_frame)
    btn_frame2.pack(fill="x", pady=5)
    
    Button3D(
        btn_frame2, 
        text="Ara", 
        style="secondary",
        width=80,
        height=32,
    ).pack(side="left", padx=5)
    
    Button3D(
        btn_frame2, 
        text="Durum Güncelle", 
        style="secondary",
        width=130,
        height=32,
    ).pack(side="left", padx=5)
    
    Button3D(
        btn_frame2, 
        text="İptal", 
        style="secondary",
        width=80,
        height=32,
    ).pack(side="left", padx=5)
    
    # Ghost butonlar (Pagination)
    ttk.Label(main_frame, text="Ghost (Önceki, Sonraki, Pagination):").pack(anchor="w", pady=(20, 5))
    btn_frame3 = ttk.Frame(main_frame)
    btn_frame3.pack(fill="x", pady=5)
    
    Button3D(
        btn_frame3, 
        text="Önceki", 
        style="ghost",
        width=80,
        height=30,
    ).pack(side="left", padx=5)
    
    Button3D(
        btn_frame3, 
        text="<", 
        style="ghost",
        width=36,
        height=30,
    ).pack(side="left", padx=2)
    
    Button3D(
        btn_frame3, 
        text="|", 
        style="ghost",
        width=30,
        height=30,
    ).pack(side="left", padx=2)
    
    Button3D(
        btn_frame3, 
        text=">", 
        style="ghost",
        width=36,
        height=30,
    ).pack(side="left", padx=2)
    
    # Danger & Success
    ttk.Label(main_frame, text="Danger & Success:").pack(anchor="w", pady=(20, 5))
    btn_frame4 = ttk.Frame(main_frame)
    btn_frame4.pack(fill="x", pady=5)
    
    Button3D(
        btn_frame4, 
        text="Sil", 
        style="danger",
        width=80,
        height=32,
    ).pack(side="left", padx=5)
    
    Button3D(
        btn_frame4, 
        text="Onayla", 
        style="success",
        width=90,
        height=32,
    ).pack(side="left", padx=5)
    
    # Toolbar butonlar
    ttk.Label(main_frame, text="Toolbar:").pack(anchor="w", pady=(20, 5))
    btn_frame5 = ttk.Frame(main_frame)
    btn_frame5.pack(fill="x", pady=5)
    
    Button3D(
        btn_frame5, 
        text="Excel", 
        style="toolbar",
        width=70,
        height=30,
    ).pack(side="left", padx=5)
    
    Button3D(
        btn_frame5, 
        text="PDF", 
        style="toolbar",
        width=60,
        height=30,
    ).pack(side="left", padx=5)
    
    Button3D(
        btn_frame5, 
        text="Yazdır", 
        style="toolbar",
        width=70,
        height=30,
    ).pack(side="left", padx=5)
    
    root.mainloop()


if __name__ == "__main__":
    main()
