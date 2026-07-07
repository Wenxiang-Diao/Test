# Sprint 2 Data Visualisation Implementation Log

Date: 2026-07-07

Scope: Continue the customer-prioritised Data Visualisation and Data Analysis workstream until the following dashboard functions are completed:

- Current bed status card
- Daily sleep quality summary
- Bed-exit event timeline
- Heart-rate and breathing-rate trend charts

## Backend Changes

Files updated:

- `sprint1-en-final/backend/app/schemas/schemas.py`
- `sprint1-en-final/backend/app/services/resident_services.py`
- `sprint1-en-final/backend/app/services/baseline_service.py`

Implemented:

- `DashboardResponse` now returns a fuller daily sleep summary:
  - `awake_minutes`
  - `light_sleep_minutes`
  - `deep_sleep_minutes`
  - `longest_out_of_bed_minutes`
- Dashboard data now uses the resident's latest device event as the 12-hour chart/timeline anchor.
  - This is required because the provided JLSP01 dataset is historical May/June 2026 data. Using the machine's current time would return empty timeline/chart data.
- Baseline calculation now accepts an optional `as_of_date`.
  - Dashboard baseline comparisons can now be computed relative to the latest sleep-summary date rather than today's date.

## Frontend Changes

Files updated:

- `sprint1-en-final/frontend/src/api/client.ts`
- `sprint1-en-final/frontend/src/components/SleepSummaryCards.tsx`
- `sprint1-en-final/frontend/src/components/BedExitTimeline.tsx`
- `sprint1-en-final/frontend/src/components/VitalSignCharts.tsx`

Implemented:

- Current bed status card already existed and is now supported by the historical-data dashboard anchor.
- Daily sleep quality summary now displays:
  - sleep score
  - total sleep duration
  - awake time
  - light sleep
  - deep sleep
  - sleep efficiency
  - bed exits
  - longest out-of-bed proxy
  - average heart rate
  - average breathing rate
- Bed-exit timeline was rewritten with a dynamic time axis based on actual bed-exit interval timestamps.
  - This avoids the previous fixed 22:00-06:00 axis hiding events that occur outside that range in the sample logs.
- Vital-sign chart now shows an explicit no-data message instead of an empty chart when no vitals exist in the selected dashboard window.

## Data Import Path

File added:

- `sprint1-en-final/backend/scripts/import_cleaned_jlsp01_csv.py`

Implemented:

- Imports cleaned JLSP01 CSVs from `Test/data_conversion_cleaning/output_verified` by default:
  - `bed_events.csv`
  - `vital_samples.csv`
  - `daily_sleep_summary.csv`
- Skips duplicate resident/timestamp/date records.
- Creates resident/device records if they do not already exist.
- Adds resident profile/location columns to older PostgreSQL databases if needed.

Run from `Test/sprint1-en-final` after the backend environment is installed:

```powershell
python backend\scripts\import_cleaned_jlsp01_csv.py
```

## Verification

Completed:

- Python syntax check passed:
  - `python -m compileall backend\app backend\scripts`

Blocked by local environment:

- Import script execution in the bundled Python failed because `sqlalchemy` is not installed in that runtime.
- Full frontend TypeScript/Vite build is still blocked because local `node_modules` are not installed and the bundled runtime does not include TypeScript/Vite CLI packages.

Required local verification once dependencies are installed:

```powershell
cd Test\sprint1-en-final
conda activate comp9900
pip install -r backend\requirements.txt
python backend\scripts\import_cleaned_jlsp01_csv.py

cd frontend
npm install
npm run build
```

