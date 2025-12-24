# -*- coding: utf-8 -*-
"""KasaPro yapılandırması.

- Varsayılanlar bu dosyada.
- Aynı klasördeki `kasapro.ini` ile override edebilirsin.
- `KASAPRO_HOME` environment variable set edersen, data/log dosyaları oraya yazılır.
"""

from __future__ import annotations

import importlib.util as _importlib_util
import os
import sys
from configparser import ConfigParser


# -----------------
# Uygulama
# -----------------
APP_TITLE = "KasaPro v3"

# -----------------
# Varsayılanlar
# -----------------
DEFAULT_DB_FILENAME = "kasa_pro.db"
DEFAULT_USERS_DB_FILENAME = "kasa_users.db"
DEFAULT_DATA_DIRNAME = "kasa_data"
DEFAULT_LOG_DIRNAME = "logs"
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_SHARED_STORAGE_DIRNAME = "shared_storage"
DEFAULT_MESSAGE_ATTACHMENTS_DIRNAME = "attachments"
DEFAULT_MESSAGE_ATTACHMENT_MAX_MB = 10

DEFAULT_CURRENCIES = ["TL", "USD", "EUR"]
DEFAULT_PAYMENTS = ["Nakit", "Kredi Kartı", "Havale/EFT", "Çek", "Diğer"]
DEFAULT_CATEGORIES = ["Yemek", "Ulaşım", "Malzeme", "Kira", "Maaş", "Vergi", "Diğer"]
DEFAULT_STOCK_UNITS = ["Adet", "Kg", "Lt", "M", "Paket", "Kutu", "Set"]
DEFAULT_STOCK_CATEGORIES = ["Hammadde", "Yarı Mamul", "Mamül", "Sarf", "Ambalaj", "Diğer"]

HAS_OPENPYXL = _importlib_util.find_spec("openpyxl") is not None
HAS_REPORTLAB = _importlib_util.find_spec("reportlab") is not None
HAS_TKSHEET = _importlib_util.find_spec("tksheet") is not None

# -----------------
# Base dir
# -----------------
def _guess_app_base_dir() -> str:
    try:
        env_home = os.environ.get("KASAPRO_HOME")
        if env_home:
            return os.path.abspath(env_home)

        p = os.path.abspath(sys.argv[0]) if sys.argv and sys.argv[0] else ""
        d = os.path.dirname(p) if p else ""
        return d or os.getcwd()
    except Exception:
        return os.getcwd()

APP_BASE_DIR = _guess_app_base_dir()

# -----------------
# INI override
# -----------------
CONFIG_FILENAME = "kasapro.ini"
CONFIG_PATH = os.path.join(APP_BASE_DIR, CONFIG_FILENAME)
_cfg = ConfigParser()
try:
    if os.path.exists(CONFIG_PATH):
        _cfg.read(CONFIG_PATH, encoding="utf-8")
except Exception:
    pass

DB_FILENAME = _cfg.get("db", "db_filename", fallback=DEFAULT_DB_FILENAME)
USERS_DB_FILENAME = _cfg.get("db", "users_db_filename", fallback=DEFAULT_USERS_DB_FILENAME)
DATA_DIRNAME = _cfg.get("paths", "data_dir", fallback=DEFAULT_DATA_DIRNAME)
SHARED_STORAGE_DIRNAME = _cfg.get("paths", "shared_storage_dir", fallback=DEFAULT_SHARED_STORAGE_DIRNAME)
MESSAGE_ATTACHMENTS_DIRNAME = _cfg.get("paths", "message_attachments_dir", fallback=DEFAULT_MESSAGE_ATTACHMENTS_DIRNAME)
MESSAGE_ATTACHMENT_MAX_MB = _cfg.getint("messages", "attachment_max_mb", fallback=DEFAULT_MESSAGE_ATTACHMENT_MAX_MB)
LOG_DIRNAME = _cfg.get("logging", "log_dir", fallback=DEFAULT_LOG_DIRNAME)
LOG_LEVEL = _cfg.get("logging", "level", fallback=DEFAULT_LOG_LEVEL)

SHARED_STORAGE_DIR = os.path.join(APP_BASE_DIR, SHARED_STORAGE_DIRNAME)
MESSAGE_ATTACHMENT_MAX_BYTES = MESSAGE_ATTACHMENT_MAX_MB * 1024 * 1024
# Shared storage dizinini otomatik oluştur
try:
    os.makedirs(SHARED_STORAGE_DIR, exist_ok=True)
except Exception:
    pass