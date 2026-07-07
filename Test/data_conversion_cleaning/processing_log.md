# Data Conversion and Cleaning Processing Log

Date: 2026-07-06

Scope: Sprint 2 data conversion and cleaning for the customer-prioritised Data Visualisation and Data Analysis workstream.

## Input Files

Source directory:

`../../dataset/dataset`

Processed files:

- `20260525device863060076192434_request_log.txt`
- `20260526device863060076192434_request_log(1).txt`
- `20260527device863060076192434_request_log.txt`
- `20260602device863060076192434_request_log.txt`
- `20260603device863060076192434_request_log.txt`

Total parsed rows: 251,898

Parse failures: 0

## Raw Data Types Detected

The parser detected these JLSP01 methods:

- Presence and bed state: `someoneExists`, `getIntoBed`
- Activity and movement: `motionStatus`, `movementSigns`
- Vital signs: `heartRateValue`, `breathValue`, `breathInform`
- Sleep state and summary: `sleepStatus`, `sleepComprehensiveStatus`, `awakeDuration`, `lightSleepDuration`, `deepSleepDuration`, `sleepScore`, `sleepQualityAnalysis`, `abnormalSleep`
- Device state: `online`

## Mapping Rules Implemented

- `getIntoBed = 1` mapped to `IN_BED`.
- `getIntoBed = 0` mapped to `OUT_OF_BED`.
- `someoneExists = 0` mapped to `NO_PERSON`.
- `someoneExists = 1` mapped to fallback `IN_BED` only when no explicit `getIntoBed` state exists.
- `motionStatus = 1` mapped to `STATIC`.
- `motionStatus = 2` mapped to `ACTIVE`.
- `motionStatus = 0` or `255` mapped to `UNKNOWN` and logged as lower-confidence data.
- `heartRateValue` mapped to `heart_rate_bpm`.
- `breathValue` mapped to `breathing_rate_per_min`.
- `sleepStatus = 0/1/2/3` mapped to `DEEP_SLEEP` / `LIGHT_SLEEP` / `AWAKE` / `NONE`.
- `sleepQualityAnalysis` mapped into daily sleep summary when it contains plausible non-zero values.

## Cleaning Rules Implemented

- Every log line is parsed as local timestamp plus quoted JSON payload.
- Invalid JSON or malformed lines are written to `data_quality_events.csv`.
- Heart rate values outside 30-200 bpm are excluded from vital samples and logged.
- Breathing-rate values outside 5-40 breaths/min are excluded from vital samples and logged.
- Empty `sleepQualityAnalysis` arrays such as all-zero values are ignored and logged.
- Device offline events are retained in `data_quality_events.csv`.
- High-frequency vital-sign and movement data are resampled to 60-second buckets.
  - Vital samples use average heart rate, average breathing rate, and average confidence per minute.
  - Activity samples use the dominant motion status and average movement-sign value per minute.

## Mid-Process Check and Rework

Initial script output produced approximately one vital sample per raw heart-rate or breathing-rate report. This created 95,119 vital rows, which was too high-frequency for dashboard use and would make CSV upload unnecessarily heavy.

Rework completed:

- Added 60-second resampling for `vital_samples.csv`.
- Added 60-second resampling for `activity_samples.csv`.
- Re-ran the conversion.

Final row counts after rework:

- `bed_events.csv`: 26 rows
- `vital_samples.csv`: 2,353 rows
- `daily_sleep_summary.csv`: 2 rows
- `activity_samples.csv`: 2,392 rows
- `sleep_stage_samples.csv`: 297 rows
- `data_quality_events.csv`: 27 rows

## Output Files

Generated under `output/`:

- `bed_events.csv`
  - Backend upload compatible with `/api/upload/bed-events`.
  - Required columns verified: `resident_id`, `timestamp`, `bed_status`, `activity_status`, `confidence`.
- `vital_samples.csv`
  - Backend upload compatible with `/api/upload/vitals`.
  - Required columns verified: `resident_id`, `timestamp`, `heart_rate_bpm`, `breathing_rate_per_min`, `confidence`.
  - Cleaned HR range: 62.0-102.4 bpm.
  - Cleaned BR range: 6.7-25.0 breaths/min.
- `daily_sleep_summary.csv`
  - Backend upload compatible with `/api/upload/sleep-summary`.
  - Required columns verified: `resident_id`, `date`, `total_sleep_minutes`, `sleep_efficiency`, `sleep_score`, `bed_exit_count`, `avg_heart_rate`, `avg_breathing_rate`.
  - Valid daily summaries detected for 2026-06-02 and 2026-06-03.
- `activity_samples.csv`
  - Future dashboard input for movement intensity and active/static timeline visualisation.
- `sleep_stage_samples.csv`
  - Future dashboard input for deep/light/awake/none sleep-stage timeline visualisation.
