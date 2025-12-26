# -*- coding: utf-8 -*-
"""Servis konteyneri.

App açılırken tek bir yerde oluşturulur ve UI'ye `app.services` olarak verilir.
"""

from __future__ import annotations

import sys
import os
from dataclasses import dataclass
from typing import Callable, Optional

from ..db.main_db import DB
from ..db.users_db import UsersDB

from .export_service import ExportService
from .settings_service import SettingsService
from .company_users_service import CompanyUsersService
from .cari_service import CariService
from .messages_service import MessagesService
from .wms_service import WmsService
from ..modules.notes_reminders.service import NotesRemindersService
from ..modules.dms.service import DmsService
from ..modules.integrations.service import IntegrationService
from ..modules.hakedis.service import HakedisService

# HR modülü için dinamik import (modules/ klasöründen)
try:
    _modules_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "modules"))
    if _modules_path not in sys.path:
        sys.path.insert(0, _modules_path)
    from hr.service import HRService
except ImportError:
    HRService = None


@dataclass
class Services:
    db: DB
    usersdb: UsersDB

    exporter: ExportService
    settings: SettingsService
    company_users: CompanyUsersService
    cari: CariService
    messages: MessagesService
    notes_reminders: NotesRemindersService
    wms: WmsService
    integrations: IntegrationService

    @classmethod
    def build(cls, db: DB, usersdb: UsersDB, context_provider) -> "Services":
        exporter = ExportService()
        hr_service = HRService(db, context_provider) if HRService else None
        hakedis_service = HakedisService(db)
        return cls(
            db=db,
            usersdb=usersdb,
            exporter=exporter,
            settings=SettingsService(db),
            company_users=CompanyUsersService(db),
            cari=CariService(db, exporter),
            messages=MessagesService(db, usersdb),
            notes_reminders=NotesRemindersService(db, usersdb),
            wms=WmsService(db),
            integrations=IntegrationService(db, context_provider),
        )
