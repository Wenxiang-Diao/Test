from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.analytics.bed_exit_xgboost import (
    ALERT_THRESHOLD,
    WINDOWS,
    build_explanation,
    build_supervised_dataset,
    calibrated_predict_proba,
    enforce_horizon_order,
    fit_platt_calibrated_model,
    probability_metrics,
    risk_level,
    split_train_validation,
    summarise_split,
)


LOGISTIC_FEATURES = [
    "rule_score",
    "hour",
    "minutes_since_midnight",
    "is_night",
    "is_common_exit_period",
    "heart_rate_delta_from_daily_avg",
    "breathing_rate_delta_from_daily_avg",
    "movement_signs",
    "movement_mean_10m",
    "movement_slope_10m",
    "bed_exit_count_so_far",
    "minutes_since_last_bed_exit",
    "confidence_mean",
    "missing_rate_10m",
    "activity_status_ACTIVE",
    "motion_status_ACTIVE",
    "sleep_status_AWAKE",
    "sleep_status_LIGHT_SLEEP",
    "previous_night_sleep_efficiency",
    "previous_night_sleep_score",
    "previous_night_total_sleep_minutes",
    "previous_night_bed_exit_count",
    "previous_night_summary_missing",
]

REGULARIZATION_C = {15: 0.10, 30: 0.03, 60: 0.03}


def build_logistic_dataset(output_dir: str | Path) -> pd.DataFrame:
    dataset = build_supervised_dataset(output_dir)
    dataset["rule_score"] = dataset.apply(calculate_rule_score, axis=1)
    for feature in LOGISTIC_FEATURES:
        if feature not in dataset:
            dataset[feature] = 0
    dataset[LOGISTIC_FEATURES] = dataset[LOGISTIC_FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0)
    return dataset


def calculate_rule_score(row: pd.Series) -> float:
    """Small interpretable baseline score used by the MVP model.

    The score is intentionally simple and bounded. It is not a diagnosis; it is
    a stabilising feature and fallback for the logistic model.
    """

    score = 0.08
    if row.get("is_night", 0) == 1:
        score += 0.08
    if row.get("is_common_exit_period", 0) == 1:
        score += 0.12
    if row.get("sleep_status_AWAKE", 0) == 1:
        score += 0.14
    elif row.get("sleep_status_LIGHT_SLEEP", 0) == 1:
        score += 0.05
    if row.get("activity_status_ACTIVE", 0) == 1 or row.get("motion_status_ACTIVE", 0) == 1:
        score += 0.10
    if row.get("movement_slope_10m", 0) > 0:
        score += 0.10
    if row.get("heart_rate_delta_from_daily_avg", 0) > 5:
        score += 0.10
    if row.get("breathing_rate_delta_from_daily_avg", 0) > 2:
        score += 0.08
    if row.get("bed_exit_count_so_far", 0) > 0:
        score += 0.10
    if row.get("confidence_mean", 1) < 0.7 or row.get("missing_rate_10m", 0) > 0.5:
        score -= 0.05
    return round(float(min(max(score, 0.03), 0.95)), 4)


