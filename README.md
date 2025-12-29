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
Run against the configured site list (processes seeds and discovered URLs, extracts specs, performs inference, and writes outputs as CSVs plus an Excel workbook):
```bash
python -m src.datacenter_layerA.run_pipeline
```
Outputs are written to `data/out/` including per-table CSVs in `data/out/tables/` and a consolidated `data/out/datacenter_layerA.xlsx` workbook.

## Testing
Execute unit tests with:
```bash
pytest
```
