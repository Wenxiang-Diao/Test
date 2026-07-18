from __future__ import annotations

import json
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.services.alert_explanation import explain_model_risk


WINDOWS = (15, 30, 60)
FREQUENCY = "5min"

BASE_FEATURES = [
    "hour",
    "minutes_since_midnight",
    "is_night",
    "is_common_exit_period",
    "heart_rate_bpm",
    "heart_rate_mean_10m",
    "heart_rate_slope_10m",
    "heart_rate_delta_from_daily_avg",
    "breathing_rate_per_min",
    "breathing_rate_mean_10m",
    "breathing_rate_slope_10m",
    "breathing_rate_delta_from_daily_avg",
    "movement_signs",
    "movement_mean_10m",
    "movement_slope_10m",
    "bed_exit_count_so_far",
    "minutes_since_last_bed_exit",
    "confidence_mean",
    "missing_rate_10m",
    "stale_data_flag",
    "bed_status_IN_BED",
    "bed_status_UNKNOWN",
    "activity_status_ACTIVE",
    "activity_status_STATIC",
    "motion_status_ACTIVE",
    "motion_status_STATIC",
    "sleep_status_AWAKE",
    "sleep_status_DEEP_SLEEP",
    "sleep_status_LIGHT_SLEEP",
    "sleep_status_NONE",
    "sleep_status_UNKNOWN",
    "previous_night_sleep_efficiency",
    "previous_night_sleep_score",
    "previous_night_total_sleep_minutes",
    "previous_night_bed_exit_count",
    "previous_night_summary_missing",
]

RISK_MEDIUM_THRESHOLD = 0.10
RISK_HIGH_THRESHOLD = 0.30
ALERT_THRESHOLD = 0.30


@dataclass(frozen=True)
class SplitSummary:
    name: str
    samples: int
    positives: dict[int, int]
    negatives: dict[int, int]
    scale_pos_weight: dict[int, float | None]


def risk_level(probability: float) -> str:
    if probability >= RISK_HIGH_THRESHOLD:
        return "High"
    if probability >= RISK_MEDIUM_THRESHOLD:
        return "Medium"
    return "Low"


def build_supervised_dataset(output_dir: str | Path) -> pd.DataFrame:
    """Build 5-minute bed-exit prediction samples from cleaned JLSP01 CSV files.

    The builder keeps sleep negative windows. It excludes rows where the resident
    is already OUT_OF_BED or NO_PERSON because those are not pre-exit prediction
    candidates.
    """

    output_path = Path(output_dir)
    bed = _read_csv(output_path / "bed_events.csv", ["timestamp"])
    vitals = _read_csv(output_path / "vital_samples.csv", ["timestamp"])
    activity = _read_csv(output_path / "activity_samples.csv", ["timestamp"])
    sleep = _read_csv(output_path / "sleep_stage_samples.csv", ["timestamp"])
    summary = _read_csv(output_path / "daily_sleep_summary.csv", ["date"])

    if vitals.empty or activity.empty:
        raise ValueError("vital_samples.csv and activity_samples.csv are required")

    start = min(vitals["timestamp"].min(), activity["timestamp"].min()).floor(FREQUENCY)
    end = max(vitals["timestamp"].max(), activity["timestamp"].max()).ceil(FREQUENCY)
    grid = pd.DataFrame({"timestamp": pd.date_range(start, end, freq=FREQUENCY)})
    grid["resident_id"] = "R001"

    df = _merge_recent(
        grid,
        vitals[["timestamp", "heart_rate_bpm", "breathing_rate_per_min", "confidence"]]
        .rename(columns={"confidence": "vital_confidence"}),
        tolerance="10min",
    )
    df = _merge_recent(
        df,
        activity[["timestamp", "motion_status", "movement_signs", "confidence"]]
        .rename(columns={"confidence": "activity_confidence"}),
        tolerance="10min",
    )
    df = _merge_recent(
        df,
        bed[["timestamp", "bed_status", "activity_status", "confidence"]]
        .rename(columns={"confidence": "bed_confidence"}),
        tolerance=None,
    )
    df = _merge_recent(
        df,
        sleep[["timestamp", "sleep_status", "confidence"]].rename(columns={"confidence": "sleep_confidence"}),
        tolerance="20min",
    )

    df = df.dropna(subset=["heart_rate_bpm", "breathing_rate_per_min", "movement_signs"]).copy()
    df = _keep_prediction_candidates(df)
    df = _add_rolling_features(df)
    df = _add_summary_features(df, summary)
    df = _add_bed_exit_history(df, bed)
    df = _add_labels(df, bed)
    df = _add_encoded_categories(df)
    df = _finalise_features(df)
    return df.sort_values("timestamp").reset_index(drop=True)


