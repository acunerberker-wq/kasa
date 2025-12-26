# -*- coding: utf-8 -*-
"""KasaPro Uygulaması Başlatıcı
Logging'i yapılandırır ve ana uygulamayı başlatır.
"""

import sys
import traceback

from kasapro.config import APP_BASE_DIR, LOG_DIRNAME, LOG_LEVEL
from kasapro.core.logging import setup_logging

if __name__ == "__main__":
    try:
        setup_logging(APP_BASE_DIR, log_dirname=LOG_DIRNAME, level=LOG_LEVEL)
        from kasapro.app import main
        main()
    except KeyboardInterrupt:
        print("\nUygulama kullanıcı tarafından durduruldu.", file=sys.stderr)
        sys.exit(0)
    except ImportError as e:
        print(f"HATA: Gerekli modül yüklenemedi: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"KRİTİK HATA: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)