from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pandas as pd

INFERENCE_NOTES = "inferred from heuristics"

DEFAULT_KW_PER_RACK = 12
DENSITY_TIERS = {
    "low": (5, 12, 37.7, 53.8),
    "high": (12, 20, 53.8, 75.3),
    "very_high": (20, 100, 64.6, 96.9),
}


@dataclass
class ResolvedDrivers:
    power_mw_est: Optional[float]
    power_mw_low: Optional[float]
    power_mw_high: Optional[float]
    square_ft_est: Optional[float]
    square_ft_low: Optional[float]
    square_ft_high: Optional[float]
    kw_per_rack_est: Optional[float]
    kw_per_rack_low: Optional[float]
    kw_per_rack_high: Optional[float]
    rack_count_est: Optional[float]
    rack_count_low: Optional[float]
    rack_count_high: Optional[float]
    cooling_type_est: Optional[str]
    phase_go_live_date_est: Optional[str]
    confidence_overall: float
    resolution_notes: str
    primary_source_url: Optional[str]


SPEC_TO_FIELD = {
    "power_mw": "power_mw_est",
    "square_ft": "square_ft_est",
    "kw_per_rack": "kw_per_rack_est",
    "rack_count": "rack_count_est",
    "cooling_type": "cooling_type_est",
    "go_live_date": "phase_go_live_date_est",
}


LOW_CONFIDENCE_INFERENCE = 0.3


def _best_observation(observations: pd.DataFrame, spec_name: str) -> Optional[pd.Series]:
    subset = observations[observations["spec_name"] == spec_name]
    if subset.empty:
        return None
    subset = subset.sort_values(by=["confidence", "date_accessed"], ascending=[False, False])
    return subset.iloc[0]


def _min_max(observations: pd.DataFrame, spec_name: str) -> Tuple[Optional[float], Optional[float]]:
    subset = observations[(observations["spec_name"] == spec_name) & observations["value_num"].notnull()]
    if subset.empty:
        return None, None
    return subset["value_num"].min(), subset["value_num"].max()


def infer_missing(datacenter_id: str, drivers: Dict[str, Optional[float]], notes: List[str], inferred_obs: List[Dict]) -> None:
    cooling = drivers.get("cooling_type_est", "") or ""
    kw_per_rack = drivers.get("kw_per_rack_est") or (30 if "liquid" in cooling.lower() else DEFAULT_KW_PER_RACK)
    drivers["kw_per_rack_est"] = kw_per_rack
    if drivers.get("square_ft_est") and not drivers.get("rack_count_est"):
        tier = "high" if kw_per_rack >= 12 else "low"
        if kw_per_rack > 20:
            tier = "very_high"
        sqft_low, sqft_high = DENSITY_TIERS[tier][2], DENSITY_TIERS[tier][3]
        drivers["rack_count_low"] = drivers["square_ft_est"] / sqft_high
        drivers["rack_count_high"] = drivers["square_ft_est"] / sqft_low
        drivers["rack_count_est"] = (drivers["rack_count_low"] + drivers["rack_count_high"]) / 2
        notes.append("rack_count inferred from square_ft and density tier")
    if drivers.get("rack_count_est") and not drivers.get("power_mw_est"):
        drivers["power_mw_est"] = drivers["rack_count_est"] * kw_per_rack / 1000
        notes.append("power inferred from racks and kw_per_rack")
    if drivers.get("power_mw_est") and not drivers.get("rack_count_est"):
        drivers["rack_count_est"] = drivers["power_mw_est"] * 1000 / kw_per_rack
        notes.append("rack_count inferred from power and kw_per_rack")
    for field in ["power_mw_est", "square_ft_est", "rack_count_est", "kw_per_rack_est"]:
        if drivers.get(field) is not None:
            inferred_obs.append(
                {
                    "datacenter_id": datacenter_id,
                    "spec_name": field.replace("_est", ""),
                    "value_num": drivers[field],
                    "unit": "MW" if "power" in field else ("sqft" if "square_ft" in field else ("kW_per_rack" if "kw_per_rack" in field else "racks")),
                    "value_text": str(drivers[field]),
                    "source_url": "inference",
                    "snippet": "heuristic inference",
                    "date_accessed": pd.Timestamp.utcnow().isoformat(),
                    "confidence": LOW_CONFIDENCE_INFERENCE,
                    "method": "inference",
                }
            )


