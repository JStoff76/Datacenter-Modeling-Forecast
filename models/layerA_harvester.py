import re
import hashlib
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime

WB_PATH = "datacenter_layerA.xlsx"
USER_AGENT = "Mozilla/5.0 (SpecHarvester/1.0)"

# ---------- Helpers ----------
def md5_id(*parts: str) -> str:
    s = "|".join([(p or "").strip().lower() for p in parts])
    return hashlib.md5(s.encode("utf-8")).hexdigest()

def fetch_text(url: str, timeout: int = 25) -> str:
    r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    return re.sub(r"\s+", " ", text).strip()

def snippet(text: str, start: int, end: int, pad: int = 120) -> str:
    return text[max(0, start-pad):min(len(text), end+pad)]

def has_dc_context(s: str) -> bool:
    return re.search(r"(data\s*center|datacenter|critical\s*power|it\s*load|white\s*space|colo|colocation)",
                     s, re.I) is not None

# ---------- Extractors ----------
PATTERNS = [
    ("power_mw", re.compile(r"(?P<num>\d+(?:\.\d+)?)\s*(?P<unit>MW|megawatt(?:s)?)", re.I), "MW"),
    ("square_ft", re.compile(r"(?P<num>\d{1,3}(?:,\d{3})+|\d+)\s*(?P<unit>sq\.?\s*ft|square\s+feet|sf)\b", re.I), "SQFT"),
    ("rack_count", re.compile(r"(?P<num>\d{2,6})\s*(?P<unit>racks|cabinets)\b", re.I), "RACKS"),
    ("kw_per_rack", re.compile(r"(?P<num>\d+(?:\.\d+)?)\s*(?P<unit>kW\s*/\s*rack|kW\s+per\s+rack)", re.I), "KW_PER_RACK"),
]

def extract_observations(datacenter_id: str, url: str, text: str) -> list[dict]:
    out = []
    accessed = datetime.utcnow().strftime("%Y-%m-%d")
    for spec_name, pat, unit_std in PATTERNS:
        for m in pat.finditer(text):
            raw = m.group("num").replace(",", "")
            try:
                val = float(raw)
            except:
                continue

            snip = snippet(text, m.start(), m.end())
            conf = "MED" if has_dc_context(snip) else "LOW"

            # sanity bounds
            if spec_name == "power_mw" and not (0.5 <= val <= 50000):  # MW
                continue
            if spec_name == "square_ft" and not (1000 <= val <= 1_000_000_000):
                continue
            if spec_name == "rack_count" and not (10 <= val <= 1_000_000):
                continue
            if spec_name == "kw_per_rack" and not (1 <= val <= 200):
                continue

            out.append({
                "datacenter_id": datacenter_id,
                "spec_name": spec_name,
                "value_num": val,
                "unit": unit_std,
                "value_text": m.group(0),
                "source_url": url,
                "snippet": snip,
                "date_accessed": accessed,
                "confidence": conf,
                "method": "SCRAPED_REGEX",
            })
    return out

# ---------- Resolve ----------
def resolve_specs(obs_df: pd.DataFrame) -> pd.DataFrame:
    # For each datacenter_id/spec_name, compute point/low/high based on observed values
    if obs_df.empty:
        return pd.DataFrame()

    g = obs_df.groupby(["datacenter_id", "spec_name"])["value_num"]
    resolved = g.agg(
        value_p50="median",
        value_p25=lambda s: s.quantile(0.25),
        value_p75=lambda s: s.quantile(0.75),
        n="count"
    ).reset_index()

    return resolved

