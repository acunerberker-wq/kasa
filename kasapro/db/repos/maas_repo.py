# -*- coding: utf-8 -*-

from __future__ import annotations

import sqlite3
from typing import Any, List, Optional

from ...utils import parse_date_smart


class MaasRepo:
    """Şirket Maaş Takibi veri erişim katmanı."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    # -----------------
    # Çalışanlar
    # -----------------
    def calisan_list(self, q: str = "", only_active: bool = False) -> List[sqlite3.Row]:
        clauses = []
        params: List[Any] = []
        q = (q or "").strip()
        if q:
            clauses.append("(c.ad LIKE ? OR c.notlar LIKE ?)")
            params += [f"%{q}%", f"%{q}%"]
        if only_active:
            clauses.append("c.aktif=1")
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"""
        SELECT c.*, m.ad AS meslek_ad
        FROM maas_calisan c
        LEFT JOIN maas_meslek m ON m.id=c.meslek_id
        {where}
        ORDER BY c.ad
        """
        return list(self.conn.execute(sql, tuple(params)))

    def calisan_add(
        self,
        ad: str,
        aylik_tutar: float,
        para: str = "TL",
        aktif: int = 1,
        notlar: str = "",
        meslek_id: Optional[int] = None,
    ) -> int:
        cur = self.conn.execute(
            "INSERT INTO maas_calisan(ad,aylik_tutar,para,meslek_id,aktif,notlar) VALUES(?,?,?,?,?,?)",
            (str(ad).strip(), float(aylik_tutar), para or "TL", int(meslek_id) if meslek_id is not None else None, int(aktif), notlar or ""),
        )
        self.conn.commit()
        return int(cur.lastrowid or 0)

    def calisan_get_by_name(self, ad: str) -> Optional[sqlite3.Row]:
        ad = (ad or "").strip()
        if not ad:
            return None
        return self.conn.execute("SELECT * FROM maas_calisan WHERE ad=?", (ad,)).fetchone()

    def calisan_get_or_create(self, ad: str, *, para: str = "TL", default_amount: float = 0.0) -> int:
        """Çalışan yoksa oluşturup id döndürür."""
        ad = (ad or "").strip()
        if not ad:
            raise ValueError("Çalışan adı boş olamaz")
        r = self.calisan_get_by_name(ad)
        if r:
            return int(r["id"])
        return self.calisan_add(ad, float(default_amount), para=para or "TL", aktif=1, notlar="")

    def calisan_update(
        self,
        cid: int,
        ad: str,
        aylik_tutar: float,
        para: str = "TL",
        aktif: int = 1,
        notlar: str = "",
        meslek_id: Optional[int] = None,
    ) -> None:
        self.conn.execute(
            "UPDATE maas_calisan SET ad=?, aylik_tutar=?, para=?, meslek_id=?, aktif=?, notlar=? WHERE id=?",
            (
                str(ad).strip(),
                float(aylik_tutar),
                para or "TL",
                int(meslek_id) if meslek_id is not None else None,
                int(aktif),
                notlar or "",
                int(cid),
            ),
        )
        self.conn.commit()

    def calisan_set_active(self, cid: int, aktif: int) -> None:
        """Çalışanı aktif/pasif yapar. (0 = aktif değil)"""
        self.conn.execute("UPDATE maas_calisan SET aktif=? WHERE id=?", (int(aktif), int(cid)))
        self.conn.commit()

    # -----------------
    # Meslekler
    # -----------------
    def meslek_list(self, q: str = "", only_active: bool = False) -> List[sqlite3.Row]:
        clauses = []
        params: List[Any] = []
        q = (q or "").strip()
        if q:
            clauses.append("(ad LIKE ? OR notlar LIKE ?)")
            params += [f"%{q}%", f"%{q}%"]
        if only_active:
            clauses.append("aktif=1")
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT * FROM maas_meslek {where} ORDER BY ad"
        return list(self.conn.execute(sql, tuple(params)))

    def meslek_add(self, ad: str, aktif: int = 1, notlar: str = "") -> int:
        cur = self.conn.execute(
            "INSERT INTO maas_meslek(ad,aktif,notlar) VALUES(?,?,?)",
            (str(ad).strip(), int(aktif), notlar or ""),
        )
        self.conn.commit()
        return int(cur.lastrowid or 0)

    def meslek_update(self, mid: int, ad: str, aktif: int = 1, notlar: str = "") -> None:
        self.conn.execute(
            "UPDATE maas_meslek SET ad=?, aktif=?, notlar=? WHERE id=?",
            (str(ad).strip(), int(aktif), notlar or "", int(mid)),
        )
        self.conn.commit()

    def meslek_set_active(self, mid: int, aktif: int) -> None:
        """Mesleği aktif/pasif yapar. (0 = aktif değil)"""
        self.conn.execute("UPDATE maas_meslek SET aktif=? WHERE id=?", (int(aktif), int(mid)))
        self.conn.commit()

    def meslek_delete(self, mid: int) -> None:
        # Çalışanlarda bağı kopar
        try:
            self.conn.execute("UPDATE maas_calisan SET meslek_id=NULL WHERE meslek_id=?", (int(mid),))
        except Exception:
            pass
        self.conn.execute("DELETE FROM maas_meslek WHERE id=?", (int(mid),))
        self.conn.commit()

    def calisan_delete(self, cid: int) -> None:
        # Ödemeleri de sil
        self.conn.execute("DELETE FROM maas_odeme WHERE calisan_id=?", (int(cid),))
        self.conn.execute("DELETE FROM maas_calisan WHERE id=?", (int(cid),))
        self.conn.commit()

    # -----------------
    # Aylık Maaşlar
    # -----------------
    def ensure_donem(self, donem: str) -> None:
        """İlgili dönem için aktif tüm çalışanlar adına maaş satırı oluşturur (yoksa)."""
        donem = (donem or "").strip()
        if not donem:
            return
        calisanlar = self.calisan_list(only_active=True)
        for c in calisanlar:
            try:
                self.conn.execute(
                    """
                    INSERT OR IGNORE INTO maas_odeme(donem, calisan_id, tutar, para, odendi, odeme_tarihi, aciklama)
                    VALUES(?,?,?,?,0,'','')
                    """,
                    (donem, int(c["id"]), float(c["aylik_tutar"]), str(c["para"] or "TL")),
                )
            except Exception:
                pass
        self.conn.commit()

    def donem_list(self, limit: int = 36) -> List[str]:
        try:
            lim = int(limit)
        except Exception:
            lim = 36
        if lim <= 0:
            lim = 36
        rows = list(
            self.conn.execute(
                "SELECT DISTINCT donem FROM maas_odeme WHERE donem<>'' ORDER BY donem DESC LIMIT ?",
                (lim,),
            )
        )
        out: List[str] = []
        for r in rows:
            try:
                out.append(str(r[0]))
            except Exception:
                pass
        return out

    def odeme_list(self, donem: str = "", q: str = "", odendi: Optional[int] = None, *, include_inactive: bool = False) -> List[sqlite3.Row]:
        clauses = []
        params: List[Any] = []
        if (donem or "").strip():
            clauses.append("p.donem=?")
            params.append(donem)
        if odendi is not None:
            clauses.append("p.odendi=?")
            params.append(int(odendi))
        if (q or "").strip():
            clauses.append("(e.ad LIKE ? OR p.aciklama LIKE ?)")
            params += [f"%{q}%", f"%{q}%"]
        if not include_inactive:
            clauses.append("e.aktif=1")
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"""
        SELECT p.*, e.ad calisan_ad
        FROM maas_odeme p
        JOIN maas_calisan e ON e.id=p.calisan_id
        {where}
        ORDER BY p.donem DESC, e.ad
        """
        return list(self.conn.execute(sql, tuple(params)))


    def odeme_get(self, oid: int) -> Optional[sqlite3.Row]:
        """Tek bir maaş ödeme kaydını getir (çalışan adı dahil)."""
        return self.conn.execute(
            """
            SELECT p.*, e.ad calisan_ad
            FROM maas_odeme p
            JOIN maas_calisan e ON e.id=p.calisan_id
            WHERE p.id=?
            """,
            (int(oid),),
        ).fetchone()

    def odeme_set_paid(self, oid: int, odendi: int, odeme_tarihi: str = "") -> None:
        self.conn.execute(
            "UPDATE maas_odeme SET odendi=?, odeme_tarihi=? WHERE id=?",
            (int(odendi), parse_date_smart(odeme_tarihi) if odeme_tarihi else "", int(oid)),
        )
        self.conn.commit()

    def odeme_update_amount(self, oid: int, tutar: float, para: str = "TL", aciklama: str = "") -> None:
        self.conn.execute(
            "UPDATE maas_odeme SET tutar=?, para=?, aciklama=? WHERE id=?",
            (float(tutar), para or "TL", aciklama or "", int(oid)),
        )
        self.conn.commit()

    def odeme_upsert_from_excel(
        self,
        donem: str,
        calisan_ad: str,
        tutar: float,
        *,
        para: str = "TL",
        odendi: int = 0,
        odeme_tarihi: str = "",
        aciklama: str = "",
    ) -> int:
        """Excel import için maaş satırı upsert.

        - Çalışan yoksa oluşturur
        - (calisan_id, donem) unique olduğu için INSERT OR IGNORE + UPDATE kullanır
        """
        donem = (donem or "").strip()
        if not donem:
            raise ValueError("Dönem (YYYY-MM) boş olamaz")

        emp_id = self.calisan_get_or_create(calisan_ad, para=para or "TL", default_amount=float(tutar or 0.0))

        self.conn.execute(
            """
            INSERT OR IGNORE INTO maas_odeme(donem, calisan_id, tutar, para, odendi, odeme_tarihi, aciklama)
            VALUES(?,?,?,?,?,?,?)
            """,
            (
                donem,
                int(emp_id),
                float(tutar or 0.0),
                para or "TL",
                int(odendi or 0),
                parse_date_smart(odeme_tarihi) if odeme_tarihi else "",
                aciklama or "",
            ),
        )

        # update (varsa)
        self.conn.execute(
            """
            UPDATE maas_odeme
            SET tutar=?, para=?, odendi=?, odeme_tarihi=?, aciklama=?
            WHERE donem=? AND calisan_id=?
            """,
            (
                float(tutar or 0.0),
                para or "TL",
                int(odendi or 0),
                parse_date_smart(odeme_tarihi) if odeme_tarihi else "",
                aciklama or "",
                donem,
                int(emp_id),
            ),
        )
        self.conn.commit()

        row = self.conn.execute(
            "SELECT id FROM maas_odeme WHERE donem=? AND calisan_id=?",
            (donem, int(emp_id)),
        ).fetchone()
        return int(row[0]) if row else 0

    def odeme_link_bank(self, oid: int, banka_hareket_id: int, *, score: float = 0.0, note: str = "") -> None:
        self.conn.execute(
            "UPDATE maas_odeme SET banka_hareket_id=?, banka_match_score=?, banka_match_note=? WHERE id=?",
            (int(banka_hareket_id), float(score), str(note or ""), int(oid)),
        )
        self.conn.commit()

    def odeme_clear_bank_link(self, oid: int) -> None:
        self.conn.execute(
            "UPDATE maas_odeme SET banka_hareket_id=NULL, banka_match_score=NULL, banka_match_note='' WHERE id=?",
            (int(oid),),
        )
        self.conn.commit()

    def donem_ozet(self, donem: str, *, include_inactive: bool = False) -> sqlite3.Row:
        """Dönem toplam/ödenen/ödenmeyen. (Varsayılan: pasif çalışanlar hariç)"""
        extra = "" if include_inactive else "AND e.aktif=1"
        row = self.conn.execute(
            f"""
            SELECT
                SUM(p.tutar) AS toplam,
                SUM(CASE WHEN p.odendi=1 THEN p.tutar ELSE 0 END) AS odenen,
                SUM(CASE WHEN p.odendi=0 THEN p.tutar ELSE 0 END) AS odenmeyen,
                SUM(CASE WHEN p.odendi=1 THEN 1 ELSE 0 END) AS odenen_adet,
                COUNT(*) AS adet
            FROM maas_odeme p
            JOIN maas_calisan e ON e.id=p.calisan_id
            WHERE p.donem=? {extra}
            """,
            (donem,),
        ).fetchone()
        return row


    def aylik_toplamlar(self, limit: int = 24, *, include_inactive: bool = False) -> List[sqlite3.Row]:
        try:
            lim = int(limit)
        except Exception:
            lim = 24
        if lim <= 0:
            lim = 24
        extra = "" if include_inactive else "AND e.aktif=1"
        return list(
            self.conn.execute(
                f"""
                SELECT
                    p.donem,
                    SUM(p.tutar) toplam,
                    SUM(CASE WHEN p.odendi=1 THEN p.tutar ELSE 0 END) odenen,
                    SUM(CASE WHEN p.odendi=0 THEN p.tutar ELSE 0 END) odenmeyen
                FROM maas_odeme p
                JOIN maas_calisan e ON e.id=p.calisan_id
                WHERE p.donem<>'' {extra}
                GROUP BY p.donem
                ORDER BY p.donem DESC
                LIMIT ?
                """,
                (lim,),
            )
        )


    # -----------------
    # Maaş - Hesap Hareketleri (Banka eşleştirme geçmişi)
    # -----------------
    def hesap_hareket_add(
        self,
        *,
        donem: str,
        calisan_id: int,
        banka_hareket_id: int,
        odeme_id: Optional[int] = None,
        match_score: float = 0.0,
        match_type: str = "auto_name",
        note: str = "",
    ) -> int:
        """Eşleştirme geçmişine kayıt ekler. Aynı (donem,calisan_id,banka_hareket_id) tekrar eklenmez."""
        donem = (donem or "").strip()
        if not donem:
            raise ValueError("donem boş olamaz")
        cur = self.conn.execute(
            """
            INSERT OR IGNORE INTO maas_hesap_hareket(donem,calisan_id,odeme_id,banka_hareket_id,match_score,match_type,note)
            VALUES(?,?,?,?,?,?,?)
            """,
            (
                donem,
                int(calisan_id),
                (None if odeme_id is None else int(odeme_id)),
                int(banka_hareket_id),
                float(match_score or 0.0),
                str(match_type or "auto_name"),
                str(note or ""),
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid or 0)

    def hesap_hareket_list(
        self,
        *,
        donem: str = "",
        calisan_id: Optional[int] = None,
        q: str = "",
        date_from: str = "",
        date_to: str = "",
        limit: int = 5000,
        include_inactive: bool = True,
    ) -> List[sqlite3.Row]:
        """Eşleştirme geçmişi listesi.

        - q: çalışan adı veya banka açıklamasında arama
        - date_from/date_to: banka hareket tarihi filtresi
        """
        clauses = []
        params: List[Any] = []

        if (donem or "").strip():
            clauses.append("h.donem=?")
            params.append(str(donem).strip())
        if calisan_id is not None:
            clauses.append("h.calisan_id=?")
            params.append(int(calisan_id))
        if not include_inactive:
            clauses.append("e.aktif=1")

        if (q or "").strip():
            like = f"%{q.strip()}%"
            clauses.append("(e.ad LIKE ? OR b.aciklama LIKE ?)")
            params += [like, like]

        if (date_from or "").strip():
            clauses.append("b.tarih>=?")
            params.append(parse_date_smart(date_from))
        if (date_to or "").strip():
            clauses.append("b.tarih<=?")
            params.append(parse_date_smart(date_to))

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

        try:
            lim = int(limit)
        except Exception:
            lim = 5000
        if lim <= 0:
            lim = 5000

        sql = f"""
        SELECT
            h.id,
            h.created_at,
            h.donem,
            h.calisan_id,
            e.ad AS calisan_ad,
            h.odeme_id,
            p.tutar AS maas_tutar,
            p.para AS maas_para,
            p.odendi AS maas_odendi,
            p.odeme_tarihi AS maas_odeme_tarihi,
            h.banka_hareket_id,
            b.tarih AS banka_tarih,
            b.tutar AS banka_tutar,
            b.para AS banka_para,
            b.tip AS banka_tip,
            b.banka AS banka,
            b.hesap AS hesap,
            b.aciklama AS banka_aciklama,
            h.match_score,
            h.match_type,
            h.note
        FROM maas_hesap_hareket h
        JOIN maas_calisan e ON e.id=h.calisan_id
        LEFT JOIN maas_odeme p ON p.id=h.odeme_id
        JOIN banka_hareket b ON b.id=h.banka_hareket_id
        {where}
        ORDER BY b.tarih DESC, b.id DESC
        LIMIT ?
        """
        params.append(lim)
        return list(self.conn.execute(sql, tuple(params)))

    def hesap_hareket_clear_donem(self, donem: str) -> int:
        """İlgili dönem eşleştirme geçmişini temizler."""
        donem = (donem or "").strip()
        if not donem:
            return 0
        cur = self.conn.execute("DELETE FROM maas_hesap_hareket WHERE donem=?", (donem,))
        self.conn.commit()
        try:
            return int(cur.rowcount or 0)
        except Exception:
            return 0
