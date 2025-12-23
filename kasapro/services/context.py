# -*- coding: utf-8 -*-
"""Servis konteyneri.

App açılırken tek bir yerde oluşturulur ve UI'ye `app.services` olarak verilir.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..db.main_db import DB
from ..db.users_db import UsersDB

from .export_service import ExportService
from .settings_service import SettingsService
from .company_users_service import CompanyUsersService
from .cari_service import CariService


@dataclass
class Services:
    db: DB
    usersdb: UsersDB

    exporter: ExportService
    settings: SettingsService
    company_users: CompanyUsersService
    cari: CariService

    @classmethod
    def build(cls, db: DB, usersdb: UsersDB) -> "Services":
        exporter = ExportService()
        return cls(
            db=db,
            usersdb=usersdb,
            exporter=exporter,
            settings=SettingsService(db),
            company_users=CompanyUsersService(db),
            cari=CariService(db, exporter),
        )
