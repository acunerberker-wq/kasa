# -*- coding: utf-8 -*-
"""Basit startup ve ekran açılış sürelerini ölç."""

from __future__ import annotations

import json
import time
from typing import Dict, List

import tkinter as tk


def _can_start_tk() -> bool:
    try:
        root = tk.Tk()
        root.withdraw()
        root.update_idletasks()
        root.destroy()
        return True
    except tk.TclError:
        return False


def _measure_startup() -> Dict[str, float]:
    t0 = time.perf_counter()
    from kasapro.app import App  # local import for timing

    t_import = time.perf_counter()
    app = App(test_mode=True)
    t_init = time.perf_counter()
    try:
        app.on_close()
    except Exception:
        pass
    t_close = time.perf_counter()
    return {
        "import_s": round(t_import - t0, 4),
        "app_init_s": round(t_init - t_import, 4),
        "app_close_s": round(t_close - t_init, 4),
        "total_s": round(t_close - t0, 4),
    }


def _measure_screens(screen_keys: List[str]) -> Dict[str, float]:
    from kasapro.app import App  # local import for timing

    app = App(test_mode=True)
    results: Dict[str, float] = {}
    for key in screen_keys:
        started = time.perf_counter()
        app.show(key)
        results[key] = round(time.perf_counter() - started, 4)
    try:
        app.on_close()
    except Exception:
        pass
    return results


def main() -> None:
    if not _can_start_tk():
        print(json.dumps({"error": "Tkinter başlatılamadı (headless ortam)."}))
        return

    startup = _measure_startup()
    screens = _measure_screens(["kasa", "tanimlar", "rapor_araclar", "satis_raporlari", "entegrasyonlar"])

    print(json.dumps({"startup": startup, "screens": screens}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
