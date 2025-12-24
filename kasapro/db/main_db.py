# -*- coding: utf-8 -*-
"""Company DB (SQLite) erişim katmanı.

Bu sınıf UI tarafından kullanılıyor. İçeride repository'lere delegasyon yapar.
"""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional

from .connection import connect
from .schema import init_schema, migrate_schema, seed_defaults
from .repos import (
    LogsRepo,
    SettingsRepo,
    UsersRepo,
    CarilerRepo,
    CariHareketRepo,
    KasaRepo,
    SearchRepo,
    MaasRepo,
    BankaRepo,
    FaturaRepo,
    NakliyeRepo,
)


class DB:
    def __init__(self, path: str):
        self.path = path
        self.conn = connect(path)

        # Önce tablolar, sonra migrasyon + seed
        init_schema(self.conn)

        # Repo'lar (log_fn -> logs tablosu hazır)
        self.logs = LogsRepo(self.conn)
        self.settings = SettingsRepo(self.conn, log_fn=self.logs.log)
        self.users = UsersRepo(self.conn)
        self.cariler = CarilerRepo(self.conn)
        self.cari_hareket = CariHareketRepo(self.conn)
        self.kasa = KasaRepo(self.conn)
        self.search = SearchRepo(self.conn)
        self.maas = MaasRepo(self.conn)
        self.banka = BankaRepo(self.conn)
        self.fatura = FaturaRepo(self.conn)
        self.nakliye = NakliyeRepo(self.conn)

        migrate_schema(self.conn, log_fn=self._safe_log)
        seed_defaults(self.conn, log_fn=self._safe_log)

    def _safe_log(self, islem: str, detay: str = ""):
        try:
            self.logs.log(islem, detay)
        except Exception:
            pass

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass

    # -----------------
    # Logs
    # -----------------
    def log(self, islem: str, detay: str = ""):
        self.logs.log(islem, detay)

    def logs_list(self, limit: int = 800):
        return self.logs.list(limit=limit)

    # -----------------
    # Settings
    # -----------------
    def get_setting(self, key: str) -> Optional[str]:
        return self.settings.get(key)

    def set_setting(self, key: str, value: str):
        self.settings.set(key, value)

    def _get_list_setting(self, key: str, default: List[str]) -> List[str]:
        # geriye dönük uyumluluk (UI bu metodu doğrudan çağırmıyor)
        try:
            s = self.get_setting(key)
        except Exception:
            s = None
        if not s:
            return default[:]
        try:
            import json
            v = json.loads(s)
            if isinstance(v, list) and v:
                return [str(x) for x in v]
        except Exception:
            pass
        return default[:]

    def next_belge_no(self, prefix: str = "BLG") -> str:
        return self.settings.next_belge_no(prefix=prefix)

    def list_currencies(self) -> List[str]:
        return self.settings.list_currencies()

    def list_payments(self) -> List[str]:
        return self.settings.list_payments()

    def list_categories(self) -> List[str]:
        return self.settings.list_categories()

    def list_stock_units(self) -> List[str]:
        return self.settings.list_stock_units()

    def list_stock_categories(self) -> List[str]:
        return self.settings.list_stock_categories()

    # -----------------
    # Company içi Users (SettingsWindow)
    # -----------------
    def user_auth(self, username: str, password: str) -> Optional[sqlite3.Row]:
        return self.users.auth(username, password)

    def users_list(self) -> List[sqlite3.Row]:
        return self.users.list()

    def user_add(self, username: str, password: str, role: str):
        self.users.add(username, password, role)

    def user_set_password(self, user_id: int, new_password: str):
        self.users.set_password(user_id, new_password)

    def user_set_role(self, user_id: int, role: str):
        self.users.set_role(user_id, role)

    def user_delete(self, user_id: int):
        self.users.delete(user_id)

    # -----------------
    # Cariler
    # -----------------
    def cari_list(self, q: str = "", only_active: bool = False) -> List[sqlite3.Row]:
        return self.cariler.list(q=q, only_active=only_active)

    def cari_get_by_name(self, ad: str) -> Optional[sqlite3.Row]:
        return self.cariler.get_by_name(ad)

    def cari_get(self, cid: int) -> Optional[sqlite3.Row]:
        return self.cariler.get(cid)

    def cari_upsert(self, ad: str, tur: str = "", telefon: str = "", notlar: str = "", acilis_bakiye: float = 0.0, aktif: int = 1) -> int:
        return self.cariler.upsert(ad, tur=tur, telefon=telefon, notlar=notlar, acilis_bakiye=acilis_bakiye, aktif=aktif)

    def cari_delete(self, cid: int):
        return self.cariler.delete(cid)

    def cari_set_active(self, cid: int, aktif: int):
        return self.cariler.set_active(cid, aktif)

    # -----------------
    # Cari Hareket
    # -----------------
    def cari_hareket_add(self, tarih: Any, cari_id: int, tip: str, tutar: float, para: str,
                         aciklama: str, odeme: str, belge: str, etiket: str):
        return self.cari_hareket.add(tarih, cari_id, tip, tutar, para, aciklama, odeme, belge, etiket)

    def cari_hareket_list(self, cari_id: Optional[int] = None, q: str = "", date_from: str = "", date_to: str = "") -> List[sqlite3.Row]:
        return self.cari_hareket.list(cari_id=cari_id, q=q, date_from=date_from, date_to=date_to)

    def cari_hareket_get(self, hid: int) -> Optional[sqlite3.Row]:
        return self.cari_hareket.get(hid)

    def cari_hareket_update(self, hid: int, tarih: Any, cari_id: int, tip: str, tutar: float, para: str,
                            aciklama: str, odeme: str, belge: str, etiket: str):
        return self.cari_hareket.update(hid, tarih, cari_id, tip, tutar, para, aciklama, odeme, belge, etiket)

    def cari_hareket_delete(self, hid: int):
        return self.cari_hareket.delete(hid)

    # -----------------
    # Kasa
    # -----------------
    def kasa_add(self, tarih: Any, tip: str, tutar: float, para: str, odeme: str, kategori: str,
                 cari_id: Optional[int], aciklama: str, belge: str, etiket: str):
        return self.kasa.add(tarih, tip, tutar, para, odeme, kategori, cari_id, aciklama, belge, etiket)

    def kasa_list(
        self,
        q: str = "",
        date_from: str = "",
        date_to: str = "",
        tip: str = "",
        kategori: str = "",
        has_cari: Optional[bool] = None,
    ) -> List[sqlite3.Row]:
        return self.kasa.list(q=q, date_from=date_from, date_to=date_to, tip=tip, kategori=kategori, has_cari=has_cari)

    def kasa_get(self, kid: int) -> Optional[sqlite3.Row]:
        return self.kasa.get(kid)

    def kasa_update(self, kid: int, tarih: Any, tip: str, tutar: float, para: str, odeme: str, kategori: str,
                    cari_id: Optional[int], aciklama: str, belge: str, etiket: str):
        return self.kasa.update(kid, tarih, tip, tutar, para, odeme, kategori, cari_id, aciklama, belge, etiket)

    def kasa_delete(self, kid: int):
        return self.kasa.delete(kid)

    def kasa_toplam(self, date_from: str = "", date_to: str = "", has_cari: Optional[bool] = None) -> Dict[str, float]:
        # geriye dönük uyumluluk için toplam() bırakıldı
        if has_cari is None:
            return self.kasa.toplam(date_from=date_from, date_to=date_to)
        return self.kasa.toplam_filtered(date_from=date_from, date_to=date_to, has_cari=has_cari)

    def kasa_gunluk(self, date_from: str, date_to: str, has_cari: Optional[bool] = None):
        return self.kasa.gunluk(date_from, date_to, has_cari=has_cari)

    def kasa_kategori_ozet(self, date_from: str, date_to: str, tip: str = "Gider", has_cari: Optional[bool] = None):
        return self.kasa.kategori_ozet(date_from, date_to, tip=tip, has_cari=has_cari)

    def kasa_aylik_ozet(self, limit: int = 24, has_cari: Optional[bool] = None):
        return self.kasa.aylik_ozet(limit=limit, has_cari=has_cari)

    # -----------------
    # Stok
    # -----------------
    def stok_urun_list(self, q: str = "", only_active: bool = False) -> List[sqlite3.Row]:
        return self.stok.urun_list(q=q, only_active=only_active)

    def stok_urun_get(self, uid: int) -> Optional[sqlite3.Row]:
        return self.stok.urun_get(uid)

    def stok_urun_get_by_code(self, kod: str) -> Optional[sqlite3.Row]:
        return self.stok.urun_get_by_code(kod)

    def stok_urun_add(
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
        return self.stok.urun_add(
            kod,
            ad,
            kategori,
            birim,
            min_stok,
            max_stok,
            kritik_stok,
            raf,
            tedarikci_id,
            barkod,
            aktif,
            aciklama,
        )

    def stok_urun_update(
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
        return self.stok.urun_update(
            uid,
            kod,
            ad,
            kategori,
            birim,
            min_stok,
            max_stok,
            kritik_stok,
            raf,
            tedarikci_id,
            barkod,
            aktif,
            aciklama,
        )

    def stok_urun_delete(self, uid: int) -> None:
        return self.stok.urun_delete(uid)

    def stok_urun_stok_ozet(self, uid: int) -> Dict[str, float]:
        return self.stok.urun_stok_ozet(uid)

    def stok_urun_stok_by_location(self, uid: int) -> List[sqlite3.Row]:
        return self.stok.urun_stok_by_location(uid)

    def stok_summary_by_location(self) -> List[sqlite3.Row]:
        return self.stok.stok_summary_by_location()

    def stok_lokasyon_list(self, only_active: bool = False) -> List[sqlite3.Row]:
        return self.stok.lokasyon_list(only_active=only_active)

    def stok_lokasyon_upsert(self, ad: str, aciklama: str = "", aktif: int = 1) -> int:
        return self.stok.lokasyon_upsert(ad=ad, aciklama=aciklama, aktif=aktif)

    def stok_lokasyon_set_active(self, lid: int, aktif: int) -> None:
        return self.stok.lokasyon_set_active(lid, aktif)

    def stok_parti_list(self, urun_id: Optional[int] = None) -> List[sqlite3.Row]:
        return self.stok.parti_list(urun_id=urun_id)

    def stok_parti_upsert(self, urun_id: int, parti_no: str, skt: str = "", uretim_tarih: str = "", aciklama: str = "") -> int:
        return self.stok.parti_upsert(urun_id=urun_id, parti_no=parti_no, skt=skt, uretim_tarih=uretim_tarih, aciklama=aciklama)

    def stok_hareket_add(
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
        return self.stok.hareket_add(
            tarih,
            urun_id,
            tip,
            miktar,
            birim,
            kaynak_lokasyon_id,
            hedef_lokasyon_id,
            parti_id,
            referans_tipi,
            referans_id,
            maliyet,
            aciklama,
        )

    def stok_hareket_list(self, q: str = "", urun_id: Optional[int] = None, limit: int = 500) -> List[sqlite3.Row]:
        return self.stok.hareket_list(q=q, urun_id=urun_id, limit=limit)

    def stok_hareket_delete(self, hid: int) -> None:
        return self.stok.hareket_delete(hid)

    # -----------------
    # Banka
    # -----------------
    def banka_add(self, tarih: Any, banka: str, hesap: str, tip: str, tutar: float, para: str,
                  aciklama: str, referans: str, belge: str, etiket: str, import_grup: str = "", bakiye: Optional[float] = None):
        return self.banka.add(tarih, banka, hesap, tip, tutar, para, aciklama, referans, belge, etiket, import_grup=import_grup, bakiye=bakiye)

    # -----------------
    # Nakliye
    # -----------------
    def nakliye_firma_list(self, q: str = "", only_active: bool = False):
        return self.nakliye.firma_list(q=q, only_active=only_active)

    def nakliye_firma_add(self, ad: str, telefon: str = "", eposta: str = "", adres: str = "", aktif: int = 1, notlar: str = ""):
        return self.nakliye.firma_add(ad, telefon=telefon, eposta=eposta, adres=adres, aktif=aktif, notlar=notlar)

    def nakliye_firma_get(self, fid: int):
        return self.nakliye.firma_get(fid)

    def nakliye_firma_get_by_name(self, ad: str):
        return self.nakliye.firma_get_by_name(ad)

    def nakliye_firma_update(self, fid: int, ad: str, telefon: str = "", eposta: str = "", adres: str = "", aktif: int = 1, notlar: str = ""):
        return self.nakliye.firma_update(fid, ad, telefon=telefon, eposta=eposta, adres=adres, aktif=aktif, notlar=notlar)

    def nakliye_firma_set_active(self, fid: int, aktif: int):
        return self.nakliye.firma_set_active(fid, aktif)

    def nakliye_firma_delete(self, fid: int):
        return self.nakliye.firma_delete(fid)

    def nakliye_arac_list(self, q: str = "", firma_id: Optional[int] = None, only_active: bool = False):
        return self.nakliye.arac_list(q=q, firma_id=firma_id, only_active=only_active)

    def nakliye_arac_add(
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
    ):
        return self.nakliye.arac_add(
            plaka,
            firma_id=firma_id,
            tip=tip,
            marka=marka,
            model=model,
            yil=yil,
            kapasite=kapasite,
            surucu=surucu,
            aktif=aktif,
            notlar=notlar,
        )

    def nakliye_arac_get(self, aid: int):
        return self.nakliye.arac_get(aid)

    def nakliye_arac_update(
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
    ):
        return self.nakliye.arac_update(
            aid,
            plaka,
            firma_id=firma_id,
            tip=tip,
            marka=marka,
            model=model,
            yil=yil,
            kapasite=kapasite,
            surucu=surucu,
            aktif=aktif,
            notlar=notlar,
        )

    def nakliye_arac_set_active(self, aid: int, aktif: int):
        return self.nakliye.arac_set_active(aid, aktif)

    def nakliye_arac_delete(self, aid: int):
        return self.nakliye.arac_delete(aid)

    def nakliye_rota_list(self, q: str = "", only_active: bool = False):
        return self.nakliye.rota_list(q=q, only_active=only_active)

    def nakliye_rota_add(
        self,
        ad: str,
        cikis: str = "",
        varis: str = "",
        mesafe_km: float = 0.0,
        sure_saat: float = 0.0,
        aktif: int = 1,
        notlar: str = "",
    ):
        return self.nakliye.rota_add(ad, cikis=cikis, varis=varis, mesafe_km=mesafe_km, sure_saat=sure_saat, aktif=aktif, notlar=notlar)

    def nakliye_rota_get(self, rid: int):
        return self.nakliye.rota_get(rid)

    def nakliye_rota_update(
        self,
        rid: int,
        ad: str,
        cikis: str = "",
        varis: str = "",
        mesafe_km: float = 0.0,
        sure_saat: float = 0.0,
        aktif: int = 1,
        notlar: str = "",
    ):
        return self.nakliye.rota_update(rid, ad, cikis=cikis, varis=varis, mesafe_km=mesafe_km, sure_saat=sure_saat, aktif=aktif, notlar=notlar)

    def nakliye_rota_set_active(self, rid: int, aktif: int):
        return self.nakliye.rota_set_active(rid, aktif)

    def nakliye_rota_delete(self, rid: int):
        return self.nakliye.rota_delete(rid)

    def nakliye_is_list(
        self,
        q: str = "",
        date_from: str = "",
        date_to: str = "",
        firma_id: Optional[int] = None,
        durum: str = "",
    ):
        return self.nakliye.is_list(q=q, date_from=date_from, date_to=date_to, firma_id=firma_id, durum=durum)

    def nakliye_is_add(
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
    ):
        return self.nakliye.is_add(
            is_no,
            tarih,
            saat=saat,
            firma_id=firma_id,
            arac_id=arac_id,
            rota_id=rota_id,
            cikis=cikis,
            varis=varis,
            yuk=yuk,
            durum=durum,
            ucret=ucret,
            para=para,
            notlar=notlar,
        )

    def nakliye_is_get(self, iid: int):
        return self.nakliye.is_get(iid)

    def nakliye_is_update(
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
    ):
        return self.nakliye.is_update(
            iid,
            is_no,
            tarih,
            saat=saat,
            firma_id=firma_id,
            arac_id=arac_id,
            rota_id=rota_id,
            cikis=cikis,
            varis=varis,
            yuk=yuk,
            durum=durum,
            ucret=ucret,
            para=para,
            notlar=notlar,
        )

    def nakliye_is_set_durum(self, iid: int, durum: str, aciklama: str = ""):
        return self.nakliye.is_set_durum(iid, durum, aciklama=aciklama)

    def nakliye_is_delete(self, iid: int):
        return self.nakliye.is_delete(iid)

    def nakliye_islem_list(self, is_id: int):
        return self.nakliye.islem_list(is_id)

    def nakliye_islem_add(self, is_id: int, tarih: Any, saat: str = "", tip: str = "İşlem", aciklama: str = ""):
        return self.nakliye.islem_add(is_id, tarih, saat=saat, tip=tip, aciklama=aciklama)

    def nakliye_islem_delete(self, islem_id: int):
        return self.nakliye.islem_delete(islem_id)

    def banka_list(self, q: str = "", date_from: str = "", date_to: str = "", tip: str = "",
                   banka: str = "", hesap: str = "", import_grup: str = "", limit: int = 2000):
        return self.banka.list(q=q, date_from=date_from, date_to=date_to, tip=tip, banka=banka, hesap=hesap, import_grup=import_grup, limit=limit)

    def banka_get(self, hid: int) -> Optional[sqlite3.Row]:
        return self.banka.get(hid)

    def banka_get_many(self, ids: List[int]) -> List[sqlite3.Row]:
        return self.banka.get_many(ids)

    def banka_update(self, hid: int, tarih: Any, banka: str, hesap: str, tip: str, tutar: float, para: str,
                     aciklama: str, referans: str, belge: str, etiket: str, import_grup: str = "", bakiye: Optional[float] = None):
        return self.banka.update(hid, tarih, banka, hesap, tip, tutar, para, aciklama, referans, belge, etiket, import_grup=import_grup, bakiye=bakiye)

    def banka_update_many(self, items: List[Dict[str, Any]]) -> None:
        """Banka hareketlerini toplu güncelle (tek transaction)."""
        return self.banka.update_many(items)

    def banka_import_groups(self, limit: int = 60) -> List[str]:
        return self.banka.import_groups(limit=limit)

    def banka_import_group_summaries(self, limit: int = 200):
        return self.banka.import_group_summaries(limit=limit)

    def banka_last_import_group(self) -> str:
        return self.banka.last_import_group()

    def banka_ids_by_import_group(self, import_grup: str, limit: int = 20000) -> List[int]:
        return self.banka.ids_by_import_group(import_grup, limit=limit)

    def banka_delete(self, hid: int):
        return self.banka.delete(hid)

    def banka_toplam(self, date_from: str = "", date_to: str = "", banka: str = "", hesap: str = "") -> Dict[str, float]:
        return self.banka.toplam(date_from=date_from, date_to=date_to, banka=banka, hesap=hesap)

    def banka_distinct_banks(self) -> List[str]:
        return self.banka.distinct_banks()

    def banka_distinct_accounts(self, banka: str = "") -> List[str]:
        return self.banka.distinct_accounts(banka=banka)

    # -----------------
    # Cari ekstre/bakiye
    # -----------------
    def cari_bakiye(self, cid: int) -> Dict[str, float]:
        c = self.cari_get(cid)
        acilis = float(c["acilis_bakiye"] if c else 0.0)
        return self.cari_hareket.bakiye(cid, acilis=acilis)

    def cari_ekstre(self, cid: int, date_from: str = "", date_to: str = "", q: str = "") -> Dict[str, Any]:
        c = self.cari_get(cid)
        acilis = float(c["acilis_bakiye"] if c else 0.0)
        return self.cari_hareket.ekstre(cid, acilis=acilis, date_from=date_from, date_to=date_to, q=q)

    # -----------------
    # Global Search
    # -----------------
    def global_search(self, q: str, limit: int = 300):
        return self.search.global_search(q, limit=limit)

    # -----------------
    # Maaş Takibi
    # -----------------
    def maas_calisan_list(self, q: str = "", only_active: bool = False):
        return self.maas.calisan_list(q=q, only_active=only_active)

    def maas_calisan_add(
        self,
        ad: str,
        aylik_tutar: float,
        para: str = "TL",
        aktif: int = 1,
        notlar: str = "",
        meslek_id: Optional[int] = None,
    ) -> int:
        return self.maas.calisan_add(ad, aylik_tutar, para=para, aktif=aktif, notlar=notlar, meslek_id=meslek_id)

    def maas_calisan_update(
        self,
        cid: int,
        ad: str,
        aylik_tutar: float,
        para: str = "TL",
        aktif: int = 1,
        notlar: str = "",
        meslek_id: Optional[int] = None,
    ):
        return self.maas.calisan_update(cid, ad, aylik_tutar, para=para, aktif=aktif, notlar=notlar, meslek_id=meslek_id)

    def maas_calisan_set_active(self, cid: int, aktif: int):
        return self.maas.calisan_set_active(cid, aktif)

    def maas_meslek_list(self, q: str = "", only_active: bool = False):
        return self.maas.meslek_list(q=q, only_active=only_active)

    def maas_meslek_add(self, ad: str, aktif: int = 1, notlar: str = "") -> int:
        return self.maas.meslek_add(ad, aktif=aktif, notlar=notlar)

    def maas_meslek_update(self, mid: int, ad: str, aktif: int = 1, notlar: str = ""):
        return self.maas.meslek_update(mid, ad, aktif=aktif, notlar=notlar)

    def maas_meslek_set_active(self, mid: int, aktif: int):
        return self.maas.meslek_set_active(mid, aktif)

    def maas_meslek_delete(self, mid: int):
        return self.maas.meslek_delete(mid)

    def maas_calisan_delete(self, cid: int):
        return self.maas.calisan_delete(cid)

    def maas_ensure_donem(self, donem: str):
        return self.maas.ensure_donem(donem)

    def maas_donem_list(self, limit: int = 36):
        return self.maas.donem_list(limit=limit)

    def maas_odeme_list(self, donem: str = "", q: str = "", odendi: Optional[int] = None, *, include_inactive: bool = False):
        return self.maas.odeme_list(donem=donem, q=q, odendi=odendi, include_inactive=include_inactive)

    def maas_odeme_get(self, oid: int) -> Optional[sqlite3.Row]:
        return self.maas.odeme_get(oid)


    def maas_odeme_set_paid(self, oid: int, odendi: int, odeme_tarihi: str = ""):
        return self.maas.odeme_set_paid(oid, odendi, odeme_tarihi=odeme_tarihi)

    def maas_odeme_update_amount(self, oid: int, tutar: float, para: str = "TL", aciklama: str = ""):
        return self.maas.odeme_update_amount(oid, tutar, para=para, aciklama=aciklama)

    def maas_odeme_upsert_from_excel(
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
        return self.maas.odeme_upsert_from_excel(
            donem,
            calisan_ad,
            tutar,
            para=para,
            odendi=odendi,
            odeme_tarihi=odeme_tarihi,
            aciklama=aciklama,
        )

    def maas_odeme_link_bank(self, oid: int, banka_hareket_id: int, *, score: float = 0.0, note: str = ""):
        return self.maas.odeme_link_bank(oid, banka_hareket_id, score=score, note=note)

    def maas_odeme_clear_bank_link(self, oid: int):
        return self.maas.odeme_clear_bank_link(oid)

    def maas_donem_ozet(self, donem: str, *, include_inactive: bool = False):
        return self.maas.donem_ozet(donem, include_inactive=include_inactive)

    def maas_aylik_toplamlar(self, limit: int = 24):
        return self.maas.aylik_toplamlar(limit=limit)

    def maas_hesap_hareket_add(
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
        return self.maas.hesap_hareket_add(
            donem=donem,
            calisan_id=calisan_id,
            banka_hareket_id=banka_hareket_id,
            odeme_id=odeme_id,
            match_score=match_score,
            match_type=match_type,
            note=note,
        )

    def maas_hesap_hareket_list(
        self,
        *,
        donem: str = "",
        calisan_id: Optional[int] = None,
        q: str = "",
        date_from: str = "",
        date_to: str = "",
        limit: int = 5000,
        include_inactive: bool = True,
    ):
        return self.maas.hesap_hareket_list(
            donem=donem,
            calisan_id=calisan_id,
            q=q,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            include_inactive=include_inactive,
        )

    def maas_hesap_hareket_clear_donem(self, donem: str) -> int:
        return self.maas.hesap_hareket_clear_donem(donem)

    # -----------------
    # Fatura
    # -----------------
    def fatura_seri_list(self):
        return self.fatura.list_seri()

    def fatura_seri_upsert(
        self,
        *,
        seri: str,
        yil: int,
        prefix: str = "FTR",
        last_no: int = 0,
        padding: int = 6,
        fmt: str = "{yil}{seri}{no_pad}",
        aktif: int = 1,
    ):
        return self.fatura.seri_upsert(seri=seri, yil=yil, prefix=prefix, last_no=last_no, padding=padding, fmt=fmt, aktif=aktif)

    def fatura_next_no(self, seri: str = "A", yil: Optional[int] = None) -> str:
        return self.fatura.next_fatura_no(seri=seri, yil=yil)

    def fatura_list(self, *, q: str = "", date_from: str = "", date_to: str = "", tur: str = "", durum: str = "", cari_id: Optional[int] = None):
        return self.fatura.list(q=q, date_from=date_from, date_to=date_to, tur=tur, durum=durum, cari_id=cari_id)

    def fatura_get(self, fid: int):
        return self.fatura.get(fid)

    def fatura_create(self, header: Dict[str, Any], kalemler: List[Dict[str, Any]]) -> int:
        return self.fatura.create(header, kalemler)

    def fatura_update(self, fid: int, header: Dict[str, Any], kalemler: List[Dict[str, Any]]):
        return self.fatura.update(fid, header, kalemler)

    def fatura_delete(self, fid: int):
        return self.fatura.delete(fid)

    def fatura_kalem_list(self, fid: int):
        return self.fatura.kalem_list(fid)

    def fatura_odeme_list(self, fid: int):
        return self.fatura.odeme_list(fid)

    def fatura_odeme_add(
        self,
        *,
        fid: int,
        tarih: Any,
        tutar: float,
        para: str,
        odeme: str,
        aciklama: str = "",
        ref: str = "",
        kasa_hareket_id: Optional[int] = None,
        banka_hareket_id: Optional[int] = None,
    ) -> int:
        return self.fatura.odeme_add(
            fid,
            tarih=tarih,
            tutar=tutar,
            para=para,
            odeme=odeme,
            aciklama=aciklama,
            ref=ref,
            kasa_hareket_id=kasa_hareket_id,
            banka_hareket_id=banka_hareket_id,
        )

    def fatura_odeme_delete(self, odeme_id: int):
        return self.fatura.odeme_delete(odeme_id)

    def fatura_odeme_toplam(self, fid: int) -> float:
        return self.fatura.odeme_toplam(fid)
