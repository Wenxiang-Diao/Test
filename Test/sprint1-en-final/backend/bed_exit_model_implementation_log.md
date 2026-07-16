# Bed-Exit XGBoost Implementation Log

Date: 2026-07-14

## Scope

Implemented a first XGBoost-based bed-exit prediction pipeline using the cleaned JLSP01 CSV outputs. The implementation focuses only on model construction and result output:

- Build supervised 5-minute prediction samples.
- Keep sleep negative samples.
- Exclude only rows where the resident is already `OUT_OF_BED` or `NO_PERSON`.
- Create three labels for future bed-exit risk: 15, 30, and 60 minutes.
- Use a time-based train/validation split.
- Train three XGBoost binary classifiers.
- Handle class imbalance with `scale_pos_weight`, not negative downsampling.
- Save model artifacts, split report, training report, supervised dataset, and validation predictions.

## Files Added or Updated

- `app/analytics/bed_exit_xgboost.py`
  - Feature and label generation.
  - Time-based split helper.
  - XGBoost training.
  - Prediction output helper.
  - Simple explanation generation.

- `scripts/train_bed_exit_xgboost.py`
  - Command-line training script.
  - Reads cleaned data from `Test/data_conversion_cleaning/output`.
  - Writes artifacts to `backend/artifacts/bed_exit_xgboost`.

- `requirements.txt`
  - Added `xgboost==2.1.3`.

## Dataset Construction

Input files:

- `bed_events.csv`
- `vital_samples.csv`
- `activity_samples.csv`
- `sleep_stage_samples.csv`
- `daily_sleep_summary.csv`

Sampling:

- Frequency: 5 minutes.
- Total supervised samples: 376.
- Candidate rows are retained when the resident is not already out of bed and there is sleep or in-bed context.
- Sleep negative samples are kept; no negative downsampling is used.

Labels:

- `y_15 = 1` if an `OUT_OF_BED` event occurs in `(t, t + 15min]`.
- `y_30 = 1` if an `OUT_OF_BED` event occurs in `(t, t + 30min]`.
- `y_60 = 1` if an `OUT_OF_BED` event occurs in `(t, t + 60min]`.

## Split

The split is time-based, not random:

- Train: samples before `2026-06-03`.
- Validation: samples from `2026-06-03` onward.
- No independent test set is created because the current dataset is too small.

Train distribution:

- Samples: 269.
- 15 min: 10 positive, 259 negative, `scale_pos_weight = 25.9`.
- 30 min: 16 positive, 253 negative, `scale_pos_weight = 15.8125`.
- 60 min: 28 positive, 241 negative, `scale_pos_weight = 8.6071`.

Validation distribution:

- Samples: 107.
- 15 min: 5 positive, 102 negative.
- 30 min: 8 positive, 99 negative.
- 60 min: 14 positive, 93 negative.

## Model

Three separate models are trained:

- `bed_exit_xgb_15.json`
- `bed_exit_xgb_30.json`
- `bed_exit_xgb_60.json`

Reason for three models:

- Each prediction horizon has a different label definition.
- Each horizon has a different imbalance ratio.
- The API needs separate probabilities for 15, 30, and 60 minutes.

Initial XGBoost parameters:

- `objective = binary:logistic`
- `eval_metric = aucpr`
- `max_depth = 2`
- `learning_rate = 0.05`
- `n_estimators = 120`
- `subsample = 0.8`
- `colsample_bytree = 0.8`
- `scale_pos_weight = negative_count / positive_count`

## Validation Results

Threshold used for binary validation report: `0.35`.

15-minute model:

- PR-AUC: 0.72.
- Precision: 0.2105.
- Recall: 0.8.
- F1: 0.3333.
- TP: 4, FP: 15, TN: 87, FN: 1.

30-minute model:

- PR-AUC: 0.7345.
- Precision: 0.3333.
- Recall: 0.875.
- F1: 0.4828.
- TP: 7, FP: 14, TN: 85, FN: 1.

60-minute model:

- PR-AUC: 0.6807.
- Precision: 0.5652.
- Recall: 0.9286.
- F1: 0.7027.
- TP: 13, FP: 10, TN: 83, FN: 1.

## Generated Artifacts

Directory:

`backend/artifacts/bed_exit_xgboost`

Files:

- `supervised_bed_exit_dataset.csv`
- `split_report.json`
- `training_report.json`
- `validation_predictions.csv`
- `bed_exit_xgb_15.json`
- `bed_exit_xgb_30.json`
- `bed_exit_xgb_60.json`

## Self Review

What is appropriate:

- The split is time-based, so validation does not randomly leak adjacent training windows.
- Negative sleep windows are not deleted.
- Class imbalance is handled by XGBoost sample weighting through `scale_pos_weight`.
- Three separate models are justified because the 15/30/60 minute horizons have different labels and imbalance ratios.
- Model outputs include probability and Low/Medium/High risk levels.
- Reports include PR-AUC, precision, recall, F1, and confusion counts instead of relying on accuracy.

Limitations:

- The dataset is very small: only 8 `OUT_OF_BED` events in the cleaned data.
- Validation has only one day, so metrics are useful for sanity checking but not strong evidence of generalization.
- The 15- and 30-minute models have many false positives at threshold `0.35`.
- 30-day personal baselines cannot be properly learned from the current two summary days.
- The backend database schema currently stores bed/vital/summary data, but not the cleaned `activity_samples` or `sleep_stage_samples`; the first implementation therefore trains from CSV artifacts rather than live database rows.

Decision after self review:

- Keep the implementation as the first model version because it satisfies the project constraints and avoids deleting negative sleep samples.
- Do not tune thresholds aggressively yet, because the validation set is too small and this would likely overfit.
- When more data arrives, use the newest nights as a held-out test set first, then rebuild dataset versions and retrain.
