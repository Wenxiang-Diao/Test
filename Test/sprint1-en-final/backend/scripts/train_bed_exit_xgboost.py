from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.analytics.bed_exit_xgboost import (  # noqa: E402
    build_supervised_dataset,
    split_train_validation,
    summarise_split,
    train_xgboost_models,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train XGBoost bed-exit prediction models.")
    parser.add_argument(
        "--input-dir",
        default=str(ROOT.parent.parent / "data_conversion_cleaning" / "output"),
        help="Directory containing cleaned JLSP01 CSV files.",
    )
    parser.add_argument(
        "--model-dir",
        default=str(ROOT / "artifacts" / "bed_exit_xgboost"),
        help="Directory where trained XGBoost models and reports are written.",
    )
    parser.add_argument(
        "--validation-start",
        default="2026-06-03",
        help="Timestamp/date where validation split starts.",
    )
    args = parser.parse_args()

    dataset = build_supervised_dataset(args.input_dir)
    model_dir = Path(args.model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)

    dataset_path = model_dir / "supervised_bed_exit_dataset.csv"
    dataset.to_csv(dataset_path, index=False)

    train, validation = split_train_validation(dataset, args.validation_start)
    split_report = {
        "dataset_path": str(dataset_path),
        "total_samples": int(len(dataset)),
        "validation_start": args.validation_start,
        "train": summarise_split("train", train).__dict__,
        "validation": summarise_split("validation", validation).__dict__,
    }

    with (model_dir / "split_report.json").open("w", encoding="utf-8") as fh:
        json.dump(split_report, fh, indent=2)

    training_report = train_xgboost_models(train, validation, model_dir)
    print(json.dumps({"split_report": split_report, "training_report": training_report}, indent=2))


if __name__ == "__main__":
    main()