def build_project_drivers(resolved: pd.DataFrame) -> pd.DataFrame:
    # Pivot into wide form
    wide = resolved.pivot(index="datacenter_id", columns="spec_name", values="value_p50")
    wide_low = resolved.pivot(index="datacenter_id", columns="spec_name", values="value_p25")
    wide_high = resolved.pivot(index="datacenter_id", columns="spec_name", values="value_p75")

    out = pd.DataFrame(index=wide.index).reset_index()

    def col(df, name): return df[name] if name in df.columns else pd.Series([None]*len(out))

    out["power_mw_est"] = col(wide, "power_mw").values
    out["power_mw_low"] = col(wide_low, "power_mw").values
    out["power_mw_high"] = col(wide_high, "power_mw").values

    out["square_ft_est"] = col(wide, "square_ft").values
    out["square_ft_low"] = col(wide_low, "square_ft").values
    out["square_ft_high"] = col(wide_high, "square_ft").values

    out["kw_per_rack_est"] = col(wide, "kw_per_rack").values
    out["kw_per_rack_low"] = col(wide_low, "kw_per_rack").values
    out["kw_per_rack_high"] = col(wide_high, "kw_per_rack").values

    out["rack_count_est"] = col(wide, "rack_count").values
    out["rack_count_low"] = col(wide_low, "rack_count").values
    out["rack_count_high"] = col(wide_high, "rack_count").values

    # Back-calcs (fill missing rack_count or power_mw if possible)
    # racks = (MW*1000)/kW_per_rack
    mask_racks_missing = out["rack_count_est"].isna() & out["power_mw_est"].notna() & out["kw_per_rack_est"].notna()
    out.loc[mask_racks_missing, "rack_count_est"] = (out.loc[mask_racks_missing, "power_mw_est"] * 1000.0) / out.loc[mask_racks_missing, "kw_per_rack_est"]

    # MW = (racks*kW)/1000
    mask_mw_missing = out["power_mw_est"].isna() & out["rack_count_est"].notna() & out["kw_per_rack_est"].notna()
    out.loc[mask_mw_missing, "power_mw_est"] = (out.loc[mask_mw_missing, "rack_count_est"] * out.loc[mask_mw_missing, "kw_per_rack_est"]) / 1000.0

    out["confidence_overall"] = "MED"  # you can improve this using % of HIGH observations, conflicts, etc.
    out["resolution_notes"] = "Resolved from observations; back-calcs applied where possible."
    return out

# ---------- Main ----------
def main():
    # Read inputs
    site_df = pd.read_excel(WB_PATH, sheet_name="site_list")
    urls_df = pd.read_excel(WB_PATH, sheet_name="url_candidates")

    # Ensure datacenter_id exists
    if "datacenter_id" not in site_df.columns:
        site_df["datacenter_id"] = site_df.apply(
            lambda r: md5_id(r.get("DATACENTER_BUILDING_NAME"), r.get("DATACENTER_CAMPUS_NAME"), r.get("PROVIDER_NAME")),
            axis=1
        )

    # Build a lookup
    id_by_building = dict(zip(site_df["DATACENTER_BUILDING_NAME"], site_df["datacenter_id"]))

    # Scrape only URLs marked keep_flag == 'Y' (if column exists)
    if "keep_flag" in urls_df.columns:
        urls_df = urls_df[urls_df["keep_flag"].fillna("").str.upper().eq("Y")]

    observations = []
    for _, row in urls_df.iterrows():
        dcid = row["datacenter_id"]
        url = row["url"]
        try:
            text = fetch_text(url)
            observations.extend(extract_observations(dcid, url, text))
        except Exception as e:
            observations.append({
                "datacenter_id": dcid,
                "spec_name": "ERROR",
                "value_num": None,
                "unit": None,
                "value_text": None,
                "source_url": url,
                "snippet": str(e),
                "date_accessed": datetime.utcnow().strftime("%Y-%m-%d"),
                "confidence": "LOW",
                "method": "FETCH_ERROR",
            })

    obs_df = pd.DataFrame(observations)

    resolved = resolve_specs(obs_df[obs_df["spec_name"] != "ERROR"].copy())
    drivers = build_project_drivers(resolved)

    # Write back to Excel
    with pd.ExcelWriter(WB_PATH, engine="openpyxl", mode="a", if_sheet_exists="replace") as w:
        site_df.to_excel(w, sheet_name="site_list", index=False)
        obs_df.to_excel(w, sheet_name="spec_observations", index=False)
        drivers.to_excel(w, sheet_name="project_drivers_layerA", index=False)

    print("Done: updated spec_observations and project_drivers_layerA.")

if __name__ == "__main__":
    main()
