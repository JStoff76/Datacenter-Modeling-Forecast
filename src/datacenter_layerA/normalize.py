import hashlib
import re
from typing import Optional


WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(value: Optional[str]) -> str:
    """Lowercase and collapse whitespace/punctuation for consistent comparisons."""
    if value is None:
        return ""
    cleaned = value.strip().lower()
    cleaned = re.sub(r"[\t\n\r]+", " ", cleaned)
    cleaned = re.sub(r"[^\w\s]+", " ", cleaned)
    return WHITESPACE_RE.sub(" ", cleaned).strip()


def md5_hash_bytes(content: bytes) -> str:
    md5 = hashlib.md5()
    md5.update(content)
    return md5.hexdigest()


def md5_hash_string(content: str) -> str:
    return md5_hash_bytes(content.encode("utf-8"))
