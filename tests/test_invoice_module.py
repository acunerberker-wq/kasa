# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import tempfile
import threading
import unittest

from kasapro.config import HAS_REPORTLAB
from kasapro.db.connection import connect
from kasapro.db.main_db import DB
from kasapro.modules.invoice import calculate_totals
from kasapro.modules.invoice.repo import AdvancedInvoiceRepo
from kasapro.modules.invoice.security import can_create_document
from kasapro.modules.invoice.export import export_csv, export_pdf


class InvoiceModuleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "invoice.db")
        self.db = DB(self.db_path)
        self.repo = self.db.invoice_adv
        self.customer_id = self.db.cari_upsert("Test Cari")

    def tearDown(self) -> None:
        try:
            self.db.close()
        finally:
            self.tmpdir.cleanup()

    def _basic_header(self, doc_type: str = "sales") -> dict:
        return {
            "company_id": 1,
            "doc_type": doc_type,
            "doc_date": "2025-01-10",
            "currency": "TL",
            "series": "A",
            "status": "POSTED",
        }

    def test_sales_invoice_totals(self) -> None:
        lines = [{"description": "Ürün", "qty": 2, "unit_price": 100, "vat_rate": 20}]
        doc_id = self.repo.create_doc(self._basic_header("sales"), lines)
        header = self.repo.get_doc(doc_id)["header"]
        self.assertAlmostEqual(header["subtotal"], 200.0)
        self.assertAlmostEqual(header["vat_total"], 40.0)
        self.assertAlmostEqual(header["grand_total"], 240.0)

    def test_purchase_invoice_totals(self) -> None:
        lines = [{"description": "Hizmet", "qty": 1, "unit_price": 500, "vat_rate": 10}]
        doc_id = self.repo.create_doc(self._basic_header("purchase"), lines)
        header = self.repo.get_doc(doc_id)["header"]
        self.assertAlmostEqual(header["subtotal"], 500.0)
        self.assertAlmostEqual(header["vat_total"], 50.0)
        self.assertAlmostEqual(header["grand_total"], 550.0)

    def test_discounts(self) -> None:
        totals = calculate_totals(
            [
                {
                    "description": "Satır",
                    "qty": 1,
                    "unit_price": 200,
                    "vat_rate": 20,
                    "line_discount_type": "percent",
                    "line_discount_value": 10,
                }
            ],
            invoice_discount_value=20,
            invoice_discount_type="amount",
            vat_included=False,
            sign=1,
        )
        self.assertAlmostEqual(totals.subtotal, 200.0)
        self.assertAlmostEqual(totals.discount_total, 40.0)
        self.assertAlmostEqual(totals.grand_total, 192.0)

    def test_discount_recalculates_vat(self) -> None:
        totals = calculate_totals(
            [{"description": "Satır", "qty": 1, "unit_price": 100, "vat_rate": 20}],
            invoice_discount_value=50,
            invoice_discount_type="percent",
            vat_included=False,
            sign=1,
        )
        self.assertAlmostEqual(totals.vat_total, 10.0)
        self.assertAlmostEqual(totals.grand_total, 60.0)

    def test_vat_included(self) -> None:
        totals = calculate_totals(
            [{"description": "KDV dahil", "qty": 1, "unit_price": 118, "vat_rate": 18}],
            vat_included=True,
        )
        self.assertAlmostEqual(totals.subtotal, 100.0)
        self.assertAlmostEqual(totals.vat_total, 18.0)
        self.assertAlmostEqual(totals.grand_total, 118.0)

    def test_return_invoice_negative(self) -> None:
        lines = [{"description": "İade", "qty": 1, "unit_price": 100, "vat_rate": 20}]
        header = self._basic_header("sales_return")
        header["customer_id"] = self.customer_id
        header["customer_name"] = "Müşteri"
        doc_id = self.repo.create_doc(header, lines)
        header = self.repo.get_doc(doc_id)["header"]
        self.assertLess(header["grand_total"], 0)
        hareket = list(self.db.cari_hareket.list(cari_id=header["customer_id"]))
        self.assertTrue(hareket)
        self.assertEqual(hareket[0]["tip"], "Borç")

    def test_purchase_invoice_cari_tip(self) -> None:
        header = self._basic_header("purchase")
        header["customer_id"] = self.customer_id
        header["customer_name"] = "Tedarikci"
        lines = [{"description": "Alış", "qty": 1, "unit_price": 100, "vat_rate": 20}]
        doc_id = self.repo.create_doc(header, lines)
        data = self.repo.get_doc(doc_id)
        hareket = list(self.db.cari_hareket.list(cari_id=header["customer_id"]))
        self.assertTrue(hareket)
        self.assertEqual(hareket[0]["tip"], "Borç")
        self.assertAlmostEqual(hareket[0]["tutar"], abs(data["header"]["grand_total"]))

    def test_void_creates_reversal(self) -> None:
        lines = [{"description": "Test", "qty": 1, "unit_price": 100, "vat_rate": 20}]
        doc_id = self.repo.create_doc(self._basic_header("sales"), lines)
        reverse_id = self.repo.void_doc(doc_id)
        header = self.repo.get_doc(doc_id)["header"]
        self.assertEqual(header["status"], "VOID")
        reverse_header = self.repo.get_doc(reverse_id)["header"]
        self.assertEqual(reverse_header["doc_type"], "void")

    def test_partial_payment(self) -> None:
        lines = [{"description": "Test", "qty": 1, "unit_price": 100, "vat_rate": 20}]
        header = self._basic_header("sales")
        header["customer_id"] = self.customer_id
        header["customer_name"] = "Musteri"
        doc_id = self.repo.create_doc(header, lines)
        self.repo.add_payment(doc_id, "2025-01-10", 50, "TL", "Kasa")
        remaining = self.repo.remaining_balance(doc_id)
        self.assertAlmostEqual(remaining, 70.0)
        updated = self.repo.get_doc(doc_id)["header"]
        self.assertEqual(updated["payment_status"], "PART_PAID")

    def test_overpayment_rejected_on_zero_due(self) -> None:
        header = self._basic_header("sales")
        header["customer_id"] = self.customer_id
        header["customer_name"] = "Musteri"
        lines = [{"description": "Test", "qty": 0, "unit_price": 100, "vat_rate": 20}]
        doc_id = self.repo.create_doc(header, lines)
        with self.assertRaises(ValueError):
            self.repo.add_payment(doc_id, "2025-01-10", 10, "TL", "Kasa")

    def test_full_payment_status(self) -> None:
        lines = [{"description": "Test", "qty": 1, "unit_price": 100, "vat_rate": 20}]
        header = self._basic_header("sales")
        header["customer_id"] = self.customer_id
        header["customer_name"] = "Musteri"
        doc_id = self.repo.create_doc(header, lines)
        self.repo.add_payment(doc_id, "2025-01-10", 120, "TL", "Kasa")
        updated = self.repo.get_doc(doc_id)["header"]
        self.assertEqual(updated["payment_status"], "PAID")

    def test_payment_rejects_overpayment(self) -> None:
        lines = [{"description": "Test", "qty": 1, "unit_price": 100, "vat_rate": 20}]
        header = self._basic_header("sales")
        header["customer_id"] = self.customer_id
        header["customer_name"] = "Musteri"
        doc_id = self.repo.create_doc(header, lines)
        with self.assertRaises(ValueError):
            self.repo.add_payment(doc_id, "2025-01-10", 200, "TL", "Kasa")

    def test_number_collision(self) -> None:
        def worker(result_list):
            repo = AdvancedInvoiceRepo(connect(self.db_path))
            doc_id = repo.create_doc(self._basic_header("sales"), [{"description": "A", "qty": 1, "unit_price": 10, "vat_rate": 1}])
            header = repo.get_doc(doc_id)["header"]
            result_list.append(header["doc_no"])

        results: list[str] = []
        threads = [threading.Thread(target=worker, args=(results,)) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(results), 2)
        self.assertNotEqual(results[0], results[1])

    def test_role_security(self) -> None:
        self.assertFalse(can_create_document("read-only"))
        self.assertTrue(can_create_document("admin"))

    def test_export_csv(self) -> None:
        lines = [{"description": "CSV", "qty": 1, "unit_price": 10, "vat_rate": 1}]
        doc_id = self.repo.create_doc(self._basic_header("sales"), lines)
        payload = self.repo.get_doc(doc_id)
        path = os.path.join(self.tmpdir.name, "invoice.csv")
        export_csv(path, dict(payload["header"]), [dict(l) for l in payload["lines"]], {
            "subtotal": payload["header"]["subtotal"],
            "discount_total": payload["header"]["discount_total"],
            "vat_total": payload["header"]["vat_total"],
            "grand_total": payload["header"]["grand_total"],
        })
        self.assertTrue(os.path.exists(path))

    @unittest.skipUnless(HAS_REPORTLAB, "ReportLab yok")
    def test_export_pdf(self) -> None:
        lines = [{"description": "PDF", "qty": 1, "unit_price": 10, "vat_rate": 1}]
        doc_id = self.repo.create_doc(self._basic_header("sales"), lines)
        payload = self.repo.get_doc(doc_id)
        path = os.path.join(self.tmpdir.name, "invoice.pdf")
        export_pdf(path, dict(payload["header"]), [dict(l) for l in payload["lines"]], {
            "subtotal": payload["header"]["subtotal"],
            "discount_total": payload["header"]["discount_total"],
            "vat_total": payload["header"]["vat_total"],
            "grand_total": payload["header"]["grand_total"],
        }, {"name": "Test Co"})
        self.assertTrue(os.path.exists(path))
