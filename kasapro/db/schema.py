# -*- coding: utf-8 -*-

from __future__ import annotations

import sqlite3
from typing import Callable, Optional


def init_schema(conn: sqlite3.Connection) -> None:
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        salt TEXT NOT NULL,
        pass_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user',
        created_at TEXT NOT NULL
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS settings(
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS cariler(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ad TEXT UNIQUE NOT NULL,
        tur TEXT DEFAULT '',
        telefon TEXT DEFAULT '',
        notlar TEXT DEFAULT '',
        acilis_bakiye REAL DEFAULT 0,
        aktif INTEGER NOT NULL DEFAULT 1
    );""")


    c.execute("""
    CREATE TABLE IF NOT EXISTS cari_hareket(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tarih TEXT NOT NULL,
        cari_id INTEGER NOT NULL,
        tip TEXT NOT NULL,
        tutar REAL NOT NULL,
        para TEXT DEFAULT 'TL',
        aciklama TEXT DEFAULT '',
        odeme TEXT DEFAULT '',
        belge TEXT DEFAULT '',
        etiket TEXT DEFAULT '',
        FOREIGN KEY(cari_id) REFERENCES cariler(id)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS kasa_hareket(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tarih TEXT NOT NULL,
        tip TEXT NOT NULL,
        tutar REAL NOT NULL,
        para TEXT DEFAULT 'TL',
        odeme TEXT DEFAULT '',
        kategori TEXT DEFAULT '',
        cari_id INTEGER,
        aciklama TEXT DEFAULT '',
        belge TEXT DEFAULT '',
        etiket TEXT DEFAULT '',
        FOREIGN KEY(cari_id) REFERENCES cariler(id)
    );""")

    # -----------------
    # Banka Hareketleri
    # -----------------
    # Not:
    # - Çoklu banka/hesap desteği için banka+hesap alanları serbest metindir.
    # - Import tarafında "Giriş/Çıkış" tipine normalize edilir.
    c.execute("""
    CREATE TABLE IF NOT EXISTS banka_hareket(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tarih TEXT NOT NULL,
        banka TEXT DEFAULT '',
        hesap TEXT DEFAULT '',
        tip TEXT NOT NULL, -- 'Giriş' / 'Çıkış'
        tutar REAL NOT NULL,
        para TEXT DEFAULT 'TL',
        aciklama TEXT DEFAULT '',
        referans TEXT DEFAULT '',
        belge TEXT DEFAULT '',
        etiket TEXT DEFAULT '',
        import_grup TEXT DEFAULT '',
        bakiye REAL
    );""")

    # -----------------
    # Faturalar
    # -----------------
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS fatura(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tarih TEXT NOT NULL,
        vade TEXT DEFAULT '',
        tur TEXT NOT NULL DEFAULT 'Satış',
        durum TEXT NOT NULL DEFAULT 'Taslak',
        fatura_no TEXT NOT NULL UNIQUE,
        seri TEXT DEFAULT '',

        cari_id INTEGER,
        cari_ad TEXT DEFAULT '',
        cari_vkn TEXT DEFAULT '',
        cari_vergi_dairesi TEXT DEFAULT '',
        cari_adres TEXT DEFAULT '',
        cari_eposta TEXT DEFAULT '',

        para TEXT DEFAULT 'TL',
        ara_toplam REAL DEFAULT 0,
        iskonto_toplam REAL DEFAULT 0,
        kdv_toplam REAL DEFAULT 0,
        genel_toplam REAL DEFAULT 0,

        notlar TEXT DEFAULT '',
        etiket TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(cari_id) REFERENCES cariler(id)
    );"""
    )

    c.execute(
        """
    CREATE TABLE IF NOT EXISTS fatura_kalem(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fatura_id INTEGER NOT NULL,
        sira INTEGER NOT NULL DEFAULT 1,
        urun TEXT DEFAULT '',
        aciklama TEXT DEFAULT '',
        miktar REAL DEFAULT 0,
        birim TEXT DEFAULT 'Adet',
        birim_fiyat REAL DEFAULT 0,
        iskonto_oran REAL DEFAULT 0,
        kdv_oran REAL DEFAULT 20,
        ara_tutar REAL DEFAULT 0,
        iskonto_tutar REAL DEFAULT 0,
        kdv_tutar REAL DEFAULT 0,
        toplam REAL DEFAULT 0,
        FOREIGN KEY(fatura_id) REFERENCES fatura(id) ON DELETE CASCADE
    );"""
    )

    c.execute(
        """
    CREATE TABLE IF NOT EXISTS fatura_odeme(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fatura_id INTEGER NOT NULL,
        tarih TEXT NOT NULL,
        tutar REAL NOT NULL DEFAULT 0,
        para TEXT DEFAULT 'TL',
        odeme TEXT DEFAULT '',
        aciklama TEXT DEFAULT '',
        ref TEXT DEFAULT '',
        kasa_hareket_id INTEGER,
        banka_hareket_id INTEGER,
        FOREIGN KEY(fatura_id) REFERENCES fatura(id) ON DELETE CASCADE,
        FOREIGN KEY(kasa_hareket_id) REFERENCES kasa_hareket(id) ON DELETE SET NULL,
        FOREIGN KEY(banka_hareket_id) REFERENCES banka_hareket(id) ON DELETE SET NULL
    );"""
    )

    c.execute(
        """
    CREATE TABLE IF NOT EXISTS fatura_seri(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        seri TEXT NOT NULL,
        yil INTEGER NOT NULL,
        prefix TEXT DEFAULT 'FTR',
        last_no INTEGER NOT NULL DEFAULT 0,
        padding INTEGER NOT NULL DEFAULT 6,
        format TEXT DEFAULT '{yil}{seri}{no_pad}',
        aktif INTEGER NOT NULL DEFAULT 1,
        UNIQUE(seri,yil)
    );"""
    )

    # -----------------
    # Satış Siparişleri
    # -----------------
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS satis_siparis(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tarih TEXT NOT NULL,
        teslim_tarih TEXT DEFAULT '',
        siparis_no TEXT NOT NULL UNIQUE,
        cari_id INTEGER,
        cari_ad TEXT DEFAULT '',
        temsilci TEXT DEFAULT '',
        depo_id INTEGER,
        durum TEXT NOT NULL DEFAULT 'Açık',
        para TEXT DEFAULT 'TL',
        toplam REAL DEFAULT 0,
        aciklama TEXT DEFAULT '',
        sevk_tarih TEXT DEFAULT '',
        sevk_no TEXT DEFAULT '',
        fatura_id INTEGER,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(cari_id) REFERENCES cariler(id),
        FOREIGN KEY(depo_id) REFERENCES stok_lokasyon(id),
        FOREIGN KEY(fatura_id) REFERENCES fatura(id)
    );"""
    )

    c.execute(
        """
    CREATE TABLE IF NOT EXISTS satis_siparis_kalem(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        siparis_id INTEGER NOT NULL,
        urun_id INTEGER,
        urun_kod TEXT DEFAULT '',
        urun_ad TEXT DEFAULT '',
        birim TEXT DEFAULT 'Adet',
        miktar REAL DEFAULT 0,
        birim_fiyat REAL DEFAULT 0,
        toplam REAL DEFAULT 0,
        sevk_miktar REAL DEFAULT 0,
        aciklama TEXT DEFAULT '',
        FOREIGN KEY(siparis_id) REFERENCES satis_siparis(id) ON DELETE CASCADE,
        FOREIGN KEY(urun_id) REFERENCES stok_urun(id)
    );"""
    )

    c.execute("""
    CREATE TABLE IF NOT EXISTS logs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL,
        islem TEXT NOT NULL,
        detay TEXT DEFAULT ''
    );""")

    # -----------------
    # Mesajlar
    # -----------------
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS messages(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER NOT NULL,
        sender_username TEXT NOT NULL,
        subject TEXT DEFAULT '',
        body TEXT DEFAULT '',
        is_draft INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );"""
    )
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS message_recipients(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id INTEGER NOT NULL,
        recipient_id INTEGER NOT NULL,
        recipient_username TEXT NOT NULL,
        is_read INTEGER NOT NULL DEFAULT 0,
        read_at TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(message_id) REFERENCES messages(id) ON DELETE CASCADE
    );"""
    )
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS message_attachments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id INTEGER NOT NULL,
        filename TEXT NOT NULL,
        stored_name TEXT NOT NULL,
        size_bytes INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(message_id) REFERENCES messages(id) ON DELETE CASCADE
    );"""
    )

    # -----------------
    # Stok Yönetimi
    # -----------------
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS stok_urun(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kod TEXT NOT NULL UNIQUE,
        ad TEXT NOT NULL,
        kategori TEXT DEFAULT '',
        birim TEXT DEFAULT 'Adet',
        min_stok REAL DEFAULT 0,
        max_stok REAL DEFAULT 0,
        kritik_stok REAL DEFAULT 0,
        raf TEXT DEFAULT '',
        tedarikci_id INTEGER,
        barkod TEXT DEFAULT '',
        aktif INTEGER NOT NULL DEFAULT 1,
        aciklama TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(tedarikci_id) REFERENCES cariler(id)
    );"""
    )

    c.execute(
        """
    CREATE TABLE IF NOT EXISTS stok_lokasyon(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ad TEXT NOT NULL UNIQUE,
        aciklama TEXT DEFAULT '',
        aktif INTEGER NOT NULL DEFAULT 1
    );"""
    )

    c.execute(
        """
    CREATE TABLE IF NOT EXISTS stok_parti(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        urun_id INTEGER NOT NULL,
        parti_no TEXT NOT NULL,
        skt TEXT DEFAULT '',
        uretim_tarih TEXT DEFAULT '',
        aciklama TEXT DEFAULT '',
        UNIQUE(urun_id, parti_no),
        FOREIGN KEY(urun_id) REFERENCES stok_urun(id) ON DELETE CASCADE
    );"""
    )

    c.execute(
        """
    CREATE TABLE IF NOT EXISTS stok_hareket(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tarih TEXT NOT NULL,
        urun_id INTEGER NOT NULL,
        tip TEXT NOT NULL, -- Giris/Cikis/Transfer/Fire/Sayim/Duzeltme/Uretim
        miktar REAL NOT NULL DEFAULT 0,
        birim TEXT DEFAULT 'Adet',
        kaynak_lokasyon_id INTEGER,
        hedef_lokasyon_id INTEGER,
        parti_id INTEGER,
        referans_tipi TEXT DEFAULT '',
        referans_id INTEGER,
        maliyet REAL DEFAULT 0,
        aciklama TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(urun_id) REFERENCES stok_urun(id),
        FOREIGN KEY(kaynak_lokasyon_id) REFERENCES stok_lokasyon(id),
        FOREIGN KEY(hedef_lokasyon_id) REFERENCES stok_lokasyon(id),
        FOREIGN KEY(parti_id) REFERENCES stok_parti(id)
    );"""
    )

    # -----------------
    # Maaş Takibi
    # -----------------
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS maas_meslek(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ad TEXT NOT NULL,
        aktif INTEGER NOT NULL DEFAULT 1,
        notlar TEXT DEFAULT '',
        UNIQUE(ad)
    );"""
    )

    c.execute("""
    CREATE TABLE IF NOT EXISTS maas_calisan(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ad TEXT NOT NULL,
        aylik_tutar REAL NOT NULL DEFAULT 0,
        para TEXT DEFAULT 'TL',
        meslek_id INTEGER,
        aktif INTEGER NOT NULL DEFAULT 1,
        notlar TEXT DEFAULT '',
        UNIQUE(ad)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS maas_odeme(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        donem TEXT NOT NULL, -- YYYY-MM
        calisan_id INTEGER NOT NULL,
        tutar REAL NOT NULL DEFAULT 0,
        para TEXT DEFAULT 'TL',
        odendi INTEGER NOT NULL DEFAULT 0,
        odeme_tarihi TEXT DEFAULT '',
        aciklama TEXT DEFAULT '',
        banka_hareket_id INTEGER,
        banka_match_score REAL,
        banka_match_note TEXT DEFAULT '',
        UNIQUE(calisan_id, donem),
        FOREIGN KEY(calisan_id) REFERENCES maas_calisan(id) ON DELETE CASCADE
    );""")


    # Maaş - Hesap Hareketleri (eşleştirme geçmişi)
    # Not: SQLite bazı sürümlerde DEFAULT ifadesinde fonksiyon çağrısına izin vermeyebilir.
    # Bu yüzden en uyumlu seçenek olan CURRENT_TIMESTAMP kullanıyoruz.
    c.execute("""
    CREATE TABLE IF NOT EXISTS maas_hesap_hareket(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        donem TEXT NOT NULL, -- YYYY-MM
        calisan_id INTEGER NOT NULL,
        odeme_id INTEGER,
        banka_hareket_id INTEGER NOT NULL,
        match_score REAL DEFAULT 0,
        match_type TEXT DEFAULT 'auto_name',
        note TEXT DEFAULT '',
        UNIQUE(donem, calisan_id, banka_hareket_id),
        FOREIGN KEY(calisan_id) REFERENCES maas_calisan(id) ON DELETE CASCADE,
        FOREIGN KEY(odeme_id) REFERENCES maas_odeme(id) ON DELETE SET NULL,
        FOREIGN KEY(banka_hareket_id) REFERENCES banka_hareket(id) ON DELETE CASCADE
    );""")

    # -----------------
    # Nakliye Sistemi
    # -----------------
    c.execute("""
    CREATE TABLE IF NOT EXISTS nakliye_firma(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ad TEXT NOT NULL,
        telefon TEXT DEFAULT '',
        eposta TEXT DEFAULT '',
        adres TEXT DEFAULT '',
        aktif INTEGER NOT NULL DEFAULT 1,
        notlar TEXT DEFAULT '',
        UNIQUE(ad)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS nakliye_arac(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        firma_id INTEGER,
        plaka TEXT NOT NULL,
        tip TEXT DEFAULT '',
        marka TEXT DEFAULT '',
        model TEXT DEFAULT '',
        yil TEXT DEFAULT '',
        kapasite TEXT DEFAULT '',
        surucu TEXT DEFAULT '',
        aktif INTEGER NOT NULL DEFAULT 1,
        notlar TEXT DEFAULT '',
        UNIQUE(plaka),
        FOREIGN KEY(firma_id) REFERENCES nakliye_firma(id) ON DELETE SET NULL
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS nakliye_rota(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ad TEXT NOT NULL,
        cikis TEXT DEFAULT '',
        varis TEXT DEFAULT '',
        mesafe_km REAL DEFAULT 0,
        sure_saat REAL DEFAULT 0,
        aktif INTEGER NOT NULL DEFAULT 1,
        notlar TEXT DEFAULT ''
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS nakliye_is(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        is_no TEXT NOT NULL UNIQUE,
        tarih TEXT NOT NULL,
        saat TEXT DEFAULT '',
        firma_id INTEGER,
        arac_id INTEGER,
        rota_id INTEGER,
        cikis TEXT DEFAULT '',
        varis TEXT DEFAULT '',
        yuk TEXT DEFAULT '',
        durum TEXT DEFAULT 'Planlandı',
        ucret REAL DEFAULT 0,
        para TEXT DEFAULT 'TL',
        notlar TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(firma_id) REFERENCES nakliye_firma(id) ON DELETE SET NULL,
        FOREIGN KEY(arac_id) REFERENCES nakliye_arac(id) ON DELETE SET NULL,
        FOREIGN KEY(rota_id) REFERENCES nakliye_rota(id) ON DELETE SET NULL
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS nakliye_islem(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        is_id INTEGER NOT NULL,
        tarih TEXT NOT NULL,
        saat TEXT DEFAULT '',
        tip TEXT NOT NULL,
        aciklama TEXT DEFAULT '',
        FOREIGN KEY(is_id) REFERENCES nakliye_is(id) ON DELETE CASCADE
    );""")

    conn.commit()


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    try:
        rows = list(conn.execute(f"PRAGMA table_info({table})"))
        out = set()
        for r in rows:
            try:
                out.add(str(r[1]))  # name
            except Exception:
                pass
        return out
    except Exception:
        return set()


