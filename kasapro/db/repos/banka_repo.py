# -*- coding: utf-8 -*-
from __future__ import annotations
import sqlite3
from typing import Any, Dict, List, Optional
from ...utils import parse_date_smart, safe_float
class BankaRepo:
    """Banka hareketleri repository.
    Veri modeli (banka_hareket):
      - tip: 'Giriş' / 'Çıkış'
      - tutar: her zaman pozitif sayı (tip ile yön belirlenir)
    """
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
    def add(
        self,
        tarih: Any,
        banka: str,
        hesap: str,
        tip: str,
        tutar: float,
        para: str,
        aciklama: str,
        referans: str,
        belge: str,
        etiket: str,
        import_grup: str = "",
        bakiye: Optional[float] = None,
    ) -> int:
        cur = self.conn.execute(
            """INSERT INTO banka_hareket(tarih,banka,hesap,tip,tutar,para,aciklama,referans,belge,etiket,import_grup,bakiye)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                parse_date_smart(tarih),
                str(banka or ""),
                str(hesap or ""),
                str(tip or "Giriş"),
                float(abs(safe_float(tutar))),
                str(para or "TL"),
                str(aciklama or ""),
                str(referans or ""),
                str(belge or ""),
                str(etiket or ""),
                str(import_grup or ""),
                None if bakiye is None else float(safe_float(bakiye)),
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid or 0)
    def list(
        self,
        q: str = "",
        date_from: str = "",
        date_to: str = "",
        tip: str = "",
        banka: str = "",
        hesap: str = "",
        import_grup: str = "",
        limit: int = 2000,
    ) -> List[sqlite3.Row]:
        clauses = []
        params: List[Any] = []
        if (tip or "").strip():
            clauses.append("tip=?")
            params.append(str(tip))
        if (banka or "").strip():
            clauses.append("banka=?")
            params.append(str(banka))
        if (hesap or "").strip():
            clauses.append("hesap=?")
            params.append(str(hesap))
        if (import_grup or "").strip():
            clauses.append("import_grup=?")
            params.append(str(import_grup))
        if (q or "").strip():
            like = f"%{q}%"
            clauses.append("(aciklama LIKE ? OR referans LIKE ? OR belge LIKE ? OR etiket LIKE ? OR banka LIKE ? OR hesap LIKE ?)")
            params += [like, like, like, like, like, like]
        if (date_from or "").strip():
            clauses.append("tarih>=?")
            params.append(parse_date_smart(date_from))
        if (date_to or "").strip():
            clauses.append("tarih<=?")
            params.append(parse_date_smart(date_to))
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"""
        SELECT * FROM banka_hareket
        {where}
        ORDER BY tarih DESC, id DESC
        LIMIT ?
        """
        params.append(int(limit))
        return list(self.conn.execute(sql, tuple(params)))
    def get(self, hid: int) -> Optional[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM banka_hareket WHERE id=?", (int(hid),)).fetchone()
    def get_many(self, ids: List[int]) -> List[sqlite3.Row]:
        """Birden fazla banka hareketini id listesine göre getirir.
        Not: SQLite IN (...) placeholder sayısı pratikte sınırlıdır (çoğu kurulumda ~999).
        Bu yüzden id listesini parça parça (chunk) sorgularız.
        """
        clean: List[int] = []
        for x in (ids or []):
            try:
                clean.append(int(x))
            except Exception:
                pass
        if not clean:
            return []
        # Güvenli limit: 900 (999 sınırına yaklaşmamak için)
        CHUNK = 900
        all_rows: List[sqlite3.Row] = []
        for i in range(0, len(clean), CHUNK):
            chunk = clean[i : i + CHUNK]
            placeholders = ",".join(["?"] * len(chunk))
            q = f"SELECT * FROM banka_hareket WHERE id IN ({placeholders})"
            all_rows.extend(list(self.conn.execute(q, tuple(chunk))))
        # Uygulamada tarih formatı genelde ISO (YYYY-MM-DD) olduğu için string sıralama yeterli.
        # Her ihtimale karşı id ile de sıralıyoruz.
        try:
            all_rows.sort(key=lambda r: (str(r["tarih"] or ""), int(r["id"])), reverse=True)
        except Exception:
            try:
                all_rows.sort(key=lambda r: (str(r[1] or ""), int(r[0])), reverse=True)  # fallback
            except Exception:
                pass
        return all_rows
    def update(
        self,
        hid: int,
        tarih: Any,
        banka: str,
        hesap: str,
        tip: str,
        tutar: float,
        para: str,
        aciklama: str,
        referans: str,
        belge: str,
        etiket: str,
        import_grup: str = "",
        bakiye: Optional[float] = None,
            commit: bool = True,
    ) -> None:
        self.conn.execute(
            """UPDATE banka_hareket
               SET tarih=?, banka=?, hesap=?, tip=?, tutar=?, para=?, aciklama=?, referans=?, belge=?, etiket=?, import_grup=?, bakiye=?
               WHERE id=?""",
            (
                parse_date_smart(tarih),
                str(banka or ""),
                str(hesap or ""),
                str(tip or "Giriş"),
                float(abs(safe_float(tutar))),
                str(para or "TL"),
                str(aciklama or ""),
                str(referans or ""),
                str(belge or ""),
                str(etiket or ""),
                str(import_grup or ""),
                None if bakiye is None else float(safe_float(bakiye)),
                int(hid),
            ),
        )
        if commit:
            self.conn.commit()
    def update_many(self, items: List[Dict[str, Any]]) -> None:
        """Birden çok banka hareketini tek transaction ile günceller.
        items: her eleman şu anahtarları taşımalı:
          id, tarih, banka, hesap, tip, tutar, para, aciklama, referans, belge, etiket, import_grup, bakiye
        """
        if not items:
            return
        q = (
            """UPDATE banka_hareket
               SET tarih=?, banka=?, hesap=?, tip=?, tutar=?, para=?, aciklama=?, referans=?, belge=?, etiket=?, import_grup=?, bakiye=?
               WHERE id=?"""
        )
        params: List[tuple] = []
        for it in items:
            hid = int(it.get("id"))  # type: ignore[arg-type]
            tarih = parse_date_smart(it.get("tarih"))
            banka = str(it.get("banka") or "")
            hesap = str(it.get("hesap") or "")
            tip = str(it.get("tip") or "Giriş")
            tutar = float(abs(safe_float(it.get("tutar"))))
            para = str(it.get("para") or "TL")
            aciklama = str(it.get("aciklama") or "")
            referans = str(it.get("referans") or "")
            belge = str(it.get("belge") or "")
            etiket = str(it.get("etiket") or "")
            import_grup = str(it.get("import_grup") or "")
            bakiye = it.get("bakiye")
            bakiye_val = None if bakiye is None else float(safe_float(bakiye))
            params.append(
                (
                    tarih,
                    banka,
                    hesap,
                    tip,
                    tutar,
                    para,
                    aciklama,
                    referans,
                    belge,
                    etiket,
                    import_grup,
                    bakiye_val,
                    hid,
                )
            )
        try:
            self.conn.execute("BEGIN")
            self.conn.executemany(q, params)
            self.conn.commit()
        except Exception:
            try:
                self.conn.rollback()
            except Exception:
                pass
            raise
    def import_groups(self, limit: int = 60) -> List[str]:
        """Son import gruplarını (en yeni -> eski) döndürür."""
        rows = list(
            self.conn.execute(
                """SELECT import_grup, MAX(id) mid
                   FROM banka_hareket
                   WHERE import_grup<>''
                   GROUP BY import_grup
                   ORDER BY mid DESC
                   LIMIT ?""",
                (int(limit),),
            )
        )
        out: List[str] = []
        for r in rows:
            try:
                if r and r[0]:
                    out.append(str(r[0]))
            except Exception:
                pass
        return out
    def import_group_summaries(self, limit: int = 200) -> List[sqlite3.Row]:
        """Import gruplarını özetleyerek döndürür.
        Dönüş kolonları:
          - import_grup
          - min_tarih / max_tarih
          - adet
          - giris / cikis / net
          - mid (sıralama için)
        """
        return list(
            self.conn.execute(
                """SELECT
                       import_grup,
                       MIN(tarih) AS min_tarih,
                       MAX(tarih) AS max_tarih,
                       COUNT(*)    AS adet,
                       SUM(CASE WHEN tip='Giriş' THEN tutar ELSE 0 END) AS giris,
                       SUM(CASE WHEN tip='Çıkış' THEN tutar ELSE 0 END) AS cikis,
                       (SUM(CASE WHEN tip='Giriş' THEN tutar ELSE 0 END) -
                        SUM(CASE WHEN tip='Çıkış' THEN tutar ELSE 0 END)) AS net,
                       MAX(id) AS mid
                   FROM banka_hareket
                   WHERE import_grup<>''
                   GROUP BY import_grup
                   ORDER BY mid DESC
                   LIMIT ?""",
                (int(limit),),
            )
        )
    def last_import_group(self) -> str:
        row = self.conn.execute(
            "SELECT import_grup FROM banka_hareket WHERE import_grup<>'' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return str(row[0]) if row and row[0] else ""
    def ids_by_import_group(self, import_grup: str, limit: int = 20000) -> List[int]:
        rows = list(
            self.conn.execute(
                "SELECT id FROM banka_hareket WHERE import_grup=? ORDER BY id DESC LIMIT ?",
                (str(import_grup), int(limit)),
            )
        )
        out: List[int] = []
        for r in rows:
            try:
                out.append(int(r[0]))
            except Exception:
                pass
        return out
    def delete(self, hid: int) -> None:
        self.conn.execute("DELETE FROM banka_hareket WHERE id=?", (int(hid),))
        self.conn.commit()
    def toplam(self, date_from: str = "", date_to: str = "", banka: str = "", hesap: str = "") -> Dict[str, float]:
        clauses = []
        params: List[Any] = []
        if (date_from or "").strip():
            clauses.append("tarih>=?")
            params.append(parse_date_smart(date_from))
        if (date_to or "").strip():
            clauses.append("tarih<=?")
            params.append(parse_date_smart(date_to))
        if (banka or "").strip():
            clauses.append("banka=?")
            params.append(str(banka))
        if (hesap or "").strip():
            clauses.append("hesap=?")
            params.append(str(hesap))
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        cur = self.conn.execute(
            f"""SELECT
                SUM(CASE WHEN tip='Giriş' THEN tutar ELSE 0 END) giris,
                SUM(CASE WHEN tip='Çıkış' THEN tutar ELSE 0 END) cikis
               FROM banka_hareket {where}""",
            tuple(params),
        )
        row = cur.fetchone()
        giris = safe_float(row[0] if row else 0)
        cikis = safe_float(row[1] if row else 0)
        return {"giris": giris, "cikis": cikis, "net": giris - cikis}
    def distinct_banks(self) -> List[str]:
        rows = list(self.conn.execute("SELECT DISTINCT banka FROM banka_hareket WHERE banka<>'' ORDER BY banka"))
        return [str(r[0]) for r in rows if r and r[0] is not None]
    def distinct_accounts(self, banka: str = "") -> List[str]:
        if (banka or "").strip():
            rows = list(self.conn.execute(
                "SELECT DISTINCT hesap FROM banka_hareket WHERE hesap<>'' AND banka=? ORDER BY hesap",
                (str(banka),),
            ))
        else:
            rows = list(self.conn.execute("SELECT DISTINCT hesap FROM banka_hareket WHERE hesap<>'' ORDER BY hesap"))
        return [str(r[0]) for r in rows if r and r[0] is not None]
