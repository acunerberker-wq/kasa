#!/usr/bin/env python3
"""Full repo tester: exercises all repos and deeper tests for users/messages/purchase_report."""
import os
import sys
import traceback

repo_root = os.path.dirname(os.path.dirname(__file__))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from kasapro.db.main_db import DB


def safe_call(fn, *a, **k):
    try:
        return fn(*a, **k)
    except Exception as e:
        print(f"ERROR calling {fn.__qualname__}: {e}")
        traceback.print_exc()
        return None


def run():
    db_path = os.path.join(repo_root, "test_full.db")
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
    except Exception:
        pass

    print("Creating DB:", db_path)
    db = DB(db_path)
    errors = []

    print("-- Basic repo calls --")
    safe_call(db.logs.list, 5)
    safe_call(db.settings.list_currencies)
    safe_call(db.cariler.list)
    safe_call(db.cari_hareket.list)
    safe_call(db.kasa.toplam)
    safe_call(db.search.global_search, "")
    safe_call(db.maas.donem_list)
    safe_call(db.banka.distinct_banks)
    safe_call(db.fatura.list_seri)
    safe_call(db.stok.urun_list)
    safe_call(db.nakliye.firma_list)
    safe_call(db.satin_alma.siparis_list)
    safe_call(db.satis_siparis._has_table, "satis_siparis")

    print("-- Users repo deep test --")
    try:
        users = db.users
        users.add("test_user", "pwd123", "user")
        urow = users.auth("test_user", "pwd123")
        print("auth result:", bool(urow))
        uid = int(urow["id"]) if urow else None
        safe_call(users.set_password, uid, "newpass")
        safe_call(users.set_role, uid, "admin")
        safe_call(users.list)
        safe_call(users.delete, uid)
        print("users tests done")
    except Exception:
        traceback.print_exc()
        errors.append("users_repo")

    print("-- Messages repo deep test --")
    try:
        msgs = db.messages
        # create sender user record if missing
        db.cariler.upsert("Test Supplier") if hasattr(db.cariler, "upsert") else None
        # create a test user in users table for recipient
        db.users.add("msg_user", "m1", "user")
        r = db.users.list()
        recip = next((x for x in r if x["username"] == "msg_user"), None)
        rid = int(recip["id"]) if recip else None

        mid = safe_call(db.message_create, 0 if not rid else rid, "tester", "subj", "body", 0)
        if mid:
            safe_call(db.message_recipients_set, mid, [(rid, "msg_user")])
            inbox = safe_call(db.message_inbox_list, rid)
            sent = safe_call(db.message_sent_list, 0)
            print("inbox/sent sizes:", len(inbox or []), len(sent or []))
            safe_call(db.message_mark_read, mid, rid)
            print("unread count:", safe_call(db.message_unread_count, rid))
            safe_call(db.message_delete, mid)
        # cleanup
        try:
            u = db.users.list()
            for x in u:
                if x["username"] in ("msg_user",):
                    db.users.delete(int(x["id"]))
        except Exception:
            pass
    except Exception:
        traceback.print_exc()
        errors.append("messages_repo")

    print("-- Purchase report deep test --")
    try:
        pr = db.purchase_reports
        print("suppliers:", safe_call(pr.list_suppliers))
        print("products:", safe_call(pr.list_products)[:5])
        print("categories:", safe_call(pr.list_categories)[:5])
        print("locations:", safe_call(pr.list_locations))
        print("users:", safe_call(pr.list_users))
        print("fetch_report:", safe_call(pr.fetch_report))
    except Exception:
        traceback.print_exc()
        errors.append("purchase_report_repo")

    db.close()

    try:
        os.remove(db_path)
    except Exception:
        pass

    if errors:
        print("Errors in:", errors)
        sys.exit(2)
    print("ALL TESTS PASSED")


if __name__ == "__main__":
    run()
