from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import yaml
from sklearn.model_selection import GroupKFold

from .adapters.catalog import get_provider
from .dataset_shift import provider_shift_report
from .metrics import ndcg_at_k, pairwise_ranking_accuracy, recall_at_k
from .models import LearnedOptionModel, add_baseline_scores
from .pilot import (
    ITEM_COLUMNS,
    canonical_sha256,
    sha256_file,
    validate_candidate_generator_sources,
    validate_causal_feature_contract,
    validate_regenerated_candidates,
    verify_pilot_freeze,
)
from .provider_quality_review import verify_provider_quality_review

MODEL_COLUMNS = {
    "B0_naive": "naive_score",
    "B1_static": "static_score",
    "B2_dynamic": "geometric_score",
    "B3_learned": "learned_score",
}

DEFAULT_B3_FEATURES = (
    "distance_m",
    "lane_clearance_m",
    "interception_margin_s",
    "pressure_shadow",
    "receiver_pressure",
    "receiver_space",
    "future_space",
    "forward_progress",
    "xt_start",
    "xt_end",
    "xt_gain",
    "body_orientation",
    "visibility",
    "target_motion_alignment",
    "option_creation",
    "uncertainty_adjusted_clearance_m",
    "target_uncertainty_m",
    "defender_uncertainty_m",
    "visible_pitch_fraction",
    "state_confidence",
)


@dataclass(frozen=True)
class FrozenBenchmarkConfig:
    experiment_id: str = "midfielders-eye-b0-b3-v1"
    protocols: tuple[str, ...] = ("sequence_held_out", "provider_held_out")
    sequence_splits: int = 5
    target_column: str = "label_value"
    bootstrap_iterations: int = 1000
    random_seed: int = 7
    k: int = 3
    allow_synthetic_software_validation: bool = False
    dynamic_eligible_providers: tuple[str, ...] = ()
    b3_features: tuple[str, ...] = DEFAULT_B3_FEATURES


def _availability_binary(series: pd.Series) -> np.ndarray:
    def parse(value: Any) -> float:
        if pd.isna(value):
            return float("nan")
        if isinstance(value, (bool, np.bool_)):
            return float(bool(value))
        normalized = str(value).strip().casefold()
        if normalized in {"yes", "true", "1"}:
            return 1.0
        if normalized in {"no", "false", "0"}:
            return 0.0
        if normalized == "uncertain":
            return float("nan")
        raise ValueError(f"Unknown availability label: {value!r}")

    return np.asarray([parse(value) for value in series], dtype=float)


def evaluate_benchmark_rankings(
    dataframe: pd.DataFrame,
    score_column: str,
    *,
    value_column: str,
    k: int,
) -> dict[str, float]:
    """Evaluate only labels with a defined target; uncertainty remains missing, not negative."""

    frame_metrics: list[dict[str, float]] = []
    for _, group in dataframe.groupby(["sequence_id", "frame_id"], sort=False):
        scores = pd.to_numeric(group[score_column], errors="coerce").to_numpy(float)
        if not np.isfinite(scores).all():
            raise ValueError(f"{score_column} contains non-finite predictions")
        values = pd.to_numeric(group[value_column], errors="coerce").to_numpy(float)
        value_mask = np.isfinite(values)
        availability = _availability_binary(group["label_available"])
        availability_mask = np.isfinite(availability)
        metrics: dict[str, float] = {}
        metrics["ndcg"] = (
            ndcg_at_k(values[value_mask], scores[value_mask], k=k)
            if value_mask.any()
            else float("nan")
        )
        metrics["pairwise"] = (
            pairwise_ranking_accuracy(values[value_mask], scores[value_mask])
            if value_mask.any()
            else float("nan")
        )
        if not availability_mask.all():
            metrics["recall"] = float("nan")
            metrics["recall_null_uncertain"] = 1.0
        elif availability_mask.any():
            metrics["recall"] = recall_at_k(
                availability.astype(bool),
                scores,
                k=k,
            )
            metrics["recall_null_uncertain"] = 0.0
        else:
            metrics["recall"] = float("nan")
            metrics["recall_null_uncertain"] = 0.0
        frame_metrics.append(metrics)

    def mean(key: str) -> float:
        values = [row[key] for row in frame_metrics if np.isfinite(row[key])]
        return float(np.mean(values)) if values else float("nan")

    return {
        f"ndcg@{k}": mean("ndcg"),
        f"recall@{k}": mean("recall"),
        "pairwise": mean("pairwise"),
        "evaluated_frames": len(frame_metrics),
        "recall_evaluated_frames": sum(
            np.isfinite(row["recall"]) for row in frame_metrics
        ),
        "recall_null_uncertain_frames": int(
            sum(row["recall_null_uncertain"] for row in frame_metrics)
        ),
    }


