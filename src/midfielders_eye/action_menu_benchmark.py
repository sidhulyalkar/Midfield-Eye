from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .action_menu import stable_option_key
from .frozen_benchmark import (
    FrozenBenchmarkConfig,
    evaluate_benchmark_rankings,
    run_frozen_benchmark,
    verify_frozen_benchmark,
)
from .pilot import canonical_sha256, sha256_file

ACTION_MENU_MODEL_COLUMNS = {
    "B0_naive": "naive_score",
    "B1_static": "static_score",
    "B2_dynamic": "dynamic_score",
    "B2-V_viewpoint": "viewpoint_score",
    "B3_learned": "learned_score",
}


def _write_json(path: Path, payload: Any) -> None:
    def clean(value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): clean(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [clean(item) for item in value]
        if isinstance(value, np.integer):
            return int(value)
        if isinstance(value, np.floating):
            return None if not np.isfinite(value) else float(value)
        if isinstance(value, np.bool_):
            return bool(value)
        if isinstance(value, float) and not np.isfinite(value):
            return None
        return value

    path.write_text(
        json.dumps(clean(payload), indent=2, allow_nan=False),
        encoding="utf-8",
    )


def _top_k_stability(
    dataframe: pd.DataFrame,
    score_column: str,
    *,
    k: int,
) -> dict[str, float | int | None]:
    values: list[float] = []
    transitions = 0
    for _, sequence in dataframe.groupby("sequence_id", sort=False):
        previous: set[str] | None = None
        for _, frame in sequence.groupby("frame_id", sort=True):
            ranked = frame.sort_values(score_column, ascending=False).head(k)
            current = {
                stable_option_key(row)
                for row in ranked.to_dict(orient="records")
            }
            if previous is not None:
                union = previous | current
                values.append(
                    len(previous & current) / len(union) if union else 1.0
                )
                transitions += 1
            previous = current
    return {
        f"top_{k}_jaccard_stability": (
            float(np.mean(values)) if values else None
        ),
        "stability_transitions": transitions,
    }


def _evaluate(
    dataframe: pd.DataFrame,
    score_column: str,
    *,
    config: FrozenBenchmarkConfig,
) -> dict[str, Any]:
    return {
        **evaluate_benchmark_rankings(
            dataframe,
            score_column,
            value_column=config.target_column,
            k=config.k,
        ),
        **_top_k_stability(dataframe, score_column, k=config.k),
    }


def _metrics_table(
    predictions: pd.DataFrame,
    config: FrozenBenchmarkConfig,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for protocol, protocol_rows in predictions.groupby(
        "evaluation_protocol",
        sort=True,
    ):
        for fold, fold_rows in protocol_rows.groupby("fold", sort=True):
            held_out = fold_rows["held_out_provider"].dropna().astype(str).unique()
            held_out_provider = held_out[0] if len(held_out) == 1 else None
            for model, score_column in ACTION_MENU_MODEL_COLUMNS.items():
                rows.append(
                    {
                        "evaluation_protocol": protocol,
                        "scope": "fold",
                        "fold": int(fold),
                        "held_out_provider": held_out_provider,
                        "model": model,
                        **_evaluate(fold_rows, score_column, config=config),
                    }
                )
        for model, score_column in ACTION_MENU_MODEL_COLUMNS.items():
            rows.append(
                {
                    "evaluation_protocol": protocol,
                    "scope": "aggregate",
                    "fold": None,
                    "held_out_provider": None,
                    "model": model,
                    **_evaluate(protocol_rows, score_column, config=config),
                }
            )
    return pd.DataFrame(rows)


def _bootstrap_intervals(
    predictions: pd.DataFrame,
    config: FrozenBenchmarkConfig,
) -> dict[str, Any]:
    metrics = [
        f"ndcg@{config.k}",
        f"recall@{config.k}",
        "pairwise",
        f"top_{config.k}_jaccard_stability",
    ]
    output: dict[str, Any] = {}
    for protocol_index, (protocol, protocol_rows) in enumerate(
        predictions.groupby("evaluation_protocol", sort=True)
    ):
        sequences = sorted(protocol_rows["sequence_id"].astype(str).unique())
        if len(sequences) < 2:
            raise ValueError("Action-menu bootstrap requires at least two sequences")
        output[protocol] = {}
        for model_index, (model, score_column) in enumerate(
            ACTION_MENU_MODEL_COLUMNS.items()
        ):
            point = _evaluate(protocol_rows, score_column, config=config)
            samples: dict[str, list[float]] = {metric: [] for metric in metrics}
            rng = np.random.default_rng(
                config.random_seed + protocol_index * 100 + model_index
            )
            for _ in range(config.bootstrap_iterations):
                selected = rng.choice(
                    sequences,
                    size=len(sequences),
                    replace=True,
                )
                pieces: list[pd.DataFrame] = []
                for replicate, sequence_id in enumerate(selected):
                    piece = protocol_rows[
                        protocol_rows["sequence_id"].astype(str) == sequence_id
                    ].copy()
                    piece["sequence_id"] = f"bootstrap:{replicate}:{sequence_id}"
                    pieces.append(piece)
                result = _evaluate(
                    pd.concat(pieces, ignore_index=True),
                    score_column,
                    config=config,
                )
                for metric in metrics:
                    value = result.get(metric)
                    if value is not None and np.isfinite(value):
                        samples[metric].append(float(value))
            output[protocol][model] = {
                metric: {
                    "point": (
                        float(point[metric])
                        if point.get(metric) is not None
                        and np.isfinite(point[metric])
                        else None
                    ),
                    "lower_95": (
                        float(np.quantile(samples[metric], 0.025))
                        if samples[metric]
                        else None
                    ),
                    "upper_95": (
                        float(np.quantile(samples[metric], 0.975))
                        if samples[metric]
                        else None
                    ),
                    "iterations": config.bootstrap_iterations,
                    "valid_replicates": len(samples[metric]),
                }
                for metric in metrics
            }
    return output


def _prespecified_contrasts(
    metrics: pd.DataFrame,
    *,
    k: int,
) -> dict[str, Any]:
    metric_names = [
        f"ndcg@{k}",
        f"recall@{k}",
        "pairwise",
        f"top_{k}_jaccard_stability",
    ]
    comparisons = [
        ("B2_dynamic", "B1_static"),
        ("B2-V_viewpoint", "B2_dynamic"),
        ("B3_learned", "B2-V_viewpoint"),
        ("B3_learned", "B1_static"),
    ]
    rows: list[dict[str, Any]] = []
    aggregate = metrics[metrics["scope"] == "aggregate"]
    for protocol, group in aggregate.groupby("evaluation_protocol", sort=True):
        indexed = group.set_index("model")
        for model, reference in comparisons:
            for metric in metric_names:
                left = indexed.loc[model, metric]
                right = indexed.loc[reference, metric]
                if pd.isna(left) or pd.isna(right):
                    delta = None
                else:
                    delta = float(left - right)
                rows.append(
                    {
                        "evaluation_protocol": protocol,
                        "model": model,
                        "reference": reference,
                        "metric": metric,
                        "delta": delta,
                        "outcome": (
                            "not_estimable"
                            if delta is None
                            else "positive"
                            if delta > 0
                            else "negative_or_null"
                        ),
                    }
                )
    return {
        "policy": (
            "All prespecified contrasts are retained, including negative, null, "
            "and non-estimable results."
        ),
        "all_contrasts": rows,
        "negative_or_null": [
            row
            for row in rows
            if row["outcome"] in {"negative_or_null", "not_estimable"}
        ],
    }


def run_action_menu_benchmark(
    options_path: str | Path,
    output_dir: str | Path,
    *,
    config: FrozenBenchmarkConfig | None = None,
    pilot_freeze_path: str | Path | None = None,
    config_source_path: str | Path | None = None,
    provider_quality_review_path: str | Path | None = None,
) -> Path:
    """Run the canonical v0.7 B0/B1/B2/B2-V/B3 benchmark.

    The existing frozen benchmark remains the validation foundation. v0.7 then
    recomputes the public model ladder from the exact same held-out predictions
    with B2 and B2-V kept scientifically distinct.
    """

    config = config or FrozenBenchmarkConfig()
    output = Path(output_dir)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(
            f"Refusing to overwrite action-menu benchmark directory: {output}"
        )
    output.mkdir(parents=True, exist_ok=True)
    foundation = output / "foundation"
    foundation_manifest = run_frozen_benchmark(
        options_path,
        foundation,
        config=config,
        pilot_freeze_path=pilot_freeze_path,
        config_source_path=config_source_path,
        provider_quality_review_path=provider_quality_review_path,
    )
    foundation_failures = verify_frozen_benchmark(foundation_manifest)
    if foundation_failures:
        raise RuntimeError(
            f"Foundation benchmark did not verify: {foundation_failures}"
        )

    predictions_path = foundation / "predictions.csv"
    predictions = pd.read_csv(predictions_path)
    missing_scores = sorted(
        set(ACTION_MENU_MODEL_COLUMNS.values()) - set(predictions.columns)
    )
    if missing_scores:
        raise ValueError(
            f"Foundation predictions lack v0.7 score columns: {missing_scores}"
        )

    metrics = _metrics_table(predictions, config)
    intervals = _bootstrap_intervals(predictions, config)
    contrasts = _prespecified_contrasts(metrics, k=config.k)

    metrics_path = output / "action_menu_metrics.csv"
    intervals_path = output / "action_menu_bootstrap_intervals.json"
    contrasts_path = output / "action_menu_contrasts.json"
    metrics.to_csv(metrics_path, index=False)
    _write_json(intervals_path, intervals)
    _write_json(contrasts_path, contrasts)

    outputs = [metrics_path, intervals_path, contrasts_path]
    manifest: dict[str, Any] = {
        "schema_version": "action-menu-benchmark-v2",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "experiment_id": f"{config.experiment_id}-action-menu-v2",
        "evidence_status": (
            "synthetic_software_validation_only"
            if config.allow_synthetic_software_validation
            else "empirical_human_annotated_evaluation"
        ),
        "config": asdict(config),
        "config_sha256": canonical_sha256(asdict(config)),
        "foundation": {
            "manifest": foundation_manifest.relative_to(output).as_posix(),
            "manifest_sha256": sha256_file(foundation_manifest),
            "verification_failures": [],
            "prediction_path": predictions_path.relative_to(output).as_posix(),
            "prediction_sha256": sha256_file(predictions_path),
        },
        "models": {
            "B0_naive": {
                "score_column": "naive_score",
                "description": "Pass distance only; carry forward progress only.",
            },
            "B1_static": {
                "score_column": "static_score",
                "description": "Static lane, local pressure/space, progress, xT, and distance.",
            },
            "B2_dynamic": {
                "score_column": "dynamic_score",
                "description": (
                    "Dynamic geometry with interception timing, future space, "
                    "option creation, uncertainty-adjusted clearance, and state confidence; "
                    "body orientation and player-view proxy are excluded."
                ),
            },
            "B2-V_viewpoint": {
                "score_column": "viewpoint_score",
                "description": (
                    "The exact B2 dynamic score plus carrier body orientation and "
                    "perceptual-visibility proxy. Proxy evidence is never renamed as literal gaze."
                ),
            },
            "B3_learned": {
                "score_column": "learned_score",
                "description": "Nonlinear tabular ranker trained only inside each held-out fold.",
                "features": list(config.b3_features),
            },
        },
        "split_contract": {
            "identical_foundation_predictions_for_all_models": True,
            "random_frame_split_permitted": False,
            "statistical_unit": "sequence_id",
        },
        "stability_contract": {
            "metric": f"top_{config.k}_jaccard_stability",
            "identity": "stable candidate action identity",
            "interpretation": (
                "Adjacent observed-frame ranking stability; not a future-aware feature."
            ),
        },
        "negative_result_policy": contrasts["policy"],
        "outputs": [
            {
                "path": path.relative_to(output).as_posix(),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
            for path in outputs
        ],
    }
    manifest["manifest_content_sha256"] = canonical_sha256(manifest)
    manifest_path = output / "action_menu_benchmark_manifest.json"
    _write_json(manifest_path, manifest)
    return manifest_path


def verify_action_menu_benchmark(
    manifest_path: str | Path,
) -> list[str]:
    manifest_file = Path(manifest_path)
    payload = json.loads(manifest_file.read_text(encoding="utf-8"))
    failures: list[str] = []
    expected = payload.pop("manifest_content_sha256", None)
    actual = canonical_sha256(payload)
    if expected != actual:
        failures.append(
            f"action-menu manifest hash mismatch: expected {expected}, got {actual}"
        )

    foundation_path = manifest_file.parent / payload["foundation"]["manifest"]
    if not foundation_path.exists():
        failures.append(f"missing foundation manifest: {foundation_path}")
    else:
        if sha256_file(foundation_path) != payload["foundation"]["manifest_sha256"]:
            failures.append("foundation manifest hash mismatch")
        failures.extend(
            f"foundation: {failure}"
            for failure in verify_frozen_benchmark(foundation_path)
        )

    prediction_path = manifest_file.parent / payload["foundation"]["prediction_path"]
    if not prediction_path.exists():
        failures.append(f"missing foundation predictions: {prediction_path}")
    elif sha256_file(prediction_path) != payload["foundation"]["prediction_sha256"]:
        failures.append("foundation prediction hash mismatch")

    for record in payload.get("outputs", []):
        path = manifest_file.parent / record["path"]
        if not path.exists():
            failures.append(f"missing output: {record['path']}")
        elif sha256_file(path) != record["sha256"]:
            failures.append(f"output hash mismatch: {record['path']}")
    return failures
