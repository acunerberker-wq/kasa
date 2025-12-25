# -*- coding: utf-8 -*-
"""Basic UI smoke checks for KasaPro.

Runs a headless-ish instantiate + show cycle for key screens.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from kasapro.app import App


def run() -> int:
    logging.getLogger("kasapro.ui_smoke").info("Starting UI smoke test")
    app = App(test_mode=True)
    try:
        for key in list(app.frames.keys()):
            app.show(key)
            app.root.update_idletasks()
        logging.getLogger("kasapro.ui_smoke").info("UI smoke test completed")
        return 0
    finally:
        try:
            app.root.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(run())
