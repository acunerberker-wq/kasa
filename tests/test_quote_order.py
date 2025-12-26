# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import tempfile
import threading
import unittest
from datetime import date, timedelta

from kasapro.db.main_db import DB
from kasapro.modules.quote_order.service import QuoteOrderService


class QuoteOrderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "quote_order.db")
        self.db = DB(self.db_path)
        self.service = QuoteOrderService(self.db)
        self.actor = {"id": 1, "username": "admin", "role": "ADMIN"}

    def tearDown(self) -> None:
        self.db.close()
        self.tmpdir.cleanup()

    def _sample_lines(self):
        return [
            {"urun": "Ürün A", "miktar": 2, "birim_fiyat": 100, "iskonto_oran": 10, "kdv_oran": 20},
            {"urun": "Ürün B", "miktar": 1, "birim_fiyat": 200, "iskonto_oran": 0, "kdv_oran": 20},
        ]

    def _create_quote(self, **kwargs):
        data = {
            "cari_ad": "ACME",
            "valid_until": (date.today() + timedelta(days=7)).isoformat(),
            "para": "TL",
            "kur": 1,
            "genel_iskonto_oran": 0,
        }
        data.update(kwargs)
        return self.service.create_quote(data, self._sample_lines(), actor=self.actor)

    def test_quote_totals(self):
        quote_id = self._create_quote(genel_iskonto_oran=5)
        quote = self.service.get_quote(quote_id)
        self.assertAlmostEqual(float(quote["ara_toplam"]), 400.0)
        self.assertAlmostEqual(float(quote["iskonto_toplam"]), 20.0)
        self.assertAlmostEqual(float(quote["kdv_toplam"]), 76.0)
        self.assertAlmostEqual(float(quote["genel_iskonto_tutar"]), 22.8, places=1)
        self.assertAlmostEqual(float(quote["genel_toplam"]), 433.2, places=1)

    def test_revision_flow(self):
        quote_id = self._create_quote()
        new_id = self.service.revise_quote(quote_id, actor=self.actor)
        old = self.service.get_quote(quote_id)
        new = self.service.get_quote(new_id)
        self.assertEqual(old["status"], "REVISED")
        self.assertEqual(new["version"], old["version"] + 1)
        with self.assertRaises(ValueError):
            self.service.update_quote(quote_id, {"cari_ad": "X"}, self._sample_lines(), actor=self.actor)

    def test_valid_until_expired(self):
        quote_id = self.service.create_quote(
            {
                "cari_ad": "ACME",
                "valid_until": (date.today() - timedelta(days=1)).isoformat(),
                "genel_iskonto_oran": 0,
            },
            self._sample_lines(),
            actor=self.actor,
        )
        self.service.list_quotes()
        quote = self.service.get_quote(quote_id)
        self.assertEqual(quote["status"], "EXPIRED")

    def test_status_transitions(self):
        quote_id = self._create_quote()
        self.service.send_quote(quote_id, actor=self.actor)
        self.service.approve_quote(quote_id, actor=self.actor)
        quote = self.service.get_quote(quote_id)
        self.assertEqual(quote["status"], "CUSTOMER_APPROVED")

        quote_id2 = self._create_quote()
        self.service.reject_quote(quote_id2, actor=self.actor)
        quote2 = self.service.get_quote(quote_id2)
        self.assertEqual(quote2["status"], "REJECTED")

    def test_convert_to_order(self):
        quote_id = self._create_quote()
        self.service.approve_quote(quote_id, actor=self.actor)
        order_id = self.service.convert_to_order(quote_id, actor=self.actor)
        order = self.service.get_order(order_id)
        quote = self.service.get_quote(quote_id)
        self.assertEqual(order["quote_id"], quote_id)
        self.assertEqual(len(order["lines"]), len(quote["lines"]))
        self.assertEqual(order["lines"][0]["urun"], quote["lines"][0]["urun"])

    def test_converted_quote_locked(self):
        quote_id = self._create_quote()
        self.service.approve_quote(quote_id, actor=self.actor)
        self.service.convert_to_order(quote_id, actor=self.actor)
        with self.assertRaises(ValueError):
            self.service.update_quote(quote_id, {"cari_ad": "X"}, self._sample_lines(), actor=self.actor)

    def test_series_concurrency(self):
        results = []
        lock = threading.Lock()

        def worker():
            no = self.service.next_quote_no()
            with lock:
                results.append(no)

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(set(results)), 2)

    def test_pagination(self):
        for _ in range(30):
            self._create_quote()
        rows, total = self.service.list_quotes(limit=10, offset=0)
        self.assertEqual(total, 30)
        self.assertEqual(len(rows), 10)

    def test_permission_convert(self):
        quote_id = self._create_quote()
        self.service.approve_quote(quote_id, actor=self.actor)
        with self.assertRaises(PermissionError):
            self.service.convert_to_order(quote_id, actor={"id": 2, "username": "viewer", "role": "VIEWER"})

    def test_audit_log(self):
        quote_id = self._create_quote()
        self.service.approve_quote(quote_id, actor=self.actor)
        audits = self.service.list_audit("quote", quote_id)
        actions = [a["action"] for a in audits]
        self.assertIn("create", actions)
        self.assertIn("approve", actions)


if __name__ == "__main__":
    unittest.main()
