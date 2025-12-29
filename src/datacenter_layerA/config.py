import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


def _get_bool(env_value: Optional[str], default: bool) -> bool:
    if env_value is None:
        return default
    return env_value.strip().lower() in {"1", "true", "yes", "y"}


@dataclass
class PipelineConfig:
    input_site_list_path: str = field(default_factory=lambda: os.getenv("INPUT_SITE_LIST_PATH", "data/input/site_list.xlsx"))
    output_dir: str = field(default_factory=lambda: os.getenv("OUTPUT_DIR", "data/out"))
    use_selenium: bool = field(default_factory=lambda: _get_bool(os.getenv("USE_SELENIUM"), False))
    allow_external_sources: bool = field(default_factory=lambda: _get_bool(os.getenv("ALLOW_EXTERNAL_SOURCES"), False))
    max_pages_per_datacenter: int = field(default_factory=lambda: int(os.getenv("MAX_PAGES_PER_DATACENTER", "30")))
    keep_top_urls: int = field(default_factory=lambda: int(os.getenv("KEEP_TOP_URLS", "10")))
    delay_seconds: float = field(default_factory=lambda: float(os.getenv("DELAY_SECONDS", "1.5")))
    nominatim_email: Optional[str] = field(default_factory=lambda: os.getenv("NOMINATIM_EMAIL"))

    @property
    def run_date(self) -> str:
        return datetime.utcnow().date().isoformat()


CONFIG = PipelineConfig()