def _validate_options(dataframe: pd.DataFrame, config: FrozenBenchmarkConfig) -> pd.DataFrame:
    required = {
        *ITEM_COLUMNS,
        "kind",
        "geometric_score",
        "label_available",
        config.target_column,
        "source_provider",
        *config.b3_features,
    }
    missing = sorted(required - set(dataframe.columns))
    if missing:
        raise ValueError(f"Benchmark options are missing columns: {missing}")
    if dataframe.empty:
        raise ValueError("Benchmark options are empty")
    if dataframe.duplicated(ITEM_COLUMNS).any():
        raise ValueError(
            "Benchmark input must contain one consensus/adjudicated row per option; "
            "raw multi-rater annotations belong in the reliability pipeline"
        )
    if dataframe[config.target_column].isna().any():
        raise ValueError("Every frozen benchmark option needs a tactical-value label")
    if not np.isfinite(
        pd.to_numeric(dataframe["geometric_score"], errors="coerce").to_numpy(float)
    ).all():
        raise ValueError("B2 geometric_score must be finite for every option")

    output = dataframe.copy()
    output["sequence_id"] = output["sequence_id"].astype(str)
    output["source_provider"] = output["source_provider"].astype(str)
    sequence_provider_counts = output.groupby("sequence_id")["source_provider"].nunique()
    if (sequence_provider_counts != 1).any():
        offenders = sequence_provider_counts[sequence_provider_counts != 1].index.tolist()
        raise ValueError(f"Each sequence must map to exactly one provider: {offenders}")
    if output["sequence_id"].nunique() < 2:
        raise ValueError("At least two possession sequences are required")

    provenance = output.get("provenance", pd.Series("", index=output.index)).astype(str)
    synthetic_mask = (
        output["source_provider"].str.casefold().eq("synthetic")
        | provenance.str.casefold().str.contains("synthetic|pseudo|bootstrap", regex=True)
    )
    if synthetic_mask.any() and not config.allow_synthetic_software_validation:
        raise ValueError(
            "Synthetic or pseudo-label rows cannot produce empirical benchmark claims. "
            "Enable allow_synthetic_software_validation only for software tests."
        )
    if not config.allow_synthetic_software_validation:
        invalid_provenance = ~provenance.str.casefold().str.startswith(
            ("human-annotation", "human-adjudication", "human-consensus")
        )
        if invalid_provenance.any():
            raise ValueError(
                "Empirical B0-B3 evaluation requires human annotation/adjudication provenance"
            )
    return output


def _provider_spec_evidence(
    dataframe: pd.DataFrame,
    config: FrozenBenchmarkConfig,
) -> list[dict[str, Any]]:
    if config.allow_synthetic_software_validation:
        return []
    eligible = set(config.dynamic_eligible_providers)
    observed = set(dataframe["source_provider"].unique())
    if not eligible:
        raise ValueError(
            "Empirical B0-B3 evaluation requires an explicit dynamic_eligible_providers "
            "allowlist from provider quality review"
        )
    unapproved = sorted(observed - eligible)
    if unapproved:
        raise ValueError(
            "Providers not explicitly approved for continuous dynamic evaluation: "
            f"{unapproved}"
        )
    evidence: list[dict[str, Any]] = []
    for provider_id in sorted(eligible):
        try:
            spec = get_provider(provider_id)
        except KeyError as exc:
            raise ValueError(
                f"Dynamic provider {provider_id!r} is absent from adapters.catalog"
            ) from exc
        if provider_id == "statsbomb360" or spec.coverage == "event_snapshot":
            raise ValueError(
                f"Event-snapshot provider {provider_id!r} is categorically prohibited from "
                "B0-B3 dynamic evaluation"
            )
        if not spec.capabilities.tracking or spec.coverage not in {
            "full_tracking",
            "partial_tracking",
        }:
            raise ValueError(
                f"Provider {provider_id!r} lacks catalog coverage for continuous dynamic "
                "evaluation"
            )
        evidence.append(
            {
                "provider_id": provider_id,
                "observed_in_benchmark": provider_id in observed,
                "coverage": spec.coverage,
                "native_rate_hz": spec.native_rate_hz,
                "tracking": spec.capabilities.tracking,
                "events": spec.capabilities.events,
                "ball_tracking": spec.capabilities.ball_tracking,
                "possession": spec.capabilities.possession,
                "full_pitch": spec.capabilities.full_pitch,
                "camera_visibility": spec.capabilities.camera_visibility,
                "limitations": list(spec.limitations),
                "catalog_evidence_sha256": canonical_sha256(spec.to_dict()),
            }
        )
    return evidence