def train_logistic_models(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    model_dir: str | Path,
) -> dict[str, Any]:
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    model_path = Path(model_dir)
    model_path.mkdir(parents=True, exist_ok=True)

    X_train = train[LOGISTIC_FEATURES]
    X_val = validation[LOGISTIC_FEATURES]
    report: dict[str, Any] = {
        "model_type": "baseline_rules_as_features_plus_probability_calibrated_logistic_regression",
        "feature_columns": LOGISTIC_FEATURES,
        "train": summarise_split("train", train).__dict__,
        "validation": summarise_split("validation", validation).__dict__,
        "probability_objective": "unweighted log loss followed by training-only out-of-fold Platt scaling",
        "rule_usage": "rule_score is an input feature; it is not blended into the final probability",
        "calibration": "3-fold stratified out-of-fold predictions on the training split",
        "horizon_constraint": "P15 <= P30 <= P60",
        "models": {},
    }
    validation_predictions = validation[["resident_id", "timestamp", "rule_score"]].copy()
    raw_probabilities: dict[int, np.ndarray] = {}
    calibrated_probabilities: dict[int, np.ndarray] = {}
    bundles: dict[int, dict[str, Any]] = {}

    for window in WINDOWS:
        y_train = train[f"y_{window}"]
        y_val = validation[f"y_{window}"]
        pos = int(y_train.sum())
        neg = int(len(y_train) - pos)
        if pos == 0:
            raise ValueError(f"Cannot train {window} minute logistic model because train positives are zero")

        def estimator_factory():
            return Pipeline(
                steps=[
                    ("scaler", StandardScaler()),
                    (
                        "logistic",
                        LogisticRegression(
                            C=REGULARIZATION_C[window],
                            class_weight=None,
                            max_iter=1000,
                            solver="liblinear",
                            random_state=42,
                        ),
                    ),
                ]
            )

        bundle = fit_platt_calibrated_model(estimator_factory, X_train, y_train)
        bundle["use_calibrator"] = True
        raw_probabilities[window] = bundle["estimator"].predict_proba(X_val)[:, 1]
        calibrated_probabilities[window] = calibrated_predict_proba(bundle, X_val)
        bundles[window] = bundle

    coherent_probabilities = enforce_horizon_order(calibrated_probabilities)
    for window in WINDOWS:
        y_val = validation[f"y_{window}"].to_numpy()
        probabilities = coherent_probabilities[window]
        predictions = (probabilities >= ALERT_THRESHOLD).astype(int)
        validation_predictions[f"raw_probability_{window}"] = np.round(raw_probabilities[window], 4)
        validation_predictions[f"calibrated_probability_{window}"] = np.round(
            calibrated_probabilities[window], 4
        )
        validation_predictions[f"probability_{window}"] = np.round(probabilities, 4)
        validation_predictions[f"risk_level_{window}"] = [risk_level(float(p)) for p in probabilities]
        validation_predictions[f"predicted_{window}_at_{str(ALERT_THRESHOLD).replace('.', '_')}"] = predictions
        validation_predictions[f"actual_{window}"] = y_val
        report["models"][str(window)] = {
            "positive_count": int(train[f"y_{window}"].sum()),
            "negative_count": int(len(train) - train[f"y_{window}"].sum()),
            "class_weight": None,
            "regularization_c": REGULARIZATION_C[window],
            "alert_threshold": ALERT_THRESHOLD,
            "raw_validation": probability_metrics(y_val, raw_probabilities[window], ALERT_THRESHOLD),
            "calibrated_validation": probability_metrics(y_val, probabilities, ALERT_THRESHOLD),
        }
        with (model_path / f"bed_exit_logistic_calibrated_{window}.pkl").open("wb") as fh:
            pickle.dump(bundles[window], fh)

    validation_predictions.to_csv(model_path / "validation_predictions.csv", index=False)
    with (model_path / "training_report.json").open("w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    return report


def predict_with_models(feature_row: pd.DataFrame, model_dir: str | Path) -> dict[str, Any]:
    row = feature_row.copy()
    if "rule_score" not in row:
        row["rule_score"] = row.apply(calculate_rule_score, axis=1)
    for feature in LOGISTIC_FEATURES:
        if feature not in row:
            row[feature] = 0

    X = row[LOGISTIC_FEATURES]
    raw: dict[int, np.ndarray] = {}
    for window in WINDOWS:
        with (Path(model_dir) / f"bed_exit_logistic_calibrated_{window}.pkl").open("rb") as fh:
            bundle = pickle.load(fh)
        raw[window] = calibrated_predict_proba(bundle, X)
    probabilities = enforce_horizon_order(raw)
    windows = []
    for window in WINDOWS:
        final_probability = float(probabilities[window][0])
        windows.append(
            {
                "minutes": window,
                "probability": round(final_probability, 2),
                "risk_level": risk_level(final_probability),
            }
        )
    return {
        "windows": windows,
        "explanation": build_explanation(row.iloc[0]),
        "model_version": "baseline_rules_logistic_calibrated_v3",
    }


def _safe_metric(metric, *args, **kwargs) -> float | None:
    try:
        value = metric(*args, **kwargs)
        if pd.isna(value):
            return None
        return round(float(value), 4)
    except ValueError:
        return None
