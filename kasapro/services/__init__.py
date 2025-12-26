# -*- coding: utf-8 -*-

from .context import Services
from .settings_service import SettingsService
from .company_users_service import CompanyUsersService
from .cari_service import CariService
from .export_service import ExportService
from .messages_service import MessagesService
from modules.hakedis.service import HakedisService
from ..modules.hakedis.service import HakedisService
from ..modules.quote_order.service import QuoteOrderService
from modules.hr.service import HRService
from .wms_service import WmsService
from ..modules.notes_reminders.service import NotesRemindersService

__all__ = [
    "Services",
    "SettingsService",
    "CompanyUsersService",
    "CariService",
    "ExportService",
    "MessagesService",
    "HakedisService",
    "HakedisService",
    "QuoteOrderService",
    "HRService",
    "NotesRemindersService",
    "WmsService",
]
