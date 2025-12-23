# -*- coding: utf-8 -*-

from .config import APP_BASE_DIR, LOG_DIRNAME, LOG_LEVEL
from .core.logging import setup_logging
from .app import main

if __name__ == "__main__":
    setup_logging(APP_BASE_DIR, log_dirname=LOG_DIRNAME, level=LOG_LEVEL)
    main()
