from __future__ import annotations

from pathlib import Path
from typing import Dict

import pandas as pd

from .config import CONFIG
from .discover import discover_urls
from .dq import changelog, dq_report
from .extract import build_spec_df, parse_content
from .fetcher import Fetcher
from .geo import enrich_geo
from .io import ensure_output_dirs, load_previous_drivers, read_site_list, write_excel_workbook, write_tables_to_csv
from .resolve import compute_status, resolve_project_drivers


REQUIRED_TABLES = [
    "site_list",
    "url_candidates",
    "spec_observations",
    "project_drivers_layerA",
    "source_registry",
    "geo_enrichment",
    "dq_report",
    "changelog",
]


def run() -> Dict[str, pd.DataFrame]:
    cfg = CONFIG
    output_dirs = ensure_output_dirs(cfg.output_dir)
    site_list = read_site_list(cfg.input_site_list_path)
    fetcher = Fetcher(cfg.delay_seconds)
    url_candidates = discover_urls(site_list, fetcher)
    spec_obs_records = []
    source_registry_records = []
    for _, row in url_candidates[url_candidates["keep_flag"]].iterrows():
        result = fetcher.fetch(row["url"])
        source_registry_records.append(
            {
                "source_url": row["url"],
                "datacenter_id": row["datacenter_id"],
                "retrieved_at": result.retrieved_at,
                "http_status": result.status_code,
                "content_type": result.content_type,
                "fetch_method": result.fetch_method,
                "parse_method": None,
                "raw_content_hash": result.raw_content_hash,
                "error": result.error,
            }
        )
        observations, metadata = parse_content(result, row["datacenter_id"])
        if observations:
            spec_obs_records.extend([obs.__dict__ for obs in observations])
        if metadata.get("parse_method"):
            source_registry_records[-1]["parse_method"] = metadata["parse_method"]
    spec_observations = pd.DataFrame(spec_obs_records)
    if spec_observations.empty:
        spec_observations = build_spec_df([])
    drivers, inferred_obs = resolve_project_drivers(spec_observations)
    if not inferred_obs.empty:
        spec_observations = pd.concat([spec_observations, inferred_obs], ignore_index=True)
    geo = enrich_geo(site_list, spec_observations)
    site_with_status = compute_status(site_list, drivers, geo)
    dq = dq_report(site_with_status, drivers, geo)
    previous_drivers = load_previous_drivers(output_dirs["previous"])
    change_df = changelog(previous_drivers, drivers)

    tables = {
        "site_list": site_with_status,
        "url_candidates": url_candidates,
        "spec_observations": spec_observations,
        "project_drivers_layerA": drivers,
        "source_registry": pd.DataFrame(source_registry_records),
        "geo_enrichment": geo,
        "dq_report": dq,
        "changelog": change_df,
    }
    write_tables_to_csv(tables, output_dirs["tables"])
    workbook_path = Path(cfg.output_dir) / "datacenter_layerA.xlsx"
    write_excel_workbook(tables, workbook_path)
    drivers.to_csv(output_dirs["tables"] / "project_drivers_layerA.csv", index=False)
    return tables


if __name__ == "__main__":
    run()
