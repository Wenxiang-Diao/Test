# JLSP01 Data Conversion and Cleaning

This folder contains the Sprint 2 data conversion and cleaning pipeline for the customer-provided sleep monitoring device logs.

## Purpose

Convert raw JLSP01 request logs into structured CSV files that match or extend the existing backend ingestion model.

## Input

Default input folder:

`../../dataset/dataset`

Expected files:

`*request_log*.txt`

Each line is expected to contain a local timestamp followed by a quoted JSON payload.

## Outputs

Generated under `output/`:

- `bed_events.csv`: compatible with `/api/upload/bed-events`
- `vital_samples.csv`: compatible with `/api/upload/vitals`
- `daily_sleep_summary.csv`: compatible with `/api/upload/sleep-summary`
- `daily_sleep_analysis.csv`: protocol-faithful sleep quality analysis fields
- `activity_samples.csv`: movement and motion-status samples for future analysis visualisation
- `presence_events.csv`: human presence events from `someoneExists`
- `sleep_stage_samples.csv`: deep/light/awake/out-of-bed state samples for future sleep-stage timeline visualisation
- `sleep_comprehensive_status.csv`: real-time 8-field sleep comprehensive status samples
- `device_status_events.csv`: online, breathing-status, and abnormal-sleep status events
- `data_quality_events.csv`: invalid, stale, offline, and parsing/cleaning notes
- `conversion_summary.json`: counts and date ranges by file

## Run

From this folder:

```powershell
python convert_jlsp01_logs.py
```

From repository root:

```powershell
python Test\data_conversion_cleaning\convert_jlsp01_logs.py
```

If a CSV is open in Excel or another process, write to a separate folder:

```powershell
python Test\data_conversion_cleaning\convert_jlsp01_logs.py --output-dir Test\data_conversion_cleaning\output_verified
```

## Current Mapping

- `getIntoBed = 1` -> `IN_BED`
- `getIntoBed = 0` -> `OUT_OF_BED`
- `someoneExists = 0` -> `NO_PERSON` in `presence_events.csv`, and a `NO_PERSON` bed event for backend compatibility
- `someoneExists = 1` -> `PRESENT` in `presence_events.csv`; it is not treated as `IN_BED`
- `motionStatus = 0` -> `NONE`
- `motionStatus = 1` -> `STATIC`
- `motionStatus = 2` -> `ACTIVE`
- undocumented values such as `motionStatus = 255` -> `UNKNOWN`, lower confidence
- `heartRateValue` -> `heart_rate_bpm`
- `breathValue` -> `breathing_rate_per_min`
- `sleepStatus = 0/1/2/3` -> `DEEP_SLEEP` / `LIGHT_SLEEP` / `AWAKE` / `NONE`
- `sleepComprehensiveStatus` -> presence, sleep status, average respiration, average heartbeat, turns, large/small movement percentages, apnea count
- `sleepQualityAnalysis` -> sleep score, 2-byte total sleep duration, awake/light/deep ratios, total out-of-bed duration, bed-exit count, turn count, average respiration, average heartbeat, apnea count
- `breathInform = 1/2/3/4` -> `NORMAL` / `TOO_HIGH` / `TOO_LOW` / `DETECTING`
- `abnormalSleep = 0/1/2/3` -> under-4-hours / over-12-hours / long-no-person / none

## Protocol Audit Notes

`daily_sleep_summary.csv` remains backend-compatible, but the JLSP01 protocol does not provide a true longest out-of-bed field. The converter therefore uses the protocol's total out-of-bed duration as a conservative proxy for `longest_out_of_bed_minutes` in the backend upload CSV. The more precise protocol field name is retained in `daily_sleep_analysis.csv` as `total_out_of_bed_minutes`.