def resolve_project_drivers(observations: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    inferred_obs: List[Dict] = []
    for datacenter_id, group in observations.groupby("datacenter_id"):
        drivers: Dict[str, Optional[float]] = {field: None for field in SPEC_TO_FIELD.values()}
        low_high: Dict[str, Tuple[Optional[float], Optional[float]]] = {}
        notes: List[str] = []
        anchor_url: Optional[str] = None
        for spec, field in SPEC_TO_FIELD.items():
            best = _best_observation(group, spec)
            low_high[spec] = _min_max(group, spec)
            if best is not None:
                drivers[field] = best.get("value_num") or best.get("value_text")
                anchor_url = anchor_url or best.get("source_url")
                notes.append(f"{spec} observed")
        infer_missing(datacenter_id, drivers, notes, inferred_obs)
        confidence_components = []
        inferred_fields = 0
        resolved_fields = 0
        for spec, field in SPEC_TO_FIELD.items():
            val = drivers.get(field)
            if val is not None:
                resolved_fields += 1
                best = _best_observation(group, spec)
                if best is not None:
                    confidence_components.append(best.get("confidence", 0.5))
                else:
                    inferred_fields += 1
                    confidence_components.append(LOW_CONFIDENCE_INFERENCE)
        confidence_overall = 0.0
        if confidence_components:
            confidence_overall = sum(confidence_components) / len(confidence_components)
        if resolved_fields and inferred_fields / max(resolved_fields, 1) > 0.5:
            confidence_overall *= 0.8
        confidence_overall = min(confidence_overall, 0.95)
        rows.append(
            {
                "datacenter_id": datacenter_id,
                "power_mw_est": drivers.get("power_mw_est"),
                "power_mw_low": low_high.get("power_mw", (None, None))[0],
                "power_mw_high": low_high.get("power_mw", (None, None))[1],
                "square_ft_est": drivers.get("square_ft_est"),
                "square_ft_low": low_high.get("square_ft", (None, None))[0],
                "square_ft_high": low_high.get("square_ft", (None, None))[1],
                "kw_per_rack_est": drivers.get("kw_per_rack_est"),
                "kw_per_rack_low": low_high.get("kw_per_rack", (None, None))[0],
                "kw_per_rack_high": low_high.get("kw_per_rack", (None, None))[1],
                "rack_count_est": drivers.get("rack_count_est"),
                "rack_count_low": low_high.get("rack_count", (None, None))[0],
                "rack_count_high": low_high.get("rack_count", (None, None))[1],
                "cooling_type_est": drivers.get("cooling_type_est"),
                "phase_go_live_date_est": drivers.get("phase_go_live_date_est"),
                "confidence_overall": confidence_overall,
                "resolution_notes": "; ".join(notes) if notes else "inferred",
                "primary_source_url": anchor_url,
            }
        )
    return pd.DataFrame(rows), pd.DataFrame(inferred_obs)


def compute_status(site_list: pd.DataFrame, drivers: pd.DataFrame, geo: pd.DataFrame) -> pd.DataFrame:
    driver_fields = [
        "power_mw_est",
        "square_ft_est",
        "kw_per_rack_est",
        "rack_count_est",
        "cooling_type_est",
    ]
    enriched = site_list.copy()
    enriched["status_computed"] = "To Research"
    geo_lookup = geo.set_index("datacenter_id") if not geo.empty else pd.DataFrame()
    driver_lookup = drivers.set_index("datacenter_id") if not drivers.empty else pd.DataFrame()
    for idx, row in enriched.iterrows():
        datacenter_id = row["datacenter_id"]
        has_name = bool(row.get("datacenter_campus_name")) or bool(row.get("datacenter_building_name"))
        urls = [row.get("campus_or_property_url"), row.get("provider_url_primary")]
        has_url = any([u for u in urls if isinstance(u, str) and u.startswith("http")])
        geo_row = geo_lookup.loc[datacenter_id] if datacenter_id in getattr(geo_lookup, "index", []) else None
        has_geo = False
        if geo_row is not None:
            has_geo = bool(geo_row.get("city")) or bool(geo_row.get("latitude"))
        driver_row = driver_lookup.loc[datacenter_id] if datacenter_id in getattr(driver_lookup, "index", []) else None
        driver_count = 0
        if driver_row is not None:
            driver_count = sum(bool(driver_row.get(f)) for f in driver_fields)
        if has_name and has_url and has_geo and driver_count >= 3:
            enriched.data[idx]["status_computed"] = "Complete"
        elif driver_count >= 1:
            enriched.data[idx]["status_computed"] = "In Progress"
    return enriched