def _sequence_folds(
    dataframe: pd.DataFrame,
    requested_splits: int,
) -> list[dict[str, Any]]:
    groups = dataframe["sequence_id"].astype(str)
    n_splits = min(requested_splits, groups.nunique())
    if n_splits < 2:
        raise ValueError("At least two sequence folds are required")
    splitter = GroupKFold(n_splits=n_splits)
    folds: list[dict[str, Any]] = []
    for fold, (train_index, test_index) in enumerate(
        splitter.split(dataframe, groups=groups), start=1
    ):
        train_sequences = sorted(dataframe.iloc[train_index]["sequence_id"].unique())
        test_sequences = sorted(dataframe.iloc[test_index]["sequence_id"].unique())
        folds.append(
            {
                "fold": fold,
                "train_indices": train_index,
                "test_indices": test_index,
                "train_sequences": train_sequences,
                "test_sequences": test_sequences,
                "held_out_provider": None,
            }
        )
    return folds


def _provider_folds(dataframe: pd.DataFrame) -> list[dict[str, Any]]:
    providers = sorted(dataframe["source_provider"].dropna().unique())
    if len(providers) < 2:
        raise ValueError("Provider-held-out evaluation requires at least two providers")
    folds: list[dict[str, Any]] = []
    for fold, provider in enumerate(providers, start=1):
        test_mask = dataframe["source_provider"] == provider
        train_indices = np.flatnonzero((~test_mask).to_numpy())
        test_indices = np.flatnonzero(test_mask.to_numpy())
        folds.append(
            {
                "fold": fold,
                "train_indices": train_indices,
                "test_indices": test_indices,
                "train_sequences": sorted(
                    dataframe.iloc[train_indices]["sequence_id"].unique()
                ),
                "test_sequences": sorted(
                    dataframe.iloc[test_indices]["sequence_id"].unique()
                ),
                "held_out_provider": provider,
            }
        )
    return folds


def _fit_b3(
    train: pd.DataFrame,
    test: pd.DataFrame,
    config: FrozenBenchmarkConfig,
    fold_seed: int,
) -> np.ndarray:
    columns = list(config.b3_features) + [config.target_column]
    model = LearnedOptionModel(random_state=fold_seed)
    model.fit(train[columns], target=config.target_column)
    return model.predict(test[list(config.b3_features)])


def _run_protocol(
    dataframe: pd.DataFrame,
    protocol: str,
    config: FrozenBenchmarkConfig,
) -> tuple[pd.DataFrame, list[dict[str, Any]], list[dict[str, Any]]]:
    if protocol == "sequence_held_out":
        folds = _sequence_folds(dataframe, config.sequence_splits)
    elif protocol == "provider_held_out":
        folds = _provider_folds(dataframe)
    else:
        raise ValueError(f"Unknown evaluation protocol: {protocol}")

    prediction_pieces: list[pd.DataFrame] = []
    metric_rows: list[dict[str, Any]] = []
    fold_manifest: list[dict[str, Any]] = []
    for fold in folds:
        train = dataframe.iloc[fold["train_indices"]].copy()
        test = dataframe.iloc[fold["test_indices"]].copy()
        leakage = set(train["sequence_id"]) & set(test["sequence_id"])
        if leakage:
            raise RuntimeError(f"Sequence leakage in {protocol} fold {fold['fold']}: {leakage}")
        test["learned_score"] = _fit_b3(
            train,
            test,
            config,
            config.random_seed + int(fold["fold"]),
        )
        test["evaluation_protocol"] = protocol
        test["fold"] = int(fold["fold"])
        test["held_out_provider"] = fold["held_out_provider"]
        prediction_pieces.append(test)

        for model, score_column in MODEL_COLUMNS.items():
            metric_rows.append(
                {
                    "evaluation_protocol": protocol,
                    "scope": "fold",
                    "fold": int(fold["fold"]),
                    "held_out_provider": fold["held_out_provider"],
                    "model": model,
                    **evaluate_benchmark_rankings(
                        test,
                        score_column,
                        value_column=config.target_column,
                        k=config.k,
                    ),
                }
            )
        fold_manifest.append(
            {
                "fold": int(fold["fold"]),
                "held_out_provider": fold["held_out_provider"],
                "train_sequences": fold["train_sequences"],
                "test_sequences": fold["test_sequences"],
                "train_rows": len(train),
                "test_rows": len(test),
                "sequence_overlap": [],
            }
        )

    predictions = pd.concat(prediction_pieces, ignore_index=True)
    if predictions[ITEM_COLUMNS].duplicated().any():
        raise RuntimeError(f"{protocol} did not evaluate each option exactly once")
    for model, score_column in MODEL_COLUMNS.items():
        metric_rows.append(
            {
                "evaluation_protocol": protocol,
                "scope": "aggregate",
                "fold": None,
                "held_out_provider": None,
                "model": model,
                **evaluate_benchmark_rankings(
                    predictions,
                    score_column,
                    value_column=config.target_column,
                    k=config.k,
                ),
            }
        )
    return predictions, metric_rows, fold_manifest


