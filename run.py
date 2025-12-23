# -*- coding: utf-8 -*-

from kasapro.config import APP_BASE_DIR, LOG_DIRNAME, LOG_LEVEL
from kasapro.core.logging import setup_logging
from kasapro.app import main

if __name__ == "__main__":
    setup_logging(APP_BASE_DIR, log_dirname=LOG_DIRNAME, level=LOG_LEVEL)
    main()
