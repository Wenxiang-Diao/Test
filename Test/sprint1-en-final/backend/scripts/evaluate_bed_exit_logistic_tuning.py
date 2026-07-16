from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.analytics.bed_exit_logistic import LOGISTIC_FEATURES  # noqa: E402
from app.analytics.bed_exit_xgboost import (  # noqa: E402
    WINDOWS,
    build_supervised_dataset,
    split_train_validation,
)


THRESHOLDS = (0.35, 0.45, 0.55)
BLENDS = (1.0, 0.85, 0.70)
CLASS_WEIGHT_MODES = ("none", "mild", "medium", "balanced")
RULE_PROFILES = ("current", "conservative", "stable_protect")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Logistic MVP tuning options.")
    parser.add_argument(
        "--input-dir",
        default=str(ROOT.parent.parent / "data_conversion_cleaning" / "output"),
    )
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "artifacts" / "bed_exit_logistic_tuning"),
    )
    parser.add_argument("--validation-start", default="2026-06-03")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    base_dataset = build_supervised_dataset(args.input_dir)
    all_results = []

    for rule_profile in RULE_PROFILES:
        dataset = base_dataset.copy()
        dataset["rule_score"] = dataset.apply(lambda row: calculate_rule_score(row, rule_profile), axis=1)
        for feature in LOGISTIC_FEATURES:
            if feature not in dataset:
                dataset[feature] = 0
        dataset[LOGISTIC_FEATURES] = dataset[LOGISTIC_FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0)

        train, validation = split_train_validation(dataset, args.validation_start)
        for class_weight_mode in CLASS_WEIGHT_MODES:
            for blend in BLENDS:
                all_results.extend(
                    evaluate_config(
                        train=train,
                        validation=validation,
                        rule_profile=rule_profile,
                        class_weight_mode=class_weight_mode,
                        blend=blend,
                    )
                )

    results = pd.DataFrame(all_results)
    results_path = output_dir / "all_results.csv"
    results.to_csv(results_path, index=False)

    summary = {
        "total_rows": int(len(results)),
        "results_path": str(results_path),
        "best_by_window_pr_auc": _best_rows(results, "pr_auc"),
        "best_by_window_f1": _best_rows(results, "f1"),
        "best_by_window_recall_at_least_0_80_min_fp": _best_recall_floor(results, recall_floor=0.80),
    }
    with (output_dir / "summary.json").open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    print(json.dumps(summary, indent=2))


def evaluate_config(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    rule_profile: str,
    class_weight_mode: str,
    blend: float,
) -> list[dict]:
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    rows = []
    X_train = train[LOGISTIC_FEATURES]
    X_val = validation[LOGISTIC_FEATURES]

    for window in WINDOWS:
        y_train = train[f"y_{window}"]
        y_val = validation[f"y_{window}"]
        pos = int(y_train.sum())
        neg = int(len(y_train) - pos)
        if pos == 0:
            continue

        class_weight = build_class_weight(class_weight_mode, neg / pos)
        model = Pipeline(
            steps=[
                ("scaler", StandardScaler()),
                (
                    "logistic",
                    LogisticRegression(
                        class_weight=class_weight,
                        max_iter=1000,
                        solver="liblinear",
                        random_state=42,
                    ),
                ),
            ]
        )
        model.fit(X_train, y_train)
        logistic_prob = model.predict_proba(X_val)[:, 1]
        final_prob = np.clip((blend * logistic_prob) + ((1.0 - blend) * validation["rule_score"].to_numpy()), 0.03, 0.97)
        pr_auc = safe_metric(average_precision_score, y_val, final_prob)

        for threshold in THRESHOLDS:
            pred = (final_prob >= threshold).astype(int)
            y_val_array = y_val.to_numpy()
            tp = int(((pred == 1) & (y_val_array == 1)).sum())
            fp = int(((pred == 1) & (y_val_array == 0)).sum())
            tn = int(((pred == 0) & (y_val_array == 0)).sum())
            fn = int(((pred == 0) & (y_val_array == 1)).sum())
            rows.append(
                {
                    "window": window,
                    "rule_profile": rule_profile,
                    "class_weight_mode": class_weight_mode,
                    "positive_weight": class_weight[1] if isinstance(class_weight, dict) else class_weight_mode,
                    "blend_logistic": blend,
                    "blend_rule": round(1.0 - blend, 2),
                    "threshold": threshold,
                    "pr_auc": pr_auc,
                    "precision": safe_metric(precision_score, y_val, pred, zero_division=0),
                    "recall": safe_metric(recall_score, y_val, pred, zero_division=0),
                    "f1": safe_metric(f1_score, y_val, pred, zero_division=0),
                    "tp": tp,
                    "fp": fp,
                    "tn": tn,
                    "fn": fn,
                    "validation_positives": int(y_val.sum()),
                    "validation_negatives": int(len(y_val) - int(y_val.sum())),
                }
            )
    return rows


