# -*- coding: utf-8 -*-

from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional

from ...utils import parse_date_smart, safe_float


class StokRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    # -----------------
    # Ürünler
    # -----------------
    def urun_list(self, q: str = "", only_active: bool = False) -> List[sqlite3.Row]:
        clauses = []
        params: List[Any] = []
        if (q or "").strip():
            clauses.append("(u.kod LIKE ? OR u.ad LIKE ? OR u.kategori LIKE ? OR u.barkod LIKE ?)")
            like = f"%{q}%"
            params += [like, like, like, like]
        if only_active:
            clauses.append("u.aktif=1")
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"""
        SELECT u.*, c.ad tedarikci_ad
        FROM stok_urun u
        LEFT JOIN cariler c ON c.id=u.tedarikci_id
        {where}
        ORDER BY u.ad
        """
        return list(self.conn.execute(sql, tuple(params)))

    def urun_get(self, uid: int) -> Optional[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM stok_urun WHERE id=?", (int(uid),)).fetchone()

    def urun_get_by_code(self, kod: str) -> Optional[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM stok_urun WHERE kod=?", (kod,)).fetchone()

    def urun_add(
        self,
        kod: str,
        ad: str,
        kategori: str,
        birim: str,
        min_stok: float,
        max_stok: float,
        kritik_stok: float,
        raf: str,
        tedarikci_id: Optional[int],
        barkod: str,
        aktif: int,
        aciklama: str,
    ) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO stok_urun(kod,ad,kategori,birim,min_stok,max_stok,kritik_stok,raf,tedarikci_id,barkod,aktif,aciklama)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                str(kod).strip(),
                str(ad).strip(),
                str(kategori or ""),
                str(birim or "Adet"),
                float(min_stok or 0),
                float(max_stok or 0),
                float(kritik_stok or 0),
                str(raf or ""),
                int(tedarikci_id) if tedarikci_id else None,
                str(barkod or ""),
                int(aktif),
                str(aciklama or ""),
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def urun_update(
        self,
        uid: int,
        kod: str,
        ad: str,
        kategori: str,
        birim: str,
        min_stok: float,
        max_stok: float,
        kritik_stok: float,
        raf: str,
        tedarikci_id: Optional[int],
        barkod: str,
        aktif: int,
        aciklama: str,
    ) -> None:
        self.conn.execute(
            """
            UPDATE stok_urun
            SET kod=?, ad=?, kategori=?, birim=?, min_stok=?, max_stok=?, kritik_stok=?, raf=?,
                tedarikci_id=?, barkod=?, aktif=?, aciklama=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (
                str(kod).strip(),
                str(ad).strip(),
                str(kategori or ""),
                str(birim or "Adet"),
                float(min_stok or 0),
                float(max_stok or 0),
                float(kritik_stok or 0),
                str(raf or ""),
                int(tedarikci_id) if tedarikci_id else None,
                str(barkod or ""),
                int(aktif),
                str(aciklama or ""),
                int(uid),
            ),
        )
        self.conn.commit()

    def urun_delete(self, uid: int) -> None:
        self.conn.execute("DELETE FROM stok_urun WHERE id=?", (int(uid),))
        self.conn.commit()

    def urun_stok_ozet(self, uid: int) -> Dict[str, float]:
        cur = self.conn.execute(
            """
            SELECT
                SUM(CASE
                    WHEN tip IN ('Giris','Uretim') THEN miktar
                    WHEN tip IN ('Cikis','Fire') THEN -miktar
                    WHEN tip IN ('Sayim','Duzeltme') THEN miktar
                    ELSE 0
                END) toplam
            FROM stok_hareket WHERE urun_id=?
            """,
            (int(uid),),
        )
        row = cur.fetchone()
        toplam = safe_float(row[0] if row else 0)
        return {"toplam": toplam}

    def urun_stok_by_location(self, uid: int) -> List[sqlite3.Row]:
        sql = """
        SELECT l.id lokasyon_id,
               l.ad lokasyon,
               SUM(CASE
                   WHEN h.hedef_lokasyon_id=l.id THEN h.miktar
                   WHEN h.kaynak_lokasyon_id=l.id THEN -h.miktar
                   ELSE 0
               END) miktar
        FROM stok_lokasyon l
        LEFT JOIN stok_hareket h ON h.urun_id=? AND (h.kaynak_lokasyon_id=l.id OR h.hedef_lokasyon_id=l.id)
        WHERE l.aktif=1
        GROUP BY l.id, l.ad
        ORDER BY l.ad
        """
        return list(self.conn.execute(sql, (int(uid),)))

    def stok_summary_by_location(self) -> List[sqlite3.Row]:
        sql = """
        SELECT l.id lokasyon_id,
               l.ad lokasyon,
               SUM(CASE
                   WHEN h.hedef_lokasyon_id=l.id THEN h.miktar
                   WHEN h.kaynak_lokasyon_id=l.id THEN -h.miktar
                   ELSE 0
               END) miktar
        FROM stok_lokasyon l
        LEFT JOIN stok_hareket h ON h.kaynak_lokasyon_id=l.id OR h.hedef_lokasyon_id=l.id
        GROUP BY l.id, l.ad
        ORDER BY l.ad
        """
        return list(self.conn.execute(sql))

    # -----------------
    # Lokasyonlar
    # -----------------
    def lokasyon_list(self, only_active: bool = False) -> List[sqlite3.Row]:
        where = "WHERE aktif=1" if only_active else ""
        return list(self.conn.execute(f"SELECT * FROM stok_lokasyon {where} ORDER BY ad"))

    def lokasyon_upsert(self, ad: str, aciklama: str = "", aktif: int = 1) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO stok_lokasyon(ad,aciklama,aktif)
            VALUES(?,?,?)
            ON CONFLICT(ad) DO UPDATE SET aciklama=excluded.aciklama, aktif=excluded.aktif
            """,
            (str(ad).strip(), str(aciklama or ""), int(aktif)),
        )
        self.conn.commit()
        return int(cur.lastrowid or 0)

    def lokasyon_set_active(self, lid: int, aktif: int) -> None:
        self.conn.execute("UPDATE stok_lokasyon SET aktif=? WHERE id=?", (int(aktif), int(lid)))
        self.conn.commit()

    # -----------------
    # Partiler
    # -----------------
    def parti_list(self, urun_id: Optional[int] = None) -> List[sqlite3.Row]:
        if urun_id:
            return list(
                self.conn.execute(
                    "SELECT * FROM stok_parti WHERE urun_id=? ORDER BY parti_no",
                    (int(urun_id),),
                )
            )
        return list(self.conn.execute("SELECT * FROM stok_parti ORDER BY parti_no"))

    def parti_upsert(self, urun_id: int, parti_no: str, skt: str = "", uretim_tarih: str = "", aciklama: str = "") -> int:
        cur = self.conn.execute(
            """
            INSERT INTO stok_parti(urun_id,parti_no,skt,uretim_tarih,aciklama)
            VALUES(?,?,?,?,?)
            ON CONFLICT(urun_id,parti_no) DO UPDATE SET
                skt=excluded.skt,
                uretim_tarih=excluded.uretim_tarih,
                aciklama=excluded.aciklama
            """,
            (int(urun_id), str(parti_no).strip(), str(skt or ""), str(uretim_tarih or ""), str(aciklama or "")),
        )
        self.conn.commit()
        return int(cur.lastrowid or 0)

    # -----------------
    # Hareketler
    # -----------------
    def hareket_add(
        self,
        tarih: Any,
        urun_id: int,
        tip: str,
        miktar: float,
        birim: str,
        kaynak_lokasyon_id: Optional[int],
        hedef_lokasyon_id: Optional[int],
        parti_id: Optional[int],
        referans_tipi: str,
        referans_id: Optional[int],
        maliyet: float,
        aciklama: str,
    ) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO stok_hareket(
                tarih,urun_id,tip,miktar,birim,kaynak_lokasyon_id,hedef_lokasyon_id,parti_id,
                referans_tipi,referans_id,maliyet,aciklama
            )
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                parse_date_smart(tarih),
                int(urun_id),
                str(tip),
                float(miktar),
                str(birim or "Adet"),
                int(kaynak_lokasyon_id) if kaynak_lokasyon_id else None,
                int(hedef_lokasyon_id) if hedef_lokasyon_id else None,
                int(parti_id) if parti_id else None,
                str(referans_tipi or ""),
                int(referans_id) if referans_id else None,
                float(maliyet or 0),
                str(aciklama or ""),
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def hareket_list(self, q: str = "", urun_id: Optional[int] = None, limit: int = 500) -> List[sqlite3.Row]:
        clauses = []
        params: List[Any] = []
        if urun_id:
            clauses.append("h.urun_id=?")
            params.append(int(urun_id))
        if (q or "").strip():
            clauses.append("(u.kod LIKE ? OR u.ad LIKE ? OR h.tip LIKE ? OR h.aciklama LIKE ?)")
            like = f"%{q}%"
            params += [like, like, like, like]
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"""
        SELECT h.*, u.kod urun_kod, u.ad urun_ad,
               lk.ad kaynak_lokasyon, lh.ad hedef_lokasyon,
               p.parti_no parti_no
        FROM stok_hareket h
        JOIN stok_urun u ON u.id=h.urun_id
        LEFT JOIN stok_lokasyon lk ON lk.id=h.kaynak_lokasyon_id
        LEFT JOIN stok_lokasyon lh ON lh.id=h.hedef_lokasyon_id
        LEFT JOIN stok_parti p ON p.id=h.parti_id
        {where}
        ORDER BY h.tarih DESC, h.id DESC
        LIMIT ?
        """
        params.append(int(limit))
        return list(self.conn.execute(sql, tuple(params)))

    def hareket_delete(self, hid: int) -> None:
        self.conn.execute("DELETE FROM stok_hareket WHERE id=?", (int(hid),))
        self.conn.commit()
