# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import re
import shutil
import threading
import uuid
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from kasapro.config import DATA_DIRNAME, HAS_OPENPYXL
from kasapro.db.main_db import DB
from kasapro.services.export_service import ExportService
from kasapro.utils import fmt_amount, now_iso

from .providers import deserialize_indices, fetch_indices, serialize_indices
from .providers.hakedis_org import IndexRow
from .repo import HakedisRepo


ALLOWED_STATUSES = [
    "Taslak",
    "Kontrole Gönderildi",
    "Onaylandı",
    "Tahakkuk",
    "Ödendi",
    "İtirazlı",
]


STATUS_TRANSITIONS = {
    "Taslak": {"Kontrole Gönderildi"},
    "Kontrole Gönderildi": {"Onaylandı", "İtirazlı"},
    "Onaylandı": {"Tahakkuk"},
    "Tahakkuk": {"Ödendi"},
    "Ödendi": set(),
    "İtirazlı": {"Kontrole Gönderildi"},
}


@dataclass
class PriceDiffRow:
    dataset: str
    base_value: float
    current_value: float
    coefficient: float


class HakedisService:
    def __init__(self, db: DB, exporter: Optional[ExportService] = None):
        self.db = db
        self.repo: HakedisRepo = db.hakedis
        self.exporter = exporter or ExportService()

    # -----------------
    # Rol kontrolü
    # -----------------
    def require_role(self, project_id: int, user_id: int, allowed_roles: Sequence[str], is_admin: bool = False) -> None:
        if is_admin:
            return
        role = self.repo.get_user_role(project_id, user_id)
        if role not in allowed_roles:
            raise PermissionError("Hakediş işlemi için yetkiniz yok.")

    # -----------------
    # Proje / Poz / Dönem
    # -----------------
    def create_project(self, user_id: Optional[int], **kwargs) -> int:
        pid = self.repo.create_project(**kwargs)
        self.repo.add_audit_log(user_id, "create", "project", pid, f"Proje oluşturuldu: {kwargs.get('isin_adi','')}")
        return pid

    def add_position(self, user_id: Optional[int], project_id: int, **kwargs) -> int:
        pos_id = self.repo.add_position(project_id=project_id, **kwargs)
        self.repo.add_audit_log(user_id, "create", "position", pos_id, f"Poz eklendi: {kwargs.get('kod','')}")
        return pos_id

    def add_period(self, user_id: Optional[int], project_id: int, **kwargs) -> int:
        period_id = self.repo.add_period(project_id=project_id, **kwargs)
        self.repo.add_audit_log(user_id, "create", "period", period_id, "Hakediş dönemi oluşturuldu")
        return period_id

    def update_period_status(self, user_id: Optional[int], project_id: int, period_id: int, new_status: str, is_admin: bool = False) -> None:
        self.require_role(project_id, user_id or 0, ["hazirlayan", "kontrol", "idare"], is_admin=is_admin)
        row = self.repo.get_period(period_id)
        if not row:
            raise ValueError("Hakediş dönemi bulunamadı.")
        current = str(row["status"])
        if new_status not in ALLOWED_STATUSES:
            raise ValueError("Geçersiz hakediş statüsü.")
        allowed = STATUS_TRANSITIONS.get(current, set())
        if new_status not in allowed:
            raise ValueError(f"{current} -> {new_status} geçişi izinli değil.")
        self.repo.update_period_status(period_id, new_status)
        self.repo.add_audit_log(user_id, "update", "period", period_id, f"Statü güncellendi: {current} -> {new_status}")

    # -----------------
    # Metraj hesapları
    # -----------------
    def record_measurement(self, user_id: Optional[int], period_id: int, position_id: int, bu_donem_miktar: float) -> None:
        onceki = self.repo.sum_previous_measurements(position_id, period_id)
        kumulatif = onceki + float(bu_donem_miktar or 0)
        self.repo.upsert_measurement(period_id, position_id, onceki, bu_donem_miktar, kumulatif)
        self.repo.add_audit_log(user_id, "update", "measurement", None, f"Metraj güncellendi: poz={position_id}")

    def period_summary(self, period_id: int) -> Dict[str, float]:
        period = self.repo.get_period(period_id)
        if not period:
            raise ValueError("Hakediş dönemi bulunamadı.")
        project_id = int(period["project_id"])
        positions = self.repo.list_positions(project_id)
        measurements = {int(r["position_id"]): r for r in self.repo.list_measurements(period_id)}

        this_total = 0.0
        prev_total = 0.0
        for pos in positions:
            pos_id = int(pos["id"])
            unit_price = float(pos["birim_fiyat"] or 0)
            m = measurements.get(pos_id)
            bu_donem = float(m["bu_donem_miktar"]) if m else 0.0
            onceki = float(m["onceki_miktar"]) if m else self.repo.sum_previous_measurements(pos_id, period_id)
            this_total += bu_donem * unit_price
            prev_total += onceki * unit_price
        return {
            "this_total": this_total,
            "previous_total": prev_total,
            "cumulative_total": this_total + prev_total,
        }

    # -----------------
    # Kesintiler
    # -----------------
    def calculate_deductions_total(self, period_id: int, base_total: float) -> float:
        total = 0.0
        for row in self.repo.list_deductions(period_id):
            tip = str(row["tip"])
            deger = float(row["deger"] or 0)
            if tip == "oran":
                tutar = base_total * (deger / 100.0)
            else:
                tutar = deger
            total += tutar
        return total

    def add_deduction(self, user_id: Optional[int], period_id: int, ad: str, tip: str, deger: float, base_total: float) -> int:
        if tip not in {"oran", "tutar"}:
            raise ValueError("Kesinti tipi 'oran' veya 'tutar' olmalı.")
        hesaplanan = (base_total * (deger / 100.0)) if tip == "oran" else deger
        did = self.repo.add_deduction(period_id, ad, tip, deger, hesaplanan)
        self.repo.add_audit_log(user_id, "create", "deduction", did, f"Kesinti eklendi: {ad}")
        return did

    # -----------------
    # Ataşman
    # -----------------
    def _attachments_root(self) -> str:
        data_dir = os.path.dirname(self.db.path)
        base = os.path.splitext(os.path.basename(self.db.path))[0] or "company"
        root = os.path.join(data_dir, DATA_DIRNAME, "attachments", base, "hakedis")
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

    def save_attachment(self, period_id: int, source_path: str) -> Tuple[str, str, int]:
        if not source_path or not os.path.exists(source_path):
            raise ValueError("Dosya bulunamadı.")
        size = int(os.path.getsize(source_path))
        original = self._safe_filename(os.path.basename(source_path))
        root = self._attachments_root()
        ext = os.path.splitext(original)[1]
        stored_name = f"{uuid.uuid4().hex}{ext}"
        dest = self._ensure_path_inside(root, os.path.join(root, stored_name))
        shutil.copy2(source_path, dest)
        self.repo.add_attachment(period_id, original, stored_name, size)
        return original, stored_name, size

    def get_attachment_path(self, stored_name: str) -> str:
        root = self._attachments_root()
        safe = self._safe_filename(stored_name)
        return self._ensure_path_inside(root, os.path.join(root, safe))

    # -----------------
    # Endeks / Fiyat Farkı
    # -----------------
    def fetch_indices_with_cache(
        self,
        selected_sets: Iterable[str],
        allow_network: bool = True,
        fetcher=fetch_indices,
    ) -> Dict[str, List[IndexRow]]:
        selected = [s for s in selected_sets if s]
        if allow_network:
            try:
                indices = fetcher(selected)
                for key, rows in indices.items():
                    payload = serialize_indices({key: rows})
                    self.repo.upsert_indices_cache("hakedis_org", key, payload, now_iso())
                return indices
            except Exception:
                pass
        cached: Dict[str, List[IndexRow]] = {}
        for key in selected:
            row = self.repo.get_indices_cache("hakedis_org", key)
            if row and row["payload_json"]:
                parsed = deserialize_indices(str(row["payload_json"]))
                cached.update(parsed)
        if not cached:
            raise RuntimeError("Endeks verisi alınamadı ve cache boş.")
        return cached

    def set_index_selections(self, project_id: int, selections: Dict[str, bool]) -> None:
        for key, enabled in selections.items():
            self.repo.set_index_selection(project_id, key, 1 if enabled else 0)

    def get_selected_index_sets(self, project_id: int) -> List[str]:
        rows = self.repo.list_index_selections(project_id)
        out = []
        for r in rows:
            if int(r["enabled"] or 0) == 1:
                out.append(str(r["dataset_key"]))
        return out

    def calculate_price_difference(self, indices: Dict[str, List[IndexRow]]) -> List[PriceDiffRow]:
        rows: List[PriceDiffRow] = []
        for key, series in indices.items():
            if len(series) < 2:
                continue
            base_value = series[0].value
            current_value = series[-1].value
            if base_value == 0:
                continue
            coefficient = current_value / base_value
            rows.append(
                PriceDiffRow(
                    dataset=key,
                    base_value=base_value,
                    current_value=current_value,
                    coefficient=coefficient,
                )
            )
        return rows

    # -----------------
    # Rapor / Export
    # -----------------
    def export_reports(self, period_id: int, directory: str) -> Dict[str, str]:
        period = self.repo.get_period(period_id)
        if not period:
            raise ValueError("Hakediş dönemi bulunamadı.")
        project_id = int(period["project_id"])
        project = self.repo.get_project(project_id)
        positions = self.repo.list_positions(project_id)
        measurements = {int(r["position_id"]): r for r in self.repo.list_measurements(period_id)}

        summary = self.period_summary(period_id)
        ded_total = self.calculate_deductions_total(period_id, summary["this_total"])

        os.makedirs(directory, exist_ok=True)
        base_name = f"hakedis_{project_id}_{period_id}"

        summary_headers = ["Kalem", "Tutar"]
        summary_rows = [
            ["Bu Dönem", fmt_amount(summary["this_total"])],
            ["Önceki", fmt_amount(summary["previous_total"])],
            ["Kümülatif", fmt_amount(summary["cumulative_total"])],
            ["Kesintiler", fmt_amount(ded_total)],
        ]
        summary_csv = os.path.join(directory, f"{base_name}_ozet.csv")
        self.exporter.export_table_csv(summary_headers, summary_rows, summary_csv)
        summary_xlsx = ""
        if HAS_OPENPYXL:
            summary_xlsx = os.path.join(directory, f"{base_name}_ozet.xlsx")
            self.exporter.export_table_excel(summary_headers, summary_rows, summary_xlsx)

        poz_headers = ["Poz", "Açıklama", "Birim", "Birim Fiyat", "Bu Dönem", "Kümülatif", "Tutar"]
        poz_rows = []
        for pos in positions:
            pos_id = int(pos["id"])
            m = measurements.get(pos_id)
            bu_donem = float(m["bu_donem_miktar"]) if m else 0.0
            kumulatif = float(m["kumulatif_miktar"]) if m else bu_donem
            unit_price = float(pos["birim_fiyat"] or 0)
            poz_rows.append(
                [
                    pos["kod"],
                    pos["aciklama"],
                    pos["birim"],
                    fmt_amount(unit_price),
                    bu_donem,
                    kumulatif,
                    fmt_amount(kumulatif * unit_price),
                ]
            )

        poz_csv = os.path.join(directory, f"{base_name}_poz.csv")
        self.exporter.export_table_csv(poz_headers, poz_rows, poz_csv)
        poz_xlsx = ""
        if HAS_OPENPYXL:
            poz_xlsx = os.path.join(directory, f"{base_name}_poz.xlsx")
            self.exporter.export_table_excel(poz_headers, poz_rows, poz_xlsx)

        metraj_headers = ["Poz", "Önceki", "Bu Dönem", "Kümülatif"]
        metraj_rows = []
        for pos in positions:
            pos_id = int(pos["id"])
            m = measurements.get(pos_id)
            onceki = float(m["onceki_miktar"]) if m else 0.0
            bu_donem = float(m["bu_donem_miktar"]) if m else 0.0
            kumulatif = float(m["kumulatif_miktar"]) if m else onceki + bu_donem
            metraj_rows.append([pos["kod"], onceki, bu_donem, kumulatif])

        metraj_csv = os.path.join(directory, f"{base_name}_metraj.csv")
        self.exporter.export_table_csv(metraj_headers, metraj_rows, metraj_csv)
        metraj_xlsx = ""
        if HAS_OPENPYXL:
            metraj_xlsx = os.path.join(directory, f"{base_name}_metraj.xlsx")
            self.exporter.export_table_excel(metraj_headers, metraj_rows, metraj_xlsx)

        pdf_path = os.path.join(directory, f"{base_name}_ozet.pdf")
        self._export_summary_pdf(project, period, summary, ded_total, pdf_path)

        return {
            "summary_csv": summary_csv,
            "poz_csv": poz_csv,
            "metraj_csv": metraj_csv,
            "summary_xlsx": summary_xlsx,
            "poz_xlsx": poz_xlsx,
            "metraj_xlsx": metraj_xlsx,
            "summary_pdf": pdf_path,
        }

    def export_reports_async(self, period_id: int, directory: str, callback=None) -> None:
        def worker():
            result = self.export_reports(period_id, directory)
            if callback:
                callback(result)

        threading.Thread(target=worker, daemon=True).start()

    def _export_summary_pdf(self, project, period, summary, deductions_total, filepath: str) -> None:
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib import colors
            from kasapro.utils import ensure_pdf_fonts
        except Exception:
            self._write_simple_pdf(filepath, summary, deductions_total)
            return

        doc = SimpleDocTemplate(filepath, pagesize=A4, leftMargin=28, rightMargin=28, topMargin=28, bottomMargin=28)
        font_reg, font_bold = ensure_pdf_fonts()

        styles = getSampleStyleSheet()
        for k in ("Normal", "Title", "Heading1", "Heading2"):
            if k in styles:
                styles[k].fontName = (font_bold if k != "Normal" else font_reg)

        title = f"Hakediş Özeti - {project['isin_adi'] if project else ''}"
        story = [Paragraph(f"<b>{title}</b>", styles["Title"])]
        story.append(Spacer(1, 8))
        story.append(Paragraph(f"Hakediş No: {period['hakedis_no']}", styles["Normal"]))
        story.append(Paragraph(f"Dönem: {period['ay']:02d}/{period['yil']}", styles["Normal"]))
        story.append(Spacer(1, 10))

        table_data = [
            ["Kalem", "Tutar"],
            ["Bu Dönem", fmt_amount(summary["this_total"])],
            ["Önceki", fmt_amount(summary["previous_total"])],
            ["Kümülatif", fmt_amount(summary["cumulative_total"])],
            ["Kesintiler", fmt_amount(deductions_total)],
        ]
        tbl = Table(table_data, repeatRows=1)
        tbl.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), font_bold),
            ("FONTNAME", (0, 1), (-1, -1), font_reg),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ]))
        story.append(tbl)
        doc.build(story)

    def _write_simple_pdf(self, filepath: str, summary, deductions_total) -> None:
        lines = [
            "%PDF-1.4",
            "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj",
            "2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj",
            "3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R >> endobj",
            "4 0 obj << /Length 5 0 R >> stream",
            "BT /F1 12 Tf 50 780 Td (Hakediş Özeti) Tj ET",
            f"BT /F1 10 Tf 50 760 Td (Bu Dönem: {summary['this_total']:.2f}) Tj ET",
            f"BT /F1 10 Tf 50 745 Td (Önceki: {summary['previous_total']:.2f}) Tj ET",
            f"BT /F1 10 Tf 50 730 Td (Kümülatif: {summary['cumulative_total']:.2f}) Tj ET",
            f"BT /F1 10 Tf 50 715 Td (Kesintiler: {deductions_total:.2f}) Tj ET",
            "endstream endobj",
            "5 0 obj 0 endobj",
            "xref 0 6",
            "0000000000 65535 f ",
            "0000000010 00000 n ",
            "0000000060 00000 n ",
            "0000000111 00000 n ",
            "0000000200 00000 n ",
            "0000000000 00000 n ",
            "trailer << /Root 1 0 R /Size 6 >>",
            "startxref",
            "0",
            "%%EOF",
        ]
        with open(filepath, "wb") as handle:
            handle.write("\n".join(lines).encode("latin-1", errors="ignore"))

    # -----------------
    # Demo veri
    # -----------------
    def seed_demo(self, user_id: Optional[int] = None) -> Dict[str, int]:
        project_id = self.create_project(
            user_id,
            idare="Örnek İdare",
            yuklenici="Örnek Yüklenici",
            isin_adi="Örnek Yapım İşi",
            sozlesme_bedeli=1200000,
            baslangic="2024-01-01",
            bitis="2024-12-31",
            sure_gun=365,
            artis_eksilis=0,
            avans=100000,
        )
        pos1 = self.add_position(
            user_id,
            project_id=project_id,
            kod="PZ-001",
            aciklama="Kazı işleri",
            birim="m3",
            sozlesme_miktar=1000,
            birim_fiyat=250,
        )
        period_id = self.add_period(
            user_id,
            project_id=project_id,
            hakedis_no="1",
            ay=1,
            yil=2024,
            tarih_bas="2024-01-01",
            tarih_bit="2024-01-31",
            status="Taslak",
        )
        self.record_measurement(user_id, period_id, pos1, bu_donem_miktar=100)
        return {"project_id": project_id, "period_id": period_id}
