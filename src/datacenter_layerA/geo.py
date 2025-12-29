from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests

from .config import CONFIG


CITY_STATE_RE = re.compile(r"([A-Z][a-zA-Z]+)\s*,\s*([A-Z]{2})")
COUNTRY_RE = re.compile(r"([A-Z][a-zA-Z]+)\s*,\s*([A-Z][a-zA-Z]+)")


@dataclass
class GeoResult:
    city: Optional[str]
    region_state: Optional[str]
    country_code: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    geo_confidence: float
    geo_source: str
    geo_notes: str


def parse_geo_from_text(text: str) -> GeoResult:
    city = region = country = None
    match = CITY_STATE_RE.search(text)
    if match:
        city, region = match.groups()
        return GeoResult(city, region, None, None, None, 0.8, "parsed_from_text", "city,state pattern")
    match = COUNTRY_RE.search(text)
    if match:
        city, country = match.groups()
        return GeoResult(city, None, country[:2].upper(), None, None, 0.6, "parsed_from_text", "city,country pattern")
    return GeoResult(None, None, None, None, None, 0.0, "missing", "no pattern matched")


def geocode_location(query: str) -> GeoResult:
    if not CONFIG.nominatim_email:
        return GeoResult(None, None, None, None, None, 0.0, "missing", "NOMINATIM_EMAIL not set")
    params = {"q": query, "format": "json", "limit": 1}
    headers = {"User-Agent": f"datacenter-layerA/1 ({CONFIG.nominatim_email})"}
    try:
        resp = requests.get("https://nominatim.openstreetmap.org/search", params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data:
            item = data[0]
            return GeoResult(
                city=item.get("display_name"),
                region_state=item.get("state"),
                country_code=item.get("country_code", "").upper(),
                latitude=float(item.get("lat")),
                longitude=float(item.get("lon")),
                geo_confidence=0.6,
                geo_source="geocoded",
                geo_notes="nominatim",
            )
    except Exception as exc:  # noqa: BLE001
        return GeoResult(None, None, None, None, None, 0.0, "missing", str(exc))
    return GeoResult(None, None, None, None, None, 0.0, "missing", "no results")


def enrich_geo(site_list: pd.DataFrame, observations: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in site_list.iterrows():
        datacenter_id = row["datacenter_id"]
        seed_text = " ".join(
            [
                str(row.get("datacenter_campus_name", "")),
                str(row.get("datacenter_building_name", "")),
                str(row.get("notes", "")),
            ]
        )
        geo = parse_geo_from_text(seed_text)
        if geo.city is None and geo.geo_confidence < 0.6:
            geo = geocode_location(seed_text)
        rows.append(
            {
                "datacenter_id": datacenter_id,
                "city": geo.city,
                "region_state": geo.region_state,
                "country_code": geo.country_code,
                "latitude": geo.latitude,
                "longitude": geo.longitude,
                "geo_confidence": geo.geo_confidence,
                "geo_source": geo.geo_source,
                "geo_notes": geo.geo_notes,
            }
        )
    return pd.DataFrame(rows)
