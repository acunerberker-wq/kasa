# -*- coding: utf-8 -*-

from __future__ import annotations

import tempfile
import unittest

import tkinter as tk

from kasapro.db.main_db import DB
from kasapro.db.users_db import UsersDB
from kasapro.ui.navigation import ScreenRegistry
from kasapro.ui.plugins import diagnostics
from kasapro.ui.plugins.loader import discover_ui_plugins


def _can_start_tk() -> bool:
    try:
        root = tk.Tk()
        root.withdraw()
        root.update_idletasks()
        root.destroy()
        return True
    except tk.TclError:
        return False


class AppStub:
    def __init__(self, base_dir: str, is_admin: bool = True):
        self.usersdb = UsersDB(base_dir)
        admin = self.usersdb.get_user_by_username("admin")
        self.data_owner_user_id = int(admin["id"]) if admin else 1
        self.db = DB(self.usersdb.get_user_db_path(admin))
        self.is_admin = is_admin

    def close(self) -> None:
        self.db.close()
        self.usersdb.close()


class DiagnosticsPluginTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_plugin_discovery_loaded(self) -> None:
        plugins = discover_ui_plugins()
        keys = {p.key for p in plugins}
        self.assertIn("diagnostics", keys)

    @unittest.skipUnless(_can_start_tk(), "Tkinter ekranı başlatılamıyor (headless ortam).")
    def test_register_adds_ui_hook(self) -> None:
        app = AppStub(self.tmpdir.name)
        root = tk.Tk()
        root.withdraw()
        try:
            container = tk.Frame(root)
            registry = ScreenRegistry(container, app)
            registry.register("diagnostics", diagnostics.build, title="Sistem Testleri")
            self.assertIn("diagnostics", registry.frames)
        finally:
            root.destroy()
            app.close()

    def test_config_missing_defaults(self) -> None:
        app = AppStub(self.tmpdir.name)
        try:
            config = diagnostics.load_config(app.db)
            self.assertFalse(config["auto_run"])
            self.assertEqual(config["min_free_mb"], 100)
        finally:
            app.close()

    def test_db_migration_settings_table(self) -> None:
        app = AppStub(self.tmpdir.name)
        try:
            row = app.db.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='settings'"
            ).fetchone()
            self.assertIsNotNone(row)
        finally:
            app.close()

    @unittest.skipUnless(_can_start_tk(), "Tkinter ekranı başlatılamıyor (headless ortam).")
    def test_core_check_version(self) -> None:
        app = AppStub(self.tmpdir.name)
        root = tk.Tk()
        root.withdraw()
        try:
            frame = diagnostics.DiagnosticsFrame(root, app)
            ok, detail = frame._check_version()
            self.assertTrue(ok)
            self.assertIn("Sürüm", detail)
        finally:
            root.destroy()
            app.close()

    def test_error_handling_returns_message(self) -> None:
        app = AppStub(self.tmpdir.name)
        try:
            frame = diagnostics.DiagnosticsFrame.__new__(diagnostics.DiagnosticsFrame)
            frame.app = app
            res = diagnostics.DiagnosticsFrame._run_check(frame, "fail", lambda: (_ for _ in ()).throw(ValueError("boom")))
            self.assertFalse(res.ok)
            self.assertIn("Beklenmeyen hata", res.detail)
        finally:
            app.close()

    @unittest.skipUnless(_can_start_tk(), "Tkinter ekranı başlatılamıyor (headless ortam).")
    def test_unauthorized_user_disabled(self) -> None:
        app = AppStub(self.tmpdir.name, is_admin=False)
        root = tk.Tk()
        root.withdraw()
        try:
            frame = diagnostics.DiagnosticsFrame(root, app)
            self.assertEqual(str(frame.btn_run["state"]), "disabled")
        finally:
            root.destroy()
            app.close()

    @unittest.skipUnless(_can_start_tk(), "Tkinter ekranı başlatılamıyor (headless ortam).")
    def test_smoke_instantiate_plugin_frame(self) -> None:
        app = AppStub(self.tmpdir.name)
        root = tk.Tk()
        root.withdraw()
        try:
            frame = diagnostics.build(root, app)
            self.assertIsInstance(frame, diagnostics.DiagnosticsFrame)
        finally:
            root.destroy()
            app.close()
