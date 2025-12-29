from __future__ import annotations

from typing import Dict

import pandas as pd


def dq_report(site_list: pd.DataFrame, drivers: pd.DataFrame, geo: pd.DataFrame) -> pd.DataFrame:
    records = []
    total = len(site_list)
    driver_fields = ["power_mw_est", "square_ft_est", "kw_per_rack_est", "rack_count_est", "cooling_type_est"]
    for field in driver_fields:
        missing = drivers[field].isnull().sum() if not drivers.empty else total
        records.append({"metric": f"missing_{field}", "value": missing / max(total, 1)})
    missing_geo = geo["city"].isnull().sum() if not geo.empty else total
    records.append({"metric": "missing_geo", "value": missing_geo / max(total, 1)})
    complete = site_list[site_list.get("status_computed", "To Research") == "Complete"]
    records.append({"metric": "%_complete", "value": len(complete) / max(total, 1)})
    return pd.DataFrame(records)


def row_counts(site_list: pd.DataFrame) -> pd.DataFrame:
    return (
        site_list.groupby(["provider_name", "status_computed"], dropna=False)
        .size()
        .reset_index(name="total_rows")
        .rename(columns={"status_computed": "site_type"})
    )


def changelog(previous: pd.DataFrame, current: pd.DataFrame) -> pd.DataFrame:
    if previous.empty:
        return pd.DataFrame(columns=["datacenter_id", "field", "old_value", "new_value", "changed_at"])
    rows = []
    for _, row in current.iterrows():
        datacenter_id = row["datacenter_id"]
        prev_row = previous[previous["datacenter_id"] == datacenter_id]
        if prev_row.empty:
            continue
        prev_row = prev_row.iloc[0]
        for col in current.columns:
            if col == "datacenter_id":
                continue
            if str(row.get(col)) != str(prev_row.get(col)):
                rows.append(
                    {
                        "datacenter_id": datacenter_id,
                        "field": col,
                        "old_value": prev_row.get(col),
                        "new_value": row.get(col),
                        "changed_at": pd.Timestamp.utcnow().isoformat(),
                    }
                )
    return pd.DataFrame(rows)
