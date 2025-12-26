# -*- coding: utf-8 -*-

from __future__ import annotations

import csv
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ...utils import now_iso, today_iso
from .constants import (
    CONVERT_ROLES,
    ORDER_STATUSES,
    QUOTE_STATUSES,
    ROLE_ADMIN,
    ROLE_VIEWER,
)
from .repo import QuoteOrderRepo


@dataclass
class Actor:
    user_id: Optional[int]
    username: str
    role: str


class QuoteOrderService:
    def __init__(self, db):
        self.db = db
        self.repo = QuoteOrderRepo(db.conn, log_fn=db.log)

    def _normalize_role(self, role: str) -> str:
        role = (role or "").strip().upper()
        if role == "ADMIN":
            return ROLE_ADMIN
        if role == "USER":
            return ROLE_VIEWER
        if role == "ADMINISTRATOR":
            return ROLE_ADMIN
        if role == "":
            return ROLE_VIEWER
        return role

    def _actor(self, actor: Optional[Dict[str, Any]] = None) -> Actor:
        if actor is None:
            return Actor(user_id=None, username="system", role=ROLE_ADMIN)
        return Actor(
            user_id=int(actor.get("id")) if actor.get("id") is not None else None,
            username=str(actor.get("username") or "system"),
            role=self._normalize_role(str(actor.get("role") or "")),
        )

    def _compute_lines(self, lines: Iterable[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, float]]:
        computed: List[Dict[str, Any]] = []
        ara_toplam = 0.0
        iskonto_toplam = 0.0
        kdv_toplam = 0.0
        genel_toplam = 0.0

        for idx, line in enumerate(lines, start=1):
            miktar = float(line.get("miktar", 0))
            birim_fiyat = float(line.get("birim_fiyat", 0))
            iskonto_oran = float(line.get("iskonto_oran", 0))
            kdv_oran = float(line.get("kdv_oran", 0))
            ara = miktar * birim_fiyat
            iskonto = ara * iskonto_oran / 100.0
            net = ara - iskonto
            kdv = net * kdv_oran / 100.0
            toplam = net + kdv

            ara_toplam += ara
            iskonto_toplam += iskonto
            kdv_toplam += kdv
            genel_toplam += toplam

            computed.append(
                {
                    **line,
                    "line_no": int(line.get("line_no", idx)),
                    "miktar": miktar,
                    "birim_fiyat": birim_fiyat,
                    "iskonto_oran": iskonto_oran,
                    "iskonto_tutar": iskonto,
                    "kdv_oran": kdv_oran,
                    "kdv_tutar": kdv,
                    "toplam": toplam,
                }
            )

        totals = {
            "ara_toplam": ara_toplam,
            "iskonto_toplam": iskonto_toplam,
            "kdv_toplam": kdv_toplam,
            "genel_toplam": genel_toplam,
        }
        return computed, totals

    def _apply_general_discount(self, totals: Dict[str, float], rate: float) -> Dict[str, float]:
        rate = float(rate or 0)
        net = totals["genel_toplam"]
        genel_iskonto = net * rate / 100.0
        totals["genel_iskonto_oran"] = rate
        totals["genel_iskonto_tutar"] = genel_iskonto
        totals["genel_toplam"] = net - genel_iskonto
        return totals

    def next_quote_no(self, prefix: str = "Q") -> str:
        return self.repo.next_series_no("quote_no", prefix=prefix)

    def next_order_no(self, prefix: str = "SO") -> str:
        return self.repo.next_series_no("order_no", prefix=prefix)

    def create_quote(self, data: Dict[str, Any], lines: Iterable[Dict[str, Any]], actor: Optional[Dict[str, Any]] = None) -> int:
        actor_obj = self._actor(actor)
        quote_no = data.get("quote_no") or self.next_quote_no()
        computed_lines, totals = self._compute_lines(lines)
        totals = self._apply_general_discount(totals, float(data.get("genel_iskonto_oran", 0)))
        payload = {
            **data,
            "quote_no": quote_no,
            "version": 1,
            "status": data.get("status", "DRAFT"),
            "ara_toplam": totals["ara_toplam"],
            "iskonto_toplam": totals["iskonto_toplam"],
            "genel_iskonto_oran": totals.get("genel_iskonto_oran", 0),
            "genel_iskonto_tutar": totals.get("genel_iskonto_tutar", 0),
            "kdv_toplam": totals["kdv_toplam"],
            "genel_toplam": totals["genel_toplam"],
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        quote_id = self.repo.insert_quote(payload)
        self.repo.update_quote(quote_id, {"quote_group_id": quote_id, **payload})
        self.repo.insert_quote_lines(quote_id, computed_lines)
        self.repo.add_audit("quote", quote_id, "create", actor_obj.user_id, actor_obj.username, actor_obj.role)
        return quote_id

    def update_quote(self, quote_id: int, data: Dict[str, Any], lines: Iterable[Dict[str, Any]], actor: Optional[Dict[str, Any]] = None) -> None:
        actor_obj = self._actor(actor)
        quote = self.repo.get_quote(quote_id)
        if not quote:
            raise ValueError("quote bulunamadı")
        if int(quote["locked"] or 0) == 1 or quote["status"] == "CONVERTED":
            raise ValueError("Dönüştürülen teklif değiştirilemez")
        versions = self.repo.get_quote_versions(str(quote["quote_no"]))
        latest_version = max(int(v["version"]) for v in versions) if versions else int(quote["version"])
        if int(quote["version"]) != latest_version:
            raise ValueError("Eski versiyon düzenlenemez")

        computed_lines, totals = self._compute_lines(lines)
        totals = self._apply_general_discount(totals, float(data.get("genel_iskonto_oran", 0)))
        payload = {
            **data,
            "status": data.get("status", quote["status"]),
            "ara_toplam": totals["ara_toplam"],
            "iskonto_toplam": totals["iskonto_toplam"],
            "genel_iskonto_oran": totals.get("genel_iskonto_oran", 0),
            "genel_iskonto_tutar": totals.get("genel_iskonto_tutar", 0),
            "kdv_toplam": totals["kdv_toplam"],
            "genel_toplam": totals["genel_toplam"],
            "updated_at": now_iso(),
        }
        self.repo.update_quote(quote_id, payload)
        self.repo.replace_quote_lines(quote_id, computed_lines)
        self.repo.add_audit("quote", quote_id, "update", actor_obj.user_id, actor_obj.username, actor_obj.role)

    def revise_quote(self, quote_id: int, actor: Optional[Dict[str, Any]] = None) -> int:
        actor_obj = self._actor(actor)
        quote = self.repo.get_quote(quote_id)
        if not quote:
            raise ValueError("quote bulunamadı")
        if quote["status"] == "CONVERTED":
            raise ValueError("Dönüştürülen teklif revize edilemez")
        quote_no = str(quote["quote_no"])
        versions = self.repo.get_quote_versions(quote_no)
        latest_version = max(int(v["version"]) for v in versions) if versions else int(quote["version"])
        new_version = latest_version + 1

        lines = self.repo.get_quote_lines(quote_id)
        line_dicts = [dict(row) for row in lines]
        payload = dict(quote)
        payload.update(
            {
                "version": new_version,
                "status": "DRAFT",
                "locked": 0,
                "created_at": now_iso(),
                "updated_at": now_iso(),
            }
        )
        payload.pop("id", None)
        new_id = self.repo.insert_quote(payload)
        self.repo.insert_quote_lines(new_id, line_dicts)
        self.repo.update_quote_status(quote_id, "REVISED")
        self.repo.add_audit("quote", quote_id, "revise", actor_obj.user_id, actor_obj.username, actor_obj.role)
        self.repo.add_audit("quote", new_id, "create_revision", actor_obj.user_id, actor_obj.username, actor_obj.role)
        return new_id

    def send_quote(self, quote_id: int, actor: Optional[Dict[str, Any]] = None) -> None:
        self._set_quote_status(quote_id, "SENT", actor, action="send")

    def approve_quote(self, quote_id: int, actor: Optional[Dict[str, Any]] = None) -> None:
        self._set_quote_status(quote_id, "CUSTOMER_APPROVED", actor, action="approve")

    def reject_quote(self, quote_id: int, actor: Optional[Dict[str, Any]] = None, note: str = "") -> None:
        self._set_quote_status(quote_id, "REJECTED", actor, action="reject", note=note)

    def _set_quote_status(self, quote_id: int, status: str, actor: Optional[Dict[str, Any]], action: str, note: str = "") -> None:
        actor_obj = self._actor(actor)
        if status not in QUOTE_STATUSES:
            raise ValueError("Geçersiz durum")
        self.repo.update_quote_status(quote_id, status)
        self.repo.add_audit("quote", quote_id, action, actor_obj.user_id, actor_obj.username, actor_obj.role, note)

    def list_quotes(self, q: str = "", status: str = "", limit: int = 50, offset: int = 0) -> Tuple[List[Dict[str, Any]], int]:
        self.repo.expire_quotes(today_iso())
        rows = self.repo.list_quotes(q=q, status=status, limit=limit, offset=offset)
        total = self.repo.count_quotes(q=q, status=status)
        return [dict(r) for r in rows], total

    def get_quote(self, quote_id: int, with_lines: bool = True) -> Dict[str, Any]:
        self.repo.expire_quotes(today_iso())
        row = self.repo.get_quote(quote_id)
        if not row:
            raise ValueError("quote bulunamadı")
        data = dict(row)
        if with_lines:
            data["lines"] = [dict(r) for r in self.repo.get_quote_lines(quote_id)]
        return data

    def convert_to_order(self, quote_id: int, actor: Optional[Dict[str, Any]] = None) -> int:
        actor_obj = self._actor(actor)
        role = self._normalize_role(actor_obj.role)
        if role not in CONVERT_ROLES:
            raise PermissionError("Yetkisiz işlem")
        quote = self.repo.get_quote(quote_id)
        if not quote:
            raise ValueError("quote bulunamadı")
        if quote["status"] == "CONVERTED":
            raise ValueError("Teklif zaten dönüştürüldü")
        if quote["status"] in ("REJECTED", "EXPIRED"):
            raise ValueError("Teklif dönüştürülemez")
        if quote["status"] != "CUSTOMER_APPROVED":
            raise ValueError("Teklif onaylanmadan dönüştürülemez")

        order_no = self.next_order_no()
        lines = [dict(r) for r in self.repo.get_quote_lines(quote_id)]
        payload = {
            "order_no": order_no,
            "quote_id": int(quote_id),
            "status": "DRAFT",
            "cari_id": quote["cari_id"],
            "cari_ad": quote["cari_ad"],
            "para": quote["para"],
            "kur": quote["kur"],
            "ara_toplam": quote["ara_toplam"],
            "iskonto_toplam": quote["iskonto_toplam"],
            "kdv_toplam": quote["kdv_toplam"],
            "genel_toplam": quote["genel_toplam"],
            "notlar": quote["notlar"],
        }
        order_id = self.repo.insert_order(payload)
        self.repo.insert_order_lines(order_id, lines)
        self.repo.update_quote_status(quote_id, "CONVERTED", locked=1)
        self.repo.add_audit("quote", quote_id, "convert", actor_obj.user_id, actor_obj.username, actor_obj.role)
        self.repo.add_audit("order", order_id, "create", actor_obj.user_id, actor_obj.username, actor_obj.role)
        return order_id

    def list_orders(self, q: str = "", status: str = "", limit: int = 50, offset: int = 0) -> Tuple[List[Dict[str, Any]], int]:
        rows = self.repo.list_orders(q=q, status=status, limit=limit, offset=offset)
        total = self.repo.count_orders(q=q, status=status)
        return [dict(r) for r in rows], total

    def get_order(self, order_id: int, with_lines: bool = True) -> Dict[str, Any]:
        row = self.repo.get_order(order_id)
        if not row:
            raise ValueError("order bulunamadı")
        data = dict(row)
        if with_lines:
            data["lines"] = [dict(r) for r in self.repo.get_order_lines(order_id)]
        return data

    def update_order_status(self, order_id: int, status: str, actor: Optional[Dict[str, Any]] = None) -> None:
        actor_obj = self._actor(actor)
        if status not in ORDER_STATUSES:
            raise ValueError("Geçersiz durum")
        self.repo.update_order_status(order_id, status)
        self.repo.add_audit("order", order_id, "status", actor_obj.user_id, actor_obj.username, actor_obj.role, status)

    def list_audit(self, entity_type: str, entity_id: int) -> List[Dict[str, Any]]:
        rows = self.repo.list_audit(entity_type, entity_id)
        return [dict(r) for r in rows]

    def export_quotes_csv(self, path: str, rows: Iterable[Dict[str, Any]]) -> None:
        headers = [
            "quote_no",
            "version",
            "status",
            "cari_ad",
            "valid_until",
            "para",
            "kur",
            "ara_toplam",
            "iskonto_toplam",
            "kdv_toplam",
            "genel_toplam",
            "created_at",
        ]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for row in rows:
                writer.writerow({k: row.get(k, "") for k in headers})