def _ensure_column(
    conn: sqlite3.Connection,
    table: str,
    col: str,
    col_def_sql: str,
    log_fn: Optional[Callable[[str, str], None]] = None,
) -> None:
    cols = _table_columns(conn, table)
    if col in cols:
        return
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def_sql}")
        conn.commit()
        if log_fn:
            log_fn("Schema Migration", f"{table}: added column {col}")
    except Exception as e:
        if log_fn:
            try:
                log_fn("Schema Migration Error", f"{table}.{col}: {e}")
            except Exception:
                pass


def _ensure_index(
    conn: sqlite3.Connection,
    name: str,
    table: str,
    cols_sql: str,
    log_fn: Optional[Callable[[str, str], None]] = None,
) -> None:
    try:
        conn.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({cols_sql})")
        conn.commit()
    except Exception as e:
        if log_fn:
            try:
                log_fn("Schema Migration Error", f"index {name}: {e}")
            except Exception:
                pass


def migrate_schema(conn: sqlite3.Connection, log_fn: Optional[Callable[[str, str], None]] = None) -> None:
    # Banka tabloları (eski DB'ler için)
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS banka_hareket(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarih TEXT NOT NULL,
                banka TEXT DEFAULT '',
                hesap TEXT DEFAULT '',
                tip TEXT NOT NULL,
                tutar REAL NOT NULL,
                para TEXT DEFAULT 'TL',
                aciklama TEXT DEFAULT '',
                referans TEXT DEFAULT '',
                belge TEXT DEFAULT '',
                etiket TEXT DEFAULT '',
                import_grup TEXT DEFAULT '',
                bakiye REAL
            );"""
        )
        conn.commit()
    except Exception as e:
        if log_fn:
            try:
                log_fn("Schema Migration Error", f"banka_hareket: {e}")
            except Exception:
                pass

    # banka_hareket (eski tablolar için kolon garantisi)
    _ensure_column(conn, "banka_hareket", "import_grup", "TEXT DEFAULT ''", log_fn)

    # Yeni tabloları eski DB'lerde de oluştur (init_schema bazı eski DB'lerde çalışmış olsa bile güvenlik)
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS maas_meslek(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ad TEXT NOT NULL,
                aktif INTEGER NOT NULL DEFAULT 1,
                notlar TEXT DEFAULT '',
                UNIQUE(ad)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS maas_calisan(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ad TEXT NOT NULL,
                aylik_tutar REAL NOT NULL DEFAULT 0,
                para TEXT DEFAULT 'TL',
                meslek_id INTEGER,
                aktif INTEGER NOT NULL DEFAULT 1,
                notlar TEXT DEFAULT '',
                UNIQUE(ad)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS maas_odeme(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                donem TEXT NOT NULL,
                calisan_id INTEGER NOT NULL,
                tutar REAL NOT NULL DEFAULT 0,
                para TEXT DEFAULT 'TL',
                odendi INTEGER NOT NULL DEFAULT 0,
                odeme_tarihi TEXT DEFAULT '',
                aciklama TEXT DEFAULT '',
                banka_hareket_id INTEGER,
                banka_match_score REAL,
                banka_match_note TEXT DEFAULT '',
                UNIQUE(calisan_id, donem),
                FOREIGN KEY(calisan_id) REFERENCES maas_calisan(id) ON DELETE CASCADE
            );"""
        )
        conn.commit()
    except Exception as e:
        if log_fn:
            try:
                log_fn("Schema Migration Error", f"maas tables: {e}")
            except Exception:
                pass

    

    # Maaş - Hesap Hareketleri (eşleştirme geçmişi)
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS maas_hesap_hareket(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                donem TEXT NOT NULL,
                calisan_id INTEGER NOT NULL,
                odeme_id INTEGER,
                banka_hareket_id INTEGER NOT NULL,
                match_score REAL DEFAULT 0,
                match_type TEXT DEFAULT 'auto_name',
                note TEXT DEFAULT '',
                UNIQUE(donem, calisan_id, banka_hareket_id)
            );"""
        )
        conn.commit()
    except Exception as e:
        if log_fn:
            try:
                log_fn("Schema Migration Error", f"maas_hesap_hareket: {e}")
            except Exception:
                pass

    # Maaş ödeme tablosu yeni kolonlar (banka eşleştirme için)
    _ensure_column(conn, "maas_odeme", "banka_hareket_id", "INTEGER", log_fn)
    _ensure_column(conn, "maas_odeme", "banka_match_score", "REAL", log_fn)
    _ensure_column(conn, "maas_odeme", "banka_match_note", "TEXT DEFAULT ''", log_fn)

    # Maaş çalışan: meslek alanı
    _ensure_column(conn, "maas_calisan", "meslek_id", "INTEGER", log_fn)

    # users (eski DB'ler için kolon garantisi)
    _ensure_column(conn, "users", "role", "TEXT NOT NULL DEFAULT 'user'", log_fn)
    _ensure_column(conn, "users", "created_at", "TEXT DEFAULT ''", log_fn)
    _ensure_column(conn, "users", "salt", "TEXT DEFAULT ''", log_fn)
    _ensure_column(conn, "users", "pass_hash", "TEXT DEFAULT ''", log_fn)

    # cariler
    _ensure_column(conn, "cariler", "aktif", "INTEGER NOT NULL DEFAULT 1", log_fn)
    _ensure_column(conn, "cariler", "tur", "TEXT DEFAULT ''", log_fn)
    _ensure_column(conn, "cariler", "telefon", "TEXT DEFAULT ''", log_fn)
    _ensure_column(conn, "cariler", "notlar", "TEXT DEFAULT ''", log_fn)
    _ensure_column(conn, "cariler", "acilis_bakiye", "REAL DEFAULT 0", log_fn)

    # cari_hareket
    _ensure_column(conn, "cari_hareket", "para", "TEXT DEFAULT 'TL'", log_fn)
    _ensure_column(conn, "cari_hareket", "aciklama", "TEXT DEFAULT ''", log_fn)
    _ensure_column(conn, "cari_hareket", "odeme", "TEXT DEFAULT ''", log_fn)
    _ensure_column(conn, "cari_hareket", "belge", "TEXT DEFAULT ''", log_fn)
    _ensure_column(conn, "cari_hareket", "etiket", "TEXT DEFAULT ''", log_fn)

    # banka_hareket
    _ensure_column(conn, "banka_hareket", "import_grup", "TEXT DEFAULT ''", log_fn)

    # kasa_hareket
    _ensure_column(conn, "kasa_hareket", "para", "TEXT DEFAULT 'TL'", log_fn)
    _ensure_column(conn, "kasa_hareket", "odeme", "TEXT DEFAULT ''", log_fn)
    _ensure_column(conn, "kasa_hareket", "kategori", "TEXT DEFAULT ''", log_fn)
    _ensure_column(conn, "kasa_hareket", "cari_id", "INTEGER", log_fn)
    _ensure_column(conn, "kasa_hareket", "aciklama", "TEXT DEFAULT ''", log_fn)
    _ensure_column(conn, "kasa_hareket", "belge", "TEXT DEFAULT ''", log_fn)
    _ensure_column(conn, "kasa_hareket", "etiket", "TEXT DEFAULT ''", log_fn)

    # -----------------
    # Nakliye Sistemi (eski DB'ler için)
    # -----------------
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS nakliye_firma(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ad TEXT NOT NULL,
                telefon TEXT DEFAULT '',
                eposta TEXT DEFAULT '',
                adres TEXT DEFAULT '',
                aktif INTEGER NOT NULL DEFAULT 1,
                notlar TEXT DEFAULT '',
                UNIQUE(ad)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS nakliye_arac(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                firma_id INTEGER,
                plaka TEXT NOT NULL,
                tip TEXT DEFAULT '',
                marka TEXT DEFAULT '',
                model TEXT DEFAULT '',
                yil TEXT DEFAULT '',
                kapasite TEXT DEFAULT '',
                surucu TEXT DEFAULT '',
                aktif INTEGER NOT NULL DEFAULT 1,
                notlar TEXT DEFAULT '',
                UNIQUE(plaka),
                FOREIGN KEY(firma_id) REFERENCES nakliye_firma(id) ON DELETE SET NULL
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS nakliye_rota(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ad TEXT NOT NULL,
                cikis TEXT DEFAULT '',
                varis TEXT DEFAULT '',
                mesafe_km REAL DEFAULT 0,
                sure_saat REAL DEFAULT 0,
                aktif INTEGER NOT NULL DEFAULT 1,
                notlar TEXT DEFAULT ''
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS nakliye_is(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                is_no TEXT NOT NULL UNIQUE,
                tarih TEXT NOT NULL,
                saat TEXT DEFAULT '',
                firma_id INTEGER,
                arac_id INTEGER,
                rota_id INTEGER,
                cikis TEXT DEFAULT '',
                varis TEXT DEFAULT '',
                yuk TEXT DEFAULT '',
                durum TEXT DEFAULT 'Planlandı',
                ucret REAL DEFAULT 0,
                para TEXT DEFAULT 'TL',
                notlar TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(firma_id) REFERENCES nakliye_firma(id) ON DELETE SET NULL,
                FOREIGN KEY(arac_id) REFERENCES nakliye_arac(id) ON DELETE SET NULL,
                FOREIGN KEY(rota_id) REFERENCES nakliye_rota(id) ON DELETE SET NULL
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS nakliye_islem(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                is_id INTEGER NOT NULL,
                tarih TEXT NOT NULL,
                saat TEXT DEFAULT '',
                tip TEXT NOT NULL,
                aciklama TEXT DEFAULT '',
                FOREIGN KEY(is_id) REFERENCES nakliye_is(id) ON DELETE CASCADE
            );"""
        )
        conn.commit()
    except Exception as e:
        if log_fn:
            try:
                log_fn("Schema Migration Error", f"nakliye tables: {e}")
            except Exception:
                pass

    # -----------------
    # Satış Siparişleri (eski DB'ler için)
    # -----------------
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS satis_siparis(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarih TEXT NOT NULL,
                teslim_tarih TEXT DEFAULT '',
                siparis_no TEXT NOT NULL UNIQUE,
                cari_id INTEGER,
                cari_ad TEXT DEFAULT '',
                temsilci TEXT DEFAULT '',
                depo_id INTEGER,
                durum TEXT NOT NULL DEFAULT 'Açık',
                para TEXT DEFAULT 'TL',
                toplam REAL DEFAULT 0,
                aciklama TEXT DEFAULT '',
                sevk_tarih TEXT DEFAULT '',
                sevk_no TEXT DEFAULT '',
                fatura_id INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS satis_siparis_kalem(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                siparis_id INTEGER NOT NULL,
                urun_id INTEGER,
                urun_kod TEXT DEFAULT '',
                urun_ad TEXT DEFAULT '',
                birim TEXT DEFAULT 'Adet',
                miktar REAL DEFAULT 0,
                birim_fiyat REAL DEFAULT 0,
                toplam REAL DEFAULT 0,
                sevk_miktar REAL DEFAULT 0,
                aciklama TEXT DEFAULT '',
                FOREIGN KEY(siparis_id) REFERENCES satis_siparis(id) ON DELETE CASCADE
            );"""
        )
        conn.commit()
    except Exception as e:
        if log_fn:
            try:
                log_fn("Schema Migration Error", f"satis_siparis tables: {e}")
            except Exception:
                pass

    _ensure_column(conn, "satis_siparis", "teslim_tarih", "TEXT DEFAULT ''", log_fn)
    _ensure_column(conn, "satis_siparis", "cari_ad", "TEXT DEFAULT ''", log_fn)
    _ensure_column(conn, "satis_siparis", "temsilci", "TEXT DEFAULT ''", log_fn)
    _ensure_column(conn, "satis_siparis", "depo_id", "INTEGER", log_fn)
    _ensure_column(conn, "satis_siparis", "durum", "TEXT NOT NULL DEFAULT 'Açık'", log_fn)
    _ensure_column(conn, "satis_siparis", "para", "TEXT DEFAULT 'TL'", log_fn)
    _ensure_column(conn, "satis_siparis", "toplam", "REAL DEFAULT 0", log_fn)
    _ensure_column(conn, "satis_siparis", "aciklama", "TEXT DEFAULT ''", log_fn)
    _ensure_column(conn, "satis_siparis", "sevk_tarih", "TEXT DEFAULT ''", log_fn)
    _ensure_column(conn, "satis_siparis", "sevk_no", "TEXT DEFAULT ''", log_fn)
    _ensure_column(conn, "satis_siparis", "fatura_id", "INTEGER", log_fn)

    _ensure_column(conn, "satis_siparis_kalem", "urun_id", "INTEGER", log_fn)
    _ensure_column(conn, "satis_siparis_kalem", "urun_kod", "TEXT DEFAULT ''", log_fn)
    _ensure_column(conn, "satis_siparis_kalem", "urun_ad", "TEXT DEFAULT ''", log_fn)
    _ensure_column(conn, "satis_siparis_kalem", "birim", "TEXT DEFAULT 'Adet'", log_fn)
    _ensure_column(conn, "satis_siparis_kalem", "miktar", "REAL DEFAULT 0", log_fn)
    _ensure_column(conn, "satis_siparis_kalem", "birim_fiyat", "REAL DEFAULT 0", log_fn)
    _ensure_column(conn, "satis_siparis_kalem", "toplam", "REAL DEFAULT 0", log_fn)
    _ensure_column(conn, "satis_siparis_kalem", "sevk_miktar", "REAL DEFAULT 0", log_fn)
    _ensure_column(conn, "satis_siparis_kalem", "aciklama", "TEXT DEFAULT ''", log_fn)

    # Sık kullanılan sorgular için indeksler
    _ensure_index(conn, "idx_cari_hareket_cari_tarih", "cari_hareket", "cari_id, tarih", log_fn)
    _ensure_index(conn, "idx_cari_hareket_tarih", "cari_hareket", "tarih", log_fn)
    _ensure_index(conn, "idx_kasa_hareket_tarih", "kasa_hareket", "tarih", log_fn)
    _ensure_index(conn, "idx_banka_hareket_tarih", "banka_hareket", "tarih", log_fn)
    _ensure_index(conn, "idx_banka_hareket_import_grup", "banka_hareket", "import_grup", log_fn)
    _ensure_index(conn, "idx_fatura_cari_tarih", "fatura", "cari_id, tarih", log_fn)
    _ensure_index(conn, "idx_fatura_tur_tarih", "fatura", "tur, tarih", log_fn)
    _ensure_index(conn, "idx_fatura_kalem_fatura_id", "fatura_kalem", "fatura_id", log_fn)
    _ensure_index(conn, "idx_fatura_kalem_urun", "fatura_kalem", "urun", log_fn)
    _ensure_index(conn, "idx_fatura_odeme_fatura_id", "fatura_odeme", "fatura_id", log_fn)
    _ensure_index(conn, "idx_satis_siparis_tarih", "satis_siparis", "tarih", log_fn)
    _ensure_index(conn, "idx_satis_siparis_cari", "satis_siparis", "cari_id, tarih", log_fn)
    _ensure_index(conn, "idx_satis_siparis_kalem_siparis", "satis_siparis_kalem", "siparis_id", log_fn)
    _ensure_index(conn, "idx_stok_hareket_urun_id", "stok_hareket", "urun_id", log_fn)
    _ensure_index(conn, "idx_messages_created_at", "messages", "created_at", log_fn)
    _ensure_index(conn, "idx_message_recipients_recipient_created", "message_recipients", "recipient_id, created_at", log_fn)

    _ensure_index(conn, "idx_stok_hareket_tarih", "stok_hareket", "tarih", log_fn)
    _ensure_index(conn, "idx_kasa_hareket_tip_tarih", "kasa_hareket", "tip, tarih", log_fn)


def seed_defaults(conn: sqlite3.Connection, log_fn: Optional[Callable[[str, str], None]] = None) -> None:
    """DB ilk kurulum: kullanıcı + settings seed."""
    # default admin (company db içi)
    try:
        cur = conn.execute("SELECT COUNT(*) FROM users")
        n = int(cur.fetchone()[0])
    except Exception:
        n = 0

    if n == 0:
        from ..utils import make_salt, hash_password, now_iso

        salt = make_salt()
        conn.execute(
            "INSERT INTO users(username,salt,pass_hash,role,created_at) VALUES(?,?,?,?,?)",
            ("admin", salt, hash_password("admin", salt), "admin", now_iso()),
        )
        conn.commit()
        if log_fn:
            log_fn("Init", "Default admin created (admin/admin)")

    # default lists (settings)
    try:
        import json
        from ..config import DEFAULT_CURRENCIES, DEFAULT_PAYMENTS, DEFAULT_CATEGORIES, DEFAULT_STOCK_UNITS, DEFAULT_STOCK_CATEGORIES

        def _get(k: str):
            r = conn.execute("SELECT value FROM settings WHERE key=?", (k,)).fetchone()
            return r[0] if r else None

        def _set(k: str, v: str):
            conn.execute(
                "INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (k, v),
            )
            conn.commit()

        if not _get("currencies"):
            _set("currencies", json.dumps(DEFAULT_CURRENCIES, ensure_ascii=False))
        if not _get("payments"):
            _set("payments", json.dumps(DEFAULT_PAYMENTS, ensure_ascii=False))
        if not _get("categories"):
            _set("categories", json.dumps(DEFAULT_CATEGORIES, ensure_ascii=False))
        if not _get("stock_units"):
            _set("stock_units", json.dumps(DEFAULT_STOCK_UNITS, ensure_ascii=False))
        if not _get("stock_categories"):
            _set("stock_categories", json.dumps(DEFAULT_STOCK_CATEGORIES, ensure_ascii=False))
    except Exception:
        pass
