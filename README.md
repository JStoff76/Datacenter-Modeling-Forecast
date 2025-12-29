# Datacenter Layer A Pipeline

Implements a reproducible scraping + inference pipeline to populate Layer A datacenter project driver tables.

## Project structure
```
src/datacenter_layerA/
  config.py            # environment-driven configuration
  io.py                # input/output helpers
  normalize.py         # normalization + hashing
  fetcher.py           # polite fetcher with retries
  discover.py          # seed + internal link URL discovery
  extract.py           # regex-based spec extraction
  resolve.py           # resolution + inference + completeness
  geo.py               # geography parsing + optional geocode
  dq.py                # data quality and changelog builders
  run_pipeline.py      # entrypoint
```

## Setup
1. Create and activate a Python environment (Python 3.10+ recommended).
2. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the project root:
   ```env
   INPUT_SITE_LIST_PATH=data/input/site_list.xlsx
   OUTPUT_DIR=data/out
   USE_SELENIUM=false
   ALLOW_EXTERNAL_SOURCES=false
   MAX_PAGES_PER_DATACENTER=30
   KEEP_TOP_URLS=10
   DELAY_SECONDS=1.5
   NOMINATIM_EMAIL=you@company.com
   ```

## Running the pipeline
The pipeline expects an input workbook or CSV at `INPUT_SITE_LIST_PATH` with the schema described in the project goal. To execute end-to-end:
1. Ensure the `.env` file exists with the variables above.
2. Place your `site_list.xlsx` or `site_list.csv` under `data/input/` (or point `INPUT_SITE_LIST_PATH` to your custom location).
3. Run the ETL entrypoint:
   ```bash
   python -m src.datacenter_layerA.run_pipeline
   ```
4. Review outputs in `data/out/`:
   - `data/out/tables/` contains CSV exports for `site_list`, `url_candidates`, `spec_observations`, `project_drivers_layerA`, `source_registry`, `geo_enrichment`, `dq_report`, and `changelog`.
   - `data/out/datacenter_layerA.xlsx` consolidates the same tables into a single workbook for convenience.

The pipeline is polite by default (domain delays, retries) and scopes scraping to the domains present in the seed URLs unless `ALLOW_EXTERNAL_SOURCES=true`.

## Testing
Execute unit tests with:
```bash
pytest
```
