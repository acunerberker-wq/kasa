# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import tempfile
import unittest

import tkinter as tk

from kasapro.app import App
from kasapro.db.main_db import DB


def _can_start_tk() -> bool:
    try:
        root = tk.Tk()
        root.withdraw()
        root.update_idletasks()
        root.destroy()
        return True
    except tk.TclError:
        return False


class SmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.base_dir = self.tmpdir.name

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_db_connection(self) -> None:
        db_path = os.path.join(self.base_dir, "smoke.db")
        db = DB(db_path)
        try:
            row = db.conn.execute("SELECT 1").fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], 1)
        finally:
            db.close()

    def test_critical_flows(self) -> None:
        db_path = os.path.join(self.base_dir, "flows.db")
        db = DB(db_path)
        try:
            cid = db.cari_upsert("Test Tedarikçi", tur="Tedarikçi")
            listed = db.cari_list(q="Test")
            self.assertTrue(any(int(r["id"]) == cid for r in listed))

            db.cari_set_active(cid, 0)
            db.cari_delete(cid)

            uid = db.stok_urun_add(
                kod="SMOKE-001",
                ad="Test Ürün",
                kategori="Test",
                birim="Adet",
                min_stok=0,
                max_stok=10,
                kritik_stok=1,
                raf="A1",
                tedarikci_id=None,
                barkod="",
                aktif=1,
                aciklama="",
            )
            stok_rows = db.stok_urun_list(q="SMOKE-001")
            self.assertTrue(any(int(r["id"]) == uid for r in stok_rows))
            db.stok_urun_delete(uid)

            kpi = db.satis_rapor_kpi({})
            self.assertIsInstance(kpi, dict)
        finally:
            db.close()

    @unittest.skipUnless(_can_start_tk(), "Tkinter ekranı başlatılamıyor (headless ortam).")
    def test_ui_smoke(self) -> None:
        app = App(base_dir=self.base_dir, test_mode=True)
        try:
            for key in ("kasa", "tanimlar", "rapor_araclar"):
                self.assertIn(key, app.frames)
        finally:
            app.on_close()
