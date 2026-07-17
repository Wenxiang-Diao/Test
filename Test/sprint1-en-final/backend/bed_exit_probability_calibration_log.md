# Bed-Exit Probability Calibration Log

Date: 2026-07-16

## Objective

Refocus both bed-exit models from PR-AUC-only optimisation to probability quality. The final 15, 30 and 60 minute values should be interpretable as estimated event probabilities rather than arbitrary risk scores.

## Data Controls

- Kept all eligible sleep negative samples.
- Kept the time-based split: 269 training samples and 107 validation samples.
- Did not fit the probability calibrators on validation labels.
- Replaced same-day completed sleep-summary inputs with previous-night summary features.
- Replaced same-day full-night heart-rate and breathing-rate averages with past-only expanding baselines when no previous summary is available.
- Added previous-night sleep efficiency, sleep score, total sleep minutes and bed-exit count features.

## Logistic Regression Changes

- Kept the baseline rule score as an input feature.
- Removed the direct `0.70 * logistic + 0.30 * rule` probability blend.
- Removed `class_weight="balanced"`, which changes probability scale.
- Selected probability-focused regularisation values: `C=0.10` for 15 minutes and `C=0.03` for 30/60 minutes.
- Added three-fold training-only out-of-fold Platt calibration.
- Saved calibrated bundles as `bed_exit_logistic_calibrated_15.pkl`, `30.pkl` and `60.pkl`.

Validation results:

| Window | PR-AUC | Brier | Brier skill | Log loss | ECE | Mean probability | Observed rate | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 15 min | 0.5578 | 0.0275 | 0.3818 | 0.0965 | 0.0289 | 0.0545 | 0.0467 | 0.5000 | 0.6000 | 0.5455 |
| 30 min | 0.5929 | 0.0457 | 0.3388 | 0.1501 | 0.0086 | 0.0804 | 0.0748 | 0.6667 | 0.5000 | 0.5714 |
| 60 min | 0.6707 | 0.0584 | 0.4863 | 0.1767 | 0.0402 | 0.1460 | 0.1308 | 0.6190 | 0.9286 | 0.7429 |

## XGBoost Changes

- Removed `scale_pos_weight`, which improved recall but distorted probability scale.
- Changed evaluation focus from AUC-PR to log loss.
- Used shallower, more strongly regularised trees.
- Applied training-only Platt calibration for 15 and 30 minutes.
- Retained the unweighted raw probability for 60 minutes because Platt calibration increased validation Brier and log loss for that window.
- Saved model/calibrator bundles as `bed_exit_xgb_calibrated_15.pkl`, `30.pkl` and `60.pkl`.

Validation results:

| Window | PR-AUC | Brier | Brier skill | Log loss | ECE | Mean probability | Observed rate | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 15 min | 0.7006 | 0.0359 | 0.1942 | 0.1260 | 0.0138 | 0.0462 | 0.0467 | 0.0000 | 0.0000 | 0.0000 |
| 30 min | 0.6470 | 0.0405 | 0.4143 | 0.1382 | 0.0260 | 0.0869 | 0.0748 | 0.6364 | 0.8750 | 0.7368 |
| 60 min | 0.6813 | 0.0431 | 0.6213 | 0.1624 | 0.0673 | 0.1479 | 0.1308 | 0.6190 | 0.9286 | 0.7429 |

Precision, recall and F1 above use a provisional `0.30` high-risk threshold. Threshold selection is separate from probability calibration. In particular, XGBoost 15-minute probabilities are well aligned in aggregate but do not reach `0.30`, so a lower operational alert threshold must be evaluated later.

## Horizon Consistency

Both prediction paths now apply cumulative ordering after calibration:

`P(exit within 15 min) <= P(exit within 30 min) <= P(exit within 60 min)`

Validation horizon-order violations after the change: `0 / 107` for both models.

## Self Review

- XGBoost currently has the best overall probability performance, especially for 30 and 60 minutes.
- Logistic Regression has the lowest 15-minute Brier score and remains the more interpretable MVP.
- Every Brier skill score is positive, so both models improve over predicting only the validation event prevalence.
- The previous-night sleep-quality feature path is implemented, but the training split has no earlier daily summary available for its positive day. More nights are required before the model can learn a reliable sleep-quality effect.
- Only five, eight and fourteen positive validation windows exist. Calibration metrics therefore have high variance.
- Logistic regularisation and the per-window XGBoost calibration decision were selected using the existing validation day. That day is now a model-selection set, not an untouched final test set.
- High probability confidence cannot be guaranteed until later nights are evaluated without any further parameter changes.
