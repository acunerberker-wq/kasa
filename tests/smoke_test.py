# -*- coding: utf-8 -*-

from __future__ import annotations

import unittest

import tkinter as tk

from kasapro.app import App


def _can_start_tk() -> bool:
    try:
        root = tk.Tk()
        root.withdraw()
        root.update_idletasks()
        root.destroy()
        return True
    except tk.TclError:
        return False


class SmokeTest(unittest.TestCase):
    @unittest.skipUnless(_can_start_tk(), "Tkinter ekranı başlatılamıyor (headless ortam).")
    def test_app_starts_and_closes(self) -> None:
        app = App(test_mode=True)
        try:
            self.assertIn("kasa", app.frames)
            self.assertIn("tanimlar", app.frames)
            self.assertIn("rapor_araclar", app.frames)
        finally:
            app.on_close()

    @unittest.skipUnless(_can_start_tk(), "Tkinter ekranı başlatılamıyor (headless ortam).")
    def test_critical_screens_open(self) -> None:
        app = App(test_mode=True)
        try:
            for key in ("kasa", "tanimlar", "rapor_araclar"):
                app.show(key)
        finally:
            app.on_close()


if __name__ == "__main__":
    unittest.main()
