# -*- coding: utf-8 -*-
"""Startup profilini çıkar ve en ağır fonksiyonları yazdır."""

from __future__ import annotations

import cProfile
import io
import pstats
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


def _run_profile() -> str:
    prof = cProfile.Profile()
    prof.enable()
    from kasapro.app import App  # local import for timing

    app = App(test_mode=True)
    try:
        app.on_close()
    except Exception:
        pass
    prof.disable()
    s = io.StringIO()
    stats = pstats.Stats(prof, stream=s)
    stats.sort_stats("cumulative")
    stats.print_stats(5)
    return s.getvalue()


def main() -> None:
    if not _can_start_tk():
        print("Tkinter başlatılamadı (headless ortam). Profil çıkarılamadı.")
        return
    print(_run_profile())


if __name__ == "__main__":
    main()
