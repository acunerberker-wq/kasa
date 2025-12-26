# -*- coding: utf-8 -*-
"""KasaPro Uygulaması Başlatıcı
Logging'i yapılandırır ve ana uygulamayı başlatır.
"""

import sys
import traceback

def show_splash_screen():
    """Başlatma ekranını göster."""
    try:
        import tkinter as tk
        from tkinter import ttk
        
        splash = tk.Tk()
        splash.overrideredirect(True)
        splash.attributes('-alpha', 0.95)
        
        # Merkeze konumlandır
        try:
            splash.geometry("500x300+{}+{}".format(
                splash.winfo_screenwidth() // 2 - 250,
                splash.winfo_screenheight() // 2 - 150,
            ))
        except Exception:
            splash.geometry("500x300")
        
        frame = ttk.Frame(splash, relief=tk.RAISED, borderwidth=2)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        title = ttk.Label(
            frame,
            text="🏢 KasaPro v3",
            font=("Segoe UI", 24, "bold"),
        )
        title.pack(pady=20)
        
        subtitle = ttk.Label(
            frame,
            text="Muhasebe & İş Yönetim Sistemi",
            font=("Segoe UI", 12),
        )
        subtitle.pack()
        
        status = ttk.Label(
            frame,
            text="Başlatılıyor...",
            font=("Segoe UI", 10),
        )
        status.pack(pady=30)
        
        progress = ttk.Progressbar(
            frame,
            mode='indeterminate',
            length=300,
        )
        progress.pack(pady=10)
        progress.start()
        
        splash.update()
        return splash
    except Exception as e:
        # Hata durumunda splash göstermeden devam et
        import logging
        logging.warning(f"Splash ekranı gösterilemedi: {e}")
        return None

try:
    splash = show_splash_screen()
    
    from kasapro.config import APP_BASE_DIR, LOG_DIRNAME, LOG_LEVEL
    from kasapro.core.logging import setup_logging
    from kasapro.app import main
    
    setup_logging(APP_BASE_DIR, log_dirname=LOG_DIRNAME, level=LOG_LEVEL)
    
    if splash:
        splash.destroy()
    
    main()
    
except KeyboardInterrupt:
    print("\n✋ Uygulama kullanıcı tarafından durduruldu.", file=sys.stderr)
    sys.exit(0)
except SyntaxError as e:
    print(f"❌ SYNTAX HATASI: {e.filename}:{e.lineno}", file=sys.stderr)
    print(f"   {e.msg}", file=sys.stderr)
    if "--verbose" in sys.argv:
        traceback.print_exc()
    sys.exit(1)
except ImportError as e:
    print(f"❌ IMPORT HATASI: Gerekli modül yüklenemedi", file=sys.stderr)
    print(f"   {e}", file=sys.stderr)
    if "--verbose" in sys.argv:
        traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"❌ KRİTİK HATA: {type(e).__name__}: {e}", file=sys.stderr)
    if "--verbose" in sys.argv or "--debug" in sys.argv:
        traceback.print_exc()
    else:
        print("   (Detaylı hata için: python run.py --verbose)", file=sys.stderr)
    sys.exit(1)