def build_class_weight(mode: str, imbalance_ratio: float):
    if mode == "none":
        return None
    if mode == "mild":
        return {0: 1.0, 1: round(max(1.0, imbalance_ratio * 0.35), 4)}
    if mode == "medium":
        return {0: 1.0, 1: round(max(1.0, imbalance_ratio * 0.60), 4)}
    if mode == "balanced":
        return "balanced"
    raise ValueError(f"Unknown class weight mode: {mode}")


def calculate_rule_score(row: pd.Series, profile: str) -> float:
    if profile == "current":
        weights = {
            "base": 0.08,
            "night": 0.08,
            "common_exit": 0.12,
            "awake": 0.14,
            "light": 0.05,
            "active": 0.10,
            "movement_up": 0.10,
            "hr_high": 0.10,
            "rr_high": 0.08,
            "prior_exit": 0.10,
            "low_quality": -0.05,
            "stable_deep": 0.0,
            "stable_static": 0.0,
        }
    elif profile == "conservative":
        weights = {
            "base": 0.06,
            "night": 0.05,
            "common_exit": 0.06,
            "awake": 0.10,
            "light": 0.02,
            "active": 0.07,
            "movement_up": 0.05,
            "hr_high": 0.07,
            "rr_high": 0.05,
            "prior_exit": 0.05,
            "low_quality": -0.05,
            "stable_deep": 0.0,
            "stable_static": 0.0,
        }
    elif profile == "stable_protect":
        weights = {
            "base": 0.06,
            "night": 0.05,
            "common_exit": 0.06,
            "awake": 0.10,
            "light": 0.02,
            "active": 0.07,
            "movement_up": 0.05,
            "hr_high": 0.07,
            "rr_high": 0.05,
            "prior_exit": 0.05,
            "low_quality": -0.05,
            "stable_deep": -0.08,
            "stable_static": -0.05,
        }
    else:
        raise ValueError(f"Unknown rule profile: {profile}")

    score = weights["base"]
    if row.get("is_night", 0) == 1:
        score += weights["night"]
    if row.get("is_common_exit_period", 0) == 1:
        score += weights["common_exit"]
    if row.get("sleep_status_AWAKE", 0) == 1:
        score += weights["awake"]
    elif row.get("sleep_status_LIGHT_SLEEP", 0) == 1:
        score += weights["light"]
    if row.get("activity_status_ACTIVE", 0) == 1 or row.get("motion_status_ACTIVE", 0) == 1:
        score += weights["active"]
    if row.get("movement_slope_10m", 0) > 0:
        score += weights["movement_up"]
    if row.get("heart_rate_delta_from_daily_avg", 0) > 5:
        score += weights["hr_high"]
    if row.get("breathing_rate_delta_from_daily_avg", 0) > 2:
        score += weights["rr_high"]
    if row.get("bed_exit_count_so_far", 0) > 0:
        score += weights["prior_exit"]
    if row.get("confidence_mean", 1) < 0.7 or row.get("missing_rate_10m", 0) > 0.5:
        score += weights["low_quality"]
    if row.get("sleep_status_DEEP_SLEEP", 0) == 1 and row.get("movement_slope_10m", 0) <= 0:
        score += weights["stable_deep"]
    if row.get("activity_status_STATIC", 0) == 1 and row.get("movement_slope_10m", 0) <= 0:
        score += weights["stable_static"]
    return round(float(min(max(score, 0.03), 0.95)), 4)


def safe_metric(metric, *args, **kwargs) -> float | None:
    try:
        value = metric(*args, **kwargs)
        if pd.isna(value):
            return None
        return round(float(value), 4)
    except ValueError:
        return None


def _best_rows(results: pd.DataFrame, metric: str) -> list[dict]:
    rows = []
    for window, frame in results.groupby("window"):
        best = frame.sort_values([metric, "recall", "precision"], ascending=[False, False, False]).iloc[0]
        rows.append(best.to_dict())
    return rows


def _best_recall_floor(results: pd.DataFrame, recall_floor: float) -> list[dict]:
    rows = []
    for window, frame in results.groupby("window"):
        candidates = frame[frame["recall"] >= recall_floor]
        if candidates.empty:
            candidates = frame
        best = candidates.sort_values(["fp", "f1", "pr_auc"], ascending=[True, False, False]).iloc[0]
        rows.append(best.to_dict())
    return rows


if __name__ == "__main__":
    main()
