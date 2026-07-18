# Modification Log

This file records project changes for teammates to review before commits.

## 2026-07-18

### Scope

- English Sprint 1 project only: `Test/sprint1-en-final`
- Focus area: alert explanations and local development login reliability

### Changed Files

#### `Test/sprint1-en-final/backend/app/services/alert_explanation.py`

- Added a dedicated alert and model-risk explanation module.
- Added explanation builders for:
  - Long out-of-bed events
  - Repeated bed exits
  - Abnormal heart-rate readings
  - No person detected
  - Low bed-sensor confidence
  - Vital-sign data quality issues
  - Model risk signals used by Logistic Regression and XGBoost
- Each explanation is generated from the triggered rule and runtime context, such as duration, count, confidence, baseline range, time window, and sensor-feature signals.

#### `Test/sprint1-en-final/backend/app/services/alert_service.py`

- Replaced inline alert reason strings with calls to the new explanation helpers.
- Alert reasons now vary by alert type and severity instead of using one fixed style.
- Examples of covered runtime cases:
  - High alert for no person detected during expected sleep hours
  - High alert for prolonged out-of-bed duration compared with personal baseline
  - Medium alert for repeated bed exits above the 30-day average
  - Medium alert for sustained abnormal heart-rate readings
  - Low alert for low bed-sensor confidence
  - Low alert for repeated low-confidence vital-sign readings

#### `Test/sprint1-en-final/backend/app/analytics/bed_exit_xgboost.py`

- Updated the shared `build_explanation()` function to use the new model-risk explanation helper.
- This also affects Logistic Regression because `bed_exit_logistic.py` imports and reuses `build_explanation()` from this module.
- Model explanations now map model input features to readable reasons, including:
  - Usual bed-exit time
  - Increased movement in the last 10 minutes
  - Active movement state
  - Awake or light sleep state
  - Heart-rate or breathing-rate increase
  - Earlier bed exits tonight
  - Recent bed-exit history
  - Poor previous-night sleep indicators
  - Low confidence or missing sensor data

#### `Test/sprint1-en-final/frontend/vite.config.ts`

- Changed the Vite dev proxy target from `http://localhost:8001` to `http://127.0.0.1:8001`.
- Reason: the frontend login request was returning `500` through the Vite proxy while direct backend login on port `8001` succeeded. Using `127.0.0.1` avoids localhost IPv4/IPv6 resolution ambiguity in local development.

### User-Visible Result

- Alert Centre now displays clearer, context-specific `Reason` text for each alert.
- The reason text is generated from rule/model features and current data values rather than being a single fixed message for all alerts.
- Existing alerts in the database keep their old reason text until alerts are regenerated.

### Verification

- Python syntax check passed for:
  - `backend/app/services/alert_explanation.py`
  - `backend/app/services/alert_service.py`
  - `backend/app/analytics/bed_exit_xgboost.py`
- Manual UI check confirmed the Alert Centre displays generated explanation text for R003 alerts.

### Notes For Reviewers

- No database schema changes were made.
- No frontend API response types were changed.
- To regenerate demo alerts after these changes:

```bash
cd /Users/estellewong/9900_Test/Test/sprint1-en-final/backend
python scripts/init_db.py --reset
```

