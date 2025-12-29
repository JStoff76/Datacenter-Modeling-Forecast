# spec_harvester.py
import re
import time
import json
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Optional

USER_AGENT = "Mozilla/5.0 (compatible; SpecHarvester/1.0; +internal)"

@dataclass
class SpecObservation:
    project_id: str
    spec_name: str                 # "power_mw", "square_ft", "rack_count"
    value_num: float
    unit: str                      # "MW", "SQFT", "RACKS"
    source_url: str
    extracted_snippet: str
    date_accessed: str
    confidence: str                # "HIGH" | "MED" | "LOW"
    method: str                    # "SCRAPED_REGEX"

def fetch_text(url: str, timeout: int = 20) -> str:
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    resp.raise_for_status()
    html = resp.text

    soup = BeautifulSoup(html, "html.parser")

    # Remove scripts/styles
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    # Get visible text
    text = soup.get_text(separator=" ")
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text

def window_snippet(text: str, start: int, end: int, pad: int = 120) -> str:
    s = max(0, start - pad)
    e = min(len(text), end + pad)
    return text[s:e]

def extract_specs(project_id: str, url: str, text: str) -> List[SpecObservation]:
    observations: List[SpecObservation] = []
    accessed = datetime.utcnow().strftime("%Y-%m-%d")

    # Patterns
    mw_pat = re.compile(r"(?P<num>\d+(?:\.\d+)?)\s*(?P<unit>MW|megawatt(?:s)?)", re.IGNORECASE)
    sqft_pat = re.compile(r"(?P<num>\d{1,3}(?:,\d{3})+|\d+)\s*(?P<unit>sq\.?\s*ft|square\s+feet|sf)\b", re.IGNORECASE)
    racks_pat = re.compile(r"(?P<num>\d{2,6})\s*(?P<unit>racks|cabinets)\b", re.IGNORECASE)

    # Context keywords to reduce false positives
    context_keywords = re.compile(r"(data\s*center|datacenter|it\s*load|critical\s*power|white\s*space|colocation|colo)", re.IGNORECASE)

    def add_obs(spec_name: str, val: float, unit: str, snippet: str, conf: str):
        observations.append(
            SpecObservation(
                project_id=project_id,
                spec_name=spec_name,
                value_num=val,
                unit=unit,
                source_url=url,
                extracted_snippet=snippet,
                date_accessed=accessed,
                confidence=conf,
                method="SCRAPED_REGEX",
            )
        )

    # MW extraction
    for m in mw_pat.finditer(text):
        num = float(m.group("num"))
        snip = window_snippet(text, m.start(), m.end())
        conf = "MED" if context_keywords.search(snip) else "LOW"
        # Basic sanity filter (avoid tiny or absurd values)
        if 0.5 <= num <= 50000:
            add_obs("power_mw", num, "MW", snip, conf)

    # SQFT extraction
    for m in sqft_pat.finditer(text):
        raw = m.group("num").replace(",", "")
        num = float(raw)
        snip = window_snippet(text, m.start(), m.end())
        conf = "MED" if context_keywords.search(snip) else "LOW"
        if 1000 <= num <= 1_000_000_000:
            add_obs("square_ft", num, "SQFT", snip, conf)

    # Racks extraction
    for m in racks_pat.finditer(text):
        num = float(m.group("num"))
        snip = window_snippet(text, m.start(), m.end())
        conf = "MED" if context_keywords.search(snip) else "LOW"
        if 10 <= num <= 1_000_000:
            add_obs("rack_count", num, "RACKS", snip, conf)

    return observations

def run(project_id: str, urls: List[str], sleep_s: float = 1.0) -> List[Dict]:
    out: List[Dict] = []
    for url in urls:
        try:
            text = fetch_text(url)
            obs = extract_specs(project_id, url, text)
            out.extend([asdict(o) for o in obs])
        except Exception as e:
            out.append({
                "project_id": project_id,
                "spec_name": "ERROR",
                "value_num": None,
                "unit": None,
                "source_url": url,
                "extracted_snippet": str(e),
                "date_accessed": datetime.utcnow().strftime("%Y-%m-%d"),
                "confidence": "LOW",
                "method": "FETCH_ERROR"
            })
        time.sleep(sleep_s)
    return out

if __name__ == "__main__":
    project_id = "EXAMPLE_DC_001"
    urls = [
        # populate with known pages for the project
    ]
    results = run(project_id, urls)
    print(json.dumps(results, indent=2))
