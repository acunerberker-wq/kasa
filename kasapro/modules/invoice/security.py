# -*- coding: utf-8 -*-
"""Role-based access control for invoice module."""

from __future__ import annotations

from typing import Iterable

ALLOWED_CREATE = {"admin", "muhasebe", "satis", "satin_alma", "user"}
ALLOWED_PAYMENTS = {"admin", "muhasebe", "satis", "satin_alma", "user"}
ALLOWED_VOID = {"admin", "muhasebe"}
READ_ONLY = {"read-only", "readonly", "viewer"}


def _normalize(role: str) -> str:
    return str(role or "").strip().lower()


def _allowed(role: str, allowed: Iterable[str]) -> bool:
    r = _normalize(role)
    if r in READ_ONLY:
        return False
    return r in allowed


def can_create_document(role: str) -> bool:
    return _allowed(role, ALLOWED_CREATE)


def can_manage_payments(role: str) -> bool:
    return _allowed(role, ALLOWED_PAYMENTS)


def can_void_document(role: str) -> bool:
    return _allowed(role, ALLOWED_VOID)
