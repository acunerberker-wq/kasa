#!/usr/bin/env python3
"""CRUD smoke tests across repos to exercise purchase flow and related repos."""
import os
import sys
import traceback

repo_root = os.path.dirname(os.path.dirname(__file__))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from kasapro.db.main_db import DB
from kasapro.utils import now_iso


def safe_call(fn, *a, **k):
    try:
        return fn(*a, **k)
    except Exception as e:
        print(f"ERROR calling {fn.__qualname__}: {e}")
        traceback.print_exc()
        return None


def run():
    db_path = os.path.join(repo_root, "test_crud.db")
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
    except Exception:
        pass

    print("Creating DB:", db_path)
    db = DB(db_path)

    print("-- Create supplier (cariler) --")
    sup_id = safe_call(db.cariler.upsert, "Supplier A")
    print("supplier id:", sup_id)

    print("-- Create product (stok) --")
    prod_id = safe_call(db.stok.urun_add, "P001", "Widget", "Parts", "Adet", 0, 0, 0, "R1", sup_id, "", 1, "")
    print("product id:", prod_id)

    print("-- Create invoice (fatura) as purchase (Alış) --")
    header = {
        'tarih': now_iso(),
        'tur': 'Alış',
        'durum': 'Tamamlandı',
        'cari_id': sup_id,
        'cari_ad': 'Supplier A',
        'para': 'TL',
        'ara_toplam': 100.0,
        'iskonto_toplam': 0.0,
        'kdv_toplam': 18.0,
        'genel_toplam': 118.0,
    }
    kalemler = [
        {
            'urun': 'Widget',
            'miktar': 2,
            'birim': 'Adet',
            'birim_fiyat': 50.0,
            'ara_tutar': 100.0,
            'iskonto_tutar': 0.0,
            'kdv_tutar': 18.0,
            'toplam': 118.0,
        }
    ]
    fid = safe_call(db.fatura.create, header, kalemler)
    print("fatura id:", fid)

    print("-- Add payment for invoice --")
    if fid:
        pid = safe_call(db.fatura.odeme_add, fid, now_iso(), 118.0, 'TL', 'Nakit')
        print("odeme id:", pid)

    print("-- Add kasa entry --")
    k_id = safe_call(db.kasa.add, now_iso(), 'Gider', 118.0, 'TL', 'Nakit', 'Gider', sup_id, 'Invoice payment', '', '')
    print("kasa id:", k_id)

    print("-- Add banka entry --")
    b_id = safe_call(db.banka.add, now_iso(), 'MyBank', '123', 'Giriş', 118.0, 'TL', 'Bank transfer', '', '', '')
    print("banka id:", b_id)

    print("-- Create cari_hareket --")
    ch_id = safe_call(db.cari_hareket.add, now_iso(), sup_id, 'Borç', 118.0, 'TL', 'Invoice', 'Nakit', '', '')
    print("cari_hareket id:", ch_id)

    print("-- Stock movement (stok_hareket) --")
    if prod_id:
        sh_id = safe_call(db.stok.hareket_add, now_iso(), prod_id, 'Giris', 2, 'Adet', None, None, None, 'Fatura', fid, 50.0, 'stock in')
        print("stok_hareket id:", sh_id)

    print("-- Purchase report fetch (should include our invoice/kalem) --")
    rpt = safe_call(db.purchase_report_fetch)
    print("purchase report kpis:", rpt.get('kpis') if rpt else None)

    print("-- Messages quick test --")
    # create message and recipient (use existing users table if present)
    try:
        db.users.add('crud_user', 'p', 'user')
        ulist = db.users.list()
        uid = next((int(x['id']) for x in ulist if x['username'] == 'crud_user'), None)
        mid = safe_call(db.message_create, uid or 0, 'crud_user', 'Hello', 'Body', 0)
        if mid:
            safe_call(db.message_recipients_set, mid, [(uid, 'crud_user')])
            print('message created', mid)
            safe_call(db.message_delete, mid)
        # cleanup
        if uid:
            safe_call(db.users.delete, uid)
    except Exception:
        traceback.print_exc()

    db.close()
    try:
        os.remove(db_path)
    except Exception:
        pass

    print('CRUD SMOKE TEST DONE')


if __name__ == '__main__':
    run()
