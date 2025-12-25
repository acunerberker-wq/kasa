# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from .repo import IntegrationRepo


class GenericCSVConnector:
    def __init__(self, repo: IntegrationRepo):
        self.repo = repo

    def export_cariler(self, conn, output_dir: Path) -> Path:
        rows = conn.execute("SELECT id, ad, tur, telefon FROM cariler ORDER BY id").fetchall()
        path = output_dir / "cariler.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "ad", "tur", "telefon"])
            for r in rows:
                writer.writerow([r["id"], r["ad"], r["tur"], r["telefon"]])
        return path

    def export_faturalar(self, conn, output_dir: Path) -> Path:
        rows = conn.execute(
            "SELECT id, fatura_no, cari_ad, tarih, genel_toplam FROM fatura ORDER BY id"
        ).fetchall()
        path = output_dir / "faturalar.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "fatura_no", "cari_ad", "tarih", "genel_toplam"])
            for r in rows:
                writer.writerow([r["id"], r["fatura_no"], r["cari_ad"], r["tarih"], r["genel_toplam"]])
        return path

    def export_tahsilatlar(self, conn, output_dir: Path) -> Path:
        rows = conn.execute(
            "SELECT id, fatura_id, tarih, tutar FROM fatura_odeme ORDER BY id"
        ).fetchall()
        path = output_dir / "tahsilatlar.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "fatura_id", "tarih", "tutar"])
            for r in rows:
                writer.writerow([r["id"], r["fatura_id"], r["tarih"], r["tutar"]])
        return path

    def import_csv(self, job_id: int, entity_type: str, csv_path: Path) -> Tuple[int, int]:
        ok = 0
        failed = 0
        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                payload = json.dumps(row, ensure_ascii=False)
                if not row or not any(str(v or "").strip() for v in row.values()):
                    failed += 1
                    self.repo.import_item_add(job_id, entity_type, payload, status="failed", error="Eksik veri")
                    continue
                ok += 1
                self.repo.import_item_add(job_id, entity_type, payload, status="staged")
        return ok, failed
