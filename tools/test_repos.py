# Quick repo smoke tester
import traceback
import os
import sys

# Ensure repository root is on sys.path for local package imports
repo_root = os.path.dirname(os.path.dirname(__file__))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from kasapro.db.main_db import DB

out = []

try:
    # Use a temporary file in repo root
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'test_tmp.db')
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except Exception:
            pass
    print('Creating DB at', db_path)
    db = DB(db_path)
    print('DB initialized')

    # Call a few repo methods
    print('Logs count:', len(db.logs.list(10)))
    print('Cariler count:', len(db.cariler.list()))
    print('Distinct banks:', db.banka.distinct_banks())
    print('Kasa toplam:', db.kasa.toplam())
    print('Purchase products sample:', db.purchase_report_products()[:5])
    print('Messages inbox (should be empty):', db.message_inbox_list(1))

    db.close()
    print('DB closed')

except Exception:
    print('ERROR during test:')
    traceback.print_exc()
    sys.exit(2)

# cleanup
try:
    os.remove(db_path)
    print('Removed temp DB')
except Exception:
    pass

print('SMOKE TEST OK')
