# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import tempfile
import unittest

from kasapro.db.main_db import DB


class WmsStockTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "wms.db")
        self.db = DB(self.db_path)
        self.company_id = 1
        self.branch_id = 1

        self.db.conn.execute(
            """
            INSERT OR IGNORE INTO users(username, salt, pass_hash, role, created_at)
            VALUES('admin', 'salt', 'hash', 'admin', CURRENT_TIMESTAMP)
            """
        )
        self.db.conn.execute(
            """
            INSERT OR IGNORE INTO users(username, salt, pass_hash, role, created_at)
            VALUES('viewer', 'salt', 'hash', 'user', CURRENT_TIMESTAMP)
            """
        )
        self.db.conn.commit()
        self.admin_id = int(self.db.conn.execute("SELECT id FROM users WHERE username='admin'").fetchone()[0])
        self.viewer_id = int(self.db.conn.execute("SELECT id FROM users WHERE username='viewer'").fetchone()[0])

        self.uom_id = self.db.wms_create_uom(self.company_id, "ADET", "Adet")
        self.cat_id = self.db.wms_create_category(self.company_id, "Genel")
        self.wh1 = self.db.wms_create_warehouse(self.company_id, self.branch_id, "D01", "Ana Depo")
        self.loc1 = self.db.wms_create_location(self.company_id, self.branch_id, self.wh1, "R1")
        self.wh2 = self.db.wms_create_warehouse(self.company_id, self.branch_id, "D02", "Yedek Depo")
        self.loc2 = self.db.wms_create_location(self.company_id, self.branch_id, self.wh2, "R2")

        self.item_id = self.db.wms_create_item(
            self.company_id,
            "URUN-001",
            "Ürün 1",
            self.uom_id,
            category_id=self.cat_id,
        )
        self.item_lot = self.db.wms_create_item(
            self.company_id,
            "URUN-LOT",
            "Lotlu Ürün",
            self.uom_id,
            category_id=self.cat_id,
            track_lot=1,
        )
        self.item_serial = self.db.wms_create_item(
            self.company_id,
            "URUN-SER",
            "Serili Ürün",
            self.uom_id,
            category_id=self.cat_id,
            track_serial=1,
        )
        self.lot_id = self.db.wms_create_lot(self.company_id, self.item_lot, "LOT-001", expiry_date="2025-01-01")
        self.serial_id = self.db.wms_create_serial(self.company_id, self.item_serial, "SER-001")

        self.db.wms_set_warehouse_permission(self.admin_id, self.company_id, self.branch_id, self.wh1, can_view=1, can_post=1)
        self.db.wms_set_warehouse_permission(self.viewer_id, self.company_id, self.branch_id, self.wh1, can_view=1, can_post=0)

    def tearDown(self) -> None:
        self.db.close()
        self.tmpdir.cleanup()

    def _post_grn(self, item_id: int, qty: float, location_id: int, lot_id=None, serial_id=None) -> int:
        doc_id = self.db.wms_create_doc(
            {
                "company_id": self.company_id,
                "branch_id": self.branch_id,
                "doc_type": "GRN",
                "doc_date": "2024-01-01",
                "warehouse_id": self.wh1,
            },
            [
                {
                    "item_id": item_id,
                    "qty": qty,
                    "unit": "Adet",
                    "unit_price": 10,
                    "target_location_id": location_id,
                    "lot_id": lot_id,
                    "serial_id": serial_id,
                }
            ],
            user_id=self.admin_id,
            username="admin",
        )
        self.db.wms_post_doc(doc_id, user_id=self.admin_id, username="admin")
        return doc_id

    def test_grn_increases_stock(self) -> None:
        self._post_grn(self.item_id, 10, self.loc1)
        on_hand = self.db.wms_get_on_hand(self.company_id, self.branch_id, self.wh1, self.loc1, self.item_id)
        self.assertEqual(on_hand, 10)

    def test_ship_decreases_stock(self) -> None:
        self._post_grn(self.item_id, 10, self.loc1)
        doc_id = self.db.wms_create_doc(
            {
                "company_id": self.company_id,
                "branch_id": self.branch_id,
                "doc_type": "SHIP",
                "doc_date": "2024-01-02",
                "warehouse_id": self.wh1,
            },
            [{"item_id": self.item_id, "qty": 4, "unit": "Adet", "source_location_id": self.loc1}],
        )
        self.db.wms_post_doc(doc_id)
        on_hand = self.db.wms_get_on_hand(self.company_id, self.branch_id, self.wh1, self.loc1, self.item_id)
        self.assertEqual(on_hand, 6)

    def test_transfer_moves_between_warehouses(self) -> None:
        self._post_grn(self.item_id, 10, self.loc1)
        doc_id = self.db.wms_create_doc(
            {
                "company_id": self.company_id,
                "branch_id": self.branch_id,
                "doc_type": "TRF",
                "doc_date": "2024-01-03",
                "warehouse_id": self.wh1,
            },
            [
                {
                    "item_id": self.item_id,
                    "qty": 3,
                    "unit": "Adet",
                    "source_warehouse_id": self.wh1,
                    "target_warehouse_id": self.wh2,
                    "source_location_id": self.loc1,
                    "target_location_id": self.loc2,
                }
            ],
        )
        self.db.wms_post_doc(doc_id)
        src = self.db.wms_get_on_hand(self.company_id, self.branch_id, self.wh1, self.loc1, self.item_id)
        tgt = self.db.wms_get_on_hand(self.company_id, self.branch_id, self.wh2, self.loc2, self.item_id)
        self.assertEqual(src, 7)
        self.assertEqual(tgt, 3)

    def test_lot_required(self) -> None:
        doc_id = self.db.wms_create_doc(
            {
                "company_id": self.company_id,
                "branch_id": self.branch_id,
                "doc_type": "GRN",
                "doc_date": "2024-01-04",
                "warehouse_id": self.wh1,
            },
            [{"item_id": self.item_lot, "qty": 1, "unit": "Adet", "target_location_id": self.loc1}],
        )
        with self.assertRaises(ValueError):
            self.db.wms_post_doc(doc_id)

    def test_serial_required(self) -> None:
        doc_id = self.db.wms_create_doc(
            {
                "company_id": self.company_id,
                "branch_id": self.branch_id,
                "doc_type": "GRN",
                "doc_date": "2024-01-04",
                "warehouse_id": self.wh1,
            },
            [{"item_id": self.item_serial, "qty": 1, "unit": "Adet", "target_location_id": self.loc1}],
        )
        with self.assertRaises(ValueError):
            self.db.wms_post_doc(doc_id)

    def test_fefo_picking(self) -> None:
        self.db.wms_create_lot(self.company_id, self.item_lot, "LOT-002", expiry_date="2024-06-01")
        earliest = self.db.wms_pick_lot_fefo(self.company_id, self.item_lot)
        self.assertIsNotNone(earliest)
        self.assertEqual(earliest["lot_no"], "LOT-002")

    def test_reservation_does_not_reduce_on_hand(self) -> None:
        self._post_grn(self.item_id, 5, self.loc1)
        self.db.wms_create_reservation(self.company_id, self.branch_id, self.wh1, self.loc1, self.item_id, 2)
        on_hand = self.db.wms_get_on_hand(self.company_id, self.branch_id, self.wh1, self.loc1, self.item_id)
        self.assertEqual(on_hand, 5)
        doc_id = self.db.wms_create_doc(
            {
                "company_id": self.company_id,
                "branch_id": self.branch_id,
                "doc_type": "SHIP",
                "doc_date": "2024-01-05",
                "warehouse_id": self.wh1,
            },
            [{"item_id": self.item_id, "qty": 4, "unit": "Adet", "source_location_id": self.loc1}],
        )
        with self.assertRaises(ValueError):
            self.db.wms_post_doc(doc_id)

    def test_reservation_release(self) -> None:
        self._post_grn(self.item_id, 5, self.loc1)
        reservation_id = self.db.wms_create_reservation(self.company_id, self.branch_id, self.wh1, self.loc1, self.item_id, 2)
        self.db.wms_release_reservation(reservation_id)
        doc_id = self.db.wms_create_doc(
            {
                "company_id": self.company_id,
                "branch_id": self.branch_id,
                "doc_type": "SHIP",
                "doc_date": "2024-01-05",
                "warehouse_id": self.wh1,
            },
            [{"item_id": self.item_id, "qty": 4, "unit": "Adet", "source_location_id": self.loc1}],
        )
        self.db.wms_post_doc(doc_id)

    def test_block_prevents_ship(self) -> None:
        self._post_grn(self.item_id, 5, self.loc1)
        self.db.wms_create_block(self.company_id, self.branch_id, self.wh1, self.loc1, self.item_id, 3, reason="Karantina")
        doc_id = self.db.wms_create_doc(
            {
                "company_id": self.company_id,
                "branch_id": self.branch_id,
                "doc_type": "SHIP",
                "doc_date": "2024-01-06",
                "warehouse_id": self.wh1,
            },
            [{"item_id": self.item_id, "qty": 3, "unit": "Adet", "source_location_id": self.loc1}],
        )
        with self.assertRaises(ValueError):
            self.db.wms_post_doc(doc_id)

    def test_period_lock_blocks_post(self) -> None:
        period_id = self.db.wms_create_period(self.company_id, self.branch_id, "Ocak", "2024-01-01", "2024-01-31")
        self.db.wms_lock_period(period_id, user_id=self.admin_id)
        doc_id = self.db.wms_create_doc(
            {
                "company_id": self.company_id,
                "branch_id": self.branch_id,
                "doc_type": "GRN",
                "doc_date": "2024-01-15",
                "warehouse_id": self.wh1,
            },
            [{"item_id": self.item_id, "qty": 1, "unit": "Adet", "target_location_id": self.loc1}],
        )
        with self.assertRaises(ValueError):
            self.db.wms_post_doc(doc_id)

    def test_negative_stock_forbid(self) -> None:
        doc_id = self.db.wms_create_doc(
            {
                "company_id": self.company_id,
                "branch_id": self.branch_id,
                "doc_type": "SHIP",
                "doc_date": "2024-02-01",
                "warehouse_id": self.wh1,
            },
            [{"item_id": self.item_id, "qty": 1, "unit": "Adet", "source_location_id": self.loc1}],
        )
        with self.assertRaises(ValueError):
            self.db.wms_post_doc(doc_id, negative_stock_policy="forbid")

    def test_negative_stock_warn(self) -> None:
        doc_id = self.db.wms_create_doc(
            {
                "company_id": self.company_id,
                "branch_id": self.branch_id,
                "doc_type": "SHIP",
                "doc_date": "2024-02-02",
                "warehouse_id": self.wh1,
            },
            [{"item_id": self.item_id, "qty": 1, "unit": "Adet", "source_location_id": self.loc1}],
        )
        self.db.wms_post_doc(doc_id, negative_stock_policy="warn")
        row = self.db.conn.execute("SELECT action FROM audit_log WHERE action='NEGATIVE_WARN'").fetchone()
        self.assertIsNotNone(row)

    def test_negative_stock_allow(self) -> None:
        doc_id = self.db.wms_create_doc(
            {
                "company_id": self.company_id,
                "branch_id": self.branch_id,
                "doc_type": "SHIP",
                "doc_date": "2024-02-03",
                "warehouse_id": self.wh1,
            },
            [{"item_id": self.item_id, "qty": 1, "unit": "Adet", "source_location_id": self.loc1}],
        )
        self.db.wms_post_doc(doc_id, negative_stock_policy="allow")

    def test_fifo_cost_calculation(self) -> None:
        self._post_grn(self.item_id, 5, self.loc1)
        self.db.conn.execute(
            """
            INSERT INTO stock_ledger(company_id, branch_id, warehouse_id, location_id, item_id, txn_date, qty, direction, cost)
            VALUES(?,?,?,?,?,?,?,? ,?)
            """,
            (self.company_id, self.branch_id, self.wh1, self.loc1, self.item_id, "2024-01-02", 5, "IN", 12),
        )
        self.db.conn.commit()
        cost = self.db.wms_fifo_cost(self.company_id, self.branch_id, self.wh1, self.item_id, 6)
        self.assertEqual(cost, 5 * 10 + 1 * 12)

    def test_weighted_avg_cost(self) -> None:
        self._post_grn(self.item_id, 4, self.loc1)
        self.db.conn.execute(
            """
            INSERT INTO stock_ledger(company_id, branch_id, warehouse_id, location_id, item_id, txn_date, qty, direction, cost)
            VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (self.company_id, self.branch_id, self.wh1, self.loc1, self.item_id, "2024-01-03", 6, "IN", 14),
        )
        self.db.conn.commit()
        wa_cost = self.db.wms_wa_cost(self.company_id, self.branch_id, self.wh1, self.item_id)
        self.assertAlmostEqual(wa_cost, (4 * 10 + 6 * 14) / 10)

    def test_landed_cost_distribution(self) -> None:
        allocated = self.db.wms_allocate_landed_cost(100, [2, 3, 5])
        self.assertAlmostEqual(sum(allocated), 100)

    def test_doc_numbers_unique(self) -> None:
        doc1 = self.db.wms_create_doc(
            {
                "company_id": self.company_id,
                "branch_id": self.branch_id,
                "doc_type": "GRN",
                "doc_date": "2024-02-04",
                "warehouse_id": self.wh1,
                "series": "A",
            },
            [{"item_id": self.item_id, "qty": 1, "unit": "Adet", "target_location_id": self.loc1}],
        )
        doc2 = self.db.wms_create_doc(
            {
                "company_id": self.company_id,
                "branch_id": self.branch_id,
                "doc_type": "GRN",
                "doc_date": "2024-02-04",
                "warehouse_id": self.wh1,
                "series": "A",
            },
            [{"item_id": self.item_id, "qty": 1, "unit": "Adet", "target_location_id": self.loc1}],
        )
        no1 = self.db.conn.execute("SELECT doc_no FROM docs WHERE id=?", (doc1,)).fetchone()[0]
        no2 = self.db.conn.execute("SELECT doc_no FROM docs WHERE id=?", (doc2,)).fetchone()[0]
        self.assertNotEqual(no1, no2)

    def test_audit_log_written_on_post(self) -> None:
        doc_id = self._post_grn(self.item_id, 2, self.loc1)
        row = self.db.conn.execute(
            "SELECT action FROM audit_log WHERE entity_type='stock_doc' AND entity_id=? ORDER BY id DESC",
            (doc_id,),
        ).fetchone()
        self.assertEqual(row["action"], "POST")

    def test_doc_lock_blocks_post(self) -> None:
        doc_id = self.db.wms_create_doc(
            {
                "company_id": self.company_id,
                "branch_id": self.branch_id,
                "doc_type": "GRN",
                "doc_date": "2024-02-05",
                "warehouse_id": self.wh1,
            },
            [{"item_id": self.item_id, "qty": 1, "unit": "Adet", "target_location_id": self.loc1}],
        )
        doc_no = self.db.conn.execute("SELECT doc_no FROM docs WHERE id=?", (doc_id,)).fetchone()[0]
        self.db.wms_lock_doc(self.company_id, self.branch_id, "GRN", doc_no, self.admin_id, reason="Kilitli")
        with self.assertRaises(ValueError):
            self.db.wms_post_doc(doc_id)

    def test_count_tolerance_requires_approval(self) -> None:
        self._post_grn(self.item_id, 5, self.loc1)
        doc_id = self.db.wms_create_doc(
            {
                "company_id": self.company_id,
                "branch_id": self.branch_id,
                "doc_type": "COUNT",
                "doc_date": "2024-02-06",
                "warehouse_id": self.wh1,
                "tolerance_qty": 0,
            },
            [{"item_id": self.item_id, "qty": 2, "unit": "Adet", "source_location_id": self.loc1}],
        )
        with self.assertRaises(ValueError):
            self.db.wms_post_doc(doc_id)
        status = self.db.conn.execute("SELECT status FROM docs WHERE id=?", (doc_id,)).fetchone()[0]
        self.assertEqual(status, "PENDING_APPROVAL")

    def test_cost_masking_for_unauthorized_user(self) -> None:
        self._post_grn(self.item_id, 1, self.loc1)
        rows = self.db.wms_list_ledger_masked_cost(self.viewer_id, self.company_id, self.branch_id, self.wh1)
        self.assertTrue(rows)
        self.assertIsNone(rows[0]["cost"])
