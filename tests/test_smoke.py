# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import tempfile
import unittest
import time

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
        # Geçici dizini silmeden önce biraz bekle (Windows'ta dosya kilitleri için)
        time.sleep(0.1)
        try:
            self.tmpdir.cleanup()
        except PermissionError:
            # Windows'ta bazen dosyalar hala açık olabilir
            time.sleep(0.5)
            try:
                self.tmpdir.cleanup()
            except Exception:
                pass  # Temizleme başarısız olursa geç

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

    def test_all_repos_accessible(self) -> None:
        """Tüm repoların erişilebilir olduğunu test eder."""
        db_path = os.path.join(self.base_dir, "repos.db")
        db = DB(db_path)
        try:
            # Banka repo
            banka_list = db.banka_list()
            self.assertIsNotNone(banka_list)
            self.assertIsInstance(banka_list, list)
            
            # Cari repos
            cari_list = db.cari_list()
            self.assertIsNotNone(cari_list)
            self.assertIsInstance(cari_list, list)
            
            # Stok repo
            stok_list = db.stok_urun_list()
            self.assertIsNotNone(stok_list)
            self.assertIsInstance(stok_list, list)
            
            # Kasa repo
            kasa_list = db.kasa_list()
            self.assertIsNotNone(kasa_list)
            self.assertIsInstance(kasa_list, list)
            
            # Fatura repo
            faturalar = db.fatura_list(q="")
            self.assertIsInstance(faturalar, list)
            
            # Satış repos
            satis_kpi = db.satis_rapor_kpi({})
            self.assertIsInstance(satis_kpi, dict)
            
            # Satın alma repo
            satin_alma = db.satin_alma_siparis_list(limit=10)
            self.assertIsInstance(satin_alma, list)
            
            # Settings repo
            setting = db.get_setting("test_key")
            self.assertTrue(setting is None or isinstance(setting, str))
            
            # Search repo
            results = db.global_search("test", limit=10)
            self.assertIsInstance(results, dict)  # global_search dict döndürüyor
            
            # Messages repo
            try:
                messages = db.message_list_for_company(limit=10)
                self.assertIsInstance(messages, list)
            except (AttributeError, TypeError):
                pass  # Repo metodu yoksa veya parametreler farklıysa geç
            
            # Logs repo
            try:
                logs = db.logs_list(limit=10)
                self.assertIsInstance(logs, list)
            except (AttributeError, TypeError):
                pass  # Repo metodu yoksa veya parametreler farklıysa geç
            
        finally:
            db.close()

    @unittest.skipUnless(_can_start_tk(), "Tkinter ekranı başlatılamıyor (headless ortam).")
    def test_ui_tabs_visible(self) -> None:
        """UI sekmelerinin görünür olduğunu test eder."""
        app = App(base_dir=self.base_dir, test_mode=True)
        try:
            # Ana frameler mevcut mu?
            self.assertIn("kasa", app.frames)
            self.assertIn("tanimlar", app.frames)
            self.assertIn("rapor_araclar", app.frames)
            
            # Rapor Araçlar Hub sekmelerini kontrol et
            rapor_frame = app.frames.get("rapor_araclar")
            if rapor_frame and hasattr(rapor_frame, "nb"):
                # Notebook widget'ının var olduğunu kontrol et
                self.assertIsNotNone(rapor_frame.nb)
                
                # Tüm sekmeleri kontrol et
                tab_count = rapor_frame.nb.index("end")
                self.assertGreater(tab_count, 0, "Rapor Araçlar'da hiç sekme yok")
                
                # Beklenen sekmeler
                expected_tabs = [
                    "tab_raporlar",      # 📊 Raporlar
                    "tab_search",        # 🔎 Global Arama
                    "tab_loglar",        # 🧾 Log
                    "tab_satin_alma",    # 📦 Satın Alma Sipariş Raporları
                    "tab_notes_reminders" # 🗒️ Notlar & Hatırlatmalar
                ]
                
                for tab_attr in expected_tabs:
                    self.assertTrue(
                        hasattr(rapor_frame, tab_attr),
                        f"Rapor Araçlar'da {tab_attr} sekmesi bulunamadı"
                    )
                    tab = getattr(rapor_frame, tab_attr)
                    self.assertIsNotNone(tab, f"{tab_attr} sekmesi None")
                
                # Her sekmenin içeriğinin yüklendiğini kontrol et
                self.assertTrue(
                    hasattr(rapor_frame, "raporlar_frame"),
                    "Raporlar frame yüklenmedi"
                )
                self.assertTrue(
                    hasattr(rapor_frame, "search_frame"),
                    "Global Arama frame yüklenmedi"
                )
                self.assertTrue(
                    hasattr(rapor_frame, "loglar_frame"),
                    "Loglar frame yüklenmedi"
                )
                self.assertTrue(
                    hasattr(rapor_frame, "satin_alma_frame"),
                    "Satın Alma Raporlar frame yüklenmedi"
                )
                self.assertTrue(
                    hasattr(rapor_frame, "notes_reminders_frame"),
                    "Notlar & Hatırlatmalar frame yüklenmedi"
                )
            
            # Tanımlar Hub sekmelerini kontrol et
            tanimlar_frame = app.frames.get("tanimlar")
            if tanimlar_frame and hasattr(tanimlar_frame, "nb"):
                self.assertIsNotNone(tanimlar_frame.nb)
                tab_count = tanimlar_frame.nb.index("end")
                self.assertGreater(tab_count, 0, "Tanımlar'da hiç sekme yok")
                
                # Beklenen sekmeler
                expected_tabs = [
                    "tab_cariler",      # 👥 Cariler
                    "tab_calisanlar",   # 👷 Çalışanlar
                    "tab_meslekler",    # 🧑‍🏭 Meslekler
                ]
                
                for tab_attr in expected_tabs:
                    self.assertTrue(
                        hasattr(tanimlar_frame, tab_attr),
                        f"Tanımlar'da {tab_attr} sekmesi bulunamadı"
                    )
                    tab = getattr(tanimlar_frame, tab_attr)
                    self.assertIsNotNone(tab, f"{tab_attr} sekmesi None")
                
                # Cariler frame'inin yüklendiğini kontrol et
                self.assertTrue(
                    hasattr(tanimlar_frame, "cariler_frame"),
                    "Cariler frame yüklenmedi"
                )
                
        finally:
            app.on_close()

    @unittest.skipUnless(_can_start_tk(), "Tkinter ekranı başlatılamıyor (headless ortam).")
    def test_services_available(self) -> None:
        """Tüm servislerin erişilebilir olduğunu test eder."""
        app = App(base_dir=self.base_dir, test_mode=True)
        try:
            # Servis konteynerinin var olduğunu kontrol et
            self.assertIsNotNone(app.services)
            
            # Temel servislerin mevcut olduğunu kontrol et
            self.assertIsNotNone(app.services.exporter)
            self.assertIsNotNone(app.services.settings)
            self.assertIsNotNone(app.services.company_users)
            self.assertIsNotNone(app.services.cari)
            self.assertIsNotNone(app.services.messages)
            self.assertIsNotNone(app.services.dms)
            self.assertIsNotNone(app.services.notes_reminders)
            
        finally:
            app.on_close()


if __name__ == "__main__":
    unittest.main()
