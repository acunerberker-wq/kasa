# -*- coding: utf-8 -*-

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logging(base_dir: str, log_dirname: str = "logs", level: str = "INFO") -> str:
    lvl = getattr(logging, str(level).upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(lvl)

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    # Çifte handler eklememek için
    for h in list(root.handlers):
        try:
            root.removeHandler(h)
        except Exception:
            pass

    # Konsol
    sh = logging.StreamHandler()
    sh.setLevel(lvl)
    sh.setFormatter(fmt)
    root.addHandler(sh)

    log_path = ""
    try:
        log_dir = os.path.join(base_dir, log_dirname)
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "app.log")

        # Dosya (5MB x 3)
        fh = RotatingFileHandler(log_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
        fh.setLevel(lvl)
        fh.setFormatter(fmt)
        root.addHandler(fh)
    except Exception as exc:
        root.warning("File logging disabled: %s", exc)

    return log_path
