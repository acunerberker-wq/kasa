# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import tempfile
import unittest

from kasapro.db.main_db import DB
from kasapro.modules.trade.service import TradeService, TradeUserContext


class TradeModuleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "trade.db")
        self.db = DB(self.db_path)
        self.customer_id = self.db.cari_upsert("Test Müşteri", tur="Müşteri")
        self.supplier_id = self.db.cari_upsert("Test Tedarikçi", tur="Tedarikçi")
        self.service = TradeService(
            self.db,
            TradeUserContext(user_id=1, username="admin", app_role="admin"),
            company_id=0,
        )

    def tearDown(self) -> None:
        self.db.close()
        self.tmpdir.cleanup()

    def test_sales_invoice_stock_and_cari(self) -> None:
        before = self.db.cari_bakiye(self.customer_id)["bakiye"]
        doc_id = self.service.create_sales_invoice(
            "S-001",
            "2024-01-01",
            self.customer_id,
            "Test Müşteri",
            [
                {
                    "item": "Ürün A",
                    "qty": 5,
                    "unit": "Adet",
                    "unit_price": 10,
                    "tax_rate": 20,
                }
            ],
        )
        self.assertIsInstance(doc_id, int)
        after = self.db.cari_bakiye(self.customer_id)["bakiye"]
        self.assertGreater(after, before)
        self.assertEqual(self.service.stock_balance("Ürün A"), -5)

    def test_sales_return_stock_and_cari(self) -> None:
        doc_id = self.service.create_sales_invoice(
            "S-002",
            "2024-01-02",
            self.customer_id,
            "Test Müşteri",
            [
                {
                    "item": "Ürün B",
                    "qty": 3,
                    "unit": "Adet",
                    "unit_price": 10,
                    "tax_rate": 20,
                }
            ],
        )
        before = self.db.cari_bakiye(self.customer_id)["bakiye"]
        self.service.create_sales_return(doc_id, "SR-001", "2024-01-03")
        after = self.db.cari_bakiye(self.customer_id)["bakiye"]
        self.assertLess(after, before)
        self.assertEqual(self.service.stock_balance("Ürün B"), 0)

    def test_purchase_invoice_stock_and_cari(self) -> None:
        before = self.db.cari_bakiye(self.supplier_id)["bakiye"]
        self.service.create_purchase_invoice(
            "A-001",
            "2024-02-01",
            self.supplier_id,
            "Test Tedarikçi",
            [
                {
                    "item": "Ürün C",
                    "qty": 4,
                    "unit": "Adet",
                    "unit_price": 15,
                    "tax_rate": 20,
                }
            ],
        )
        after = self.db.cari_bakiye(self.supplier_id)["bakiye"]
        self.assertLess(after, before)
        self.assertEqual(self.service.stock_balance("Ürün C"), 4)

    def test_payment_records_cash_and_cari(self) -> None:
        doc_id = self.service.create_sales_invoice(
            "S-003",
            "2024-03-01",
            self.customer_id,
            "Test Müşteri",
            [
                {
                    "item": "Ürün D",
                    "qty": 2,
                    "unit": "Adet",
                    "unit_price": 50,
                    "tax_rate": 20,
                }
            ],
        )
        before = self.db.cari_bakiye(self.customer_id)["bakiye"]
        self.service.record_payment(doc_id, 50, "2024-03-02", "Nakit", use_bank=False)
        after = self.db.cari_bakiye(self.customer_id)["bakiye"]
        self.assertLess(after, before)
        kasa_rows = self.db.kasa_list(q="S-003")
        self.assertTrue(any(r["belge"] == "S-003" for r in kasa_rows))

    def test_order_partial_and_invoice(self) -> None:
        order_id = self.service.create_order(
            "sales",
            "SO-001",
            "2024-04-01",
            self.customer_id,
            "Test Müşteri",
            [
                {
                    "item": "Ürün E",
                    "qty": 10,
                    "unit": "Adet",
                    "unit_price": 5,
                    "line_total": 50,
                    "fulfilled_qty": 0,
                }
            ],
        )
        line = self.service.repo.list_order_line_summary(order_id)[0]
        self.service.fulfill_order_to_invoice(order_id, "S-004", "2024-04-02", fulfill_map={int(line["id"]): 4})
        order = self.service.repo.get_order(order_id)
        self.assertIn(order["status"], ("Kısmi", "Kapalı"))
        docs = self.service.list_docs("sales_invoice")
        self.assertTrue(any(d["doc_no"] == "S-004" for d in docs))

    def test_unauthorized_access(self) -> None:
        service = TradeService(
            self.db,
            TradeUserContext(user_id=2, username="readonly", app_role="user"),
            company_id=0,
        )
        with self.assertRaises(PermissionError):
            service.create_sales_invoice(
                "S-005",
                "2024-05-01",
                self.customer_id,
                "Test Müşteri",
                [
                    {
                        "item": "Ürün F",
                        "qty": 1,
                        "unit": "Adet",
                        "unit_price": 10,
                        "tax_rate": 20,
                    }
                ],
            )

    def test_pagination(self) -> None:
        for i in range(30):
            self.service.create_sales_invoice(
                f"S-{100+i}",
                "2024-06-01",
                self.customer_id,
                "Test Müşteri",
                [
                    {
                        "item": "Ürün G",
                        "qty": 1,
                        "unit": "Adet",
                        "unit_price": 1,
                        "tax_rate": 20,
                    }
                ],
            )
        page = self.service.list_docs("sales_invoice", limit=10, offset=10)
        self.assertEqual(len(page), 10)

    def test_audit_logs(self) -> None:
        doc_id = self.service.create_sales_invoice(
            "S-200",
            "2024-07-01",
            self.customer_id,
            "Test Müşteri",
            [
                {
                    "item": "Ürün H",
                    "qty": 2,
                    "unit": "Adet",
                    "unit_price": 10,
                    "tax_rate": 20,
                }
            ],
        )
        self.service.void_doc(doc_id, "test")
        logs = self.service.repo.list_audit_logs(self.service.company_id, limit=20)
        self.assertTrue(any(l["action"] == "void" for l in logs))
