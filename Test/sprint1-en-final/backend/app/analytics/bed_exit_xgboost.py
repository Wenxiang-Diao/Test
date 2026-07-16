from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


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
]


@dataclass(frozen=True)
class SplitSummary:
    name: str
    samples: int
    positives: dict[int, int]
    negatives: dict[int, int]
    scale_pos_weight: dict[int, float | None]


def risk_level(probability: float) -> str:
    if probability >= 0.65:
        return "High"
    if probability >= 0.35:
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

    from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score

    model_path = Path(model_dir)
    model_path.mkdir(parents=True, exist_ok=True)

    X_train = train[BASE_FEATURES]
    X_val = validation[BASE_FEATURES]
    report: dict[str, Any] = {
        "feature_columns": BASE_FEATURES,
        "train": summarise_split("train", train).__dict__,
        "validation": summarise_split("validation", validation).__dict__,
        "models": {},
    }
    validation_predictions = validation[["resident_id", "timestamp"]].copy()

    for window in WINDOWS:
        y_train = train[f"y_{window}"]
        y_val = validation[f"y_{window}"]
        pos = int(y_train.sum())
        neg = int(len(y_train) - pos)
        if pos == 0:
            raise ValueError(f"Cannot train {window} minute model because train positives are zero")

        model = XGBClassifier(
            objective="binary:logistic",
            eval_metric="aucpr",
            max_depth=2,
            learning_rate=0.05,
            n_estimators=120,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=neg / pos,
            random_state=42,
        )
        model.fit(X_train, y_train)
        probabilities = model.predict_proba(X_val)[:, 1]
        predictions = (probabilities >= 0.35).astype(int)
        y_val_array = y_val.to_numpy()
        true_positive = int(((predictions == 1) & (y_val_array == 1)).sum())
        false_positive = int(((predictions == 1) & (y_val_array == 0)).sum())
        true_negative = int(((predictions == 0) & (y_val_array == 0)).sum())
        false_negative = int(((predictions == 0) & (y_val_array == 1)).sum())
        validation_predictions[f"probability_{window}"] = np.round(probabilities, 4)
        validation_predictions[f"risk_level_{window}"] = [risk_level(float(p)) for p in probabilities]
        validation_predictions[f"predicted_{window}_at_0_35"] = predictions
        validation_predictions[f"actual_{window}"] = y_val_array
        report["models"][str(window)] = {
            "positive_count": pos,
            "negative_count": neg,
            "scale_pos_weight": round(neg / pos, 4),
            "validation_pr_auc": _safe_metric(average_precision_score, y_val, probabilities),
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
        model.save_model(model_path / f"bed_exit_xgb_{window}.json")

    validation_predictions.to_csv(model_path / "validation_predictions.csv", index=False)
    with (model_path / "training_report.json").open("w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    return report


def predict_with_models(feature_row: pd.DataFrame, model_dir: str | Path) -> dict[str, Any]:
    try:
        from xgboost import XGBClassifier
    except ImportError as exc:
        raise RuntimeError("xgboost is not installed. Install backend requirements before prediction.") from exc

    X = feature_row[BASE_FEATURES]
    windows = []
    for window in WINDOWS:
        model = XGBClassifier()
        model.load_model(Path(model_dir) / f"bed_exit_xgb_{window}.json")
        probability = float(model.predict_proba(X)[:, 1][0])
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
        "model_version": "xgboost_bed_exit_v1",
    }


def build_explanation(row: pd.Series) -> str:
    reasons: list[str] = []
    if row.get("movement_slope_10m", 0) > 0:
        reasons.append("recent movement increased")
    if row.get("sleep_status_AWAKE", 0) == 1:
        reasons.append("sleep status is awake")
    if row.get("heart_rate_delta_from_daily_avg", 0) > 5:
        reasons.append("heart rate is above the resident's recent average")
    if row.get("breathing_rate_delta_from_daily_avg", 0) > 2:
        reasons.append("breathing rate is above the resident's recent average")
    if row.get("is_common_exit_period", 0) == 1:
        reasons.append("the time is close to observed bed-exit periods")
    if row.get("bed_exit_count_so_far", 0) > 0:
        reasons.append("the resident has already left bed earlier tonight")
    if not reasons:
        reasons.append("no strong pre-exit signal was detected")
    return "Risk is based on " + ", ".join(reasons[:3]) + "."


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
    df = df.copy()
    if summary.empty:
        df["daily_avg_heart_rate"] = df["heart_rate_bpm"].mean()
        df["daily_avg_breathing_rate"] = df["breathing_rate_per_min"].mean()
    else:
        summary = summary.copy()
        summary["summary_date"] = summary["date"].dt.date
        df["summary_date"] = df["timestamp"].dt.date
        df = df.merge(
            summary[["summary_date", "avg_heart_rate", "avg_breathing_rate"]],
            on="summary_date",
            how="left",
        )
        df["daily_avg_heart_rate"] = df["avg_heart_rate"].fillna(df["heart_rate_bpm"].mean())
        df["daily_avg_breathing_rate"] = df["avg_breathing_rate"].fillna(df["breathing_rate_per_min"].mean())
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
