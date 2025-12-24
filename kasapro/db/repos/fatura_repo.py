# -*- coding: utf-8 -*-

from __future__ import annotations

import sqlite3
from datetime import date
from typing import Any, Dict, List, Optional

from ...utils import parse_date_smart, safe_float


def _today_year() -> int:
    try:
        return int(date.today().year)
    except Exception:
        return 0


def _norm(s: Any) -> str:
    try:
        return str(s or '').strip()
    except Exception:
        return ''


class FaturaRepo:
    """Fatura (invoice) veri erişim katmanı.

    Tablolar:
    - fatura: başlık
    - fatura_kalem: kalemler (satırlar)
    - fatura_odeme: tahsilat/ödeme kayıtları
    - fatura_seri: seri & numara üretimi
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    # -----------------
    # Seri
    # -----------------
    def list_seri(self) -> List[sqlite3.Row]:
        return list(self.conn.execute("SELECT * FROM fatura_seri ORDER BY aktif DESC, yil DESC, seri ASC"))

    def seri_upsert(
        self,
        seri: str,
        yil: int,
        prefix: str = 'FTR',
        last_no: int = 0,
        padding: int = 6,
        fmt: str = '{yil}{seri}{no_pad}',
        aktif: int = 1,
    ) -> None:
        self.conn.execute(
            """INSERT INTO fatura_seri(seri,yil,prefix,last_no,padding,format,aktif)
               VALUES(?,?,?,?,?,?,?)
               ON CONFLICT(seri,yil) DO UPDATE SET
                 prefix=excluded.prefix,
                 last_no=excluded.last_no,
                 padding=excluded.padding,
                 format=excluded.format,
                 aktif=excluded.aktif""",
            (_norm(seri), int(yil), _norm(prefix), int(last_no), int(padding), _norm(fmt), int(aktif)),
        )
        self.conn.commit()

    def next_fatura_no(self, seri: str = 'A', yil: Optional[int] = None) -> str:
        s = _norm(seri) or 'A'
        y = int(yil or _today_year() or 0)

        row = self.conn.execute(
            "SELECT * FROM fatura_seri WHERE seri=? AND yil=?",
            (s, y),
        ).fetchone()

        if not row:
            # default seri kaydı
            self.seri_upsert(seri=s, yil=y, prefix='FTR', last_no=0, padding=6, fmt='{yil}{seri}{no_pad}', aktif=1)
            row = self.conn.execute(
                "SELECT * FROM fatura_seri WHERE seri=? AND yil=?",
                (s, y),
            ).fetchone()

        last_no = int(row['last_no'] or 0)
        padding = int(row['padding'] or 6)
        fmt = _norm(row['format'] or '{yil}{seri}{no_pad}')

        new_no = last_no + 1
        no_pad = str(new_no).zfill(max(1, padding))

        # güvenli format
        try:
            fatura_no = fmt.format(yil=y, seri=s, no=new_no, no_pad=no_pad, prefix=_norm(row['prefix'] or 'FTR'))
        except Exception:
            fatura_no = f"{y}{s}{no_pad}"

        self.conn.execute(
            "UPDATE fatura_seri SET last_no=? WHERE seri=? AND yil=?",
            (int(new_no), s, int(y)),
        )
        self.conn.commit()
        return fatura_no

    # -----------------
    # Fatura (başlık)
    # -----------------
    def list(
        self,
        q: str = '',
        date_from: str = '',
        date_to: str = '',
        tur: str = '',
        durum: str = '',
        cari_id: Optional[int] = None,
    ) -> List[sqlite3.Row]:
        clauses: List[str] = []
        params: List[Any] = []

        if _norm(q):
            clauses.append("(f.fatura_no LIKE ? OR COALESCE(f.cari_ad,'') LIKE ? OR COALESCE(f.notlar,'') LIKE ? OR COALESCE(f.etiket,'') LIKE ?)")
            like = f"%{_norm(q)}%"
            params += [like, like, like, like]

        if _norm(date_from):
            clauses.append("f.tarih>=?")
            params.append(parse_date_smart(date_from))

        if _norm(date_to):
            clauses.append("f.tarih<=?")
            params.append(parse_date_smart(date_to))

        if _norm(tur):
            clauses.append("f.tur=?")
            params.append(_norm(tur))

        if _norm(durum):
            clauses.append("f.durum=?")
            params.append(_norm(durum))

        if cari_id:
            clauses.append("f.cari_id=?")
            params.append(int(cari_id))

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

        sql = f"""
        SELECT
            f.*,
            COALESCE(p.odendi,0) AS odendi,
            (COALESCE(f.genel_toplam,0) - COALESCE(p.odendi,0)) AS kalan
        FROM fatura f
        LEFT JOIN (
            SELECT fatura_id, SUM(tutar) AS odendi
            FROM fatura_odeme
            GROUP BY fatura_id
        ) p ON p.fatura_id=f.id
        {where}
        ORDER BY f.tarih DESC, f.id DESC
        """
        return list(self.conn.execute(sql, tuple(params)))

    def get(self, fid: int) -> Optional[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM fatura WHERE id=?", (int(fid),)).fetchone()

    def create(self, header: Dict[str, Any], kalemler: List[Dict[str, Any]]) -> int:
        # tek transaction
        cur = self.conn.cursor()
        cur.execute(
            """INSERT INTO fatura(
                tarih,vade,tur,durum,fatura_no,seri,
                cari_id,cari_ad,cari_vkn,cari_vergi_dairesi,cari_adres,cari_eposta,
                para,ara_toplam,iskonto_toplam,kdv_toplam,genel_toplam,
                notlar,etiket
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                parse_date_smart(header.get('tarih') or ''),
                parse_date_smart(header.get('vade') or '') if _norm(header.get('vade')) else '',
                _norm(header.get('tur') or 'Satış'),
                _norm(header.get('durum') or 'Taslak'),
                _norm(header.get('fatura_no')),
                _norm(header.get('seri')),
                int(header.get('cari_id') or 0) if header.get('cari_id') is not None else None,
                _norm(header.get('cari_ad')),
                _norm(header.get('cari_vkn')),
                _norm(header.get('cari_vergi_dairesi')),
                _norm(header.get('cari_adres')),
                _norm(header.get('cari_eposta')),
                _norm(header.get('para') or 'TL'),
                float(safe_float(header.get('ara_toplam'))),
                float(safe_float(header.get('iskonto_toplam'))),
                float(safe_float(header.get('kdv_toplam'))),
                float(safe_float(header.get('genel_toplam'))),
                _norm(header.get('notlar')),
                _norm(header.get('etiket')),
            ),
        )
        fid = int(cur.lastrowid or 0)

        self._replace_kalemler(cur, fid, kalemler)

        self.conn.commit()
        return fid

    def update(self, fid: int, header: Dict[str, Any], kalemler: List[Dict[str, Any]]) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """UPDATE fatura SET
                tarih=?, vade=?, tur=?, durum=?, fatura_no=?, seri=?,
                cari_id=?, cari_ad=?, cari_vkn=?, cari_vergi_dairesi=?, cari_adres=?, cari_eposta=?,
                para=?, ara_toplam=?, iskonto_toplam=?, kdv_toplam=?, genel_toplam=?,
                notlar=?, etiket=?, updated_at=CURRENT_TIMESTAMP
               WHERE id=?""",
            (
                parse_date_smart(header.get('tarih') or ''),
                parse_date_smart(header.get('vade') or '') if _norm(header.get('vade')) else '',
                _norm(header.get('tur') or 'Satış'),
                _norm(header.get('durum') or 'Taslak'),
                _norm(header.get('fatura_no')),
                _norm(header.get('seri')),
                int(header.get('cari_id') or 0) if header.get('cari_id') is not None else None,
                _norm(header.get('cari_ad')),
                _norm(header.get('cari_vkn')),
                _norm(header.get('cari_vergi_dairesi')),
                _norm(header.get('cari_adres')),
                _norm(header.get('cari_eposta')),
                _norm(header.get('para') or 'TL'),
                float(safe_float(header.get('ara_toplam'))),
                float(safe_float(header.get('iskonto_toplam'))),
                float(safe_float(header.get('kdv_toplam'))),
                float(safe_float(header.get('genel_toplam'))),
                _norm(header.get('notlar')),
                _norm(header.get('etiket')),
                int(fid),
            ),
        )

        self._replace_kalemler(cur, int(fid), kalemler)
        self.conn.commit()

    def delete(self, fid: int) -> None:
        self.conn.execute("DELETE FROM fatura WHERE id=?", (int(fid),))
        self.conn.commit()

    # -----------------
    # Kalemler
    # -----------------
    def _replace_kalemler(self, cur: sqlite3.Cursor, fid: int, kalemler: List[Dict[str, Any]]):
        cur.execute("DELETE FROM fatura_kalem WHERE fatura_id=?", (int(fid),))
        for idx, k in enumerate(kalemler, start=1):
            cur.execute(
                """INSERT INTO fatura_kalem(
                    fatura_id,sira,urun,aciklama,miktar,birim,birim_fiyat,iskonto_oran,kdv_oran,
                    ara_tutar,iskonto_tutar,kdv_tutar,toplam
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    int(fid),
                    int(k.get('sira') or idx),
                    _norm(k.get('urun')),
                    _norm(k.get('aciklama')),
                    float(safe_float(k.get('miktar') or 0)),
                    _norm(k.get('birim') or 'Adet'),
                    float(safe_float(k.get('birim_fiyat') or 0)),
                    float(safe_float(k.get('iskonto_oran') or 0)),
                    float(safe_float(k.get('kdv_oran') or 0)),
                    float(safe_float(k.get('ara_tutar') or 0)),
                    float(safe_float(k.get('iskonto_tutar') or 0)),
                    float(safe_float(k.get('kdv_tutar') or 0)),
                    float(safe_float(k.get('toplam') or 0)),
                ),
            )

    def kalem_list(self, fid: int) -> List[sqlite3.Row]:
        return list(self.conn.execute("SELECT * FROM fatura_kalem WHERE fatura_id=? ORDER BY sira ASC, id ASC", (int(fid),)))

    # -----------------
    # Tahsilat/Ödeme
    # -----------------
    def odeme_list(self, fid: int) -> List[sqlite3.Row]:
        return list(self.conn.execute("SELECT * FROM fatura_odeme WHERE fatura_id=? ORDER BY tarih DESC, id DESC", (int(fid),)))

    def odeme_add(
        self,
        fid: int,
        tarih: Any,
        tutar: float,
        para: str,
        odeme: str,
        aciklama: str = '',
        ref: str = '',
        kasa_hareket_id: Optional[int] = None,
        banka_hareket_id: Optional[int] = None,
    ) -> int:
        cur = self.conn.cursor()
        cur.execute(
            """INSERT INTO fatura_odeme(
                fatura_id,tarih,tutar,para,odeme,aciklama,ref,kasa_hareket_id,banka_hareket_id
            ) VALUES(?,?,?,?,?,?,?,?,?)""",
            (
                int(fid),
                parse_date_smart(tarih),
                float(safe_float(tutar)),
                _norm(para or 'TL'),
                _norm(odeme),
                _norm(aciklama),
                _norm(ref),
                int(kasa_hareket_id) if kasa_hareket_id is not None else None,
                int(banka_hareket_id) if banka_hareket_id is not None else None,
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid or 0)

    def odeme_delete(self, odeme_id: int) -> None:
        self.conn.execute("DELETE FROM fatura_odeme WHERE id=?", (int(odeme_id),))
        self.conn.commit()

    def odeme_toplam(self, fid: int) -> float:
        r = self.conn.execute("SELECT COALESCE(SUM(tutar),0) FROM fatura_odeme WHERE fatura_id=?", (int(fid),)).fetchone()
        return float(safe_float(r[0] if r else 0))

    # -----------------
    # Full load
    # -----------------
    def get_full(self, fid: int) -> Optional[Dict[str, Any]]:
        h = self.get(fid)
        if not h:
            return None
        return {
            'header': h,
            'kalemler': self.kalem_list(fid),
            'odemeler': self.odeme_list(fid),
            'odendi': self.odeme_toplam(fid),
        }
