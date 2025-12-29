from __future__ import annotations

import datetime
from typing import List

import pandas as pd
import requests

from .config import CONFIG
from .fetcher import Fetcher
from .normalize import normalize_text


KEYWORDS = [
    "data center",
    "datacentre",
    "facility",
    "campus",
    "mw",
    "megawatt",
    "square feet",
    "sq ft",
    "racks",
    "capacity",
    "phase",
    "cooling",
    "liquid",
    "immersion",
]


def score_url(url: str, anchor_text: str) -> int:
    text = normalize_text(url + " " + anchor_text)
    score = 0
    for kw in KEYWORDS:
        if kw.replace(" ", "") in text.replace(" ", ""):
            score += 1
    return score


def build_seed_urls(row: pd.Series) -> List[str]:
    seeds = []
    for col in ["campus_or_property_url", "provider_url_primary"]:
        val = str(row.get(col, "")).strip()
        if val and val.lower().startswith("http"):
            seeds.append(val)
    return list(dict.fromkeys(seeds))


def discover_urls(site_list: pd.DataFrame, fetcher: Fetcher) -> pd.DataFrame:
    candidates = []
    run_date = datetime.date.today().isoformat()
    for _, row in site_list.iterrows():
        datacenter_id = row["datacenter_id"]
        seeds = build_seed_urls(row)
        seen = set()
        for seed in seeds:
            seed_domain = requests.utils.urlparse(seed).netloc
            candidates.append(
                {
                    "datacenter_id": datacenter_id,
                    "url": seed,
                    "source_type": "seed",
                    "query_text": "",
                    "rank": 1,
                    "discovered_date": run_date,
                    "keep_flag": True,
                }
            )
            seen.add(seed)
            result = fetcher.fetch(seed)
            if result.content:
                html = result.content.decode("utf-8", errors="ignore")
                links = fetcher.extract_links(html, seed)
                for link, anchor in links.items():
                    parsed = requests.utils.urlparse(link)
                    netloc = parsed.netloc or seed_domain
                    if not CONFIG.allow_external_sources and netloc != seed_domain:
                        continue
                    if link in seen:
                        continue
                    score = score_url(link, anchor)
                    candidates.append(
                        {
                            "datacenter_id": datacenter_id,
                            "url": link,
                            "source_type": "internal_link",
                            "query_text": anchor,
                            "rank": score,
                            "discovered_date": run_date,
                            "keep_flag": False,
                        }
                    )
                    seen.add(link)
        ranked = [c for c in candidates if c["datacenter_id"] == datacenter_id and c["source_type"] != "seed"]
        ranked.sort(key=lambda x: x["rank"], reverse=True)
        for i, c in enumerate(ranked[: CONFIG.keep_top_urls], start=1):
            c["rank"] = i + 1
            c["keep_flag"] = True
    return pd.DataFrame(candidates)
