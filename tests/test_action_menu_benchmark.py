from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from midfielders_eye.action_menu_benchmark import (
    ACTION_MENU_MODEL_COLUMNS,
    run_action_menu_benchmark,
    verify_action_menu_benchmark,
)
from midfielders_eye.frozen_benchmark import FrozenBenchmarkConfig
from midfielders_eye.io import options_to_dataframe
from midfielders_eye.synthetic import build_bootstrap_options, generate_dataset


def _synthetic_options(path: Path) -> pd.DataFrame:
    frames = generate_dataset(sequences=6, frames=3, seed=31)
    dataframe = options_to_dataframe(build_bootstrap_options(frames))
    first_provider = {"synthetic_00", "synthetic_01", "synthetic_02"}
    dataframe["source_provider"] = dataframe["sequence_id"].map(
        lambda value: "provider_a" if value in first_provider else "provider_b"
    )
    dataframe["source_match_id"] = dataframe["sequence_id"].map(
        lambda value: f"match:{value}"
    )
    dataframe.to_csv(path, index=False)
    return dataframe


def test_action_menu_benchmark_exposes_five_model_ladder(tmp_path: Path) -> None:
    options_path = tmp_path / "options.csv"
    _synthetic_options(options_path)
    config = FrozenBenchmarkConfig(
        sequence_splits=3,
        bootstrap_iterations=5,
        allow_synthetic_software_validation=True,
    )

    manifest_path = run_action_menu_benchmark(
        options_path,
        tmp_path / "results",
        config=config,
    )

    assert verify_action_menu_benchmark(manifest_path) == []
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "action-menu-benchmark-v2"
    assert set(manifest["models"]) == set(ACTION_MENU_MODEL_COLUMNS)
    assert manifest["split_contract"]["identical_foundation_predictions_for_all_models"] is True

    metrics = pd.read_csv(manifest_path.parent / "action_menu_metrics.csv")
    aggregate = metrics[metrics["scope"] == "aggregate"]
    for protocol in config.protocols:
        models = set(
            aggregate.loc[
                aggregate["evaluation_protocol"] == protocol,
                "model",
            ]
        )
        assert models == set(ACTION_MENU_MODEL_COLUMNS)
    assert f"top_{config.k}_jaccard_stability" in metrics.columns


def test_b2_and_b2v_scores_are_distinct_in_foundation_predictions(tmp_path: Path) -> None:
    options_path = tmp_path / "options.csv"
    _synthetic_options(options_path)
    config = FrozenBenchmarkConfig(
        sequence_splits=2,
        bootstrap_iterations=2,
        allow_synthetic_software_validation=True,
    )

    manifest_path = run_action_menu_benchmark(
        options_path,
        tmp_path / "results",
        config=config,
    )
    predictions = pd.read_csv(
        manifest_path.parent / "foundation" / "predictions.csv"
    )

    assert predictions["dynamic_score"].notna().all()
    assert predictions["viewpoint_score"].notna().all()
    assert (
        predictions["dynamic_score"] != predictions["viewpoint_score"]
    ).any()
