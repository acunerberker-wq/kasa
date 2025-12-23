# -*- coding: utf-8 -*-
"""Uygulama ayarları iş kuralları.

Amaç: UI'nin DB facade'ına (db.main_db.DB) doğrudan bağlılığını azaltmak.

Bu servis şimdilik DB'deki settings işlemlerine ince bir katman ekler.
Zamanla validasyon ve audit gibi kurallar buraya taşınabilir.
"""

from __future__ import annotations

import json
from typing import List

from ..db.main_db import DB


class SettingsService:
    def __init__(self, db: DB):
        self.db = db

    def list_currencies(self) -> List[str]:
        return self.db.list_currencies()

    def list_payments(self) -> List[str]:
        return self.db.list_payments()

    def list_categories(self) -> List[str]:
        return self.db.list_categories()

    def set_list(self, key: str, values: List[str]):
        """Listeleri JSON olarak settings tablosuna yazar."""
        payload = json.dumps([str(x) for x in values if str(x).strip()], ensure_ascii=False)
        self.db.set_setting(key, payload)

    def get_list(self, key: str, default: List[str]) -> List[str]:
        """Listeleri JSON olarak okur; bozuksa default döner."""
        raw = self.db.get_setting(key)
        if not raw:
            return default[:]
        try:
            v = json.loads(raw)
            if isinstance(v, list):
                out = [str(x) for x in v if str(x).strip()]
                return out if out else default[:]
        except Exception:
            pass
        return default[:]

    def next_belge_no(self, prefix: str = "BLG") -> str:
        return self.db.next_belge_no(prefix=prefix)
