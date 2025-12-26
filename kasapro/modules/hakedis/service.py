# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import re
import shutil
import uuid
from typing import Dict, Iterable, Optional, Sequence, Tuple

from ...config import MESSAGE_ATTACHMENT_MAX_BYTES
from ...db.main_db import DB
from ...services.export_service import ExportService
from .indices import HakedisOrgProvider


class HakedisService:
    def __init__(self, db: DB, exporter: Optional[ExportService] = None):
        self.db = db
        self.exporter = exporter
        self.provider = HakedisOrgProvider()

    def _attachments_root(self) -> str:
        data_dir = os.path.dirname(self.db.path)
        base = os.path.splitext(os.path.basename(self.db.path))[0] or "company"
        root = os.path.join(data_dir, "hakedis_attachments", base)
        os.makedirs(root, exist_ok=True)
        return root

    def _safe_filename(self, name: str) -> str:
        base = os.path.basename(name or "")
        base = re.sub(r"[^\w.\-]", "_", base)
        base = re.sub(r"_+", "_", base).strip("_")
        return base or "attachment"

    def _ensure_path_inside(self, root: str, path: str) -> str:
        root_abs = os.path.abspath(root)
        path_abs = os.path.abspath(path)
        if os.path.commonpath([root_abs, path_abs]) != root_abs:
            raise ValueError("Dosya yolu geçersiz.")
        return path_abs

    def save_attachment(self, source_path: str, company_id: int) -> Tuple[str, str, str, int]:
        if not source_path or not os.path.exists(source_path):
            raise ValueError("Dosya bulunamadı.")
        size = int(os.path.getsize(source_path))
        if size > MESSAGE_ATTACHMENT_MAX_BYTES:
            max_mb = MESSAGE_ATTACHMENT_MAX_BYTES / (1024 * 1024)
            raise ValueError(f"Ek dosya boyutu limiti aşıldı ({max_mb:.0f}MB).")
        original = self._safe_filename(os.path.basename(source_path))
        root = self._attachments_root()
        ext = os.path.splitext(original)[1]
        stored_name = f"{uuid.uuid4().hex}{ext}"
        dest = self._ensure_path_inside(root, os.path.join(root, stored_name))
        shutil.copy2(source_path, dest)
        stored_path = os.path.relpath(dest, root)
        return original, stored_name, stored_path, size

    def index_fetch_with_cache(
        self,
        company_id: int,
        index_codes: Sequence[str],
        period: str,
        refresh: bool = True,
    ) -> Dict[str, float]:
        indices: Dict[str, float] = {}
        raw = ""
        if refresh:
            try:
                result = self.provider.fetch_indices(index_codes, period)
                indices = result.indices
                raw = result.raw
            except Exception:
                indices = {}
        for code in index_codes:
            if code in indices:
                try:
                    self.db.hakedis.indices_cache_set(
                        company_id,
                        self.provider.provider_name,
                        code,
                        float(indices[code]),
                        period,
                        raw,
                    )
                except Exception:
                    pass
            else:
                cached = self.db.hakedis.indices_cache_get(
                    company_id,
                    self.provider.provider_name,
                    code,
                    period,
                )
                if cached is not None:
                    indices[code] = cached
        return indices