def split_train_validation(dataset: pd.DataFrame, validation_start: str = "2026-06-03") -> tuple[pd.DataFrame, pd.DataFrame]:
    split_ts = pd.Timestamp(validation_start)
    train = dataset[dataset["timestamp"] < split_ts].copy()
    validation = dataset[dataset["timestamp"] >= split_ts].copy()
    return train, validation


def summarise_split(name: str, frame: pd.DataFrame) -> SplitSummary:
    positives: dict[int, int] = {}
    negatives: dict[int, int] = {}
    weights: dict[int, float | None] = {}
    for window in WINDOWS:
        pos = int(frame[f"y_{window}"].sum())
        neg = int(len(frame) - pos)
        positives[window] = pos
        negatives[window] = neg
        weights[window] = round(neg / pos, 4) if pos else None
    return SplitSummary(name, int(len(frame)), positives, negatives, weights)


def train_xgboost_models(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    model_dir: str | Path,
) -> dict[str, Any]:
    try:
        from xgboost import XGBClassifier
    except ImportError as exc:
        raise RuntimeError("xgboost is not installed. Install backend requirements before training.") from exc

    model_path = Path(model_dir)
    model_path.mkdir(parents=True, exist_ok=True)

    X_train = train[BASE_FEATURES]
    X_val = validation[BASE_FEATURES]
    report: dict[str, Any] = {
        "feature_columns": BASE_FEATURES,
        "train": summarise_split("train", train).__dict__,
        "validation": summarise_split("validation", validation).__dict__,
        "probability_objective": "minimise log loss and calibrate with training-only out-of-fold Platt scaling",
        "calibration": "3-fold stratified out-of-fold predictions on the training split",
        "horizon_constraint": "P15 <= P30 <= P60",
        "models": {},
    }
    validation_predictions = validation[["resident_id", "timestamp"]].copy()
    raw_probabilities: dict[int, np.ndarray] = {}
    calibrated_probabilities: dict[int, np.ndarray] = {}
    bundles: dict[int, dict[str, Any]] = {}

    for window in WINDOWS:
        y_train = train[f"y_{window}"]
        y_val = validation[f"y_{window}"]
        pos = int(y_train.sum())
        neg = int(len(y_train) - pos)
        if pos == 0:
            raise ValueError(f"Cannot train {window} minute model because train positives are zero")

        def estimator_factory():
            return XGBClassifier(
                objective="binary:logistic",
                eval_metric="logloss",
                max_depth=2,
                learning_rate=0.03,
                n_estimators=100,
                min_child_weight=3,
                reg_lambda=3.0,
                subsample=0.85,
                colsample_bytree=0.85,
                random_state=42,
            )

        bundle = fit_platt_calibrated_model(estimator_factory, X_train, y_train)
        bundle["use_calibrator"] = window in (15, 30)
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
            "alert_threshold": ALERT_THRESHOLD,
            "raw_validation": probability_metrics(y_val, raw_probabilities[window], ALERT_THRESHOLD),
            "calibrated_validation": probability_metrics(y_val, probabilities, ALERT_THRESHOLD),
        }
        with (model_path / f"bed_exit_xgb_calibrated_{window}.pkl").open("wb") as fh:
            pickle.dump(bundles[window], fh)

    validation_predictions.to_csv(model_path / "validation_predictions.csv", index=False)
    with (model_path / "training_report.json").open("w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    return report


def predict_with_models(feature_row: pd.DataFrame, model_dir: str | Path) -> dict[str, Any]:
    X = feature_row[BASE_FEATURES]
    raw: dict[int, np.ndarray] = {}
    for window in WINDOWS:
        with (Path(model_dir) / f"bed_exit_xgb_calibrated_{window}.pkl").open("rb") as fh:
            bundle = pickle.load(fh)
        raw[window] = calibrated_predict_proba(bundle, X)
    probabilities = enforce_horizon_order(raw)
    windows = []
    for window in WINDOWS:
        probability = float(probabilities[window][0])
        windows.append(
            {
                "minutes": window,
                "probability": round(probability, 2),
                "risk_level": risk_level(probability),
            }
        )
    return {
        "windows": windows,
        "explanation": build_explanation(feature_row.iloc[0]),
        "model_version": "xgboost_bed_exit_calibrated_v2",
    }


def build_explanation(row: pd.Series) -> str:
    return explain_model_risk(row)


def _read_csv(path: Path, parse_dates: list[str]) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, parse_dates=parse_dates)


