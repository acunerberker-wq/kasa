# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Dict, Iterable, Tuple
from urllib.request import urlopen


@dataclass
class IndexFetchResult:
    provider: str
    indices: Dict[str, float]
    raw: str


class HakedisOrgProvider:
    provider_name = "hakedis_org"
    base_url = "https://hakedis.org/"  # placeholder, provider arayüzü

    def fetch_indices(self, index_codes: Iterable[str], period: str) -> IndexFetchResult:
        codes = list(index_codes)
        url = f"{self.base_url}?period={period}"
        raw = ""
        try:
            with urlopen(url, timeout=10) as resp:
                raw = resp.read().decode("utf-8", errors="ignore")
        except Exception:
            raw = ""
        indices = self.parse_indices_html(raw, codes)
        return IndexFetchResult(provider=self.provider_name, indices=indices, raw=raw)

    @staticmethod
    def parse_indices_html(html: str, index_codes: Iterable[str]) -> Dict[str, float]:
        if not html:
            return {}
        wanted = {str(c).strip(): None for c in index_codes}
        result: Dict[str, float] = {}
        for code in wanted.keys():
            pattern = rf"<tr[^>]*>\s*<td[^>]*>\s*{re.escape(code)}\s*</td>\s*<td[^>]*>([^<]+)</td>"
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                val = match.group(1).strip().replace(",", ".")
                try:
                    result[code] = float(val)
                except Exception:
                    continue
        return result

    @staticmethod
    def parse_indices_json(payload: str) -> Dict[str, float]:
        try:
            data = json.loads(payload)
        except Exception:
            return {}
        indices = {}
        for item in data.get("indices", []):
            code = str(item.get("code") or "").strip()
            value = item.get("value")
            if not code:
                continue
            try:
                indices[code] = float(value)
            except Exception:
                continue
        return indices
