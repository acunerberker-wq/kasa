# -*- coding: utf-8 -*-

from __future__ import annotations

import logging
import os
from typing import Dict, List

from ..db.main_db import DB

logger = logging.getLogger(__name__)


def _ensure_app_logger() -> None:
    if any(isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", "").endswith("app.log") for h in logger.handlers):
        return
    log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "logs", "app.log")
    log_path = os.path.abspath(log_path)
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    handler = logging.FileHandler(log_path)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class WmsService:
    def __init__(self, db: DB) -> None:
        self.db = db

    def seed_demo_data(self, company_id: int, branch_id: int) -> Dict[str, List[int]]:
        """Demo veri: 1 şirket/2 depo/3 lokasyon/5 ürün/1 lot/1 seri + giriş/transfer/sevk/sayım."""
        _ensure_app_logger()
        uom_id = self.db.wms_create_uom(company_id, "ADET", "Adet")
        cat_id = self.db.wms_create_category(company_id, "Genel")
        wh1 = self.db.wms_create_warehouse(company_id, branch_id, "D01", "Ana Depo")
        wh2 = self.db.wms_create_warehouse(company_id, branch_id, "D02", "Yedek Depo")
        loc1 = self.db.wms_create_location(company_id, branch_id, wh1, "R1")
        loc2 = self.db.wms_create_location(company_id, branch_id, wh1, "R2")
        loc3 = self.db.wms_create_location(company_id, branch_id, wh2, "R3")

        items = []
        for idx in range(1, 6):
            items.append(
                self.db.wms_create_item(
                    company_id,
                    f"URUN-{idx:03d}",
                    f"Ürün {idx}",
                    uom_id,
                    category_id=cat_id,
                    track_lot=1 if idx == 1 else 0,
                    track_serial=1 if idx == 2 else 0,
                )
            )

        lot_id = self.db.wms_create_lot(company_id, items[0], "LOT-001", expiry_date="2030-12-31")
        serial_id = self.db.wms_create_serial(company_id, items[1], "SER-001")

        grn_id = self.db.wms_create_doc(
            {
                "company_id": company_id,
                "branch_id": branch_id,
                "doc_type": "GRN",
                "doc_date": "2024-01-10",
                "warehouse_id": wh1,
            },
            [
                {"item_id": items[0], "qty": 10, "unit": "Adet", "unit_price": 5, "target_location_id": loc1, "lot_id": lot_id},
                {"item_id": items[1], "qty": 5, "unit": "Adet", "unit_price": 8, "target_location_id": loc1, "serial_id": serial_id},
            ],
        )
        self.db.wms_post_doc(grn_id)

        trf_id = self.db.wms_create_doc(
            {
                "company_id": company_id,
                "branch_id": branch_id,
                "doc_type": "TRF",
                "doc_date": "2024-01-11",
                "warehouse_id": wh1,
            },
            [
                {
                    "item_id": items[0],
                    "qty": 2,
                    "unit": "Adet",
                    "unit_price": 5,
                    "source_warehouse_id": wh1,
                    "target_warehouse_id": wh2,
                    "source_location_id": loc1,
                    "target_location_id": loc3,
                    "lot_id": lot_id,
                }
            ],
        )
        self.db.wms_post_doc(trf_id)

        ship_id = self.db.wms_create_doc(
            {
                "company_id": company_id,
                "branch_id": branch_id,
                "doc_type": "SHIP",
                "doc_date": "2024-01-12",
                "warehouse_id": wh1,
            },
            [
                {"item_id": items[0], "qty": 1, "unit": "Adet", "unit_price": 5, "source_location_id": loc1, "lot_id": lot_id}
            ],
        )
        self.db.wms_post_doc(ship_id)

        count_id = self.db.wms_create_doc(
            {
                "company_id": company_id,
                "branch_id": branch_id,
                "doc_type": "COUNT",
                "doc_date": "2024-01-13",
                "warehouse_id": wh1,
                "tolerance_qty": 2,
            },
            [
                {"item_id": items[0], "qty": 6, "unit": "Adet", "source_location_id": loc1, "lot_id": lot_id}
            ],
        )
        self.db.wms_post_doc(count_id)

        logger.info("WMS demo data seeded: company=%s branch=%s", company_id, branch_id)
        return {
            "warehouses": [wh1, wh2],
            "locations": [loc1, loc2, loc3],
            "items": items,
            "docs": [grn_id, trf_id, ship_id, count_id],
        }
