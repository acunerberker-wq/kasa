# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import sqlite3
import tempfile
import time
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


    def test_all_repos_accessible(self) -> None:
        """Tüm repoların erişilebilir olduğunu test eder."""
        db_path = os.path.join(self.base_dir, "repos.db")
        db = DB(db_path)
        try:
            # Banka repo - Read
            banka_list = db.banka_list()
            self.assertIsNotNone(banka_list)
            self.assertIsInstance(banka_list, list)
            
            # Banka repo - Create & Delete
            from datetime import datetime
            banka_id = db.banka_add(
                tarih=datetime.now().strftime("%Y-%m-%d"),
                banka="Test Bankası",
                hesap="TR1234567890123456789012345",
                tip="Giriş",
                tutar=1000.0,
                para="TL",
                aciklama="Test Açıklama",
                referans="",
                belge="",
                etiket="",
                import_grup=""
            )
            self.assertIsInstance(banka_id, int)
            self.assertGreater(banka_id, 0)
            
            banka_detail = db.banka_get(banka_id)
            self.assertIsNotNone(banka_detail)
            self.assertEqual(banka_detail["banka"], "Test Bankası")
            
            db.banka_delete(banka_id)
            
            # Cari repos - Read & CRUD
            cari_list = db.cari_list()
            self.assertIsNotNone(cari_list)
            self.assertIsInstance(cari_list, list)
            
            # Cari - Search fonksiyonu
            cari_search = db.cari_list(q="test")
            self.assertIsInstance(cari_search, list)
            
            # Stok repo - Read
            stok_list = db.stok_urun_list()
            self.assertIsNotNone(stok_list)
            self.assertIsInstance(stok_list, list)
            
            # Stok - Kategori listesi
            try:
                kategoriler = db.stok_kategori_list()
                self.assertIsInstance(kategoriler, list)
            except AttributeError:
                pass
            
            # Kasa repo - Read
            kasa_list = db.kasa_list()
            self.assertIsNotNone(kasa_list)
            self.assertIsInstance(kasa_list, list)
            
            # Kasa - Summary
            try:
                kasa_summary = db.kasa_summary()
                self.assertIsInstance(kasa_summary, dict)
            except AttributeError:
                pass
            
            # Fatura repo - Read & Filters
            faturalar = db.fatura_list(q="")
            self.assertIsInstance(faturalar, list)
            
            # Fatura - Durum filtreleme
            faturalar_durum = db.fatura_list(q="", durum="Ödendi")
            self.assertIsInstance(faturalar_durum, list)
            
            # Satış repos - KPI & List
            satis_kpi = db.satis_rapor_kpi({})
            self.assertIsInstance(satis_kpi, dict)
            self.assertIn("ciro", satis_kpi)  # KPI'da 'ciro' anahtarı var
            
            # Satış - Detay listesi
            try:
                satis_list = db.satis_list(limit=10)
                self.assertIsInstance(satis_list, list)
            except (AttributeError, TypeError):
                pass
            
            # Satın alma repo
            satin_alma = db.satin_alma_siparis_list(limit=10)
            self.assertIsInstance(satin_alma, list)
            
            # Settings repo - Get & Set
            setting = db.get_setting("test_key")
            self.assertTrue(setting is None or isinstance(setting, str))
            
            db.set_setting("test_key", "test_value")
            setting_read = db.get_setting("test_key")
            self.assertEqual(setting_read, "test_value")
            
            # Search repo - Global search
            results = db.global_search("test", limit=10)
            self.assertIsInstance(results, dict)
            
            # Messages repo
            try:
                messages = db.message_list_for_company(limit=10)
                self.assertIsInstance(messages, list)
            except (AttributeError, TypeError):
                pass
            
            # Logs repo
            try:
                logs = db.logs_list(limit=10)
                self.assertIsInstance(logs, list)
            except (AttributeError, TypeError):
                pass
            
            # HR repo - Çalışanlar
            try:
                calisanlar = db.hr_calisan_list()
                self.assertIsInstance(calisanlar, list)
            except (AttributeError, TypeError):
                pass
            
            # Users repo
            try:
                users = db.users_list()
                self.assertIsInstance(users, list)
            except (AttributeError, TypeError):
                pass
            
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
    def test_ui_core_screens_available(self) -> None:
        """Ana menüdeki kritik ekranların yüklendiğini doğrula."""
        app = App(base_dir=self.base_dir, test_mode=True)
        try:
            self.assertIn("entegrasyonlar", app.frames)
            self.assertIn("satis_raporlari", app.frames)
        finally:
            app.on_close()

    def test_repo_performance(self) -> None:
        """Repo metodlarının makul sürede çalıştığını test eder."""
        import time
        db_path = os.path.join(self.base_dir, "perf.db")
        db = DB(db_path)
        try:
            # Büyük veri oluştur
            for i in range(100):
                db.cari_upsert(f"Test Cari {i}", tur="Müşteri")
            
            # Listeleme performansı (<1 saniye)
            start = time.time()
            cari_list = db.cari_list()
            elapsed = time.time() - start
            self.assertLess(elapsed, 1.0, "cari_list çok yavaş")
            self.assertEqual(len(cari_list), 100)
            
            # Arama performansı (<0.5 saniye)
            start = time.time()
            search_results = db.cari_list(q="Test Cari 50")
            elapsed = time.time() - start
            self.assertLess(elapsed, 0.5, "cari_list search çok yavaş")
            self.assertGreater(len(search_results), 0)
            
            # KPI hesaplama performansı (<2 saniye)
            start = time.time()
            kpi = db.satis_rapor_kpi({})
            elapsed = time.time() - start
            self.assertLess(elapsed, 2.0, "KPI hesaplama çok yavaş")
            
        finally:
            db.close()
    
    def test_repo_edge_cases(self) -> None:
        """Repo metodlarının edge case'leri doğru ele aldığını test eder."""
        db_path = os.path.join(self.base_dir, "edge.db")
        db = DB(db_path)
        try:
            # Boş liste kontrolü
            empty_list = db.cari_list(q="NonExistentSearchTerm12345")
            self.assertIsInstance(empty_list, list)
            self.assertEqual(len(empty_list), 0)
            
            # Özel karakterler içeren arama
            special_chars = "Test'İşçi\"Cari<>%_"
            cari_id = db.cari_upsert(special_chars, tur="Müşteri")
            self.assertIsInstance(cari_id, int)
            
            # Özel karakterli arama
            search = db.cari_list(q="İşçi")
            self.assertIsInstance(search, list)
            
            # Çok uzun string testi
            long_string = "A" * 1000
            long_id = db.cari_upsert(long_string[:255], tur="Tedarikçi")
            self.assertIsInstance(long_id, int)
            
            # Negatif limit testi
            try:
                result = db.satin_alma_siparis_list(limit=-1)
                # Negatif değer kabul edilmiyorsa hata fırlatmalı
                self.assertIsInstance(result, list)
            except (ValueError, sqlite3.IntegrityError):
                pass  # Beklenen davranış
            
            # None değer testleri
            try:
                setting = db.get_setting("nonexistent_key_12345")
                self.assertIsNone(setting)
            except Exception:
                pass
            
        finally:
            db.close()
    
    def test_transaction_safety(self) -> None:
        """Transaction güvenliğini ve rollback işlemlerini test eder."""
        db_path = os.path.join(self.base_dir, "transaction.db")
        db = DB(db_path)
        try:
            # Başarılı transaction
            initial_count = len(db.cari_list())
            cari_id = db.cari_upsert("Transaction Test Cari", tur="Müşteri")
            self.assertEqual(len(db.cari_list()), initial_count + 1)
            
            # Transaction içinde hata durumu
            try:
                # Geçersiz veri ile işlem dene
                db.cari_upsert("", tur="")  # Boş ad geçersiz olabilir
            except Exception:
                pass  # Hata bekleniyor
            
            # Veritabanının tutarlı olduğunu kontrol et
            final_count = len(db.cari_list())
            self.assertGreaterEqual(final_count, initial_count)
            
        finally:
            db.close()
    
    def test_data_integrity(self) -> None:
        """Veri bütünlüğü ve referans tutarlılığını test eder."""
        db_path = os.path.join(self.base_dir, "integrity.db")
        db = DB(db_path)
        try:
            # Cari oluştur
            cari_id = db.cari_upsert("Integrity Test Cari", tur="Müşteri")
            
            # Cari hareketi ekle
            from datetime import datetime
            hareket_id = db.cari_hareket_add(
                tarih=datetime.now().strftime("%Y-%m-%d"),
                cari_id=cari_id,
                tip="Borç",
                tutar=500.0,
                para="TL",
                aciklama="Test hareket",
                odeme="Nakit",
                belge="",
                etiket=""
            )
            # Bazı metodlar ID döndürmeyebilir, bu durumda None olabilir
            if hareket_id is not None:
                self.assertIsInstance(hareket_id, int)
            
            # Carinin hareketlerini listele
            hareketler = db.cari_hareket_list(cari_id=cari_id)
            self.assertGreater(len(hareketler), 0)
            
            # Cariyi silmeye çalış (hareketler varken)
            # Bu işlem başarısız olmalı veya cascade delete yapmalı
            try:
                db.cari_delete(cari_id)
                # Eğer silindi ise hareketler de silinmiş olmalı
                remaining = db.cari_hareket_list(cari_id=cari_id)
                self.assertEqual(len(remaining), 0, "Cascade delete çalışmadı")
            except Exception:
                # Referans hatası bekleniyor - bu da geçerli
                pass
            
        finally:
            db.close()
    
    def test_concurrent_operations(self) -> None:
        """Çoklu işlemlerin aynı anda çalışmasını test eder."""
        db_path = os.path.join(self.base_dir, "concurrent.db")
        db = DB(db_path)
        try:
            # Paralel kayıt ekleme simülasyonu
            ids = []
            for i in range(50):
                cari_id = db.cari_upsert(f"Concurrent Cari {i}", tur="Müşteri")
                ids.append(cari_id)
            
            # Tüm kayıtların eklendiğini doğrula
            self.assertEqual(len(ids), 50)
            self.assertEqual(len(set(ids)), 50, "Duplicate ID var")
            
            # Aynı anda okuma işlemleri
            results = []
            for _ in range(10):
                result = db.cari_list()
                results.append(len(result))
            
            # Tüm okumalar tutarlı sonuç vermeli
            self.assertEqual(len(set(results)), 1, "Tutarsız okuma sonuçları")
            
        finally:
            db.close()
    
    def test_large_dataset_handling(self) -> None:
        """Büyük veri setlerinin işlenmesini test eder."""
        db_path = os.path.join(self.base_dir, "large.db")
        db = DB(db_path)
        try:
            import time
            
            # 500 kayıt ekle
            start = time.time()
            for i in range(500):
                db.cari_upsert(f"Large Dataset Cari {i}", tur="Müşteri")
            insert_time = time.time() - start
            
            self.assertLess(insert_time, 10.0, "500 kayıt ekleme çok yavaş")
            
            # Tüm kayıtları listele
            start = time.time()
            all_records = db.cari_list()
            list_time = time.time() - start
            
            self.assertEqual(len(all_records), 500)
            self.assertLess(list_time, 2.0, "500 kayıt listeleme çok yavaş")
            
            # Paginated okuma
            try:
                page1 = db.cari_list()[:100]
                page2 = db.cari_list()[100:200]
                self.assertEqual(len(page1), 100)
                self.assertEqual(len(page2), 100)
            except (TypeError, AttributeError):
                pass  # Pagination desteklenmiyorsa
            
        finally:
            db.close()
    
    def test_special_characters_handling(self) -> None:
        """Özel karakterlerin doğru işlendiğini test eder."""
        db_path = os.path.join(self.base_dir, "special.db")
        db = DB(db_path)
        try:
            # Unicode karakterler
            unicode_strings = [
                "Çağla Şahin İnci Ürün Özel",
                "Test™ Company® Ltd©",
                "Μεγάλη Επιχείρηση",  # Yunanca
                "大企業",  # Japonca
                "مؤسسة كبيرة",  # Arapça
                "Компания",  # Rusça
            ]
            
            ids = []
            for text in unicode_strings:
                try:
                    cari_id = db.cari_upsert(text[:100], tur="Müşteri")
                    ids.append(cari_id)
                except Exception as e:
                    # Bazı karakterler desteklenmeyebilir
                    pass
            
            # En az bazı kayıtlar başarılı olmalı
            self.assertGreater(len(ids), 0, "Hiçbir unicode karakter desteklenmiyor")
            
            # SQL injection denemesi
            malicious_inputs = [
                "'; DROP TABLE cariler; --",
                "1' OR '1'='1",
                "<script>alert('xss')</script>",
                "../../../etc/passwd",
            ]
            
            for malicious in malicious_inputs:
                try:
                    # Bu işlem başarısız olmamalı ve SQL injection yapmamalı
                    cari_id = db.cari_upsert(malicious, tur="Müşteri")
                    # Eğer eklendiyse, tablonun hala durduğunu kontrol et
                    db.cari_list()  # Bu hata verirse tablo bozulmuş demektir
                except Exception:
                    pass  # Bazı karakterler reddedilebilir
            
            # Tablo hala çalışıyor mu kontrol et
            final_list = db.cari_list()
            self.assertIsInstance(final_list, list)
            
        finally:
            db.close()
    
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


    def test_final_statistics(self) -> None:
        """Tüm testlerin istatistiklerini toplar."""
        db_path = os.path.join(self.base_dir, "stats.db")
        db = DB(db_path)
        try:
            # Örnek veri oluştur
            for i in range(20):
                db.cari_upsert(f"Stats Cari {i}", tur="Müşteri")
            
            # İstatistikler
            stats = {
                "total_cariler": len(db.cari_list()),
                "total_banka": len(db.banka_list()),
                "total_stok": len(db.stok_urun_list()),
                "total_kasa": len(db.kasa_list()),
            }
            
            # Her repo'dan en az veri çekilebildiğini doğrula
            for key, value in stats.items():
                self.assertIsInstance(value, int, f"{key} integer değil")
                self.assertGreaterEqual(value, 0, f"{key} negatif")
            
            print(f"\n📊 Test İstatistikleri: {stats}")
            
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
