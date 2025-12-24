# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import Dict, Set


ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    "admin": {"*"},
    "muhasebe": {"sales", "purchase", "payments", "reports", "orders", "stock", "settings"},
    "satis": {"sales", "orders", "reports", "payments"},
    "satinlama": {"purchase", "orders", "reports", "payments"},
    "depo": {"stock", "orders", "reports"},
    "read-only": {"reports"},
}


def has_permission(role: str, permission: str) -> bool:
    role = (role or "").strip().lower()
    permission = (permission or "").strip().lower()
    perms = ROLE_PERMISSIONS.get(role, set())
    return "*" in perms or permission in perms