def _merge_recent(left: pd.DataFrame, right: pd.DataFrame, tolerance: str | None) -> pd.DataFrame:
    kwargs = {}
    if tolerance is not None:
        kwargs["tolerance"] = pd.Timedelta(tolerance)
    return pd.merge_asof(
        left.sort_values("timestamp"),
        right.sort_values("timestamp"),
        on="timestamp",
        direction="backward",
        **kwargs,
    )


def _keep_prediction_candidates(df: pd.DataFrame) -> pd.DataFrame:
    candidate = (~df["bed_status"].isin(["OUT_OF_BED", "NO_PERSON"])) & (
        df["sleep_status"].notna() | df["bed_status"].eq("IN_BED")
    )
    return df[candidate].copy()


def _add_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values("timestamp").copy()
    df["hour"] = df["timestamp"].dt.hour
    df["minutes_since_midnight"] = df["hour"] * 60 + df["timestamp"].dt.minute
    df["is_night"] = ((df["hour"] >= 22) | (df["hour"] <= 6)).astype(int)
    df["is_common_exit_period"] = df["hour"].isin([0, 8, 9]).astype(int)

    indexed = df.set_index("timestamp")
    for source, target in [
        ("heart_rate_bpm", "heart_rate"),
        ("breathing_rate_per_min", "breathing_rate"),
        ("movement_signs", "movement"),
    ]:
        mean_col = f"{target}_mean_10m"
        slope_col = f"{target}_slope_10m"
        df[mean_col] = indexed[source].rolling("10min", min_periods=1).mean().to_numpy()
        df[slope_col] = indexed[source].diff().rolling("10min", min_periods=1).mean().fillna(0).to_numpy()

    df["confidence_mean"] = df[["vital_confidence", "activity_confidence", "bed_confidence", "sleep_confidence"]].mean(axis=1)
    df["missing_rate_10m"] = df[["vital_confidence", "activity_confidence", "bed_confidence", "sleep_confidence"]].isna().mean(axis=1)
    df["stale_data_flag"] = df[["vital_confidence", "activity_confidence"]].isna().any(axis=1).astype(int)
    return df


