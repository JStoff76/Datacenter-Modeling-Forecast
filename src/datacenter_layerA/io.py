from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List

import pandas as pd


REQUIRED_COLUMNS = [
    "datacenter_id",
    "provider_name",
    "provider_url_primary",
    "datacenter_building_name",
    "datacenter_campus_name",
    "campus_or_property_url",
    "status",
    "notes",
]


def read_site_list(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Site list not found at {path}")
    ext = Path(path).suffix.lower()
    if ext == ".csv":
        df = pd.read_csv(path)
    elif ext in {".xlsx", ".xls"}:
        df = pd.read_excel(path)
    else:
        raise ValueError(f"Unsupported site list extension: {ext}")
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Site list missing required columns: {missing}")
    return df.copy()


def ensure_output_dirs(output_dir: str) -> Dict[str, Path]:
    base = Path(output_dir)
    tables_dir = base / "tables"
    base.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)
    previous_dir = base / "previous"
    previous_dir.mkdir(parents=True, exist_ok=True)
    return {"base": base, "tables": tables_dir, "previous": previous_dir}


def write_tables_to_csv(tables: Dict[str, pd.DataFrame], tables_dir: Path) -> None:
    for name, df in tables.items():
        outfile = tables_dir / f"{name}.csv"
        df.to_csv(outfile, index=False)


def write_excel_workbook(tables: Dict[str, pd.DataFrame], output_path: Path) -> None:
    with pd.ExcelWriter(output_path) as writer:
        for name, df in tables.items():
            df.to_excel(writer, index=False, sheet_name=name[:31])


def load_previous_drivers(previous_dir: Path) -> pd.DataFrame:
    previous_path = previous_dir / "project_drivers_layerA.csv"
    if previous_path.exists():
        return pd.read_csv(previous_path)
    return pd.DataFrame()
