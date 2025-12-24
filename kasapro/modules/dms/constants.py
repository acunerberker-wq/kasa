# -*- coding: utf-8 -*-
from __future__ import annotations

DMS_STATUSES = [
    "ACTIVE",
    "ARCHIVED",
    "APPROVED",
    "REJECTED",
    "REVISION_REQUESTED",
]

WORKFLOW_STATUSES = [
    "NOT_STARTED",
    "IN_REVIEW",
    "REVISION_REQUESTED",
    "APPROVED",
    "REJECTED",
    "COMPLETED",
]

TASK_STATUSES = ["OPEN", "IN_PROGRESS", "DONE"]
REMINDER_STATUSES = ["PENDING", "SNOOZED", "DONE"]

DOC_TYPES = [
    "Sözleşme",
    "Teklif",
    "Tutanak",
    "Hakediş",
    "Genel",
]
