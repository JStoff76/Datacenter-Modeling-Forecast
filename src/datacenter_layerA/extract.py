from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd
import requests
from bs4 import BeautifulSoup

from .fetcher import FetchResult, guess_parse_method
from .normalize import normalize_text


SPEC_NAMES = {
    "square_ft": {
        "pattern": re.compile(r"(\d{1,3}(?:,\d{3})+|\d+)\s*(?:sq\.?\s*ft|square\s*feet)", re.I),
        "unit": "sqft",
    },
    "power_mw": {
        "pattern": re.compile(r"(\d+(?:\.\d+)?)\s*(?:MW|megawatts?)", re.I),
        "unit": "MW",
    },
    "kw_per_rack": {
        "pattern": re.compile(r"(\d{1,4}(?:\.\d+)?)\s*(?:kW)\s*/\s*rack", re.I),
        "unit": "kW_per_rack",
    },
    "rack_count": {
        "pattern": re.compile(r"(\d{1,3}(?:,\d{3})+|\d+)\s*(?:racks?)", re.I),
        "unit": "racks",
    },
    "cooling_type": {
        "pattern": re.compile(
            r"(air cooled|chilled water|direct-to-chip|liquid cooled|immersion|evaporative)",
            re.I,
        ),
        "unit": "",
    },
    "go_live_date": {
        "pattern": re.compile(r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})", re.I),
        "unit": "",
    },
}


@dataclass
class Observation:
    datacenter_id: str
    spec_name: str
    value_num: Optional[float]
    unit: str
    value_text: str
    source_url: str
    snippet: str
    date_accessed: str
    confidence: float
    method: str


WINDOW = 120


def text_snippet(text: str, start: int, end: int, window: int = WINDOW) -> str:
    left = max(0, start - window)
    right = min(len(text), end + window)
    return text[left:right][:300]


def extract_from_text(datacenter_id: str, text: str, source_url: str, base_confidence: float) -> List[Observation]:
    observations: List[Observation] = []
    for spec, meta in SPEC_NAMES.items():
        for match in meta["pattern"].finditer(text):
            raw = match.group(0)
            value_text = raw.strip()
            value_num = None
            try:
                numeric_part = match.group(1).replace(",", "")
                value_num = float(numeric_part)
            except Exception:
                value_num = None
            snippet = text_snippet(text, match.start(), match.end())
            observations.append(
                Observation(
                    datacenter_id=datacenter_id,
                    spec_name=spec,
                    value_num=value_num,
                    unit=meta["unit"],
                    value_text=value_text,
                    source_url=source_url,
                    snippet=snippet,
                    date_accessed=datetime.utcnow().isoformat(),
                    confidence=min(1.0, base_confidence + 0.05),
                    method="scrape_html",
                )
            )
    return observations


def parse_content(fetch_result: FetchResult, datacenter_id: str) -> Tuple[List[Observation], Dict[str, str]]:
    observations: List[Observation] = []
    metadata: Dict[str, str] = {}
    if not fetch_result.content:
        return observations, metadata
    parse_method = guess_parse_method(fetch_result.content_type)
    metadata["parse_method"] = parse_method
    text = ""
    if "pdf" in (fetch_result.content_type or ""):
        try:
            from pdfminer.high_level import extract_text

            text = extract_text(fetch_result.content)
        except Exception:
            text = fetch_result.content.decode("utf-8", errors="ignore")
    else:
        html = fetch_result.content.decode("utf-8", errors="ignore")
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True)
    observations.extend(extract_from_text(datacenter_id, text, fetch_result.url, 0.6))
    return observations, metadata


def build_spec_df(observations: List[Observation]) -> pd.DataFrame:
    if not observations:
        return pd.DataFrame(
            columns=[
                "datacenter_id",
                "spec_name",
                "value_num",
                "unit",
                "value_text",
                "source_url",
                "snippet",
                "date_accessed",
                "confidence",
                "method",
            ]
        )
    return pd.DataFrame([obs.__dict__ for obs in observations])
