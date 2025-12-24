# -*- coding: utf-8 -*-

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any, List, Optional

from ...utils import parse_date_smart, safe_float


class NakliyeRepo:
    """Nakliye sistemi veri erişim katmanı."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    # -----------------
    # Firmalar
    # -----------------
    def firma_list(self, q: str = "", only_active: bool = False) -> List[sqlite3.Row]:
        clauses = []
        params: List[Any] = []
        q = (q or "").strip()
        if q:
            clauses.append("(ad LIKE ? OR telefon LIKE ? OR eposta LIKE ? OR notlar LIKE ?)")
            params += [f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"]
        if only_active:
            clauses.append("aktif=1")
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT * FROM nakliye_firma {where} ORDER BY ad"
        return list(self.conn.execute(sql, tuple(params)))

    def firma_add(
        self,
        ad: str,
        telefon: str = "",
        eposta: str = "",
        adres: str = "",
        aktif: int = 1,
        notlar: str = "",
    ) -> int:
        cur = self.conn.execute(
            "INSERT INTO nakliye_firma(ad,telefon,eposta,adres,aktif,notlar) VALUES(?,?,?,?,?,?)",
            (str(ad).strip(), telefon or "", eposta or "", adres or "", int(aktif), notlar or ""),
        )
        self.conn.commit()
        return int(cur.lastrowid or 0)

    def firma_get(self, fid: int) -> Optional[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM nakliye_firma WHERE id=?", (int(fid),)).fetchone()

    def firma_get_by_name(self, ad: str) -> Optional[sqlite3.Row]:
        ad = (ad or "").strip()
        if not ad:
            return None
        return self.conn.execute("SELECT * FROM nakliye_firma WHERE ad=?", (ad,)).fetchone()

    def firma_update(
        self,
        fid: int,
        ad: str,
        telefon: str = "",
        eposta: str = "",
        adres: str = "",
        aktif: int = 1,
        notlar: str = "",
    ) -> None:
        self.conn.execute(
            "UPDATE nakliye_firma SET ad=?, telefon=?, eposta=?, adres=?, aktif=?, notlar=? WHERE id=?",
            (str(ad).strip(), telefon or "", eposta or "", adres or "", int(aktif), notlar or "", int(fid)),
        )
        self.conn.commit()

    def firma_set_active(self, fid: int, aktif: int) -> None:
        self.conn.execute("UPDATE nakliye_firma SET aktif=? WHERE id=?", (int(aktif), int(fid)))
        self.conn.commit()

    def firma_delete(self, fid: int) -> None:
        self.conn.execute("DELETE FROM nakliye_firma WHERE id=?", (int(fid),))
        self.conn.commit()

    # -----------------
    # Araçlar
    # -----------------
    def arac_list(
        self,
        q: str = "",
        firma_id: Optional[int] = None,
        only_active: bool = False,
    ) -> List[sqlite3.Row]:
        clauses = []
        params: List[Any] = []
        q = (q or "").strip()
        if q:
            clauses.append("(a.plaka LIKE ? OR a.tip LIKE ? OR a.marka LIKE ? OR a.model LIKE ? OR a.surucu LIKE ?)")
            params += [f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"]
        if firma_id:
            clauses.append("a.firma_id=?")
            params.append(int(firma_id))
        if only_active:
            clauses.append("a.aktif=1")
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"""
        SELECT a.*, f.ad AS firma_ad
        FROM nakliye_arac a
        LEFT JOIN nakliye_firma f ON f.id=a.firma_id
        {where}
        ORDER BY a.plaka
        """
        return list(self.conn.execute(sql, tuple(params)))

    def arac_add(
        self,
        plaka: str,
        firma_id: Optional[int] = None,
        tip: str = "",
        marka: str = "",
        model: str = "",
        yil: str = "",
        kapasite: str = "",
        surucu: str = "",
        aktif: int = 1,
        notlar: str = "",
    ) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO nakliye_arac(firma_id,plaka,tip,marka,model,yil,kapasite,surucu,aktif,notlar)
            VALUES(?,?,?,?,?,?,?,?,?,?)
            """,
            (
                int(firma_id) if firma_id is not None else None,
                str(plaka).strip(),
                tip or "",
                marka or "",
                model or "",
                yil or "",
                kapasite or "",
                surucu or "",
                int(aktif),
                notlar or "",
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid or 0)

    def arac_get(self, aid: int) -> Optional[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM nakliye_arac WHERE id=?", (int(aid),)).fetchone()

    def arac_update(
        self,
        aid: int,
        plaka: str,
        firma_id: Optional[int] = None,
        tip: str = "",
        marka: str = "",
        model: str = "",
        yil: str = "",
        kapasite: str = "",
        surucu: str = "",
        aktif: int = 1,
        notlar: str = "",
    ) -> None:
        self.conn.execute(
            """
            UPDATE nakliye_arac
            SET firma_id=?, plaka=?, tip=?, marka=?, model=?, yil=?, kapasite=?, surucu=?, aktif=?, notlar=?
            WHERE id=?
            """,
            (
                int(firma_id) if firma_id is not None else None,
                str(plaka).strip(),
                tip or "",
                marka or "",
                model or "",
                yil or "",
                kapasite or "",
                surucu or "",
                int(aktif),
                notlar or "",
                int(aid),
            ),
        )
        self.conn.commit()

    def arac_set_active(self, aid: int, aktif: int) -> None:
        self.conn.execute("UPDATE nakliye_arac SET aktif=? WHERE id=?", (int(aktif), int(aid)))
        self.conn.commit()

    def arac_delete(self, aid: int) -> None:
        self.conn.execute("DELETE FROM nakliye_arac WHERE id=?", (int(aid),))
        self.conn.commit()

    # -----------------
    # Rotalar
    # -----------------
    def rota_list(self, q: str = "", only_active: bool = False) -> List[sqlite3.Row]:
        clauses = []
        params: List[Any] = []
        q = (q or "").strip()
        if q:
            clauses.append("(ad LIKE ? OR cikis LIKE ? OR varis LIKE ? OR notlar LIKE ?)")
            params += [f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"]
        if only_active:
            clauses.append("aktif=1")
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT * FROM nakliye_rota {where} ORDER BY ad"
        return list(self.conn.execute(sql, tuple(params)))

    def rota_add(
        self,
        ad: str,
        cikis: str = "",
        varis: str = "",
        mesafe_km: float = 0.0,
        sure_saat: float = 0.0,
        aktif: int = 1,
        notlar: str = "",
    ) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO nakliye_rota(ad,cikis,varis,mesafe_km,sure_saat,aktif,notlar)
            VALUES(?,?,?,?,?,?,?)
            """,
            (str(ad).strip(), cikis or "", varis or "", safe_float(mesafe_km), safe_float(sure_saat), int(aktif), notlar or ""),
        )
        self.conn.commit()
        return int(cur.lastrowid or 0)

    def rota_get(self, rid: int) -> Optional[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM nakliye_rota WHERE id=?", (int(rid),)).fetchone()

    def rota_update(
        self,
        rid: int,
        ad: str,
        cikis: str = "",
        varis: str = "",
        mesafe_km: float = 0.0,
        sure_saat: float = 0.0,
        aktif: int = 1,
        notlar: str = "",
    ) -> None:
        self.conn.execute(
            """
            UPDATE nakliye_rota
            SET ad=?, cikis=?, varis=?, mesafe_km=?, sure_saat=?, aktif=?, notlar=?
            WHERE id=?
            """,
            (
                str(ad).strip(),
                cikis or "",
                varis or "",
                safe_float(mesafe_km),
                safe_float(sure_saat),
                int(aktif),
                notlar or "",
                int(rid),
            ),
        )
        self.conn.commit()

    def rota_set_active(self, rid: int, aktif: int) -> None:
        self.conn.execute("UPDATE nakliye_rota SET aktif=? WHERE id=?", (int(aktif), int(rid)))
        self.conn.commit()

    def rota_delete(self, rid: int) -> None:
        self.conn.execute("DELETE FROM nakliye_rota WHERE id=?", (int(rid),))
        self.conn.commit()

    # -----------------
    # İş Planlama
    # -----------------
    def is_list(
        self,
        q: str = "",
        date_from: str = "",
        date_to: str = "",
        firma_id: Optional[int] = None,
        durum: str = "",
    ) -> List[sqlite3.Row]:
        clauses = []
        params: List[Any] = []
        if (q or "").strip():
            clauses.append(
                "(i.is_no LIKE ? OR i.cikis LIKE ? OR i.varis LIKE ? OR i.yuk LIKE ? OR i.notlar LIKE ?)"
            )
            params += [f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"]
        if (date_from or "").strip():
            clauses.append("i.tarih>=?")
            params.append(parse_date_smart(date_from))
        if (date_to or "").strip():
            clauses.append("i.tarih<=?")
            params.append(parse_date_smart(date_to))
        if firma_id:
            clauses.append("i.firma_id=?")
            params.append(int(firma_id))
        if (durum or "").strip():
            clauses.append("i.durum=?")
            params.append(durum)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"""
        SELECT i.*, f.ad AS firma_ad, a.plaka AS arac_plaka, r.ad AS rota_ad
        FROM nakliye_is i
        LEFT JOIN nakliye_firma f ON f.id=i.firma_id
        LEFT JOIN nakliye_arac a ON a.id=i.arac_id
        LEFT JOIN nakliye_rota r ON r.id=i.rota_id
        {where}
        ORDER BY i.tarih DESC, i.saat DESC, i.id DESC
        """
        return list(self.conn.execute(sql, tuple(params)))

    def _make_is_no(self) -> str:
        return "IS" + datetime.now().strftime("%Y%m%d%H%M%S%f")

    def is_add(
        self,
        is_no: Optional[str],
        tarih: Any,
        saat: str = "",
        firma_id: Optional[int] = None,
        arac_id: Optional[int] = None,
        rota_id: Optional[int] = None,
        cikis: str = "",
        varis: str = "",
        yuk: str = "",
        durum: str = "Planlandı",
        ucret: float = 0.0,
        para: str = "TL",
        notlar: str = "",
    ) -> int:
        is_no = (is_no or "").strip() or self._make_is_no()
        cur = self.conn.execute(
            """
            INSERT INTO nakliye_is(
                is_no,tarih,saat,firma_id,arac_id,rota_id,cikis,varis,yuk,durum,ucret,para,notlar
            )
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                is_no,
                parse_date_smart(tarih),
                saat or "",
                int(firma_id) if firma_id is not None else None,
                int(arac_id) if arac_id is not None else None,
                int(rota_id) if rota_id is not None else None,
                cikis or "",
                varis or "",
                yuk or "",
                durum or "Planlandı",
                safe_float(ucret),
                para or "TL",
                notlar or "",
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid or 0)

    def is_get(self, iid: int) -> Optional[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM nakliye_is WHERE id=?", (int(iid),)).fetchone()

    def is_update(
        self,
        iid: int,
        is_no: str,
        tarih: Any,
        saat: str = "",
        firma_id: Optional[int] = None,
        arac_id: Optional[int] = None,
        rota_id: Optional[int] = None,
        cikis: str = "",
        varis: str = "",
        yuk: str = "",
        durum: str = "Planlandı",
        ucret: float = 0.0,
        para: str = "TL",
        notlar: str = "",
    ) -> None:
        self.conn.execute(
            """
            UPDATE nakliye_is
            SET is_no=?, tarih=?, saat=?, firma_id=?, arac_id=?, rota_id=?, cikis=?, varis=?, yuk=?,
                durum=?, ucret=?, para=?, notlar=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (
                str(is_no).strip(),
                parse_date_smart(tarih),
                saat or "",
                int(firma_id) if firma_id is not None else None,
                int(arac_id) if arac_id is not None else None,
                int(rota_id) if rota_id is not None else None,
                cikis or "",
                varis or "",
                yuk or "",
                durum or "Planlandı",
                safe_float(ucret),
                para or "TL",
                notlar or "",
                int(iid),
            ),
        )
        self.conn.commit()

    def is_set_durum(self, iid: int, durum: str, *, aciklama: str = "") -> None:
        self.conn.execute(
            "UPDATE nakliye_is SET durum=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (durum or "Planlandı", int(iid)),
        )
        if (aciklama or "").strip():
            self.islem_add(iid, parse_date_smart(datetime.now()), "", durum or "Güncelleme", aciklama=aciklama)
        self.conn.commit()

    def is_delete(self, iid: int) -> None:
        self.conn.execute("DELETE FROM nakliye_is WHERE id=?", (int(iid),))
        self.conn.commit()

    # -----------------
    # İşlemler (Durum/Log)
    # -----------------
    def islem_list(self, is_id: int) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT * FROM nakliye_islem WHERE is_id=? ORDER BY tarih DESC, saat DESC, id DESC",
                (int(is_id),),
            )
        )

    def islem_add(
        self,
        is_id: int,
        tarih: Any,
        saat: str = "",
        tip: str = "İşlem",
        aciklama: str = "",
    ) -> int:
        cur = self.conn.execute(
            "INSERT INTO nakliye_islem(is_id,tarih,saat,tip,aciklama) VALUES(?,?,?,?,?)",
            (int(is_id), parse_date_smart(tarih), saat or "", tip or "İşlem", aciklama or ""),
        )
        self.conn.commit()
        return int(cur.lastrowid or 0)

    def islem_delete(self, islem_id: int) -> None:
        self.conn.execute("DELETE FROM nakliye_islem WHERE id=?", (int(islem_id),))
        self.conn.commit()