def _bootstrap_metrics(
    dataframe: pd.DataFrame,
    score_column: str,
    *,
    config: FrozenBenchmarkConfig,
    seed: int,
) -> dict[str, Any]:
    sequences = sorted(dataframe["sequence_id"].unique())
    if len(sequences) < 2:
        raise ValueError("At least two sequences are required for sequence bootstrap")
    point = evaluate_benchmark_rankings(
        dataframe,
        score_column,
        value_column=config.target_column,
        k=config.k,
    )
    metric_names = [f"ndcg@{config.k}", f"recall@{config.k}", "pairwise"]
    samples: dict[str, list[float]] = {metric: [] for metric in metric_names}
    rng = np.random.default_rng(seed)
    for _ in range(config.bootstrap_iterations):
        selected = rng.choice(sequences, size=len(sequences), replace=True)
        pieces: list[pd.DataFrame] = []
        for replicate, sequence_id in enumerate(selected):
            piece = dataframe[dataframe["sequence_id"] == sequence_id].copy()
            piece["sequence_id"] = f"bootstrap:{replicate}:{sequence_id}"
            pieces.append(piece)
        result = evaluate_benchmark_rankings(
            pd.concat(pieces, ignore_index=True),
            score_column,
            value_column=config.target_column,
            k=config.k,
        )
        for metric in metric_names:
            if np.isfinite(result[metric]):
                samples[metric].append(float(result[metric]))
    return {
        metric: {
            "point": point[metric] if np.isfinite(point[metric]) else None,
            "lower_95": (
                float(np.quantile(samples[metric], 0.025)) if samples[metric] else None
            ),
            "upper_95": (
                float(np.quantile(samples[metric], 0.975)) if samples[metric] else None
            ),
            "iterations": config.bootstrap_iterations,
            "valid_replicates": len(samples[metric]),
        }
        for metric in metric_names
    }


def _provider_quality(dataframe: pd.DataFrame, config: FrozenBenchmarkConfig) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for provider, group in dataframe.groupby("source_provider", sort=True):
        availability = _availability_binary(group["label_available"])
        known_availability = np.isfinite(availability)
        feature_missing = group[list(config.b3_features)].isna().mean()
        rows.append(
            {
                "source_provider": provider,
                "sequences": int(group["sequence_id"].nunique()),
                "matches": (
                    int(group["source_match_id"].dropna().nunique())
                    if "source_match_id" in group
                    else None
                ),
                "frames": int(
                    group[["sequence_id", "frame_id"]].drop_duplicates().shape[0]
                ),
                "options": len(group),
                "value_label_coverage": float(group[config.target_column].notna().mean()),
                "availability_label_coverage": float(known_availability.mean()),
                "availability_uncertain_fraction": float((~known_availability).mean()),
                "mean_state_confidence": (
                    float(group["state_confidence"].mean())
                    if "state_confidence" in group
                    else None
                ),
                "mean_feature_missing_fraction": float(feature_missing.mean()),
                "max_feature_missing_fraction": float(feature_missing.max()),
            }
        )
    return pd.DataFrame(rows)


def _contrasts(metrics: pd.DataFrame, k: int) -> dict[str, Any]:
    aggregate = metrics[metrics["scope"] == "aggregate"]
    rows: list[dict[str, Any]] = []
    for protocol, group in aggregate.groupby("evaluation_protocol", sort=True):
        indexed = group.set_index("model")
        for left, right in [
            ("B2_dynamic", "B1_static"),
            ("B3_learned", "B1_static"),
            ("B3_learned", "B2_dynamic"),
        ]:
            for metric in [f"ndcg@{k}", f"recall@{k}", "pairwise"]:
                delta_value = float(indexed.loc[left, metric] - indexed.loc[right, metric])
                delta = delta_value if np.isfinite(delta_value) else None
                rows.append(
                    {
                        "evaluation_protocol": protocol,
                        "model": left,
                        "reference": right,
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
            "Every prespecified contrast is retained. Negative or null effects are not filtered "
            "from reports or manifests."
        ),
        "all_contrasts": rows,
        "negative_or_null": [
            row for row in rows if row["outcome"] in {"negative_or_null", "not_estimable"}
        ],
    }


