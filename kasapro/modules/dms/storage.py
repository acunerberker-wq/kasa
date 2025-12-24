# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import mimetypes
import os
import shutil
from dataclasses import dataclass
from typing import Optional, Tuple

from ...config import SHARED_STORAGE_DIR
from ...utils import _safe_slug

ALLOWED_EXTENSIONS = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".txt": "text/plain",
}

MAX_FILE_BYTES = 25 * 1024 * 1024


@dataclass(frozen=True)
class StoredFile:
    file_path: str
    original_name: str
    mime: str
    size: int
    sha256: str


def _ensure_safe_name(original_name: str) -> str:
    base = os.path.basename(original_name or "")
    if not base or base != original_name:
        raise ValueError("Geçersiz dosya adı.")
    stem, ext = os.path.splitext(base)
    ext = ext.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("İzin verilmeyen dosya uzantısı.")
    safe_stem = _safe_slug(stem)
    return f"{safe_stem}{ext}"


def _guess_mime(path: str, original_name: str) -> str:
    mime, _ = mimetypes.guess_type(original_name or path)
    return mime or "application/octet-stream"


def _validate_source(path: str, original_name: str) -> Tuple[str, str, int]:
    if not os.path.exists(path):
        raise FileNotFoundError("Dosya bulunamadı.")
    safe_name = _ensure_safe_name(original_name)
    size = os.path.getsize(path)
    if size > MAX_FILE_BYTES:
        raise ValueError("Dosya boyutu limitini aşıyor.")
    mime = _guess_mime(path, original_name)
    allowed_mime = ALLOWED_EXTENSIONS.get(os.path.splitext(safe_name)[1])
    if allowed_mime and mime != allowed_mime:
        raise ValueError("Dosya MIME tipi uyumsuz.")
    return safe_name, mime, size


def _safe_join(base_dir: str, *parts: str) -> str:
    candidate = os.path.abspath(os.path.join(base_dir, *parts))
    base_dir = os.path.abspath(base_dir)
    if not candidate.startswith(base_dir + os.sep):
        raise ValueError("Geçersiz dosya yolu.")
    return candidate


def _hash_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def store_attachment(
    company_id: int,
    document_id: int,
    version_no: int,
    source_path: str,
    original_name: str,
    base_dir: Optional[str] = None,
) -> StoredFile:
    base_dir = base_dir or SHARED_STORAGE_DIR
    safe_name, mime, size = _validate_source(source_path, original_name)

    dest_root = _safe_join(
        base_dir,
        "storage",
        "attachments",
        str(company_id),
        "document",
        str(document_id),
        str(version_no),
    )
    os.makedirs(dest_root, exist_ok=True)

    dest_path = _safe_join(dest_root, safe_name)
    shutil.copy2(source_path, dest_path)
    sha256 = _hash_file(dest_path)

    return StoredFile(
        file_path=dest_path,
        original_name=original_name,
        mime=mime,
        size=size,
        sha256=sha256,
    )
