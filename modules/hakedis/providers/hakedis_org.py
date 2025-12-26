# -*- coding: utf-8 -*-
"""hakedis.org endeks sağlayıcı."""

from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Dict, Iterable, List, Optional


HAKEDIS_ORG_URL = "https://hakedis.org/endeksler-ve-fiyat-farkina-esas-katsayilar/"


@dataclass
class IndexRow:
    period: str
    value: float


class _IndexHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.sections: Dict[str, List[IndexRow]] = {}
        self._current_section: Optional[str] = None
        self._in_heading = False
        self._in_tr = False
        self._in_td = False
        self._current_cells: List[str] = []
        self._buffer: List[str] = []

    def handle_starttag(self, tag: str, attrs):
        attrs_dict = dict(attrs or [])
        if tag in {"h2", "h3"}:
            self._in_heading = True
            self._buffer = []
        if tag in {"section", "div"}:
            data_set = attrs_dict.get("data-set") or attrs_dict.get("data-section")
            if data_set:
                self._current_section = data_set.strip()
        if tag == "tr":
            self._in_tr = True
            self._current_cells = []
        if tag in {"td", "th"} and self._in_tr:
            self._in_td = True
            self._buffer = []

    def handle_endtag(self, tag: str):
        if tag in {"h2", "h3"} and self._in_heading:
            text = "".join(self._buffer).strip()
            if text:
                self._current_section = text
            self._in_heading = False
            self._buffer = []
        if tag in {"td", "th"} and self._in_td:
            text = "".join(self._buffer).strip()
            if text:
                self._current_cells.append(text)
            self._in_td = False
            self._buffer = []
        if tag == "tr" and self._in_tr:
            self._commit_row()
            self._in_tr = False
            self._current_cells = []

    def handle_data(self, data: str):
        if self._in_heading or self._in_td:
            self._buffer.append(data)

    def _commit_row(self):
        if not self._current_section or len(self._current_cells) < 2:
            return
        period = self._current_cells[0].strip()
        value_raw = self._current_cells[1].strip()
        value = _parse_decimal(value_raw)
        if value is None:
            return
        self.sections.setdefault(self._current_section, []).append(IndexRow(period=period, value=value))


_decimal_re = re.compile(r"[^0-9,\.]+")


def _parse_decimal(value: str) -> Optional[float]:
    if not value:
        return None
    clean = _decimal_re.sub("", value)
    if not clean:
        return None
    if clean.count(",") == 1 and clean.count(".") == 0:
        clean = clean.replace(",", ".")
    elif clean.count(",") > 1 and clean.count(".") == 0:
        clean = clean.replace(".", "")
        clean = clean.replace(",", ".")
    else:
        clean = clean.replace(",", "")
    try:
        return float(clean)
    except ValueError:
        return None


def parse_indices_html(html: str, selected_sets: Optional[Iterable[str]] = None) -> Dict[str, List[IndexRow]]:
    parser = _IndexHTMLParser()
    parser.feed(html or "")
    if selected_sets:
        allowed = {s.strip() for s in selected_sets if s and str(s).strip()}
        return {k: v for k, v in parser.sections.items() if k in allowed}
    return parser.sections


def fetch_indices(selected_sets: Optional[Iterable[str]] = None, url: str = HAKEDIS_ORG_URL, timeout: int = 12) -> Dict[str, List[IndexRow]]:
    req = urllib.request.Request(url, headers={"User-Agent": "KasaPro/3.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        html = resp.read().decode("utf-8", errors="ignore")
    return parse_indices_html(html, selected_sets)


def serialize_indices(indices: Dict[str, List[IndexRow]]) -> str:
    payload = {k: [row.__dict__ for row in v] for k, v in indices.items()}
    return json.dumps(payload, ensure_ascii=False)


def deserialize_indices(payload: str) -> Dict[str, List[IndexRow]]:
    data = json.loads(payload or "{}")
    out: Dict[str, List[IndexRow]] = {}
    for key, rows in data.items():
        if not isinstance(rows, list):
            continue
        parsed: List[IndexRow] = []
        for row in rows:
            try:
                period = str(row.get("period"))
                value = float(row.get("value"))
            except Exception:
                continue
            parsed.append(IndexRow(period=period, value=value))
        if parsed:
            out[str(key)] = parsed
    return out
