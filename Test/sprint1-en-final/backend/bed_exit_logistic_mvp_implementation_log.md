# Bed-Exit Primary MVP Implementation Log

Date: 2026-07-14

## Scope

Implemented the primary MVP model:

`Baseline rules + Logistic Regression`

The model is intentionally simple and explainable. It uses baseline rule signals as a stabilising feature and fallback, then trains one Logistic Regression classifier for each prediction window:

- 15 minutes
- 30 minutes
- 60 minutes

## Files Added

- `app/analytics/bed_exit_logistic.py`
  - Builds the Logistic Regression dataset from cleaned CSV outputs.
  - Calculates an interpretable `rule_score`.
  - Trains three Logistic Regression models.
  - Saves validation predictions and training metrics.
  - Provides a prediction helper returning probability, risk level, explanation, and model version.

- `scripts/train_bed_exit_logistic.py`
  - Command-line training script for the primary MVP model.
  - Uses the same supervised sample construction and time split as the XGBoost comparison model.

## Rule Score

The baseline rule score uses simple care-relevant signals from the customer requirements:

- Night-time period.
- Time close to observed bed-exit periods.
- Awake or light-sleep status.
- Active movement or recent movement increase.
- Heart rate above recent average.
- Breathing rate above recent average.
- Earlier bed exits during the same night.
- Low confidence or missing data penalty.

The score is bounded between `0.03` and `0.95`.

## Dataset

Input:

- `bed_events.csv`
- `vital_samples.csv`
- `activity_samples.csv`
- `sleep_stage_samples.csv`
- `daily_sleep_summary.csv`

Sampling:

- 5-minute supervised samples.
- Sleep negative samples are kept.
- No negative downsampling is used.
- Rows where the resident is already `OUT_OF_BED` or `NO_PERSON` are excluded because they are not pre-exit prediction candidates.

Total supervised samples: 376.

## Labels

For each sample time `t`:

- `y_15 = 1` if `OUT_OF_BED` occurs in `(t, t + 15min]`.
- `y_30 = 1` if `OUT_OF_BED` occurs in `(t, t + 30min]`.
- `y_60 = 1` if `OUT_OF_BED` occurs in `(t, t + 60min]`.

## Split

The split is time-based:

- Train: samples before `2026-06-03`.
- Validation: samples from `2026-06-03` onward.

Train distribution:

- Samples: 269.
- 15 min: 10 positive, 259 negative.
- 30 min: 16 positive, 253 negative.
- 60 min: 28 positive, 241 negative.

Validation distribution:

- Samples: 107.
- 15 min: 5 positive, 102 negative.
- 30 min: 8 positive, 99 negative.
- 60 min: 14 positive, 93 negative.

## Imbalance Handling

Negative sleep samples were not deleted.

Class imbalance is handled with:

`LogisticRegression(class_weight="balanced")`

This keeps all negative windows while increasing the training weight of rare positive bed-exit windows.

## Model Output

The final probability blends Logistic Regression and rules:

`final_probability = 0.70 * logistic_probability + 0.30 * rule_score`

Risk levels:

- Low: `< 0.35`
- Medium: `0.35 - 0.65`
- High: `>= 0.65`

Example prediction output:

```json
{
  "windows": [
    { "minutes": 15, "probability": 0.68, "risk_level": "High" },
    { "minutes": 30, "probability": 0.72, "risk_level": "High" },
    { "minutes": 60, "probability": 0.51, "risk_level": "Medium" }
  ],
  "explanation": "Risk is based on heart rate is above the resident's recent average, the time is close to observed bed-exit periods.",
  "model_version": "baseline_rules_logistic_v1"
}
```

## Validation Results

Threshold used for the binary validation report: `0.35`.

15-minute model:

- PR-AUC: 0.4832.
- Precision: 0.2.
- Recall: 1.0.
- F1: 0.3333.
- TP: 5, FP: 20, TN: 82, FN: 0.

30-minute model:

