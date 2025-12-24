# -*- coding: utf-8 -*-
"""Cari iş kuralları."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..db.main_db import DB
from .export_service import ExportService


class CariService:
    def __init__(self, db: DB, exporter: Optional[ExportService] = None):
        self.db = db
        self.exporter = exporter or ExportService()

    def list(self, q: str = ""):
        return self.db.cari_list(q=q)

    def get(self, cid: int):
        return self.db.cari_get(int(cid))

    def upsert(self, ad: str, tur: str = "", telefon: str = "", notlar: str = "", acilis_bakiye: float = 0.0) -> int:
        return self.db.cari_upsert(ad, tur=tur, telefon=telefon, notlar=notlar, acilis_bakiye=acilis_bakiye)

    def delete(self, cid: int):
        return self.db.cari_delete(int(cid))

    def bakiye(self, cid: int) -> Dict[str, float]:
        return self.db.cari_bakiye(int(cid))

    def ekstre(self, cid: int, date_from: str = "", date_to: str = "", q: str = "") -> Dict[str, Any]:
        return self.db.cari_ekstre(int(cid), date_from=date_from, date_to=date_to, q=q)

    def export_ekstre_excel(self, data: Dict[str, Any], filepath: str):
        return self.exporter.export_cari_ekstre_excel(data, filepath)

    def export_ekstre_pdf(self, data: Dict[str, Any], filepath: str):
        return self.exporter.export_cari_ekstre_pdf(data, filepath)