- `data_quality_events.csv`
  - Device offline, invalid motion status, out-of-range vitals, and empty sleep summaries.
- `conversion_summary.json`
  - Per-file parse counts, method counts, timestamp ranges, and output row counts.

## Protocol Re-Audit Update

Date: 2026-07-06

The converter was re-checked against `JLSP01-4G_Communication_Integration_Document_V1.3.pdf` and the raw request logs. Several mappings were corrected to make each CSV key semantically meaningful.

Corrections made:

- `someoneExists = 1` is no longer treated as `IN_BED`.
  - Protocol meaning: person present in the environment.
  - Output: `presence_events.csv` with `presence_status = PRESENT`.
- `someoneExists = 0` is retained as `presence_status = NO_PERSON` and also emitted as a backend-compatible `NO_PERSON` bed event.
- `motionStatus = 0` is now treated as `NONE`, because the protocol defines it as none/no motion.
- Undocumented values such as `motionStatus = 255` remain `UNKNOWN` and are logged to `data_quality_events.csv`.
- Duplicate bed events at the same resident/timestamp are de-duplicated, with priority `NO_PERSON > OUT_OF_BED > IN_BED`.
- `sleepQualityAnalysis` is now parsed according to the protocol's 12-value order:
  - sleep quality score
  - 2-byte total sleep duration
  - awake duration ratio
  - light sleep duration ratio
  - deep sleep duration ratio
  - total out-of-bed duration
  - number of times out of bed
  - number of turns
  - average respiration
  - average heartbeat
  - apnea event count
- `sleepComprehensiveStatus` is now exported to `sleep_comprehensive_status.csv`.
- `breathInform`, `abnormalSleep`, and `online` are now exported to `device_status_events.csv`.
- The JLSP01 protocol does not provide a true `longest_out_of_bed_minutes` field. For backend upload compatibility, `daily_sleep_summary.csv` uses protocol total out-of-bed duration as a conservative proxy. The protocol-faithful field is preserved as `total_out_of_bed_minutes` in `daily_sleep_analysis.csv`.
- Sparse `getIntoBed` event-derived totals are retained in `daily_sleep_analysis.csv` for audit only. Where they conflict strongly with `sleepQualityAnalysis`, a `bed_event_summary_mismatch` quality event is logged.

During this audit, the original `output/vital_samples.csv` file was locked by another Windows process, so the verified regenerated outputs were written to:

`output_verified/`

Verified output counts:

- `bed_events.csv`: 24 rows
- `vital_samples.csv`: 2,353 rows
- `daily_sleep_summary.csv`: 2 rows
- `daily_sleep_analysis.csv`: 2 rows
- `activity_samples.csv`: 2,392 rows
- `presence_events.csv`: 16 rows
- `sleep_stage_samples.csv`: 297 rows
- `sleep_comprehensive_status.csv`: 294 rows
- `device_status_events.csv`: 21 rows
- `data_quality_events.csv`: 29 rows

Final semantic checks:

- `bed_events.csv` uses only `IN_BED`, `OUT_OF_BED`, and `NO_PERSON`.
- Backend-compatible bed event `activity_status` uses only `STATIC` and `ACTIVE`.
- `activity_samples.csv` preserves protocol-level `NONE`, `STATIC`, `ACTIVE`, and `UNKNOWN`.
- `presence_events.csv` uses only `PRESENT` and `NO_PERSON`.
- Sleep-stage outputs use `DEEP_SLEEP`, `LIGHT_SLEEP`, `AWAKE`, and `NONE`.
- Cleaned heart-rate range is 62.0-102.4 bpm.
- Cleaned breathing-rate range is 6.7-25.0 breaths/min.
- Backend-required columns are present in `bed_events.csv`, `vital_samples.csv`, and `daily_sleep_summary.csv`.

## Validation Results

Validation checks completed:

- Backend-required CSV columns are present.
- Bed status values are limited to `IN_BED`, `OUT_OF_BED`, and `NO_PERSON`.
- Activity status values are limited to `STATIC`, `ACTIVE`, and `UNKNOWN`.
- Cleaned heart-rate and breathing-rate values are within accepted backend ranges.
- Sleep stages are limited to `DEEP_SLEEP`, `LIGHT_SLEEP`, `AWAKE`, and `NONE`.
- Data-quality issue types are explicitly logged.

## Known Limitations

- All current raw files belong to one device IMEI, so the converter maps them to `R001` by default.
- Only two valid non-zero `sleepQualityAnalysis` records were found, so daily summaries are currently available for two dates only.
- The conversion keeps `activity_samples.csv` and `sleep_stage_samples.csv` outside the current backend upload API because the existing schema has no dedicated tables for those records yet.
- `someoneExists = 1` is only a fallback for `IN_BED`; `getIntoBed` remains the preferred bed-state source.
