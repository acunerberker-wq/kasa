# -*- coding: utf-8 -*-

from __future__ import annotations

import sqlite3
from typing import Iterable, List, Optional

from kasapro.utils import now_iso


class HakedisRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    # -----------------
    # Proje/Sözleşme
    # -----------------
    def create_project(
        self,
        idare: str,
        yuklenici: str,
        isin_adi: str,
        sozlesme_bedeli: float,
        baslangic: str,
        bitis: str,
        sure_gun: int,
        artis_eksilis: float,
        avans: float,
    ) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO hakedis_project(
                idare, yuklenici, isin_adi, sozlesme_bedeli,
                baslangic, bitis, sure_gun, artis_eksilis, avans,
                created_at, updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                idare,
                yuklenici,
                isin_adi,
                float(sozlesme_bedeli or 0),
                baslangic,
                bitis,
                int(sure_gun or 0),
                float(artis_eksilis or 0),
                float(avans or 0),
                now_iso(),
                now_iso(),
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def list_projects(self) -> List[sqlite3.Row]:
        return list(self.conn.execute("SELECT * FROM hakedis_project ORDER BY id DESC"))

    def get_project(self, project_id: int) -> Optional[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM hakedis_project WHERE id=?", (int(project_id),)).fetchone()

    # -----------------
    # Poz/Birim Fiyat
    # -----------------
    def add_position(
        self,
        project_id: int,
        kod: str,
        aciklama: str,
        birim: str,
        sozlesme_miktar: float,
        birim_fiyat: float,
    ) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO hakedis_position(project_id, kod, aciklama, birim, sozlesme_miktar, birim_fiyat)
            VALUES(?,?,?,?,?,?)
            """,
            (
                int(project_id),
                kod,
                aciklama,
                birim,
                float(sozlesme_miktar or 0),
                float(birim_fiyat or 0),
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def list_positions(self, project_id: int) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT * FROM hakedis_position WHERE project_id=? ORDER BY id ASC",
                (int(project_id),),
            )
        )

    # -----------------
    # Hakediş Dönemi
    # -----------------
    def add_period(
        self,
        project_id: int,
        hakedis_no: str,
        ay: int,
        yil: int,
        tarih_bas: str,
        tarih_bit: str,
        status: str,
    ) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO hakedis_period(project_id, hakedis_no, ay, yil, tarih_bas, tarih_bit, status)
            VALUES(?,?,?,?,?,?,?)
            """,
            (int(project_id), hakedis_no, int(ay), int(yil), tarih_bas, tarih_bit, status),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def list_periods(self, project_id: int) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT * FROM hakedis_period WHERE project_id=? ORDER BY id ASC",
                (int(project_id),),
            )
        )

    def get_period(self, period_id: int) -> Optional[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM hakedis_period WHERE id=?", (int(period_id),)).fetchone()

    def update_period_status(self, period_id: int, status: str) -> None:
        self.conn.execute(
            "UPDATE hakedis_period SET status=? WHERE id=?",
            (status, int(period_id)),
        )
        self.conn.commit()

    # -----------------
    # Metraj & Ataşman
    # -----------------
    def upsert_measurement(
        self,
        period_id: int,
        position_id: int,
        onceki_miktar: float,
        bu_donem_miktar: float,
        kumulatif_miktar: float,
    ) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO hakedis_measurement(period_id, position_id, onceki_miktar, bu_donem_miktar, kumulatif_miktar)
            VALUES(?,?,?,?,?)
            ON CONFLICT(period_id, position_id) DO UPDATE SET
                onceki_miktar=excluded.onceki_miktar,
                bu_donem_miktar=excluded.bu_donem_miktar,
                kumulatif_miktar=excluded.kumulatif_miktar
            """,
            (
                int(period_id),
                int(position_id),
                float(onceki_miktar or 0),
                float(bu_donem_miktar or 0),
                float(kumulatif_miktar or 0),
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid or 0)

    def list_measurements(self, period_id: int) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT * FROM hakedis_measurement WHERE period_id=? ORDER BY id ASC",
                (int(period_id),),
            )
        )

    def sum_previous_measurements(self, position_id: int, before_period_id: int) -> float:
        row = self.conn.execute(
            """
            SELECT COALESCE(SUM(bu_donem_miktar), 0) AS toplam
            FROM hakedis_measurement
            WHERE position_id=? AND period_id < ?
            """,
            (int(position_id), int(before_period_id)),
        ).fetchone()
        if not row:
            return 0.0
        try:
            return float(row["toplam"])
        except Exception:
            return 0.0

    def add_attachment(self, period_id: int, filename: str, stored_name: str, size_bytes: int) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO hakedis_attachment(period_id, filename, stored_name, size_bytes, created_at)
            VALUES(?,?,?,?,?)
            """,
            (int(period_id), filename, stored_name, int(size_bytes), now_iso()),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def list_attachments(self, period_id: int) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT * FROM hakedis_attachment WHERE period_id=? ORDER BY id DESC",
                (int(period_id),),
            )
        )

    # -----------------
    # Kesintiler
    # -----------------
    def add_deduction(
        self,
        period_id: int,
        ad: str,
        tip: str,
        deger: float,
        hesaplanan_tutar: float,
    ) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO hakedis_deduction(period_id, ad, tip, deger, hesaplanan_tutar)
            VALUES(?,?,?,?,?)
            """,
            (int(period_id), ad, tip, float(deger or 0), float(hesaplanan_tutar or 0)),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def list_deductions(self, period_id: int) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT * FROM hakedis_deduction WHERE period_id=? ORDER BY id ASC",
                (int(period_id),),
            )
        )

    # -----------------
    # Endeks cache/selection
    # -----------------
    def upsert_indices_cache(self, source: str, dataset_key: str, payload_json: str, fetched_at: str) -> None:
        self.conn.execute(
            """
            INSERT INTO hakedis_indices_cache(source, dataset_key, payload_json, fetched_at)
            VALUES(?,?,?,?)
            ON CONFLICT(source, dataset_key) DO UPDATE SET
                payload_json=excluded.payload_json,
                fetched_at=excluded.fetched_at
            """,
            (source, dataset_key, payload_json, fetched_at),
        )
        self.conn.commit()

    def get_indices_cache(self, source: str, dataset_key: str) -> Optional[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM hakedis_indices_cache WHERE source=? AND dataset_key=?",
            (source, dataset_key),
        ).fetchone()

    def set_index_selection(self, project_id: int, dataset_key: str, enabled: int) -> None:
        self.conn.execute(
            """
            INSERT INTO hakedis_index_selection(project_id, dataset_key, enabled)
            VALUES(?,?,?)
            ON CONFLICT(project_id, dataset_key) DO UPDATE SET enabled=excluded.enabled
            """,
            (int(project_id), dataset_key, int(enabled)),
        )
        self.conn.commit()

    def list_index_selections(self, project_id: int) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT * FROM hakedis_index_selection WHERE project_id=? ORDER BY dataset_key",
                (int(project_id),),
            )
        )

    # -----------------
    # Audit Log
    # -----------------
    def add_audit_log(
        self,
        user_id: Optional[int],
        action: str,
        entity: str,
        entity_id: Optional[int],
        detail: str = "",
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO hakedis_audit_log(ts, user_id, action, entity, entity_id, detail)
            VALUES(?,?,?,?,?,?)
            """,
            (now_iso(), user_id, action, entity, entity_id, detail or ""),
        )
        self.conn.commit()

    def list_audit_logs(self, limit: int = 200) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT * FROM hakedis_audit_log ORDER BY id DESC LIMIT ?",
                (int(limit),),
            )
        )

    # -----------------
    # Rol
    # -----------------
    def set_user_role(self, project_id: int, user_id: int, role: str) -> None:
        self.conn.execute(
            """
            INSERT INTO hakedis_user_roles(project_id, user_id, role)
            VALUES(?,?,?)
            ON CONFLICT(project_id, user_id) DO UPDATE SET role=excluded.role
            """,
            (int(project_id), int(user_id), role),
        )
        self.conn.commit()

    def get_user_role(self, project_id: int, user_id: int) -> Optional[str]:
        row = self.conn.execute(
            "SELECT role FROM hakedis_user_roles WHERE project_id=? AND user_id=?",
            (int(project_id), int(user_id)),
        ).fetchone()
        if not row:
            return None
        try:
            return str(row["role"])
        except Exception:
            return None

    def list_user_roles(self, project_id: int) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT * FROM hakedis_user_roles WHERE project_id=? ORDER BY id ASC",
                (int(project_id),),
            )
        )