def _write_json(path: Path, payload: Any) -> None:
    def clean(value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): clean(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [clean(item) for item in value]
        if isinstance(value, (np.integer,)):
            return int(value)
        if isinstance(value, (np.floating,)):
            return None if not np.isfinite(value) else float(value)
        if isinstance(value, (np.bool_,)):
            return bool(value)
        if isinstance(value, float) and not np.isfinite(value):
            return None
        return value

    path.write_text(
        json.dumps(clean(payload), indent=2, allow_nan=False),
        encoding="utf-8",
    )


def _file_records(paths: Iterable[Path], root: Path) -> list[dict[str, Any]]:
    return [
        {
            "path": path.relative_to(root).as_posix(),
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
        }
        for path in sorted(paths)
    ]


def _resolve_record_path(record: dict[str, Any], manifest_path: Path) -> Path:
    path = Path(record["path"])
    if path.is_absolute():
        return path
    candidates = [path, manifest_path.parent / path]
    return next((candidate for candidate in candidates if candidate.exists()), path)


def _single_input(
    manifest: dict[str, Any],
    kind: str,
) -> dict[str, Any]:
    records = [record for record in manifest.get("inputs", []) if record.get("kind") == kind]
    if len(records) != 1:
        raise ValueError(f"Pilot freeze must contain exactly one {kind!r} input")
    return records[0]


def _validate_empirical_pilot_binding(
    *,
    pilot_freeze_path: Path,
    options_path: Path,
    config_source_path: Path,
    config: FrozenBenchmarkConfig,
) -> dict[str, Any]:
    failures = verify_pilot_freeze(pilot_freeze_path)
    if failures:
        raise ValueError(f"Pilot freeze verification failed: {failures}")
    manifest = json.loads(pilot_freeze_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "expert_annotations_frozen_reliability_established":
        raise ValueError(
            "Empirical benchmark requires pilot status "
            "'expert_annotations_frozen_reliability_established'"
        )
    bindings = manifest.get("evidence_bindings")
    if not isinstance(bindings, dict):
        raise ValueError("Established pilot freeze has no evidence_bindings")

    consensus_record = _single_input(manifest, "consensus_labels")
    candidate_record = _single_input(manifest, "action_candidates")
    frames_record = _single_input(manifest, "canonical_frames")
    config_record = _single_input(manifest, "benchmark_config")
    causal_record = _single_input(manifest, "causal_feature_contract")
    if sha256_file(options_path) != consensus_record["sha256"]:
        raise ValueError("Benchmark input is not the consensus file bound by the pilot freeze")
    if sha256_file(config_source_path) != config_record["sha256"]:
        raise ValueError("Benchmark config is not the config bound by the pilot freeze")
    if bindings.get("consensus_file_sha256") != consensus_record["sha256"]:
        raise ValueError("Pilot consensus binding is internally inconsistent")
    if bindings.get("candidate_file_sha256") != candidate_record["sha256"]:
        raise ValueError("Pilot candidate binding is internally inconsistent")
    if bindings.get("benchmark_config_file_sha256") != config_record["sha256"]:
        raise ValueError("Pilot benchmark-config binding is internally inconsistent")
    if bindings.get("causal_feature_contract_file_sha256") != causal_record["sha256"]:
        raise ValueError("Pilot causal-contract binding is internally inconsistent")

    raw_config = yaml.safe_load(config_source_path.read_text(encoding="utf-8")) or {}
    normalized_config = dict(raw_config)
    for key in ("protocols", "dynamic_eligible_providers", "b3_features"):
        if key in normalized_config:
            normalized_config[key] = tuple(normalized_config[key])
    source_config = FrozenBenchmarkConfig(**normalized_config)
    if canonical_sha256(asdict(source_config)) != canonical_sha256(asdict(config)):
        raise ValueError("In-memory benchmark config differs from the bound config file")

    candidate_path = _resolve_record_path(candidate_record, pilot_freeze_path)
    frames_path = _resolve_record_path(frames_record, pilot_freeze_path)
    causal_path = _resolve_record_path(causal_record, pilot_freeze_path)
    causal_payload = json.loads(causal_path.read_text(encoding="utf-8"))
    if causal_payload.get("benchmark_config_sha256") != config_record["sha256"]:
        raise ValueError("Causal feature contract does not bind the benchmark config")
    validated_features = validate_causal_feature_contract(
        causal_payload,
        candidate_sha256=candidate_record["sha256"],
        required_features=config.b3_features,
    )
    generator_sources = validate_candidate_generator_sources(causal_payload)
    if bindings.get("causal_feature_contract_content_sha256") != canonical_sha256(
        causal_payload
    ):
        raise ValueError("Pilot causal-contract content binding is inconsistent")
    if bindings.get("validated_causal_features") != validated_features:
        raise ValueError("Pilot causal feature validation does not reproduce")
    if bindings.get("candidate_generator_sources") != generator_sources:
        raise ValueError("Pilot candidate-generator dependency binding does not reproduce")
    if sha256_file(candidate_path) != candidate_record["sha256"]:
        raise ValueError("Frozen candidate input is missing or changed")
    candidates = pd.read_csv(candidate_path)
    candidate_lineage = validate_regenerated_candidates(
        frames_path=frames_path,
        candidates=candidates,
        causal_features=validated_features,
    )
    if canonical_sha256(bindings.get("candidate_lineage")) != canonical_sha256(
        candidate_lineage
    ):
        raise ValueError("Pilot candidate lineage does not reproduce")
    return {
        "pilot_freeze_path": pilot_freeze_path.as_posix(),
        "pilot_freeze_sha256": sha256_file(pilot_freeze_path),
        "pilot_freeze_content_sha256": manifest["freeze_content_sha256"],
        "candidate_path": candidate_path.as_posix(),
        "candidate_sha256": candidate_record["sha256"],
        "canonical_frames_sha256": frames_record["sha256"],
        "consensus_sha256": consensus_record["sha256"],
        "consensus_candidate_coverage": bindings["consensus_candidate_coverage"],
        "benchmark_config_sha256": config_record["sha256"],
        "causal_feature_contract_path": causal_path.as_posix(),
        "causal_feature_contract_sha256": causal_record["sha256"],
        "validated_causal_features": validated_features,
        "candidate_generator_sources": generator_sources,
        "candidate_lineage": candidate_lineage,
        "causality_validation_scope": (
            "Timing declarations and forbidden dependencies were contract-validated; "
            "causality was not inferred or empirically proven."
        ),
    }


def _validate_pre_evaluation_quality_review(
    *,
    quality_review_path: Path,
    pilot_freeze_path: Path,
    config_source_path: Path,
    dataframe: pd.DataFrame,
    empirical_binding: dict[str, Any],
) -> dict[str, Any]:
    failures = verify_provider_quality_review(quality_review_path)
    if failures:
        raise ValueError(f"Provider quality review verification failed: {failures}")
    payload = json.loads(quality_review_path.read_text(encoding="utf-8"))
    bindings = payload.get("bindings", {})
    if bindings.get("pilot_freeze_sha256") != sha256_file(pilot_freeze_path):
        raise ValueError("Provider quality review is bound to a different pilot freeze")
    if bindings.get("pilot_freeze_content_sha256") != empirical_binding[
        "pilot_freeze_content_sha256"
    ]:
        raise ValueError("Provider quality review pilot content binding is inconsistent")
    if bindings.get("candidate_sha256") != empirical_binding["candidate_sha256"]:
        raise ValueError("Provider quality review is bound to different candidates")
    if bindings.get("benchmark_config_sha256") != sha256_file(config_source_path):
        raise ValueError("Provider quality review is bound to a different benchmark config")
    provider_rows = {
        row["provider_id"]: row for row in payload.get("providers", [])
    }
    observed = set(dataframe["source_provider"].unique())
    missing = sorted(observed - set(provider_rows))
    if missing:
        raise ValueError(f"Provider quality review omits observed providers: {missing}")
    rejected = sorted(
        provider
        for provider in observed
        if not provider_rows[provider].get("accepted_for_dynamic_evaluation", False)
    )
    if rejected:
        raise ValueError(
            "Observed providers lack pre-evaluation quality approval: "
            f"{rejected}"
        )
    return {
        "path": quality_review_path.as_posix(),
        "sha256": sha256_file(quality_review_path),
        "manifest_content_sha256": payload["manifest_content_sha256"],
        "reviewer": payload["reviewer"],
        "thresholds": payload["thresholds"],
        "approved_providers": sorted(observed),
        "provider_decisions": [
            {
                "provider_id": provider,
                "explicit_decision": provider_rows[provider]["explicit_decision"],
                "accepted_for_dynamic_evaluation": provider_rows[provider][
                    "accepted_for_dynamic_evaluation"
                ],
                "rationale": provider_rows[provider]["rationale"],
                "thresholds_passed": provider_rows[provider]["thresholds_passed"],
                "capability_passed": provider_rows[provider]["capability_passed"],
            }
            for provider in sorted(observed)
        ],
    }


def run_frozen_benchmark(
    options_path: str | Path,
    output_dir: str | Path,
    *,
    config: FrozenBenchmarkConfig | None = None,
    pilot_freeze_path: str | Path | None = None,
    config_source_path: str | Path | None = None,
    provider_quality_review_path: str | Path | None = None,
) -> Path:
    """Run B0-B3 on identical frozen folds and emit a self-auditing result directory."""

    config = config or FrozenBenchmarkConfig()
    unsupported = set(config.protocols) - {"sequence_held_out", "provider_held_out"}
    if unsupported:
        raise ValueError(f"Unsupported protocols: {sorted(unsupported)}")
    options_file = Path(options_path)
    output = Path(output_dir)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Refusing to overwrite frozen benchmark directory: {output}")
    output.mkdir(parents=True, exist_ok=True)

    empirical_binding: dict[str, Any] | None = None
    if not config.allow_synthetic_software_validation:
        if (
            pilot_freeze_path is None
            or config_source_path is None
            or provider_quality_review_path is None
        ):
            raise ValueError(
                "Empirical benchmark requires pilot_freeze_path, config_source_path, and "
                "provider_quality_review_path"
            )
        empirical_binding = _validate_empirical_pilot_binding(
            pilot_freeze_path=Path(pilot_freeze_path),
            options_path=options_file,
            config_source_path=Path(config_source_path),
            config=config,
        )
    dataframe = _validate_options(pd.read_csv(options_file), config)
    provider_spec_evidence = _provider_spec_evidence(dataframe, config)
    provider_quality_approval: dict[str, Any] | None = None
    if empirical_binding is not None:
        assert pilot_freeze_path is not None
        assert config_source_path is not None
        assert provider_quality_review_path is not None
        provider_quality_approval = _validate_pre_evaluation_quality_review(
            quality_review_path=Path(provider_quality_review_path),
            pilot_freeze_path=Path(pilot_freeze_path),
            config_source_path=Path(config_source_path),
            dataframe=dataframe,
            empirical_binding=empirical_binding,
        )
    dataframe = add_baseline_scores(dataframe)
    all_predictions: list[pd.DataFrame] = []
    metric_rows: list[dict[str, Any]] = []
    folds_payload: dict[str, Any] = {}
    for protocol in config.protocols:
        predictions, rows, folds = _run_protocol(dataframe, protocol, config)
        all_predictions.append(predictions)
        metric_rows.extend(rows)
        folds_payload[protocol] = folds
    predictions = pd.concat(all_predictions, ignore_index=True)
    metrics = pd.DataFrame(metric_rows)

    intervals: dict[str, Any] = {}
    for protocol, protocol_rows in predictions.groupby("evaluation_protocol", sort=True):
        intervals[protocol] = {}
        for offset, (model, score_column) in enumerate(MODEL_COLUMNS.items()):
            intervals[protocol][model] = _bootstrap_metrics(
                protocol_rows,
                score_column,
                config=config,
                seed=config.random_seed + offset,
            )
    quality = _provider_quality(dataframe, config)
    shift = provider_shift_report(
        dataframe,
        feature_columns=list(config.b3_features),
    )
    negative_results = _contrasts(metrics, config.k)

    predictions_path = output / "predictions.csv"
    metrics_path = output / "metrics.csv"
    folds_path = output / "folds.json"
    intervals_path = output / "bootstrap_intervals.json"
    quality_path = output / "provider_quality.csv"
    shift_path = output / "provider_shift.csv"
    negative_path = output / "prespecified_contrasts.json"
    predictions.to_csv(predictions_path, index=False)
    metrics.to_csv(metrics_path, index=False)
    _write_json(folds_path, folds_payload)
    _write_json(intervals_path, intervals)
    quality.to_csv(quality_path, index=False)
    shift.to_csv(shift_path, index=False)
    _write_json(negative_path, negative_results)

    result_paths = [
        predictions_path,
        metrics_path,
        folds_path,
        intervals_path,
        quality_path,
        shift_path,
        negative_path,
    ]
    original_inputs = [
        {
            "kind": "benchmark_options",
            "path": options_file.as_posix(),
            "sha256": sha256_file(options_file),
        }
    ]
    if empirical_binding is not None:
        assert pilot_freeze_path is not None
        assert config_source_path is not None
        assert provider_quality_review_path is not None
        pilot_file = Path(pilot_freeze_path)
        config_file = Path(config_source_path)
        quality_review_file = Path(provider_quality_review_path)
        original_inputs.extend(
            [
                {
                    "kind": "pilot_freeze",
                    "path": pilot_file.as_posix(),
                    "sha256": sha256_file(pilot_file),
                },
                {
                    "kind": "benchmark_config",
                    "path": config_file.as_posix(),
                    "sha256": sha256_file(config_file),
                },
                {
                    "kind": "provider_quality_review",
                    "path": quality_review_file.as_posix(),
                    "sha256": sha256_file(quality_review_file),
                },
            ]
        )
    config_payload = asdict(config)
    synthetic = config.allow_synthetic_software_validation
    manifest = {
        "schema_version": "frozen-b0-b3-benchmark-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "experiment_id": config.experiment_id,
        "evidence_status": (
            "synthetic_software_validation_only"
            if synthetic
            else "empirical_human_annotated_evaluation"
        ),
        "input": {
            "path": options_file.as_posix(),
            "sha256": sha256_file(options_file),
            "bytes": options_file.stat().st_size,
            "rows": len(dataframe),
            "sequences": int(dataframe["sequence_id"].nunique()),
            "providers": sorted(dataframe["source_provider"].unique()),
        },
        "empirical_pilot_binding": empirical_binding,
        "config": config_payload,
        "config_sha256": canonical_sha256(config_payload),
        "models": {
            "B0_naive": {
                "description": "Pass distance only; carry forward progress only.",
                "learned": False,
            },
            "B1_static": {
                "description": (
                    "Static lane clearance, receiver pressure/space, progress, xT gain, distance; "
                    "no velocity, future-space, or viewpoint feature."
                ),
                "learned": False,
            },
            "B2_dynamic": {
                "description": (
                    "Frozen upstream geometric_score with dynamic and viewpoint-aware state "
                    "features; upstream feature timing must remain causal."
                ),
                "learned": False,
            },
            "B3_learned": {
                "description": "Small nonlinear tabular ranker over the explicit feature allowlist.",
                "learned": True,
                "train_only_preprocessing": True,
                "features": list(config.b3_features),
            },
        },
        "feature_timing": {
            "validation_scope": (
                "Contract-validated declarations only; causality is not inferred from names "
                "or results."
            ),
            "validated_features": (
                None
                if empirical_binding is None
                else empirical_binding["validated_causal_features"]
            ),
        },
        "split_contract": {
            "unit": "sequence_id",
            "identical_folds_for_all_models": True,
            "random_frame_split_permitted": False,
            "folds_path": folds_path.name,
        },
        "uncertainty_contract": {
            "bootstrap_unit": "sequence_id",
            "availability_uncertain_handling": (
                "Recall@k is null for any frame containing an uncertain availability label"
            ),
        },
        "provider_reports": {
            "pre_evaluation_approval": provider_quality_approval,
            "quality": quality_path.name,
            "distribution_shift": shift_path.name,
            "dynamic_eligible_providers": list(config.dynamic_eligible_providers),
            "catalog_spec_evidence": provider_spec_evidence,
        },
        "negative_result_policy": negative_results["policy"],
        "outputs": _file_records(result_paths, output),
        "original_inputs": original_inputs,
    }
    manifest["manifest_content_sha256"] = canonical_sha256(manifest)
    manifest_path = output / "benchmark_manifest.json"
    _write_json(manifest_path, manifest)
    file_manifest = {
        "schema_version": "file-manifest-v1",
        "files": _file_records([*result_paths, manifest_path], output),
    }
    file_manifest["manifest_content_sha256"] = canonical_sha256(file_manifest)
    _write_json(output / "FILE_MANIFEST.json", file_manifest)
    return manifest_path


def verify_frozen_benchmark(manifest_path: str | Path) -> list[str]:
    manifest_file = Path(manifest_path)
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    failures: list[str] = []
    expected = manifest.pop("manifest_content_sha256", None)
    actual = canonical_sha256(manifest)
    if actual != expected:
        failures.append(
            f"benchmark manifest hash mismatch: expected {expected}, got {actual}"
        )
    input_path = Path(manifest["input"]["path"])
    if not input_path.exists():
        failures.append(f"missing input: {input_path}")
    elif sha256_file(input_path) != manifest["input"]["sha256"]:
        failures.append(f"input hash mismatch: {input_path}")
    for record in manifest.get("original_inputs", []):
        path = Path(record["path"])
        if not path.exists():
            failures.append(f"missing original input: {record['kind']}:{path}")
        elif sha256_file(path) != record["sha256"]:
            failures.append(f"original input hash mismatch: {record['kind']}:{path}")
        elif record["kind"] == "pilot_freeze":
            failures.extend(
                f"pilot freeze dependency: {failure}"
                for failure in verify_pilot_freeze(path)
            )
        elif record["kind"] == "provider_quality_review":
            failures.extend(
                f"provider quality dependency: {failure}"
                for failure in verify_provider_quality_review(path)
            )
    for record in manifest.get("outputs", []):
        path = manifest_file.parent / record["path"]
        if not path.exists():
            failures.append(f"missing output: {record['path']}")
        elif sha256_file(path) != record["sha256"]:
            failures.append(f"output hash mismatch: {record['path']}")
    return failures