- PR-AUC: 0.3452.
- Precision: 0.3333.
- Recall: 1.0.
- F1: 0.5.
- TP: 8, FP: 16, TN: 83, FN: 0.

60-minute model:

- PR-AUC: 0.7106.
- Precision: 0.56.
- Recall: 1.0.
- F1: 0.7179.
- TP: 14, FP: 11, TN: 82, FN: 0.

## Generated Artifacts

Directory:

`backend/artifacts/bed_exit_logistic`

Files:

- `supervised_bed_exit_dataset.csv`
- `split_report.json`
- `training_report.json`
- `validation_predictions.csv`
- `bed_exit_logistic_15.pkl`
- `bed_exit_logistic_30.pkl`
- `bed_exit_logistic_60.pkl`

## Self Review

What is appropriate:

- This is more suitable as the primary MVP than XGBoost because it is simpler and easier to explain.
- It keeps sleep negative samples and uses class weighting instead of downsampling.
- It uses a time-based split, avoiding random leakage between nearby windows.
- It outputs the required 15/30/60 minute probabilities and Low/Medium/High risk levels.
- It supports readable explanation messages.
- It remains easy to extend later with more rules or more baseline features.

What is weak:

- The dataset is too small for reliable generalisation: only 8 `OUT_OF_BED` events exist.
- The 15- and 30-minute models have high recall but many false positives at the `0.35` threshold.
- There is no independent test set yet because the available data is too limited.
- Proper 7-day or 30-day personal baselines cannot be learned from only two summary days.

Decision after self review:

- Keep this as the primary MVP implementation.
- Do not delete negative sleep windows to improve metrics artificially.
- Do not over-tune thresholds on the current validation day.
- When more data arrives, first use the newest nights as a held-out test set, then retrain with a larger time-based split.

## Tuning Experiment Update

Date: 2026-07-14

Added `scripts/evaluate_bed_exit_logistic_tuning.py` to compare several adjustment directions:

- Thresholds: `0.35`, `0.45`, `0.55`.
- Logistic/rule blends: `1.00/0.00`, `0.85/0.15`, `0.70/0.30`.
- Class weighting: `none`, `mild`, `medium`, `balanced`.
- Rule profiles: `current`, `conservative`, `stable_protect`.

The full tuning output is written to:

`backend/artifacts/bed_exit_logistic_tuning/all_results.csv`

Summary tables are written to:

`backend/artifacts/bed_exit_logistic_tuning/summary_tables.md`

The experiment produced 324 result rows.

Best PR-AUC by window:

- 15 min: `current`, no class weight, blend `0.85/0.15`, threshold `0.35`, PR-AUC `0.6033`, F1 `0.5333`, TP `4`, FP `6`, FN `1`.
- 30 min: `stable_protect`, no class weight, blend `1.00/0.00`, threshold `0.35`, PR-AUC `0.3757`, F1 `0.4`, TP `5`, FP `12`, FN `3`.
- 60 min: `current`, balanced class weight, blend `0.85/0.15`, threshold `0.45`, PR-AUC `0.7908`, F1 `0.7568`, TP `14`, FP `9`, FN `0`.

Best F1 by window:

- 15 min: `current`, no class weight, blend `0.70/0.30`, threshold `0.45`, F1 `0.6154`, TP `4`, FP `4`, FN `1`.
- 30 min: `current`, no class weight, blend `0.70/0.30`, threshold `0.35`, F1 `0.5161`, TP `8`, FP `15`, FN `0`.
- 60 min: `current`, no class weight, blend `1.00/0.00`, threshold `0.35`, F1 `0.7568`, TP `14`, FP `9`, FN `0`.

Decision after tuning:

- Avoid `class_weight="balanced"` for 15-minute prediction because it increases false positives without improving PR-AUC.
- Consider no class weight for 15 and 30 minutes on the current data.
- Keep stronger weighting only as an option for 60 minutes, where it improves PR-AUC.
- Prefer per-window thresholds instead of one global threshold.
- Treat these choices as validation-only recommendations; they should be rechecked when more nights are available.
