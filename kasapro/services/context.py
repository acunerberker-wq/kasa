# -*- coding: utf-8 -*-
"""Servis konteyneri.

App açılırken tek bir yerde oluşturulur ve UI'ye `app.services` olarak verilir.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ..db.main_db import DB
from ..db.users_db import UsersDB

from .export_service import ExportService
from .settings_service import SettingsService
from .company_users_service import CompanyUsersService
from .cari_service import CariService
from .messages_service import MessagesService
from ..modules.dms.service import DmsService
from ..modules.notes_reminders.service import NotesRemindersService
from ..modules.integrations.service import IntegrationService
from ..modules.hakedis.service import HakedisService

# HR module is in top-level modules/ not kasapro/modules/
try:
    import sys
    import os
    # Add modules/ to path if not already there
    modules_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "modules"))
    if modules_path not in sys.path:
        sys.path.insert(0, modules_path)
    from hr.service import HRService, HRContext
except ImportError:
    # Fallback: HR module may not be installed
    HRService = None
    HRContext = None


@dataclass
class Services:
    db: DB
    usersdb: UsersDB

    exporter: ExportService
    settings: SettingsService
    company_users: CompanyUsersService
    cari: CariService
    messages: MessagesService
    dms: DmsService
    notes_reminders: NotesRemindersService
    integrations: IntegrationService
    hr: HRService
    hakedis: HakedisService

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
            dms=DmsService(db),
            notes_reminders=NotesRemindersService(db, usersdb),
            integrations=IntegrationService(db, context_provider),
            hr=hr_service,
            hakedis=hakedis_service,
        )
