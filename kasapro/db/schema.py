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
        sube TEXT DEFAULT '',
        depo TEXT DEFAULT '',
        satis_temsilcisi TEXT DEFAULT '',

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
        kategori TEXT DEFAULT '',
        aciklama TEXT DEFAULT '',
        miktar REAL DEFAULT 0,
        birim TEXT DEFAULT 'Adet',
        birim_fiyat REAL DEFAULT 0,
        maliyet REAL DEFAULT 0,
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
    # Doküman & Süreç Yönetimi (DMS)
    # -----------------
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS documents(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        doc_type TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'ACTIVE',
        current_version_id INTEGER,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );"""
    )
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS document_tags(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        document_id INTEGER NOT NULL,
        tag TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );"""
    )
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS document_links(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        document_id INTEGER NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );"""
    )
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS document_versions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        document_id INTEGER NOT NULL,
        version_no INTEGER NOT NULL,
        file_path TEXT NOT NULL,
        original_name TEXT NOT NULL,
        mime TEXT NOT NULL,
        size INTEGER NOT NULL,
        sha256 TEXT NOT NULL,
        change_note TEXT DEFAULT '',
        status TEXT NOT NULL DEFAULT 'DRAFT',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );"""
    )
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS workflow_templates(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );"""
    )
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS workflow_steps(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        template_id INTEGER NOT NULL,
        step_no INTEGER NOT NULL,
        name TEXT NOT NULL,
        approver_role TEXT NOT NULL,
        approver_user_id INTEGER,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );"""
    )
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS workflow_instances(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        template_id INTEGER NOT NULL,
        document_id INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'NOT_STARTED',
        current_step_no INTEGER,
        started_by INTEGER,
        started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );"""
    )
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS workflow_actions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        instance_id INTEGER NOT NULL,
        step_no INTEGER NOT NULL,
        action TEXT NOT NULL,
        comment TEXT DEFAULT '',
        actor_id INTEGER,
        acted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );"""
    )
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS tasks(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        document_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT DEFAULT '',
        assignee_id INTEGER NOT NULL,
        due_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'OPEN',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        completed_at TEXT
    );"""
    )
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS messages(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER NOT NULL,
        sender_username TEXT NOT NULL,
        subject TEXT NOT NULL DEFAULT '',
        body TEXT NOT NULL DEFAULT '',
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
        is_read INTEGER NOT NULL DEFAULT 0,
        read_at TEXT DEFAULT NULL,
        FOREIGN KEY(message_id) REFERENCES messages(id) ON DELETE CASCADE
    );"""
    )
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS reminders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL DEFAULT 1,
        owner_user_id INTEGER,
        assignee_user_id INTEGER,
        document_id INTEGER,
        task_id INTEGER,
        title TEXT DEFAULT '',
        body TEXT DEFAULT '',
        due_at TEXT DEFAULT '',
        remind_at TEXT DEFAULT '',
        priority TEXT DEFAULT 'normal',
        status TEXT NOT NULL DEFAULT 'scheduled',
        series_id INTEGER,
        snooze_until TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );"""
    )
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS audit_log(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        actor_id INTEGER,
        details TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );"""
    )
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS series_counters(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        series TEXT NOT NULL,
        year INTEGER NOT NULL,
        last_no INTEGER NOT NULL DEFAULT 0,
        padding INTEGER NOT NULL DEFAULT 6,
        format TEXT NOT NULL DEFAULT '{series}-{year}-{no_pad}',
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );"""
    )
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS docs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        doc_no TEXT NOT NULL,
        series TEXT NOT NULL,
        year INTEGER NOT NULL,
        doc_date TEXT NOT NULL,
        due_date TEXT DEFAULT '',
        doc_type TEXT NOT NULL,
        status TEXT NOT NULL,
        is_proforma INTEGER NOT NULL DEFAULT 0,
        customer_id INTEGER,
        customer_name TEXT DEFAULT '',
        currency TEXT NOT NULL DEFAULT 'TL',
        vat_included INTEGER NOT NULL DEFAULT 0,
        invoice_discount_type TEXT DEFAULT 'amount',
        invoice_discount_value REAL NOT NULL DEFAULT 0,
        subtotal REAL NOT NULL DEFAULT 0,
        discount_total REAL NOT NULL DEFAULT 0,
        vat_total REAL NOT NULL DEFAULT 0,
        grand_total REAL NOT NULL DEFAULT 0,
        notes TEXT DEFAULT '',
        warehouse_id INTEGER,
        payment_status TEXT NOT NULL DEFAULT 'UNPAID',
        created_by INTEGER,
        created_by_name TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        voided_at TEXT,
        reversed_doc_id INTEGER
    );"""
    )
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS doc_lines(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_id INTEGER NOT NULL,
        line_no INTEGER NOT NULL,
        item_id INTEGER,
        description TEXT NOT NULL,
        qty REAL NOT NULL,
        unit TEXT DEFAULT '',
        unit_price REAL NOT NULL,
        vat_rate REAL NOT NULL DEFAULT 0,
        line_discount_type TEXT DEFAULT 'amount',
        line_discount_value REAL NOT NULL DEFAULT 0,
        line_subtotal REAL NOT NULL DEFAULT 0,
        line_discount REAL NOT NULL DEFAULT 0,
        line_vat REAL NOT NULL DEFAULT 0,
        line_total REAL NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );"""
    )
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS payments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_id INTEGER NOT NULL,
        pay_date TEXT NOT NULL,
        amount REAL NOT NULL,
        currency TEXT NOT NULL DEFAULT 'TL',
        method TEXT DEFAULT '',
        description TEXT DEFAULT '',
        ref TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );"""
    )
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS stock_moves(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_id INTEGER NOT NULL,
        line_id INTEGER,
        item_id INTEGER,
        qty REAL NOT NULL,
        unit TEXT DEFAULT '',
        direction TEXT DEFAULT '',
        move_date TEXT NOT NULL,
        warehouse_id INTEGER,
        doc_type TEXT DEFAULT '',
        doc_no TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );"""
    )
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS trade_warehouses(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );"""
    )
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS trade_docs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        doc_type TEXT NOT NULL,
        doc_no TEXT NOT NULL,
        doc_date TEXT NOT NULL,
        status TEXT NOT NULL,
        cari_id INTEGER,
        cari_name TEXT DEFAULT '',
        currency TEXT NOT NULL DEFAULT 'TL',
        subtotal REAL NOT NULL DEFAULT 0,
        tax_total REAL NOT NULL DEFAULT 0,
        discount_total REAL NOT NULL DEFAULT 0,
        total REAL NOT NULL DEFAULT 0,
        notes TEXT DEFAULT '',
        related_doc_id INTEGER,
        order_id INTEGER,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );"""
    )
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS trade_doc_lines(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_id INTEGER NOT NULL,
        item TEXT NOT NULL DEFAULT '',
        description TEXT DEFAULT '',
        qty REAL NOT NULL DEFAULT 0,
        unit TEXT NOT NULL DEFAULT 'Adet',
        unit_price REAL NOT NULL DEFAULT 0,
        tax_rate REAL NOT NULL DEFAULT 0,
        line_total REAL NOT NULL DEFAULT 0,
        tax_total REAL NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );"""
    )
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS trade_stock_moves(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        doc_id INTEGER,
        line_id INTEGER,
        item TEXT NOT NULL DEFAULT '',
        qty REAL NOT NULL,
        unit TEXT NOT NULL DEFAULT 'Adet',
        direction TEXT NOT NULL DEFAULT '',
        warehouse_id INTEGER,
        move_type TEXT NOT NULL DEFAULT '',
        note TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );"""
    )
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS trade_payments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        doc_id INTEGER,
        pay_date TEXT NOT NULL,
        direction TEXT NOT NULL DEFAULT '',
        amount REAL NOT NULL,
        currency TEXT NOT NULL DEFAULT 'TL',
        method TEXT DEFAULT '',
        reference TEXT DEFAULT '',
        kasa_hareket_id INTEGER,
        banka_hareket_id INTEGER,
        notes TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );"""
    )
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS trade_orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        order_type TEXT NOT NULL,
        order_no TEXT NOT NULL,
        order_date TEXT NOT NULL,
        status TEXT NOT NULL,
        cari_id INTEGER,
        cari_name TEXT DEFAULT '',
        currency TEXT NOT NULL DEFAULT 'TL',
        total REAL NOT NULL DEFAULT 0,
        notes TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );"""
    )
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS trade_order_lines(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        item TEXT NOT NULL DEFAULT '',
        qty REAL NOT NULL DEFAULT 0,
        fulfilled_qty REAL NOT NULL DEFAULT 0,
        unit TEXT NOT NULL DEFAULT 'Adet',
        unit_price REAL NOT NULL DEFAULT 0,
        line_total REAL NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );"""
    )
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS trade_audit_log(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        user_id INTEGER,
        username TEXT NOT NULL DEFAULT '',
        action TEXT NOT NULL,
        entity TEXT NOT NULL,
        entity_id INTEGER,
        detail TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );"""
    )
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS trade_user_roles(
        company_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        username TEXT NOT NULL,
        role TEXT NOT NULL,
        PRIMARY KEY(company_id, user_id)
    );"""
    )

    # Create indexes (safe mode - skip if table/column doesn't exist)
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status, updated_at)")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_documents_company ON documents(company_id)")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_document_tags_tag ON document_tags(tag)")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_document_links_entity ON document_links(entity_type, entity_id)")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_document_versions_doc ON document_versions(document_id, version_no)")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_workflow_instances_status ON workflow_instances(status, updated_at)")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_tasks_due ON tasks(due_at, status)")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_reminders_due ON reminders(remind_at, status)")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_log(entity_type, entity_id)")
    except sqlite3.OperationalError:
        pass

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

    # -----------------
    # Teklif & Sipariş (Quote-Order)
    # -----------------
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS series_counters(
        name TEXT PRIMARY KEY,
        prefix TEXT DEFAULT '',
        last_no INTEGER NOT NULL DEFAULT 0,
        padding INTEGER NOT NULL DEFAULT 6,
        format TEXT DEFAULT '{prefix}{no_pad}'
    );"""
    )

    c.execute(
        """
    CREATE TABLE IF NOT EXISTS quotes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quote_no TEXT NOT NULL,
        version INTEGER NOT NULL DEFAULT 1,
        status TEXT NOT NULL DEFAULT 'DRAFT',
        quote_group_id INTEGER,
        cari_id INTEGER,
        cari_ad TEXT DEFAULT '',
        valid_until TEXT DEFAULT '',
        para TEXT DEFAULT 'TL',
        kur REAL DEFAULT 1,
        ara_toplam REAL DEFAULT 0,
        iskonto_toplam REAL DEFAULT 0,
        genel_iskonto_oran REAL DEFAULT 0,
        genel_iskonto_tutar REAL DEFAULT 0,
        kdv_toplam REAL DEFAULT 0,
        genel_toplam REAL DEFAULT 0,
        notlar TEXT DEFAULT '',
        locked INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(quote_no, version),
        FOREIGN KEY(cari_id) REFERENCES cariler(id)
    );"""
    )

    c.execute(
        """
    CREATE TABLE IF NOT EXISTS quote_lines(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quote_id INTEGER NOT NULL,
        line_no INTEGER NOT NULL DEFAULT 1,
        urun TEXT DEFAULT '',
        aciklama TEXT DEFAULT '',
        miktar REAL DEFAULT 0,
        birim TEXT DEFAULT 'Adet',
        birim_fiyat REAL DEFAULT 0,
        iskonto_oran REAL DEFAULT 0,
        iskonto_tutar REAL DEFAULT 0,
        kdv_oran REAL DEFAULT 20,
        kdv_tutar REAL DEFAULT 0,
        toplam REAL DEFAULT 0,
        FOREIGN KEY(quote_id) REFERENCES quotes(id) ON DELETE CASCADE
    );"""
    )

    c.execute(
        """
    CREATE TABLE IF NOT EXISTS sales_orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_no TEXT NOT NULL UNIQUE,
        quote_id INTEGER,
        status TEXT NOT NULL DEFAULT 'DRAFT',
        cari_id INTEGER,
        cari_ad TEXT DEFAULT '',
        para TEXT DEFAULT 'TL',
        kur REAL DEFAULT 1,
        ara_toplam REAL DEFAULT 0,
        iskonto_toplam REAL DEFAULT 0,
        kdv_toplam REAL DEFAULT 0,
        genel_toplam REAL DEFAULT 0,
        notlar TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(quote_id) REFERENCES quotes(id),
        FOREIGN KEY(cari_id) REFERENCES cariler(id)
    );"""
    )

    c.execute(
        """
    CREATE TABLE IF NOT EXISTS sales_order_lines(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        line_no INTEGER NOT NULL DEFAULT 1,
        urun TEXT DEFAULT '',
        aciklama TEXT DEFAULT '',
        miktar_siparis REAL DEFAULT 0,
        miktar_sevk REAL DEFAULT 0,
        miktar_fatura REAL DEFAULT 0,
        birim TEXT DEFAULT 'Adet',
        birim_fiyat REAL DEFAULT 0,
        iskonto_oran REAL DEFAULT 0,
        iskonto_tutar REAL DEFAULT 0,
        kdv_oran REAL DEFAULT 20,
        kdv_tutar REAL DEFAULT 0,
        toplam REAL DEFAULT 0,
        FOREIGN KEY(order_id) REFERENCES sales_orders(id) ON DELETE CASCADE
    );"""
    )

    c.execute(
        """
    CREATE TABLE IF NOT EXISTS audit_log(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        entity_type TEXT NOT NULL,
        entity_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        user_id INTEGER,
        username TEXT DEFAULT '',
        role TEXT DEFAULT '',
        note TEXT DEFAULT ''
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
    # Hakediş Hazırlama Merkezi
    # -----------------
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS hakedis_project(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        idare TEXT DEFAULT '',
        yuklenici TEXT DEFAULT '',
        isin_adi TEXT DEFAULT '',
        sozlesme_bedeli REAL DEFAULT 0,
        baslangic TEXT DEFAULT '',
        bitis TEXT DEFAULT '',
        sure_gun INTEGER DEFAULT 0,
        artis_eksilis REAL DEFAULT 0,
        avans REAL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );"""
    )

    c.execute(
        """
    CREATE TABLE IF NOT EXISTS hakedis_position(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        kod TEXT DEFAULT '',
        aciklama TEXT DEFAULT '',
        birim TEXT DEFAULT '',
        sozlesme_miktar REAL DEFAULT 0,
        birim_fiyat REAL DEFAULT 0,
        FOREIGN KEY(project_id) REFERENCES hakedis_project(id) ON DELETE CASCADE
    );"""
    )

    c.execute(
        """
    CREATE TABLE IF NOT EXISTS hakedis_period(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        hakedis_no TEXT DEFAULT '',
        ay INTEGER DEFAULT 1,
        yil INTEGER DEFAULT 2000,
        tarih_bas TEXT DEFAULT '',
        tarih_bit TEXT DEFAULT '',
        status TEXT NOT NULL DEFAULT 'Taslak',
        FOREIGN KEY(project_id) REFERENCES hakedis_project(id) ON DELETE CASCADE
    );"""
    )

    c.execute(
        """
    CREATE TABLE IF NOT EXISTS hakedis_measurement(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        period_id INTEGER NOT NULL,
        position_id INTEGER NOT NULL,
        onceki_miktar REAL DEFAULT 0,
        bu_donem_miktar REAL DEFAULT 0,
        kumulatif_miktar REAL DEFAULT 0,
        UNIQUE(period_id, position_id),
        FOREIGN KEY(period_id) REFERENCES hakedis_period(id) ON DELETE CASCADE,
        FOREIGN KEY(position_id) REFERENCES hakedis_position(id) ON DELETE CASCADE
    );"""
    )

    c.execute(
        """
    CREATE TABLE IF NOT EXISTS hakedis_attachment(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        period_id INTEGER NOT NULL,
        filename TEXT NOT NULL,
        stored_name TEXT NOT NULL,
        size_bytes INTEGER DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(period_id) REFERENCES hakedis_period(id) ON DELETE CASCADE
    );"""
    )

    c.execute(
        """
    CREATE TABLE IF NOT EXISTS hakedis_deduction(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        period_id INTEGER NOT NULL,
        ad TEXT NOT NULL,
        tip TEXT NOT NULL DEFAULT 'tutar',
        deger REAL DEFAULT 0,
        hesaplanan_tutar REAL DEFAULT 0,
        FOREIGN KEY(period_id) REFERENCES hakedis_period(id) ON DELETE CASCADE
    );"""
    )

    c.execute(
        """
    CREATE TABLE IF NOT EXISTS hakedis_indices_cache(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT NOT NULL,
        dataset_key TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        fetched_at TEXT NOT NULL,
        UNIQUE(source, dataset_key)
    );"""
    )

    c.execute(
        """
    CREATE TABLE IF NOT EXISTS hakedis_index_selection(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        dataset_key TEXT NOT NULL,
        enabled INTEGER NOT NULL DEFAULT 1,
        UNIQUE(project_id, dataset_key),
        FOREIGN KEY(project_id) REFERENCES hakedis_project(id) ON DELETE CASCADE
    );"""
    )

    c.execute(
        """
    CREATE TABLE IF NOT EXISTS hakedis_audit_log(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL,
        user_id INTEGER,
        action TEXT NOT NULL,
        entity TEXT NOT NULL,
        entity_id INTEGER,
        detail TEXT DEFAULT ''
    );"""
    )

    c.execute(
        """
    CREATE TABLE IF NOT EXISTS hakedis_user_roles(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        UNIQUE(project_id, user_id),
        FOREIGN KEY(project_id) REFERENCES hakedis_project(id) ON DELETE CASCADE
    );"""
    )

    # -----------------
    # İnsan Kaynakları (İK)
    # -----------------
    c.execute("""
    CREATE TABLE IF NOT EXISTS hr_departments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(company_id, name)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS hr_positions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        department_id INTEGER,
        name TEXT NOT NULL,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(company_id, name),
        FOREIGN KEY(department_id) REFERENCES hr_departments(id)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS hr_employees(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        employee_no TEXT NOT NULL,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        phone TEXT DEFAULT '',
        email TEXT DEFAULT '',
        department_id INTEGER,
        position_id INTEGER,
        start_date TEXT DEFAULT '',
        end_date TEXT DEFAULT '',
        status TEXT NOT NULL DEFAULT 'aktif',
        tckn TEXT DEFAULT '',
        iban TEXT DEFAULT '',
        address TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(company_id, employee_no),
        FOREIGN KEY(department_id) REFERENCES hr_departments(id),
        FOREIGN KEY(position_id) REFERENCES hr_positions(id)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS hr_salary_history(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        employee_id INTEGER NOT NULL,
        amount REAL NOT NULL DEFAULT 0,
        currency TEXT DEFAULT 'TL',
        effective_date TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(employee_id) REFERENCES hr_employees(id)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS hr_documents(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        employee_id INTEGER NOT NULL,
        doc_type TEXT NOT NULL,
        filename TEXT NOT NULL,
        stored_name TEXT NOT NULL,
        size_bytes INTEGER NOT NULL DEFAULT 0,
        uploaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        active INTEGER NOT NULL DEFAULT 1,
        FOREIGN KEY(employee_id) REFERENCES hr_employees(id)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS hr_leave_types(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        annual_days REAL NOT NULL DEFAULT 0,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(company_id, name)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS hr_leave_balances(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        employee_id INTEGER NOT NULL,
        year INTEGER NOT NULL,
        total_days REAL NOT NULL DEFAULT 0,
        used_days REAL NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(company_id, employee_id, year),
        FOREIGN KEY(employee_id) REFERENCES hr_employees(id)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS hr_leave_requests(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        employee_id INTEGER NOT NULL,
        leave_type_id INTEGER NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        total_days REAL NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'pending_manager',
        manager_username TEXT DEFAULT '',
        hr_username TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(employee_id) REFERENCES hr_employees(id),
        FOREIGN KEY(leave_type_id) REFERENCES hr_leave_types(id)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS hr_shifts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        start_time TEXT DEFAULT '',
        end_time TEXT DEFAULT '',
        break_minutes INTEGER NOT NULL DEFAULT 0,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(company_id, name)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS hr_timesheets(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        employee_id INTEGER NOT NULL,
        work_date TEXT NOT NULL,
        status TEXT NOT NULL,
        shift_id INTEGER,
        check_in TEXT DEFAULT '',
        check_out TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(company_id, employee_id, work_date),
        FOREIGN KEY(employee_id) REFERENCES hr_employees(id),
        FOREIGN KEY(shift_id) REFERENCES hr_shifts(id)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS hr_overtime_requests(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        employee_id INTEGER NOT NULL,
        work_date TEXT NOT NULL,
        hours REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        approved_by TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(employee_id) REFERENCES hr_employees(id)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS hr_payroll_periods(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        year INTEGER NOT NULL,
        month INTEGER NOT NULL,
        locked INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(company_id, year, month)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS hr_payroll_items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        period_id INTEGER NOT NULL,
        employee_id INTEGER NOT NULL,
        item_type TEXT NOT NULL,
        description TEXT DEFAULT '',
        amount REAL NOT NULL DEFAULT 0,
        currency TEXT DEFAULT 'TL',
        is_void INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(period_id) REFERENCES hr_payroll_periods(id),
        FOREIGN KEY(employee_id) REFERENCES hr_employees(id)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS hr_user_roles(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        username TEXT NOT NULL,
        role TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(company_id, username)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS hr_audit_log(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id INTEGER,
        action TEXT NOT NULL,
        actor_username TEXT DEFAULT '',
        actor_role TEXT DEFAULT '',
        detail TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );""")

    # -----------------
    # Entegrasyonlar (Core)
    # -----------------
    c.execute("""
    CREATE TABLE IF NOT EXISTS event_outbox(
        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        event_type TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        idempotency_key TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        processed_at TEXT,
        UNIQUE(company_id, idempotency_key)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS jobs(
        job_id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        job_type TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        attempts INTEGER NOT NULL DEFAULT 0,
        next_retry_at TEXT,
        last_error TEXT DEFAULT '',
        idempotency_key TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT,
        UNIQUE(company_id, idempotency_key)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS dead_letter_jobs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        job_type TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        attempts INTEGER NOT NULL DEFAULT 0,
        last_error TEXT DEFAULT '',
        idempotency_key TEXT,
        failed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS integration_settings(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        setting_key TEXT NOT NULL,
        value_encrypted TEXT NOT NULL,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(company_id, setting_key)
    );""")

    # -----------------
    # Entegrasyonlar (Notifications)
    # -----------------
    c.execute("""
    CREATE TABLE IF NOT EXISTS notification_templates(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        channel TEXT NOT NULL,
        subject TEXT DEFAULT '',
        body TEXT DEFAULT '',
        variables_json TEXT DEFAULT '',
        active INTEGER NOT NULL DEFAULT 1
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS notification_rules(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        event_type TEXT NOT NULL,
        channel TEXT NOT NULL,
        recipient TEXT NOT NULL,
        template_id INTEGER NOT NULL,
        active INTEGER NOT NULL DEFAULT 1,
        FOREIGN KEY(template_id) REFERENCES notification_templates(id)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS notification_outbox(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        channel TEXT NOT NULL,
        recipient TEXT NOT NULL,
        subject TEXT DEFAULT '',
        body TEXT DEFAULT '',
        status TEXT NOT NULL DEFAULT 'pending',
        attempts INTEGER NOT NULL DEFAULT 0,
        idempotency_key TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS delivery_log(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        notification_id INTEGER NOT NULL,
        provider TEXT NOT NULL,
        status TEXT NOT NULL,
        detail TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(notification_id) REFERENCES notification_outbox(id)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS contact_consents(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        contact TEXT NOT NULL,
        channel TEXT NOT NULL,
        opt_in INTEGER NOT NULL DEFAULT 1,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(company_id, contact, channel)
    );""")

    # -----------------
    # Entegrasyonlar (External Systems)
    # -----------------
    c.execute("""
    CREATE TABLE IF NOT EXISTS external_mappings(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        system TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        internal_id INTEGER NOT NULL,
        external_id TEXT NOT NULL,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(company_id, system, entity_type, internal_id)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS export_jobs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        job_type TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS export_items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER NOT NULL,
        entity_type TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        FOREIGN KEY(job_id) REFERENCES export_jobs(id) ON DELETE CASCADE
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS import_jobs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        job_type TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS import_items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER NOT NULL,
        entity_type TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        error TEXT DEFAULT '',
        FOREIGN KEY(job_id) REFERENCES import_jobs(id) ON DELETE CASCADE
    );""")

    # -----------------
    # Entegrasyonlar (Bank)
    # -----------------
    c.execute("""
    CREATE TABLE IF NOT EXISTS bank_statements(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        source_name TEXT NOT NULL,
        period_start TEXT NOT NULL,
        period_end TEXT NOT NULL,
        imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS bank_transactions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        statement_id INTEGER NOT NULL,
        transaction_date TEXT NOT NULL,
        amount REAL NOT NULL,
        description TEXT DEFAULT '',
        unique_hash TEXT NOT NULL,
        matched INTEGER NOT NULL DEFAULT 0,
        matched_ref TEXT DEFAULT '',
        matched_at TEXT,
        FOREIGN KEY(statement_id) REFERENCES bank_statements(id),
        UNIQUE(company_id, unique_hash)
    );""")

    # -----------------
    # Entegrasyonlar (API & Webhook)
    # -----------------
    c.execute("""
    CREATE TABLE IF NOT EXISTS api_tokens(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        token_hash TEXT NOT NULL,
        scopes_json TEXT DEFAULT '',
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        last_used_at TEXT,
        UNIQUE(company_id, token_hash)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS webhook_subscriptions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        url TEXT NOT NULL,
        secret TEXT NOT NULL,
        events_json TEXT NOT NULL,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS webhook_deliveries(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        subscription_id INTEGER NOT NULL,
        event_type TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        attempts INTEGER NOT NULL DEFAULT 0,
        next_retry_at TEXT,
        last_error TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT,
        FOREIGN KEY(subscription_id) REFERENCES webhook_subscriptions(id)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS idempotency_keys(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        idempotency_key TEXT NOT NULL,
        request_hash TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(company_id, idempotency_key)
    );""")

    c.execute("CREATE INDEX IF NOT EXISTS idx_event_outbox_company_processed ON event_outbox(company_id, processed_at)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_jobs_company_status ON jobs(company_id, status, next_retry_at)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_notification_rules_event ON notification_rules(company_id, event_type)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_bank_transactions_company ON bank_transactions(company_id, matched)")

    # -----------------
    # İnsan Kaynakları (İK)
    # -----------------
    c.execute("""
    CREATE TABLE IF NOT EXISTS hr_departments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(company_id, name)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS hr_positions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        department_id INTEGER,
        name TEXT NOT NULL,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(company_id, name),
        FOREIGN KEY(department_id) REFERENCES hr_departments(id)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS hr_employees(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        employee_no TEXT NOT NULL,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        phone TEXT DEFAULT '',
        email TEXT DEFAULT '',
        department_id INTEGER,
        position_id INTEGER,
        start_date TEXT DEFAULT '',
        end_date TEXT DEFAULT '',
        status TEXT NOT NULL DEFAULT 'aktif',
        tckn TEXT DEFAULT '',
        iban TEXT DEFAULT '',
        address TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(company_id, employee_no),
        FOREIGN KEY(department_id) REFERENCES hr_departments(id),
        FOREIGN KEY(position_id) REFERENCES hr_positions(id)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS hr_salary_history(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        employee_id INTEGER NOT NULL,
        amount REAL NOT NULL DEFAULT 0,
        currency TEXT DEFAULT 'TL',
        effective_date TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(employee_id) REFERENCES hr_employees(id)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS hr_documents(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        employee_id INTEGER NOT NULL,
        doc_type TEXT NOT NULL,
        filename TEXT NOT NULL,
        stored_name TEXT NOT NULL,
        size_bytes INTEGER NOT NULL DEFAULT 0,
        uploaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        active INTEGER NOT NULL DEFAULT 1,
        FOREIGN KEY(employee_id) REFERENCES hr_employees(id)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS hr_leave_types(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        annual_days REAL NOT NULL DEFAULT 0,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(company_id, name)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS hr_leave_balances(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        employee_id INTEGER NOT NULL,
        year INTEGER NOT NULL,
        total_days REAL NOT NULL DEFAULT 0,
        used_days REAL NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(company_id, employee_id, year),
        FOREIGN KEY(employee_id) REFERENCES hr_employees(id)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS hr_leave_requests(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        employee_id INTEGER NOT NULL,
        leave_type_id INTEGER NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        total_days REAL NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'pending_manager',
        manager_username TEXT DEFAULT '',
        hr_username TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(employee_id) REFERENCES hr_employees(id),
        FOREIGN KEY(leave_type_id) REFERENCES hr_leave_types(id)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS hr_shifts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        start_time TEXT DEFAULT '',
        end_time TEXT DEFAULT '',
        break_minutes INTEGER NOT NULL DEFAULT 0,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(company_id, name)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS hr_timesheets(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        employee_id INTEGER NOT NULL,
        work_date TEXT NOT NULL,
        status TEXT NOT NULL,
        shift_id INTEGER,
        check_in TEXT DEFAULT '',
        check_out TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(company_id, employee_id, work_date),
        FOREIGN KEY(employee_id) REFERENCES hr_employees(id),
        FOREIGN KEY(shift_id) REFERENCES hr_shifts(id)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS hr_overtime_requests(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        employee_id INTEGER NOT NULL,
        work_date TEXT NOT NULL,
        hours REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        approved_by TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(employee_id) REFERENCES hr_employees(id)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS hr_payroll_periods(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        year INTEGER NOT NULL,
        month INTEGER NOT NULL,
        locked INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(company_id, year, month)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS hr_payroll_items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        period_id INTEGER NOT NULL,
        employee_id INTEGER NOT NULL,
        item_type TEXT NOT NULL,
        description TEXT DEFAULT '',
        amount REAL NOT NULL DEFAULT 0,
        currency TEXT DEFAULT 'TL',
        is_void INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(period_id) REFERENCES hr_payroll_periods(id),
        FOREIGN KEY(employee_id) REFERENCES hr_employees(id)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS hr_user_roles(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        username TEXT NOT NULL,
        role TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(company_id, username)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS hr_audit_log(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id INTEGER,
        action TEXT NOT NULL,
        actor_username TEXT DEFAULT '',
        actor_role TEXT DEFAULT '',
        detail TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );""")

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

    # -----------------
    # Hakediş Modülü
    # -----------------
    c.execute("""
    CREATE TABLE IF NOT EXISTS projects(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        code TEXT DEFAULT '',
        status TEXT NOT NULL DEFAULT 'active',
        notes TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS sites(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        project_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        location TEXT DEFAULT '',
        status TEXT NOT NULL DEFAULT 'active',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(project_id) REFERENCES projects(id)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS contracts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        project_id INTEGER NOT NULL,
        site_id INTEGER,
        contract_no TEXT NOT NULL,
        contract_type TEXT NOT NULL DEFAULT 'birim_fiyat',
        currency TEXT DEFAULT 'TL',
        advance_rate REAL DEFAULT 0,
        retention_rate REAL DEFAULT 0,
        advance_deduction_rate REAL DEFAULT 0,
        penalty_rate REAL DEFAULT 0,
        price_diff_enabled INTEGER NOT NULL DEFAULT 0,
        formula_template TEXT DEFAULT '',
        formula_params TEXT DEFAULT '',
        status TEXT NOT NULL DEFAULT 'active',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(project_id) REFERENCES projects(id),
        FOREIGN KEY(site_id) REFERENCES sites(id)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS boq_items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        project_id INTEGER NOT NULL,
        contract_id INTEGER NOT NULL,
        poz_code TEXT NOT NULL,
        name TEXT NOT NULL,
        unit TEXT DEFAULT '',
        qty_contract REAL DEFAULT 0,
        unit_price REAL DEFAULT 0,
        group_name TEXT DEFAULT '',
        mahal TEXT DEFAULT '',
        budget REAL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(project_id) REFERENCES projects(id),
        FOREIGN KEY(contract_id) REFERENCES contracts(id)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS boq_revisions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        boq_item_id INTEGER NOT NULL,
        rev_no INTEGER NOT NULL,
        note TEXT DEFAULT '',
        snapshot_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(boq_item_id) REFERENCES boq_items(id)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS attachments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        module TEXT NOT NULL,
        filename TEXT NOT NULL,
        stored_name TEXT NOT NULL,
        stored_path TEXT NOT NULL,
        size_bytes INTEGER NOT NULL,
        created_at TEXT NOT NULL
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS pay_estimates(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        project_id INTEGER NOT NULL,
        contract_id INTEGER NOT NULL,
        period_no INTEGER NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Taslak',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(project_id) REFERENCES projects(id),
        FOREIGN KEY(contract_id) REFERENCES contracts(id)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS measurements(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        project_id INTEGER NOT NULL,
        contract_id INTEGER NOT NULL,
        period_id INTEGER NOT NULL,
        boq_item_id INTEGER NOT NULL,
        qty REAL NOT NULL,
        tarih TEXT NOT NULL,
        mahal TEXT DEFAULT '',
        note TEXT DEFAULT '',
        attachment_id INTEGER,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TEXT NOT NULL,
        FOREIGN KEY(period_id) REFERENCES pay_estimates(id),
        FOREIGN KEY(boq_item_id) REFERENCES boq_items(id),
        FOREIGN KEY(attachment_id) REFERENCES attachments(id)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS pay_estimate_lines(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        pay_estimate_id INTEGER NOT NULL,
        boq_item_id INTEGER NOT NULL,
        prev_qty REAL DEFAULT 0,
        current_qty REAL DEFAULT 0,
        cum_qty REAL DEFAULT 0,
        unit_price REAL DEFAULT 0,
        prev_amount REAL DEFAULT 0,
        current_amount REAL DEFAULT 0,
        cum_amount REAL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TEXT NOT NULL,
        FOREIGN KEY(pay_estimate_id) REFERENCES pay_estimates(id),
        FOREIGN KEY(boq_item_id) REFERENCES boq_items(id)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS deductions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        pay_estimate_id INTEGER NOT NULL,
        type TEXT NOT NULL,
        rate REAL DEFAULT 0,
        amount REAL DEFAULT 0,
        note TEXT DEFAULT '',
        status TEXT NOT NULL DEFAULT 'active',
        created_at TEXT NOT NULL,
        FOREIGN KEY(pay_estimate_id) REFERENCES pay_estimates(id)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS indices_cache(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        provider TEXT NOT NULL,
        index_code TEXT NOT NULL,
        index_value REAL NOT NULL,
        period TEXT NOT NULL,
        fetched_at TEXT NOT NULL,
        raw_json TEXT DEFAULT ''
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS price_diff_rules(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        contract_id INTEGER NOT NULL,
        formula_name TEXT NOT NULL,
        formula_params TEXT NOT NULL,
        base_period TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(contract_id) REFERENCES contracts(id)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS approvals(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        module TEXT NOT NULL,
        ref_id INTEGER NOT NULL,
        status TEXT NOT NULL,
        user_id INTEGER,
        username TEXT DEFAULT '',
        comment TEXT DEFAULT '',
        created_at TEXT NOT NULL
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS audit_log(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        module TEXT NOT NULL,
        ref_id INTEGER,
        action TEXT NOT NULL,
        user_id INTEGER,
        username TEXT DEFAULT '',
        detail TEXT DEFAULT '',
        created_at TEXT NOT NULL
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS subcontracts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        project_id INTEGER NOT NULL,
        contract_id INTEGER NOT NULL,
        vendor_name TEXT NOT NULL,
        contract_amount REAL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TEXT NOT NULL,
        FOREIGN KEY(project_id) REFERENCES projects(id),
        FOREIGN KEY(contract_id) REFERENCES contracts(id)
    );""")

    # -----------------
    # Notlar & Hatırlatmalar
    # -----------------
    c.execute("""
    CREATE TABLE IF NOT EXISTS notes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL DEFAULT 1,
        owner_user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        body TEXT DEFAULT '',
        category TEXT DEFAULT '',
        priority TEXT DEFAULT 'normal',
        pinned INTEGER NOT NULL DEFAULT 0,
        scope TEXT NOT NULL DEFAULT 'personal',
        status TEXT NOT NULL DEFAULT 'active',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS note_tags(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        note_id INTEGER NOT NULL,
        tag TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(note_id) REFERENCES notes(id) ON DELETE CASCADE
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS note_attachments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        note_id INTEGER NOT NULL,
        filename TEXT NOT NULL,
        stored_name TEXT NOT NULL,
        size_bytes INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(note_id) REFERENCES notes(id) ON DELETE CASCADE
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS reminders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL DEFAULT 1,
        owner_user_id INTEGER NOT NULL,
        assignee_user_id INTEGER,
        title TEXT NOT NULL,
        body TEXT DEFAULT '',
        due_at TEXT NOT NULL,
        priority TEXT DEFAULT 'normal',
        status TEXT NOT NULL DEFAULT 'scheduled',
        series_id INTEGER,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS reminder_recurrence(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reminder_id INTEGER NOT NULL UNIQUE,
        frequency TEXT NOT NULL,
        interval INTEGER NOT NULL DEFAULT 1,
        until TEXT DEFAULT '',
        byweekday TEXT DEFAULT '',
        bymonthday TEXT DEFAULT '',
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(reminder_id) REFERENCES reminders(id) ON DELETE CASCADE
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS reminder_links(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reminder_id INTEGER NOT NULL,
        linked_type TEXT NOT NULL,
        linked_id TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(reminder_id) REFERENCES reminders(id) ON DELETE CASCADE
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS audit_log(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL DEFAULT 1,
        user_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        entity TEXT NOT NULL,
        entity_id INTEGER NOT NULL,
        detail TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );""")

    # -----------------
    # WMS / Stok Çekirdek
    # -----------------
    c.execute("""
    CREATE TABLE IF NOT EXISTS periods(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        branch_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        is_locked INTEGER NOT NULL DEFAULT 0,
        locked_by INTEGER,
        locked_at TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS warehouse_permissions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        company_id INTEGER NOT NULL,
        branch_id INTEGER NOT NULL,
        warehouse_id INTEGER NOT NULL,
        can_view INTEGER NOT NULL DEFAULT 1,
        can_post INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS doc_locks(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        branch_id INTEGER NOT NULL,
        doc_type TEXT NOT NULL,
        doc_no TEXT NOT NULL,
        locked_by INTEGER,
        locked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        reason TEXT DEFAULT '',
        is_active INTEGER NOT NULL DEFAULT 1
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS categories(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        parent_id INTEGER,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS brands(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS variants(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS uoms(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        code TEXT NOT NULL,
        name TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(company_id, code)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        item_code TEXT NOT NULL,
        name TEXT NOT NULL,
        category_id INTEGER,
        brand_id INTEGER,
        variant_id INTEGER,
        base_uom_id INTEGER NOT NULL,
        track_lot INTEGER NOT NULL DEFAULT 0,
        track_serial INTEGER NOT NULL DEFAULT 0,
        negative_stock_policy TEXT NOT NULL DEFAULT 'forbid',
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(company_id, item_code)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS item_barcodes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER NOT NULL,
        barcode TEXT NOT NULL,
        is_primary INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(barcode),
        FOREIGN KEY(item_id) REFERENCES items(id)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS item_uoms(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER NOT NULL,
        uom_id INTEGER NOT NULL,
        is_base INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(item_id, uom_id),
        FOREIGN KEY(item_id) REFERENCES items(id)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS uom_conversions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER NOT NULL,
        from_uom_id INTEGER NOT NULL,
        to_uom_id INTEGER NOT NULL,
        factor REAL NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(item_id, from_uom_id, to_uom_id),
        FOREIGN KEY(item_id) REFERENCES items(id)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS warehouses(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        branch_id INTEGER NOT NULL,
        code TEXT NOT NULL,
        name TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(company_id, branch_id, code)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS warehouse_locations(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        branch_id INTEGER NOT NULL,
        warehouse_id INTEGER NOT NULL,
        parent_id INTEGER,
        name TEXT NOT NULL,
        location_type TEXT NOT NULL DEFAULT 'STORAGE',
        capacity_qty REAL,
        capacity_weight REAL,
        capacity_volume REAL,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(warehouse_id) REFERENCES warehouses(id)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS customers(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        branch_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'ACTIVE',
        is_consignment INTEGER NOT NULL DEFAULT 0,
        customer_warehouse TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS suppliers(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        branch_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'ACTIVE',
        is_consignment INTEGER NOT NULL DEFAULT 0,
        supplier_warehouse TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS lots(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        item_id INTEGER NOT NULL,
        lot_no TEXT NOT NULL,
        expiry_date TEXT DEFAULT '',
        manufacture_date TEXT DEFAULT '',
        status TEXT NOT NULL DEFAULT 'ACTIVE',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(company_id, item_id, lot_no),
        FOREIGN KEY(item_id) REFERENCES items(id)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS serials(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        item_id INTEGER NOT NULL,
        serial_no TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'ACTIVE',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(serial_no),
        FOREIGN KEY(item_id) REFERENCES items(id)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS stock_ledger(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        branch_id INTEGER NOT NULL,
        warehouse_id INTEGER NOT NULL,
        location_id INTEGER,
        item_id INTEGER NOT NULL,
        lot_id INTEGER,
        serial_id INTEGER,
        doc_id INTEGER,
        doc_line_id INTEGER,
        txn_date TEXT NOT NULL,
        qty REAL NOT NULL,
        direction TEXT NOT NULL,
        cost REAL NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS stock_balance(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        branch_id INTEGER NOT NULL,
        warehouse_id INTEGER NOT NULL,
        location_id INTEGER NOT NULL,
        item_id INTEGER NOT NULL,
        qty_on_hand REAL NOT NULL DEFAULT 0,
        qty_reserved REAL NOT NULL DEFAULT 0,
        qty_blocked REAL NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(company_id, branch_id, warehouse_id, location_id, item_id)
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS stock_reservations(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        branch_id INTEGER NOT NULL,
        warehouse_id INTEGER NOT NULL,
        location_id INTEGER NOT NULL,
        item_id INTEGER NOT NULL,
        qty REAL NOT NULL,
        ref_doc_id INTEGER,
        status TEXT NOT NULL DEFAULT 'ACTIVE',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS stock_blocks(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        branch_id INTEGER NOT NULL,
        warehouse_id INTEGER NOT NULL,
        location_id INTEGER NOT NULL,
        item_id INTEGER NOT NULL,
        qty REAL NOT NULL,
        reason TEXT DEFAULT '',
        status TEXT NOT NULL DEFAULT 'ACTIVE',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS consignments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        branch_id INTEGER NOT NULL,
        warehouse_id INTEGER NOT NULL,
        item_id INTEGER NOT NULL,
        qty REAL NOT NULL DEFAULT 0,
        owner_type TEXT NOT NULL DEFAULT 'CUSTOMER',
        owner_id INTEGER,
        status TEXT NOT NULL DEFAULT 'ACTIVE',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS stock_ledger_archive(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        branch_id INTEGER NOT NULL,
        warehouse_id INTEGER NOT NULL,
        location_id INTEGER,
        item_id INTEGER NOT NULL,
        lot_id INTEGER,
        serial_id INTEGER,
        doc_id INTEGER,
        doc_line_id INTEGER,
        txn_date TEXT NOT NULL,
        qty REAL NOT NULL,
        direction TEXT NOT NULL,
        cost REAL NOT NULL DEFAULT 0,
        archived_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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

    # -----------------
    # Hakediş Hazırlama Merkezi tabloları
    # -----------------
    try:
        conn.execute(
            """
        CREATE TABLE IF NOT EXISTS hakedis_project(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            idare TEXT DEFAULT '',
            yuklenici TEXT DEFAULT '',
            isin_adi TEXT DEFAULT '',
            sozlesme_bedeli REAL DEFAULT 0,
            baslangic TEXT DEFAULT '',
            bitis TEXT DEFAULT '',
            sure_gun INTEGER DEFAULT 0,
            artis_eksilis REAL DEFAULT 0,
            avans REAL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );"""
        )
        conn.execute(
            """
        CREATE TABLE IF NOT EXISTS hakedis_position(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            kod TEXT DEFAULT '',
            aciklama TEXT DEFAULT '',
            birim TEXT DEFAULT '',
            sozlesme_miktar REAL DEFAULT 0,
            birim_fiyat REAL DEFAULT 0,
            FOREIGN KEY(project_id) REFERENCES hakedis_project(id) ON DELETE CASCADE
        );"""
        )
        conn.execute(
            """
        CREATE TABLE IF NOT EXISTS hakedis_period(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            hakedis_no TEXT DEFAULT '',
            ay INTEGER DEFAULT 1,
            yil INTEGER DEFAULT 2000,
            tarih_bas TEXT DEFAULT '',
            tarih_bit TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'Taslak',
            FOREIGN KEY(project_id) REFERENCES hakedis_project(id) ON DELETE CASCADE
        );"""
        )
        conn.execute(
            """
        CREATE TABLE IF NOT EXISTS hakedis_measurement(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            period_id INTEGER NOT NULL,
            position_id INTEGER NOT NULL,
            onceki_miktar REAL DEFAULT 0,
            bu_donem_miktar REAL DEFAULT 0,
            kumulatif_miktar REAL DEFAULT 0,
            UNIQUE(period_id, position_id),
            FOREIGN KEY(period_id) REFERENCES hakedis_period(id) ON DELETE CASCADE,
            FOREIGN KEY(position_id) REFERENCES hakedis_position(id) ON DELETE CASCADE
        );"""
        )
        conn.execute(
            """
        CREATE TABLE IF NOT EXISTS hakedis_attachment(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            period_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            stored_name TEXT NOT NULL,
            size_bytes INTEGER DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(period_id) REFERENCES hakedis_period(id) ON DELETE CASCADE
        );"""
        )
        conn.execute(
            """
        CREATE TABLE IF NOT EXISTS hakedis_deduction(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            period_id INTEGER NOT NULL,
            ad TEXT NOT NULL,
            tip TEXT NOT NULL DEFAULT 'tutar',
            deger REAL DEFAULT 0,
            hesaplanan_tutar REAL DEFAULT 0,
            FOREIGN KEY(period_id) REFERENCES hakedis_period(id) ON DELETE CASCADE
        );"""
        )
        conn.execute(
            """
        CREATE TABLE IF NOT EXISTS hakedis_indices_cache(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            dataset_key TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            fetched_at TEXT NOT NULL,
            UNIQUE(source, dataset_key)
        );"""
        )
        conn.execute(
            """
        CREATE TABLE IF NOT EXISTS hakedis_index_selection(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            dataset_key TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 1,
            UNIQUE(project_id, dataset_key),
            FOREIGN KEY(project_id) REFERENCES hakedis_project(id) ON DELETE CASCADE
        );"""
        )
        conn.execute(
            """
        CREATE TABLE IF NOT EXISTS hakedis_audit_log(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            user_id INTEGER,
            action TEXT NOT NULL,
            entity TEXT NOT NULL,
            entity_id INTEGER,
            detail TEXT DEFAULT ''
        );"""
        )
        conn.execute(
            """
        CREATE TABLE IF NOT EXISTS hakedis_user_roles(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            UNIQUE(project_id, user_id),
            FOREIGN KEY(project_id) REFERENCES hakedis_project(id) ON DELETE CASCADE
        );"""
        )
        conn.commit()
    except Exception as e:
        if log_fn:
            try:
                log_fn("Schema Migration Error", f"hakedis tables: {e}")
            except Exception:
                pass

    # satın alma tabloları (eski DB'ler için)
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS satin_alma_siparis(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                siparis_no TEXT NOT NULL UNIQUE,
                tedarikci_id INTEGER NOT NULL,
                tarih TEXT NOT NULL,
                teslim_tarihi TEXT DEFAULT '',
                durum TEXT NOT NULL DEFAULT 'oluşturuldu',
                para TEXT DEFAULT 'TL',
                kur REAL DEFAULT 1,
                iskonto_oran REAL DEFAULT 0,
                depo_id INTEGER,
                notlar TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(tedarikci_id) REFERENCES cariler(id),
                FOREIGN KEY(depo_id) REFERENCES stok_lokasyon(id)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS satin_alma_siparis_kalem(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                siparis_id INTEGER NOT NULL,
                urun_id INTEGER,
                urun_ad TEXT DEFAULT '',
                miktar REAL NOT NULL DEFAULT 0,
                birim TEXT DEFAULT 'Adet',
                birim_fiyat REAL NOT NULL DEFAULT 0,
                iskonto_oran REAL DEFAULT 0,
                iskonto_tutar REAL DEFAULT 0,
                toplam REAL DEFAULT 0,
                FOREIGN KEY(siparis_id) REFERENCES satin_alma_siparis(id) ON DELETE CASCADE,
                FOREIGN KEY(urun_id) REFERENCES stok_urun(id)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS satin_alma_teslim(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                siparis_id INTEGER NOT NULL,
                tarih TEXT NOT NULL,
                depo_id INTEGER,
                fatura_id INTEGER,
                durum TEXT DEFAULT 'kısmi teslim alındı',
                notlar TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(siparis_id) REFERENCES satin_alma_siparis(id) ON DELETE CASCADE,
                FOREIGN KEY(depo_id) REFERENCES stok_lokasyon(id),
                FOREIGN KEY(fatura_id) REFERENCES fatura(id)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS satin_alma_teslim_kalem(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teslim_id INTEGER NOT NULL,
                urun_id INTEGER,
                urun_ad TEXT DEFAULT '',
                miktar REAL NOT NULL DEFAULT 0,
                birim TEXT DEFAULT 'Adet',
                birim_fiyat REAL NOT NULL DEFAULT 0,
                toplam REAL DEFAULT 0,
                FOREIGN KEY(teslim_id) REFERENCES satin_alma_teslim(id) ON DELETE CASCADE,
                FOREIGN KEY(urun_id) REFERENCES stok_urun(id)
            );"""
        )
        conn.commit()
    except Exception as e:
        if log_fn:
            try:
                log_fn("Schema Migration Error", f"satin_alma: {e}")
            except Exception:
                pass

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

    # Notlar & Hatırlatmalar tabloları
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS notes(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL DEFAULT 1,
                owner_user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                body TEXT DEFAULT '',
                category TEXT DEFAULT '',
                priority TEXT DEFAULT 'normal',
                pinned INTEGER NOT NULL DEFAULT 0,
                scope TEXT NOT NULL DEFAULT 'personal',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS note_tags(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id INTEGER NOT NULL,
                tag TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS note_attachments(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                stored_name TEXT NOT NULL,
                size_bytes INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS reminders(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL DEFAULT 1,
                owner_user_id INTEGER NOT NULL,
                assignee_user_id INTEGER,
                title TEXT NOT NULL,
                body TEXT DEFAULT '',
                due_at TEXT NOT NULL,
                priority TEXT DEFAULT 'normal',
                status TEXT NOT NULL DEFAULT 'scheduled',
                series_id INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS reminder_recurrence(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reminder_id INTEGER NOT NULL UNIQUE,
                frequency TEXT NOT NULL,
                interval INTEGER NOT NULL DEFAULT 1,
                until TEXT DEFAULT '',
                byweekday TEXT DEFAULT '',
                bymonthday TEXT DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS reminder_links(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reminder_id INTEGER NOT NULL,
                linked_type TEXT NOT NULL,
                linked_id TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS audit_log(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL DEFAULT 1,
                user_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                entity TEXT NOT NULL,
                entity_id INTEGER NOT NULL,
                detail TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );"""
        )
        conn.commit()
    except Exception as e:
        if log_fn:
            try:
                log_fn("Schema Migration Error", f"notes/reminders: {e}")
            except Exception:
                pass

    # Maaş ödeme tablosu yeni kolonlar (banka eşleştirme için)
    _ensure_column(conn, "maas_odeme", "banka_hareket_id", "INTEGER", log_fn)
    _ensure_column(conn, "maas_odeme", "banka_match_score", "REAL", log_fn)
    _ensure_column(conn, "maas_odeme", "banka_match_note", "TEXT DEFAULT ''", log_fn)

    # Maaş çalışan: meslek alanı
    _ensure_column(conn, "maas_calisan", "meslek_id", "INTEGER", log_fn)

    # -----------------
    # Doküman & Süreç Yönetimi (DMS)
    # -----------------
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS documents(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                doc_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                current_version_id INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS document_tags(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                document_id INTEGER NOT NULL,
                tag TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS document_links(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                document_id INTEGER NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS document_versions(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                document_id INTEGER NOT NULL,
                version_no INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                original_name TEXT NOT NULL,
                mime TEXT NOT NULL,
                size INTEGER NOT NULL,
                sha256 TEXT NOT NULL,
                change_note TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'DRAFT',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS workflow_templates(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS workflow_steps(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                template_id INTEGER NOT NULL,
                step_no INTEGER NOT NULL,
                name TEXT NOT NULL,
                approver_role TEXT NOT NULL,
                approver_user_id INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS workflow_instances(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                template_id INTEGER NOT NULL,
                document_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'NOT_STARTED',
                current_step_no INTEGER,
                started_by INTEGER,
                started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS workflow_actions(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                instance_id INTEGER NOT NULL,
                step_no INTEGER NOT NULL,
                action TEXT NOT NULL,
                comment TEXT DEFAULT '',
                actor_id INTEGER,
                acted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS tasks(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                document_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                assignee_id INTEGER NOT NULL,
                due_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'OPEN',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS reminders(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                document_id INTEGER NOT NULL,
                task_id INTEGER,
                remind_at TEXT NOT NULL,
                snooze_until TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'PENDING',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS audit_log(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                actor_id INTEGER,
                details TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );"""
        )
        conn.commit()
    except Exception as e:
        if log_fn:
            try:
                log_fn("Schema Migration Error", f"dms tables: {e}")
            except Exception:
                pass

    # Entegrasyonlar - tablolar
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS event_outbox(
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                idempotency_key TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                processed_at TEXT,
                UNIQUE(company_id, idempotency_key)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS jobs(
                job_id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                job_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                attempts INTEGER NOT NULL DEFAULT 0,
                next_retry_at TEXT,
                last_error TEXT DEFAULT '',
                idempotency_key TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT,
                UNIQUE(company_id, idempotency_key)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS dead_letter_jobs(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                job_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                last_error TEXT DEFAULT '',
                idempotency_key TEXT,
                failed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS integration_settings(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                setting_key TEXT NOT NULL,
                value_encrypted TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(company_id, setting_key)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS notification_templates(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                channel TEXT NOT NULL,
                subject TEXT DEFAULT '',
                body TEXT DEFAULT '',
                variables_json TEXT DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS notification_rules(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                channel TEXT NOT NULL,
                recipient TEXT NOT NULL,
                template_id INTEGER NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY(template_id) REFERENCES notification_templates(id)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS notification_outbox(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                channel TEXT NOT NULL,
                recipient TEXT NOT NULL,
                subject TEXT DEFAULT '',
                body TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                attempts INTEGER NOT NULL DEFAULT 0,
                idempotency_key TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS delivery_log(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                notification_id INTEGER NOT NULL,
                provider TEXT NOT NULL,
                status TEXT NOT NULL,
                detail TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(notification_id) REFERENCES notification_outbox(id)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS contact_consents(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                contact TEXT NOT NULL,
                channel TEXT NOT NULL,
                opt_in INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(company_id, contact, channel)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS external_mappings(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                system TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                internal_id INTEGER NOT NULL,
                external_id TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(company_id, system, entity_type, internal_id)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS export_jobs(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                job_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS export_items(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                entity_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                FOREIGN KEY(job_id) REFERENCES export_jobs(id) ON DELETE CASCADE
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS import_jobs(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                job_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS import_items(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                entity_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                error TEXT DEFAULT '',
                FOREIGN KEY(job_id) REFERENCES import_jobs(id) ON DELETE CASCADE
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS bank_statements(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                source_name TEXT NOT NULL,
                period_start TEXT NOT NULL,
                period_end TEXT NOT NULL,
                imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS bank_transactions(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                statement_id INTEGER NOT NULL,
                transaction_date TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT DEFAULT '',
                unique_hash TEXT NOT NULL,
                matched INTEGER NOT NULL DEFAULT 0,
                matched_ref TEXT DEFAULT '',
                matched_at TEXT,
                FOREIGN KEY(statement_id) REFERENCES bank_statements(id),
                UNIQUE(company_id, unique_hash)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS api_tokens(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                token_hash TEXT NOT NULL,
                scopes_json TEXT DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_used_at TEXT,
                UNIQUE(company_id, token_hash)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS webhook_subscriptions(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                url TEXT NOT NULL,
                secret TEXT NOT NULL,
                events_json TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS webhook_deliveries(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                subscription_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                attempts INTEGER NOT NULL DEFAULT 0,
                next_retry_at TEXT,
                last_error TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT,
                FOREIGN KEY(subscription_id) REFERENCES webhook_subscriptions(id)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS idempotency_keys(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                idempotency_key TEXT NOT NULL,
                request_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(company_id, idempotency_key)
            );"""
        )
        conn.commit()
    except Exception as e:
        if log_fn:
            try:
                log_fn("Schema Migration Error", f"integrations tables: {e}")
            except Exception:
                pass

    _ensure_index(conn, "idx_event_outbox_company_processed", "event_outbox", "company_id, processed_at", log_fn)
    _ensure_index(conn, "idx_jobs_company_status", "jobs", "company_id, status, next_retry_at", log_fn)
    _ensure_index(conn, "idx_jobs_idem", "jobs", "company_id, idempotency_key", log_fn)
    _ensure_index(conn, "idx_outbox_idem", "event_outbox", "company_id, idempotency_key", log_fn)
    try:
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_idem_unique ON jobs(company_id, idempotency_key)")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_outbox_idem_unique ON event_outbox(company_id, idempotency_key)")
        conn.commit()
    except Exception:
        pass
    _ensure_index(conn, "idx_notification_rules_event", "notification_rules", "company_id, event_type", log_fn)
    _ensure_index(conn, "idx_bank_transactions_company", "bank_transactions", "company_id, matched", log_fn)

    _ensure_index(conn, "idx_documents_status", "documents", "status, updated_at", log_fn)
    _ensure_index(conn, "idx_documents_company", "documents", "company_id", log_fn)
    _ensure_index(conn, "idx_document_tags_tag", "document_tags", "tag", log_fn)
    _ensure_index(conn, "idx_document_links_entity", "document_links", "entity_type, entity_id", log_fn)
    _ensure_index(conn, "idx_document_versions_doc", "document_versions", "document_id, version_no", log_fn)
    _ensure_index(conn, "idx_workflow_instances_status", "workflow_instances", "status, updated_at", log_fn)
    _ensure_index(conn, "idx_tasks_due", "tasks", "due_at, status", log_fn)
    _ensure_index(conn, "idx_reminders_due", "reminders", "remind_at, status", log_fn)
    _ensure_index(conn, "idx_audit_entity", "audit_log", "entity_type, entity_id", log_fn)
    _ensure_index(conn, "idx_audit_module", "audit_log", "module, ref_id", log_fn)
    _ensure_index(conn, "idx_trade_docs_company", "trade_docs", "company_id, doc_type, status", log_fn)
    _ensure_index(conn, "idx_trade_doc_lines_doc", "trade_doc_lines", "doc_id", log_fn)
    _ensure_index(conn, "idx_trade_stock_moves_company", "trade_stock_moves", "company_id, item", log_fn)
    _ensure_index(conn, "idx_stock_moves_doc", "stock_moves", "doc_id", log_fn)
    _ensure_index(conn, "idx_trade_payments_doc", "trade_payments", "doc_id", log_fn)
    _ensure_index(conn, "idx_trade_orders_company", "trade_orders", "company_id, order_type, status", log_fn)
    _ensure_index(conn, "idx_trade_order_lines_order", "trade_order_lines", "order_id", log_fn)
    _ensure_index(conn, "idx_trade_user_roles_company", "trade_user_roles", "company_id, user_id", log_fn)
    _ensure_index(conn, "idx_stock_ledger_core", "stock_ledger", "company_id, item_id, warehouse_id, txn_date", log_fn)
    _ensure_index(conn, "idx_stock_balance_core", "stock_balance", "company_id, item_id, warehouse_id, location_id", log_fn)
    _ensure_index(conn, "idx_docs_company_docno", "docs", "company_id, doc_no", log_fn)
    _ensure_index(conn, "idx_docs_company_date_status", "docs", "company_id, doc_date, status", log_fn)
    _ensure_index(conn, "idx_item_barcodes_code", "item_barcodes", "barcode", log_fn)
    _ensure_index(conn, "idx_lots_lot_no", "lots", "lot_no", log_fn)
    _ensure_index(conn, "idx_serials_serial_no", "serials", "serial_no", log_fn)
    _ensure_index(conn, "idx_warehouse_locations_tree", "warehouse_locations", "company_id, warehouse_id, parent_id", log_fn)

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

    # audit_log (eski DB'ler için kolon garantisi)
    _ensure_column(conn, "audit_log", "module", "TEXT DEFAULT ''", log_fn)
    _ensure_column(conn, "audit_log", "ref_id", "INTEGER", log_fn)
    _ensure_column(conn, "audit_log", "user_id", "INTEGER", log_fn)
    _ensure_column(conn, "audit_log", "username", "TEXT DEFAULT ''", log_fn)
    _ensure_column(conn, "audit_log", "entity", "TEXT DEFAULT ''", log_fn)
    _ensure_column(conn, "audit_log", "message", "TEXT DEFAULT ''", log_fn)
    _ensure_column(conn, "audit_log", "detail", "TEXT DEFAULT ''", log_fn)

    # reminders (eski DB'ler için kolon garantisi)
    _ensure_column(conn, "reminders", "owner_user_id", "INTEGER", log_fn)
    _ensure_column(conn, "reminders", "assignee_user_id", "INTEGER", log_fn)
    _ensure_column(conn, "reminders", "title", "TEXT DEFAULT ''", log_fn)
    _ensure_column(conn, "reminders", "body", "TEXT DEFAULT ''", log_fn)
    _ensure_column(conn, "reminders", "due_at", "TEXT DEFAULT ''", log_fn)
    _ensure_column(conn, "reminders", "priority", "TEXT DEFAULT 'normal'", log_fn)
    _ensure_column(conn, "reminders", "status", "TEXT DEFAULT 'scheduled'", log_fn)
    _ensure_column(conn, "reminders", "series_id", "INTEGER", log_fn)
    _ensure_column(conn, "reminders", "updated_at", "TEXT DEFAULT CURRENT_TIMESTAMP", log_fn)
    _ensure_column(conn, "reminders", "document_id", "INTEGER", log_fn)
    _ensure_column(conn, "reminders", "task_id", "INTEGER", log_fn)
    _ensure_column(conn, "reminders", "remind_at", "TEXT DEFAULT ''", log_fn)
    _ensure_column(conn, "reminders", "snooze_until", "TEXT DEFAULT ''", log_fn)

    # invoice docs
    _ensure_column(conn, "docs", "voided_at", "TEXT", log_fn)
    _ensure_column(conn, "docs", "reversed_doc_id", "INTEGER", log_fn)
    _ensure_column(conn, "docs", "payment_status", "TEXT NOT NULL DEFAULT 'UNPAID'", log_fn)
    _ensure_column(conn, "docs", "module", "TEXT DEFAULT ''", log_fn)
    _ensure_column(conn, "docs", "branch_id", "INTEGER NOT NULL DEFAULT 1", log_fn)
    _ensure_column(conn, "docs", "tolerance_qty", "REAL DEFAULT 0", log_fn)
    _ensure_column(conn, "docs", "tolerance_pct", "REAL DEFAULT 0", log_fn)
    _ensure_column(conn, "doc_lines", "source_warehouse_id", "INTEGER", log_fn)
    _ensure_column(conn, "doc_lines", "target_warehouse_id", "INTEGER", log_fn)
    _ensure_column(conn, "doc_lines", "source_location_id", "INTEGER", log_fn)
    _ensure_column(conn, "doc_lines", "target_location_id", "INTEGER", log_fn)
    _ensure_column(conn, "doc_lines", "lot_id", "INTEGER", log_fn)
    _ensure_column(conn, "doc_lines", "serial_id", "INTEGER", log_fn)
    _ensure_column(conn, "doc_lines", "line_status", "TEXT DEFAULT ''", log_fn)
    _ensure_column(conn, "doc_lines", "line_notes", "TEXT DEFAULT ''", log_fn)

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
    # Stok Yönetimi (eski DB'ler için)
    # -----------------
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS stok_urun(
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
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS stok_lokasyon(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ad TEXT NOT NULL UNIQUE,
                aciklama TEXT DEFAULT '',
                aktif INTEGER NOT NULL DEFAULT 1
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS stok_parti(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                urun_id INTEGER NOT NULL,
                parti_no TEXT NOT NULL,
                skt TEXT DEFAULT '',
                uretim_tarih TEXT DEFAULT '',
                aciklama TEXT DEFAULT '',
                UNIQUE(urun_id, parti_no)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS stok_hareket(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarih TEXT NOT NULL,
                urun_id INTEGER NOT NULL,
                tip TEXT NOT NULL,
                miktar REAL NOT NULL DEFAULT 0,
                birim TEXT DEFAULT 'Adet',
                kaynak_lokasyon_id INTEGER,
                hedef_lokasyon_id INTEGER,
                parti_id INTEGER,
                referans_tipi TEXT DEFAULT '',
                referans_id INTEGER,
                maliyet REAL DEFAULT 0,
                aciklama TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );"""
        )
        conn.commit()
    except Exception as e:
        if log_fn:
            try:
                log_fn("Schema Migration Error", f"stok tables: {e}")
            except Exception:
                pass

    # Hakediş modülü tabloları (eski DB'ler için)
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS projects(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                code TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active',
                notes TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS sites(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                location TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS contracts(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                site_id INTEGER,
                contract_no TEXT NOT NULL,
                contract_type TEXT NOT NULL DEFAULT 'birim_fiyat',
                currency TEXT DEFAULT 'TL',
                advance_rate REAL DEFAULT 0,
                retention_rate REAL DEFAULT 0,
                advance_deduction_rate REAL DEFAULT 0,
                penalty_rate REAL DEFAULT 0,
                price_diff_enabled INTEGER NOT NULL DEFAULT 0,
                formula_template TEXT DEFAULT '',
                formula_params TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id),
                FOREIGN KEY(site_id) REFERENCES sites(id)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS boq_items(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                contract_id INTEGER NOT NULL,
                poz_code TEXT NOT NULL,
                name TEXT NOT NULL,
                unit TEXT DEFAULT '',
                qty_contract REAL DEFAULT 0,
                unit_price REAL DEFAULT 0,
                group_name TEXT DEFAULT '',
                mahal TEXT DEFAULT '',
                budget REAL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id),
                FOREIGN KEY(contract_id) REFERENCES contracts(id)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS boq_revisions(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                boq_item_id INTEGER NOT NULL,
                rev_no INTEGER NOT NULL,
                note TEXT DEFAULT '',
                snapshot_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(boq_item_id) REFERENCES boq_items(id)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS attachments(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                module TEXT NOT NULL,
                filename TEXT NOT NULL,
                stored_name TEXT NOT NULL,
                stored_path TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS pay_estimates(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                contract_id INTEGER NOT NULL,
                period_no INTEGER NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Taslak',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id),
                FOREIGN KEY(contract_id) REFERENCES contracts(id)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS measurements(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                contract_id INTEGER NOT NULL,
                period_id INTEGER NOT NULL,
                boq_item_id INTEGER NOT NULL,
                qty REAL NOT NULL,
                tarih TEXT NOT NULL,
                mahal TEXT DEFAULT '',
                note TEXT DEFAULT '',
                attachment_id INTEGER,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                FOREIGN KEY(period_id) REFERENCES pay_estimates(id),
                FOREIGN KEY(boq_item_id) REFERENCES boq_items(id),
                FOREIGN KEY(attachment_id) REFERENCES attachments(id)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS pay_estimate_lines(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                pay_estimate_id INTEGER NOT NULL,
                boq_item_id INTEGER NOT NULL,
                prev_qty REAL DEFAULT 0,
                current_qty REAL DEFAULT 0,
                cum_qty REAL DEFAULT 0,
                unit_price REAL DEFAULT 0,
                prev_amount REAL DEFAULT 0,
                current_amount REAL DEFAULT 0,
                cum_amount REAL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                FOREIGN KEY(pay_estimate_id) REFERENCES pay_estimates(id),
                FOREIGN KEY(boq_item_id) REFERENCES boq_items(id)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS deductions(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                pay_estimate_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                rate REAL DEFAULT 0,
                amount REAL DEFAULT 0,
                note TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                FOREIGN KEY(pay_estimate_id) REFERENCES pay_estimates(id)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS indices_cache(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                provider TEXT NOT NULL,
                index_code TEXT NOT NULL,
                index_value REAL NOT NULL,
                period TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                raw_json TEXT DEFAULT ''
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS price_diff_rules(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                contract_id INTEGER NOT NULL,
                formula_name TEXT NOT NULL,
                formula_params TEXT NOT NULL,
                base_period TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(contract_id) REFERENCES contracts(id)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS approvals(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                module TEXT NOT NULL,
                ref_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                user_id INTEGER,
                username TEXT DEFAULT '',
                comment TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS audit_log(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                module TEXT NOT NULL,
                ref_id INTEGER,
                action TEXT NOT NULL,
                user_id INTEGER,
                username TEXT DEFAULT '',
                detail TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS subcontracts(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                contract_id INTEGER NOT NULL,
                vendor_name TEXT NOT NULL,
                contract_amount REAL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id),
                FOREIGN KEY(contract_id) REFERENCES contracts(id)
            );"""
        )
        conn.commit()
    except Exception as e:
        if log_fn:
            try:
                log_fn("Schema Migration Error", f"hakedis tables: {e}")
            except Exception:
                pass

    # Teklif & Sipariş (Quote-Order) tabloları
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS series_counters(
                name TEXT PRIMARY KEY,
                prefix TEXT DEFAULT '',
                last_no INTEGER NOT NULL DEFAULT 0,
                padding INTEGER NOT NULL DEFAULT 6,
                format TEXT DEFAULT '{prefix}{no_pad}'
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS quotes(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quote_no TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'DRAFT',
                quote_group_id INTEGER,
                cari_id INTEGER,
                cari_ad TEXT DEFAULT '',
                valid_until TEXT DEFAULT '',
                para TEXT DEFAULT 'TL',
                kur REAL DEFAULT 1,
                ara_toplam REAL DEFAULT 0,
                iskonto_toplam REAL DEFAULT 0,
                genel_iskonto_oran REAL DEFAULT 0,
                genel_iskonto_tutar REAL DEFAULT 0,
                kdv_toplam REAL DEFAULT 0,
                genel_toplam REAL DEFAULT 0,
                notlar TEXT DEFAULT '',
                locked INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(quote_no, version)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS quote_lines(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quote_id INTEGER NOT NULL,
                line_no INTEGER NOT NULL DEFAULT 1,
                urun TEXT DEFAULT '',
                aciklama TEXT DEFAULT '',
                miktar REAL DEFAULT 0,
                birim TEXT DEFAULT 'Adet',
                birim_fiyat REAL DEFAULT 0,
                iskonto_oran REAL DEFAULT 0,
                iskonto_tutar REAL DEFAULT 0,
                kdv_oran REAL DEFAULT 20,
                kdv_tutar REAL DEFAULT 0,
                toplam REAL DEFAULT 0,
                FOREIGN KEY(quote_id) REFERENCES quotes(id) ON DELETE CASCADE
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS sales_orders(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_no TEXT NOT NULL UNIQUE,
                quote_id INTEGER,
                status TEXT NOT NULL DEFAULT 'DRAFT',
                cari_id INTEGER,
                cari_ad TEXT DEFAULT '',
                para TEXT DEFAULT 'TL',
                kur REAL DEFAULT 1,
                ara_toplam REAL DEFAULT 0,
                iskonto_toplam REAL DEFAULT 0,
                kdv_toplam REAL DEFAULT 0,
                genel_toplam REAL DEFAULT 0,
                notlar TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(quote_id) REFERENCES quotes(id),
                FOREIGN KEY(cari_id) REFERENCES cariler(id)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS sales_order_lines(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                line_no INTEGER NOT NULL DEFAULT 1,
                urun TEXT DEFAULT '',
                aciklama TEXT DEFAULT '',
                miktar_siparis REAL DEFAULT 0,
                miktar_sevk REAL DEFAULT 0,
                miktar_fatura REAL DEFAULT 0,
                birim TEXT DEFAULT 'Adet',
                birim_fiyat REAL DEFAULT 0,
                iskonto_oran REAL DEFAULT 0,
                iskonto_tutar REAL DEFAULT 0,
                kdv_oran REAL DEFAULT 20,
                kdv_tutar REAL DEFAULT 0,
                toplam REAL DEFAULT 0,
                FOREIGN KEY(order_id) REFERENCES sales_orders(id) ON DELETE CASCADE
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS audit_log(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                entity_type TEXT NOT NULL,
                entity_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                user_id INTEGER,
                username TEXT DEFAULT '',
                role TEXT DEFAULT '',
                note TEXT DEFAULT ''
            );"""
        )
        conn.commit()
    except Exception as e:
        if log_fn:
            try:
                log_fn("Schema Migration Error", f"quote_order tables: {e}")
            except Exception:
                pass

    # -----------------
    # WMS / Stok Çekirdek (eski DB'ler için)
    # -----------------
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS periods(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                branch_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                is_locked INTEGER NOT NULL DEFAULT 0,
                locked_by INTEGER,
                locked_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS warehouse_permissions(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                company_id INTEGER NOT NULL,
                branch_id INTEGER NOT NULL,
                warehouse_id INTEGER NOT NULL,
                can_view INTEGER NOT NULL DEFAULT 1,
                can_post INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS doc_locks(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                branch_id INTEGER NOT NULL,
                doc_type TEXT NOT NULL,
                doc_no TEXT NOT NULL,
                locked_by INTEGER,
                locked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                reason TEXT DEFAULT '',
                is_active INTEGER NOT NULL DEFAULT 1
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS categories(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                parent_id INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS brands(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS variants(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS uoms(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                code TEXT NOT NULL,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(company_id, code)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS items(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                item_code TEXT NOT NULL,
                name TEXT NOT NULL,
                category_id INTEGER,
                brand_id INTEGER,
                variant_id INTEGER,
                base_uom_id INTEGER NOT NULL,
                track_lot INTEGER NOT NULL DEFAULT 0,
                track_serial INTEGER NOT NULL DEFAULT 0,
                negative_stock_policy TEXT NOT NULL DEFAULT 'forbid',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(company_id, item_code)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS item_barcodes(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                barcode TEXT NOT NULL,
                is_primary INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(barcode)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS item_uoms(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                uom_id INTEGER NOT NULL,
                is_base INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(item_id, uom_id)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS uom_conversions(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                from_uom_id INTEGER NOT NULL,
                to_uom_id INTEGER NOT NULL,
                factor REAL NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(item_id, from_uom_id, to_uom_id)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS warehouses(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                branch_id INTEGER NOT NULL,
                code TEXT NOT NULL,
                name TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(company_id, branch_id, code)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS warehouse_locations(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                branch_id INTEGER NOT NULL,
                warehouse_id INTEGER NOT NULL,
                parent_id INTEGER,
                name TEXT NOT NULL,
                location_type TEXT NOT NULL DEFAULT 'STORAGE',
                capacity_qty REAL,
                capacity_weight REAL,
                capacity_volume REAL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS customers(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                branch_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                is_consignment INTEGER NOT NULL DEFAULT 0,
                customer_warehouse TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS suppliers(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                branch_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                is_consignment INTEGER NOT NULL DEFAULT 0,
                supplier_warehouse TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS lots(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                lot_no TEXT NOT NULL,
                expiry_date TEXT DEFAULT '',
                manufacture_date TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(company_id, item_id, lot_no)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS serials(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                serial_no TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(serial_no)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS stock_ledger(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                branch_id INTEGER NOT NULL,
                warehouse_id INTEGER NOT NULL,
                location_id INTEGER,
                item_id INTEGER NOT NULL,
                lot_id INTEGER,
                serial_id INTEGER,
                doc_id INTEGER,
                doc_line_id INTEGER,
                txn_date TEXT NOT NULL,
                qty REAL NOT NULL,
                direction TEXT NOT NULL,
                cost REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS stock_balance(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                branch_id INTEGER NOT NULL,
                warehouse_id INTEGER NOT NULL,
                location_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                qty_on_hand REAL NOT NULL DEFAULT 0,
                qty_reserved REAL NOT NULL DEFAULT 0,
                qty_blocked REAL NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(company_id, branch_id, warehouse_id, location_id, item_id)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS stock_reservations(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                branch_id INTEGER NOT NULL,
                warehouse_id INTEGER NOT NULL,
                location_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                qty REAL NOT NULL,
                ref_doc_id INTEGER,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS stock_blocks(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                branch_id INTEGER NOT NULL,
                warehouse_id INTEGER NOT NULL,
                location_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                qty REAL NOT NULL,
                reason TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS consignments(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                branch_id INTEGER NOT NULL,
                warehouse_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                qty REAL NOT NULL DEFAULT 0,
                owner_type TEXT NOT NULL DEFAULT 'CUSTOMER',
                owner_id INTEGER,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS stock_ledger_archive(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                branch_id INTEGER NOT NULL,
                warehouse_id INTEGER NOT NULL,
                location_id INTEGER,
                item_id INTEGER NOT NULL,
                lot_id INTEGER,
                serial_id INTEGER,
                doc_id INTEGER,
                doc_line_id INTEGER,
                txn_date TEXT NOT NULL,
                qty REAL NOT NULL,
                direction TEXT NOT NULL,
                cost REAL NOT NULL DEFAULT 0,
                archived_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );"""
        )
        conn.commit()
    except Exception as e:
        if log_fn:
            try:
                log_fn("Schema Migration Error", f"wms tables: {e}")
            except Exception:
                pass

    # Hakediş modülü tabloları (eski DB'ler için)
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS projects(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                code TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active',
                notes TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS sites(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                location TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS contracts(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                site_id INTEGER,
                contract_no TEXT NOT NULL,
                contract_type TEXT NOT NULL DEFAULT 'birim_fiyat',
                currency TEXT DEFAULT 'TL',
                advance_rate REAL DEFAULT 0,
                retention_rate REAL DEFAULT 0,
                advance_deduction_rate REAL DEFAULT 0,
                penalty_rate REAL DEFAULT 0,
                price_diff_enabled INTEGER NOT NULL DEFAULT 0,
                formula_template TEXT DEFAULT '',
                formula_params TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id),
                FOREIGN KEY(site_id) REFERENCES sites(id)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS boq_items(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                contract_id INTEGER NOT NULL,
                poz_code TEXT NOT NULL,
                name TEXT NOT NULL,
                unit TEXT DEFAULT '',
                qty_contract REAL DEFAULT 0,
                unit_price REAL DEFAULT 0,
                group_name TEXT DEFAULT '',
                mahal TEXT DEFAULT '',
                budget REAL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id),
                FOREIGN KEY(contract_id) REFERENCES contracts(id)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS boq_revisions(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                boq_item_id INTEGER NOT NULL,
                rev_no INTEGER NOT NULL,
                note TEXT DEFAULT '',
                snapshot_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(boq_item_id) REFERENCES boq_items(id)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS attachments(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                module TEXT NOT NULL,
                filename TEXT NOT NULL,
                stored_name TEXT NOT NULL,
                stored_path TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS pay_estimates(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                contract_id INTEGER NOT NULL,
                period_no INTEGER NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Taslak',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id),
                FOREIGN KEY(contract_id) REFERENCES contracts(id)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS measurements(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                contract_id INTEGER NOT NULL,
                period_id INTEGER NOT NULL,
                boq_item_id INTEGER NOT NULL,
                qty REAL NOT NULL,
                tarih TEXT NOT NULL,
                mahal TEXT DEFAULT '',
                note TEXT DEFAULT '',
                attachment_id INTEGER,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                FOREIGN KEY(period_id) REFERENCES pay_estimates(id),
                FOREIGN KEY(boq_item_id) REFERENCES boq_items(id),
                FOREIGN KEY(attachment_id) REFERENCES attachments(id)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS pay_estimate_lines(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                pay_estimate_id INTEGER NOT NULL,
                boq_item_id INTEGER NOT NULL,
                prev_qty REAL DEFAULT 0,
                current_qty REAL DEFAULT 0,
                cum_qty REAL DEFAULT 0,
                unit_price REAL DEFAULT 0,
                prev_amount REAL DEFAULT 0,
                current_amount REAL DEFAULT 0,
                cum_amount REAL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                FOREIGN KEY(pay_estimate_id) REFERENCES pay_estimates(id),
                FOREIGN KEY(boq_item_id) REFERENCES boq_items(id)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS deductions(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                pay_estimate_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                rate REAL DEFAULT 0,
                amount REAL DEFAULT 0,
                note TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                FOREIGN KEY(pay_estimate_id) REFERENCES pay_estimates(id)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS indices_cache(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                provider TEXT NOT NULL,
                index_code TEXT NOT NULL,
                index_value REAL NOT NULL,
                period TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                raw_json TEXT DEFAULT ''
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS price_diff_rules(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                contract_id INTEGER NOT NULL,
                formula_name TEXT NOT NULL,
                formula_params TEXT NOT NULL,
                base_period TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(contract_id) REFERENCES contracts(id)
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS approvals(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                module TEXT NOT NULL,
                ref_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                user_id INTEGER,
                username TEXT DEFAULT '',
                comment TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS audit_log(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                module TEXT NOT NULL,
                ref_id INTEGER,
                action TEXT NOT NULL,
                user_id INTEGER,
                username TEXT DEFAULT '',
                detail TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS subcontracts(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                contract_id INTEGER NOT NULL,
                vendor_name TEXT NOT NULL,
                contract_amount REAL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id),
                FOREIGN KEY(contract_id) REFERENCES contracts(id)
            );"""
        )
        conn.commit()
    except Exception as e:
        if log_fn:
            try:
                log_fn("Schema Migration Error", f"hakedis tables: {e}")
            except Exception:
                pass

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
    _ensure_index(conn, "idx_fatura_odeme_tarih", "fatura_odeme", "tarih", log_fn)
    _ensure_index(conn, "idx_stok_hareket_urun_id", "stok_hareket", "urun_id", log_fn)
    _ensure_index(conn, "idx_stok_hareket_tarih", "stok_hareket", "tarih", log_fn)
    _ensure_index(conn, "idx_kasa_hareket_tip_tarih", "kasa_hareket", "tip, tarih", log_fn)
    _ensure_index(conn, "idx_quotes_no_version", "quotes", "quote_no, version", log_fn)
    _ensure_index(conn, "idx_quotes_status", "quotes", "status", log_fn)
    _ensure_index(conn, "idx_quotes_valid_until", "quotes", "valid_until", log_fn)
    _ensure_index(conn, "idx_quote_lines_quote_id", "quote_lines", "quote_id", log_fn)
    _ensure_index(conn, "idx_sales_orders_status", "sales_orders", "status", log_fn)
    _ensure_index(conn, "idx_sales_orders_quote_id", "sales_orders", "quote_id", log_fn)
    _ensure_index(conn, "idx_sales_order_lines_order_id", "sales_order_lines", "order_id", log_fn)
    _ensure_index(conn, "idx_audit_log_entity", "audit_log", "entity_type, entity_id", log_fn)
    _ensure_index(conn, "idx_audit_log_ts", "audit_log", "ts", log_fn)
    _ensure_index(conn, "idx_hr_departments_company", "hr_departments", "company_id", log_fn)
    _ensure_index(conn, "idx_hr_positions_company", "hr_positions", "company_id", log_fn)
    _ensure_index(conn, "idx_hr_employees_company", "hr_employees", "company_id", log_fn)
    _ensure_index(conn, "idx_hr_employees_department", "hr_employees", "department_id", log_fn)
    _ensure_index(conn, "idx_hr_salary_history_employee", "hr_salary_history", "employee_id", log_fn)
    _ensure_index(conn, "idx_hr_documents_employee", "hr_documents", "employee_id", log_fn)
    _ensure_index(conn, "idx_hr_leave_types_company", "hr_leave_types", "company_id", log_fn)
    _ensure_index(conn, "idx_hr_leave_requests_employee", "hr_leave_requests", "employee_id", log_fn)
    _ensure_index(conn, "idx_hr_leave_requests_dates", "hr_leave_requests", "start_date, end_date", log_fn)
    _ensure_index(conn, "idx_hr_leave_balances_employee_year", "hr_leave_balances", "employee_id, year", log_fn)
    _ensure_index(conn, "idx_hr_shifts_company", "hr_shifts", "company_id", log_fn)
    _ensure_index(conn, "idx_hr_timesheets_company_date", "hr_timesheets", "company_id, work_date", log_fn)
    _ensure_index(conn, "idx_hr_overtime_company_date", "hr_overtime_requests", "company_id, work_date", log_fn)
    _ensure_index(conn, "idx_hr_payroll_periods_company", "hr_payroll_periods", "company_id", log_fn)
    _ensure_index(conn, "idx_hr_payroll_items_period", "hr_payroll_items", "period_id", log_fn)
    _ensure_index(conn, "idx_hr_payroll_items_employee", "hr_payroll_items", "employee_id", log_fn)
    _ensure_index(conn, "idx_hr_user_roles_company", "hr_user_roles", "company_id", log_fn)
    _ensure_index(conn, "idx_hr_audit_company", "hr_audit_log", "company_id, created_at", log_fn)
    _ensure_index(conn, "idx_notes_company_owner", "notes", "company_id, owner_user_id", log_fn)
    _ensure_index(conn, "idx_notes_status", "notes", "status", log_fn)
    _ensure_index(conn, "idx_reminders_due_at", "reminders", "due_at", log_fn)
    _ensure_index(conn, "idx_reminders_status", "reminders", "status", log_fn)
    _ensure_index(conn, "idx_reminders_owner", "reminders", "owner_user_id", log_fn)
    _ensure_index(conn, "idx_audit_log_company", "audit_log", "company_id, user_id", log_fn)

    # Hakediş indeksleri
    _ensure_index(conn, "idx_projects_company", "projects", "company_id, status", log_fn)
    _ensure_index(conn, "idx_sites_project", "sites", "project_id, status", log_fn)
    _ensure_index(conn, "idx_contracts_project", "contracts", "project_id, status", log_fn)
    _ensure_index(conn, "idx_boq_contract", "boq_items", "contract_id, poz_code", log_fn)
    _ensure_index(conn, "idx_measurements_period", "measurements", "period_id, tarih", log_fn)
    _ensure_index(conn, "idx_pay_estimates_contract", "pay_estimates", "contract_id, period_no", log_fn)
    _ensure_index(conn, "idx_pay_estimate_lines_period", "pay_estimate_lines", "pay_estimate_id", log_fn)
    _ensure_index(conn, "idx_deductions_period", "deductions", "pay_estimate_id, type", log_fn)
    _ensure_index(conn, "idx_indices_cache_key", "indices_cache", "provider, index_code, period", log_fn)
    _ensure_index(conn, "idx_approvals_ref", "approvals", "module, ref_id, status", log_fn)
    _ensure_index(conn, "idx_audit_log_ref", "audit_log", "module, ref_id, action", log_fn)


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

    # series counters defaults
    try:
        conn.execute(
            "INSERT OR IGNORE INTO series_counters(name,prefix,last_no,padding,format) VALUES(?,?,?,?,?)",
            ("quote_no", "Q", 0, 6, "{prefix}{no_pad}"),
        )
        conn.execute(
            "INSERT OR IGNORE INTO series_counters(name,prefix,last_no,padding,format) VALUES(?,?,?,?,?)",
            ("order_no", "SO", 0, 6, "{prefix}{no_pad}"),
        )
        conn.commit()
    except Exception:
        pass
