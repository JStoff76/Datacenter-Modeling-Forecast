from __future__ import annotations

import hashlib
import random
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional, Tuple

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from .config import CONFIG
from .normalize import md5_hash_bytes


DEFAULT_HEADERS = {
    "User-Agent": "DatacenterLayerA-Bot/1.0 (+https://example.com)"
}


@dataclass
class FetchResult:
    url: str
    status_code: Optional[int]
    content: Optional[bytes]
    content_type: Optional[str]
    error: Optional[str]
    fetch_method: str
    parse_method: Optional[str]
    retrieved_at: str
    raw_content_hash: Optional[str]


class Fetcher:
    def __init__(self, delay_seconds: float = CONFIG.delay_seconds) -> None:
        self.delay_seconds = delay_seconds
        self.last_fetch_per_domain: Dict[str, float] = {}
        self.session = self._build_session()

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update(DEFAULT_HEADERS)
        return session

    def _polite_delay(self, domain: str) -> None:
        last = self.last_fetch_per_domain.get(domain, 0)
        now = time.time()
        elapsed = now - last
        delay = self.delay_seconds + random.uniform(0, 0.5)
        if elapsed < delay:
            time.sleep(delay - elapsed)
        self.last_fetch_per_domain[domain] = time.time()

    def fetch(self, url: str) -> FetchResult:
        parsed = requests.utils.urlparse(url)
        self._polite_delay(parsed.netloc)
        try:
            resp = self.session.get(url, timeout=10)
            content_type = resp.headers.get("content-type", "")
            content = resp.content
            raw_hash = md5_hash_bytes(content)
            return FetchResult(
                url=url,
                status_code=resp.status_code,
                content=content,
                content_type=content_type,
                error=None,
                fetch_method="requests",
                parse_method=None,
                retrieved_at=datetime.utcnow().isoformat(),
                raw_content_hash=raw_hash,
            )
        except Exception as exc:  # noqa: BLE001
            return FetchResult(
                url=url,
                status_code=None,
                content=None,
                content_type=None,
                error=str(exc),
                fetch_method="requests",
                parse_method=None,
                retrieved_at=datetime.utcnow().isoformat(),
                raw_content_hash=None,
            )

    @staticmethod
    def extract_links(html: str, base_domain: str) -> Dict[str, str]:
        soup = BeautifulSoup(html, "html.parser")
        links = {}
        for tag in soup.find_all("a", href=True):
            href = tag.get("href")
            parsed = requests.utils.urlparse(href)
            if not parsed.scheme:
                href = requests.compat.urljoin(base_domain, href)
            links[href] = tag.get_text(strip=True)
        return links


def guess_parse_method(content_type: Optional[str]) -> str:
    if not content_type:
        return "bs4"
    if "pdf" in content_type:
        return "pdfminer"
    if "json" in content_type:
        return "json_ld"
    return "bs4"
