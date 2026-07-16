from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.analytics.bed_exit_xgboost import (
    WINDOWS,
    build_explanation,
    build_supervised_dataset,
    risk_level,
    split_train_validation,
    summarise_split,
)


LOGISTIC_FEATURES = [
    "rule_score",
    "hour",
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
]


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
    from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    model_path = Path(model_dir)
    model_path.mkdir(parents=True, exist_ok=True)

    X_train = train[LOGISTIC_FEATURES]
    X_val = validation[LOGISTIC_FEATURES]
    report: dict[str, Any] = {
        "model_type": "baseline_rules_plus_logistic_regression",
        "feature_columns": LOGISTIC_FEATURES,
        "train": summarise_split("train", train).__dict__,
        "validation": summarise_split("validation", validation).__dict__,
        "blend": "final_probability = 0.70 * logistic_probability + 0.30 * rule_score",
        "models": {},
    }
    validation_predictions = validation[["resident_id", "timestamp", "rule_score"]].copy()

    for window in WINDOWS:
        y_train = train[f"y_{window}"]
        y_val = validation[f"y_{window}"]
        pos = int(y_train.sum())
        neg = int(len(y_train) - pos)
        if pos == 0:
            raise ValueError(f"Cannot train {window} minute logistic model because train positives are zero")

        model = Pipeline(
            steps=[
                ("scaler", StandardScaler()),
                (
                    "logistic",
                    LogisticRegression(
                        class_weight="balanced",
                        max_iter=1000,
                        solver="liblinear",
                        random_state=42,
                    ),
                ),
            ]
        )
        model.fit(X_train, y_train)
        logistic_probabilities = model.predict_proba(X_val)[:, 1]
        final_probabilities = _blend_with_rule_score(logistic_probabilities, validation["rule_score"].to_numpy())
        predictions = (final_probabilities >= 0.35).astype(int)
        y_val_array = y_val.to_numpy()

        true_positive = int(((predictions == 1) & (y_val_array == 1)).sum())
        false_positive = int(((predictions == 1) & (y_val_array == 0)).sum())
        true_negative = int(((predictions == 0) & (y_val_array == 0)).sum())
        false_negative = int(((predictions == 0) & (y_val_array == 1)).sum())

        validation_predictions[f"logistic_probability_{window}"] = np.round(logistic_probabilities, 4)
        validation_predictions[f"final_probability_{window}"] = np.round(final_probabilities, 4)
        validation_predictions[f"risk_level_{window}"] = [risk_level(float(p)) for p in final_probabilities]
        validation_predictions[f"predicted_{window}_at_0_35"] = predictions
        validation_predictions[f"actual_{window}"] = y_val_array

        report["models"][str(window)] = {
            "positive_count": pos,
            "negative_count": neg,
            "class_weight": "balanced",
            "validation_pr_auc": _safe_metric(average_precision_score, y_val, final_probabilities),
            "validation_precision_at_0_35": _safe_metric(precision_score, y_val, predictions, zero_division=0),
            "validation_recall_at_0_35": _safe_metric(recall_score, y_val, predictions, zero_division=0),
            "validation_f1_at_0_35": _safe_metric(f1_score, y_val, predictions, zero_division=0),
            "validation_true_positive_at_0_35": true_positive,
            "validation_false_positive_at_0_35": false_positive,
            "validation_true_negative_at_0_35": true_negative,
            "validation_false_negative_at_0_35": false_negative,
            "validation_positive_count": int(y_val.sum()),
            "validation_negative_count": int(len(y_val) - int(y_val.sum())),
        }

        with (model_path / f"bed_exit_logistic_{window}.pkl").open("wb") as fh:
            pickle.dump(model, fh)

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
    rule_scores = row["rule_score"].to_numpy()
    windows = []
    for window in WINDOWS:
        with (Path(model_dir) / f"bed_exit_logistic_{window}.pkl").open("rb") as fh:
            model = pickle.load(fh)
        logistic_probability = float(model.predict_proba(X)[:, 1][0])
        final_probability = float(_blend_with_rule_score(np.array([logistic_probability]), rule_scores)[0])
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
        "model_version": "baseline_rules_logistic_v1",
    }


def _blend_with_rule_score(probabilities: np.ndarray, rule_scores: np.ndarray) -> np.ndarray:
    return np.clip((0.70 * probabilities) + (0.30 * rule_scores), 0.03, 0.97)


def _safe_metric(metric, *args, **kwargs) -> float | None:
    try:
        value = metric(*args, **kwargs)
        if pd.isna(value):
            return None
        return round(float(value), 4)
    except ValueError:
        return None