def _add_summary_features(df: pd.DataFrame, summary: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values("timestamp").copy()
    past_hr = df["heart_rate_bpm"].expanding().mean().shift(1).fillna(df["heart_rate_bpm"])
    past_rr = df["breathing_rate_per_min"].expanding().mean().shift(1).fillna(df["breathing_rate_per_min"])
    if summary.empty:
        df["daily_avg_heart_rate"] = past_hr
        df["daily_avg_breathing_rate"] = past_rr
        df["previous_night_sleep_efficiency"] = 0.0
        df["previous_night_sleep_score"] = 0.0
        df["previous_night_total_sleep_minutes"] = 0.0
        df["previous_night_bed_exit_count"] = 0.0
        df["previous_night_summary_missing"] = 1
    else:
        previous = summary.copy().sort_values("date")
        previous["available_at"] = previous["date"] + pd.Timedelta(days=1)
        previous = previous.rename(
            columns={
                "avg_heart_rate": "previous_avg_heart_rate",
                "avg_breathing_rate": "previous_avg_breathing_rate",
                "sleep_efficiency": "previous_night_sleep_efficiency",
                "sleep_score": "previous_night_sleep_score",
                "total_sleep_minutes": "previous_night_total_sleep_minutes",
                "bed_exit_count": "previous_night_bed_exit_count",
            }
        )
        keep = [
            "available_at",
            "previous_avg_heart_rate",
            "previous_avg_breathing_rate",
            "previous_night_sleep_efficiency",
            "previous_night_sleep_score",
            "previous_night_total_sleep_minutes",
            "previous_night_bed_exit_count",
        ]
        df = pd.merge_asof(
            df.sort_values("timestamp"),
            previous[keep].sort_values("available_at"),
            left_on="timestamp",
            right_on="available_at",
            direction="backward",
        )
        df["daily_avg_heart_rate"] = df["previous_avg_heart_rate"].fillna(past_hr)
        df["daily_avg_breathing_rate"] = df["previous_avg_breathing_rate"].fillna(past_rr)
        df["previous_night_summary_missing"] = df["previous_night_sleep_score"].isna().astype(int)
        for column in [
            "previous_night_sleep_efficiency",
            "previous_night_sleep_score",
            "previous_night_total_sleep_minutes",
            "previous_night_bed_exit_count",
        ]:
            df[column] = df[column].fillna(0.0)
    df["heart_rate_delta_from_daily_avg"] = df["heart_rate_bpm"] - df["daily_avg_heart_rate"]
    df["breathing_rate_delta_from_daily_avg"] = df["breathing_rate_per_min"] - df["daily_avg_breathing_rate"]
    return df


def _add_bed_exit_history(df: pd.DataFrame, bed: pd.DataFrame) -> pd.DataFrame:
    exits = bed[bed["bed_status"].eq("OUT_OF_BED")].sort_values("timestamp")
    counts = []
    minutes_since_last = []
    for ts in df["timestamp"]:
        prior = exits[exits["timestamp"] < ts]
        same_night = prior[prior["timestamp"].dt.date == ts.date()]
        counts.append(int(len(same_night)))
        if prior.empty:
            minutes_since_last.append(9999.0)
        else:
            minutes_since_last.append(float((ts - prior["timestamp"].iloc[-1]).total_seconds() / 60))
    df["bed_exit_count_so_far"] = counts
    df["minutes_since_last_bed_exit"] = minutes_since_last
    return df


def _add_labels(df: pd.DataFrame, bed: pd.DataFrame) -> pd.DataFrame:
    exits = bed[bed["bed_status"].eq("OUT_OF_BED")]["timestamp"]
    df = df.copy()
    for window in WINDOWS:
        labels = []
        delta = pd.Timedelta(minutes=window)
        for ts in df["timestamp"]:
            labels.append(int(((exits > ts) & (exits <= ts + delta)).any()))
        df[f"y_{window}"] = labels
    return df


def _add_encoded_categories(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["bed_status"] = df["bed_status"].fillna("UNKNOWN")
    df["activity_status"] = df["activity_status"].fillna("STATIC")
    df["motion_status"] = df["motion_status"].fillna("STATIC")
    df["sleep_status"] = df["sleep_status"].fillna("UNKNOWN")
    encoded = pd.get_dummies(
        df[["bed_status", "activity_status", "motion_status", "sleep_status"]],
        prefix=["bed_status", "activity_status", "motion_status", "sleep_status"],
        dtype=int,
    )
    df = pd.concat([df, encoded], axis=1)
    return df


def _finalise_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for feature in BASE_FEATURES:
        if feature not in df:
            df[feature] = 0
    df[BASE_FEATURES] = df[BASE_FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0)
    return df


def _safe_metric(metric, *args, **kwargs) -> float | None:
    try:
        value = metric(*args, **kwargs)
        if pd.isna(value):
            return None
        return round(float(value), 4)
    except ValueError:
        return None


def fit_platt_calibrated_model(estimator_factory, X: pd.DataFrame, y: pd.Series) -> dict[str, Any]:
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedKFold

    splitter = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
    out_of_fold = np.zeros(len(X), dtype=float)
    for train_indices, calibration_indices in splitter.split(X, y):
        fold_model = estimator_factory()
        fold_model.fit(X.iloc[train_indices], y.iloc[train_indices])
        out_of_fold[calibration_indices] = fold_model.predict_proba(X.iloc[calibration_indices])[:, 1]
    calibrator = LogisticRegression(C=1.0, solver="liblinear", random_state=42)
    calibrator.fit(_logit_feature(out_of_fold), y)
    estimator = estimator_factory()
    estimator.fit(X, y)
    return {"estimator": estimator, "calibrator": calibrator}


def calibrated_predict_proba(bundle: dict[str, Any], X: pd.DataFrame) -> np.ndarray:
    raw = bundle["estimator"].predict_proba(X)[:, 1]
    if not bundle.get("use_calibrator", True):
        return raw
    return bundle["calibrator"].predict_proba(_logit_feature(raw))[:, 1]


def enforce_horizon_order(probabilities: dict[int, np.ndarray]) -> dict[int, np.ndarray]:
    ordered = np.vstack([probabilities[window] for window in WINDOWS]).T
    ordered = np.maximum.accumulate(ordered, axis=1)
    return {window: ordered[:, index] for index, window in enumerate(WINDOWS)}


def probability_metrics(y_true: np.ndarray, probabilities: np.ndarray, threshold: float) -> dict[str, Any]:
    from sklearn.metrics import (
        average_precision_score,
        brier_score_loss,
        f1_score,
        log_loss,
        precision_score,
        recall_score,
    )

    predictions = (probabilities >= threshold).astype(int)
    observed_rate = float(np.mean(y_true))
    brier = float(brier_score_loss(y_true, probabilities))
    baseline_brier = observed_rate * (1.0 - observed_rate)
    return {
        "pr_auc": _safe_metric(average_precision_score, y_true, probabilities),
        "brier_score": round(brier, 4),
        "brier_skill_score": round(1.0 - (brier / baseline_brier), 4) if baseline_brier else None,
        "log_loss": _safe_metric(log_loss, y_true, probabilities, labels=[0, 1]),
        "ece_5_bin": expected_calibration_error(y_true, probabilities, bins=5),
        "mean_predicted_probability": round(float(np.mean(probabilities)), 4),
        "observed_positive_rate": round(observed_rate, 4),
        "mean_probability_gap": round(float(np.mean(probabilities)) - observed_rate, 4),
        "precision": _safe_metric(precision_score, y_true, predictions, zero_division=0),
        "recall": _safe_metric(recall_score, y_true, predictions, zero_division=0),
        "f1": _safe_metric(f1_score, y_true, predictions, zero_division=0),
        "predicted_positive_count": int(predictions.sum()),
    }


def expected_calibration_error(y_true: np.ndarray, probabilities: np.ndarray, bins: int = 5) -> float:
    boundaries = np.linspace(0.0, 1.0, bins + 1)
    total = len(y_true)
    error = 0.0
    for index in range(bins):
        if index == bins - 1:
            mask = (probabilities >= boundaries[index]) & (probabilities <= boundaries[index + 1])
        else:
            mask = (probabilities >= boundaries[index]) & (probabilities < boundaries[index + 1])
        if mask.any():
            error += (mask.sum() / total) * abs(float(np.mean(y_true[mask])) - float(np.mean(probabilities[mask])))
    return round(error, 4)


def _logit_feature(probabilities: np.ndarray) -> np.ndarray:
    clipped = np.clip(probabilities, 1e-6, 1.0 - 1e-6)
    return np.log(clipped / (1.0 - clipped)).reshape(-1, 1)
