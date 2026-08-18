from __future__ import annotations

import json
from dataclasses import fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import pandas as pd
import yaml

from .action_menu_benchmark import run_action_menu_benchmark
from .affordance import AffordanceEngine
from .frozen_benchmark import FrozenBenchmarkConfig
from .pilot import (
    build_adjudication_queue,
    build_consensus_labels,
    candidate_generator_source_records,
    freeze_pilot,
    load_annotations,
    sha256_file,
    validate_causal_feature_contract,
    verify_pilot_freeze,
)
from .provider_quality_review import build_provider_quality_review
from .reliability import ReliabilityGate, reliability_report

FORECAST_FEATURES = {
    "interception_margin_s",
    "future_space",
    "option_creation",
}
CAUSAL_HISTORY_FEATURES = {"target_motion_alignment"}


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")
    return path


def _resolve_r1_path(root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.exists():
        return path
    candidate = root / path.name
    if candidate.exists():
        return candidate
    return path


def load_benchmark_config(path: str | Path) -> FrozenBenchmarkConfig:
    source = Path(path)
    payload = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    tuple_fields = {"protocols", "dynamic_eligible_providers", "b3_features"}
    allowed = {field.name for field in fields(FrozenBenchmarkConfig)}
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise ValueError(f"Unknown benchmark config fields: {unknown}")
    for key in tuple_fields:
        if key in payload:
            payload[key] = tuple(payload[key])
    config = FrozenBenchmarkConfig(**payload)
    if "provider_held_out" in config.protocols:
        raise ValueError(
            "R1 Tier A must remain sequence-held-out only; provider-held-out belongs to R2 replication."
        )
    if "sequence_held_out" not in config.protocols:
        raise ValueError("R1 benchmark must include sequence_held_out evaluation")
    return config


def write_causal_contract(
    candidates_path: str | Path,
    benchmark_config_path: str | Path,
    output_path: str | Path,
    *,
    reviewed_by: str,
) -> Path:
    """Write the same explicit timing contract used by the frozen benchmark runbook."""

    candidates_path = Path(candidates_path)
    benchmark_config_path = Path(benchmark_config_path)
    output_path = Path(output_path)
    if output_path.exists():
        raise FileExistsError(f"Refusing to overwrite causal contract: {output_path}")
    if not reviewed_by.strip():
        raise ValueError("R1 causal contract requires a non-empty reviewer")
    candidates = pd.read_csv(candidates_path)
    config = yaml.safe_load(benchmark_config_path.read_text(encoding="utf-8")) or {}
    b3_features = list(config.get("b3_features", []))
    required_features = sorted(set(b3_features) | set(AffordanceEngine.feature_names))
    missing = sorted({"geometric_score", *required_features} - set(candidates.columns))
    if missing:
        raise ValueError(f"Candidate table is missing contract features: {missing}")

    features: dict[str, dict[str, Any]] = {}
    for feature in required_features:
        if feature in FORECAST_FEATURES:
            timing = "forecast_from_focal_state"
            justification = (
                "Forecast from the frozen focal state and causal kinematics; no later observed "
                "frame is read."
            )
        elif feature in CAUSAL_HISTORY_FEATURES:
            timing = "causal_history"
            justification = (
                "Uses focal state plus derivatives estimated only from timestamps at or before "
                "the focal frame."
            )
        else:
            timing = "focal_frame"
            justification = "Computed entirely from the frozen focal-frame state."
        features[feature] = {
            "timing": timing,
            "dependencies": [],
            "justification": justification,
        }
    features["geometric_score"] = {
        "timing": "derived_from_declared_causal_features",
        "dependencies": list(AffordanceEngine.feature_names),
        "justification": (
            "Frozen upstream score composed only from features declared in this contract."
        ),
    }
    payload = {
        "schema_version": "causal-feature-contract-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "reviewed_by": reviewed_by.strip(),
        "candidate_path": candidates_path.as_posix(),
        "candidate_sha256": sha256_file(candidates_path),
        "benchmark_config_path": benchmark_config_path.as_posix(),
        "benchmark_config_sha256": sha256_file(benchmark_config_path),
        "causality_scope": (
            "Contract validation only. This declaration does not empirically prove causality."
        ),
        "generator_sources": candidate_generator_source_records(),
        "features": features,
    }
    validate_causal_feature_contract(
        payload,
        candidate_sha256=payload["candidate_sha256"],
        required_features=b3_features,
    )
    return _write_json(output_path, payload)


def finalize_r1_pilot(
    r1_dir: str | Path,
    annotation_paths: Sequence[str | Path],
    *,
    reviewed_by: str,
    adjudication_path: str | Path | None = None,
    benchmark_config_path: str | Path = "configs/r1_benchmark.yaml",
    provider_review_config_path: str | Path | None = None,
    bootstrap_iterations: int = 1000,
    seed: int = 17,
    run_benchmark: bool = True,
) -> Path:
    """Advance R1 only as far as the available human evidence permits.

    Every invocation writes ``r1_finalization_status.json``. A scientifically
    incomplete state is a successful *artifact*, not a benchmark success. The
    benchmark is launched only after reliability, adjudication, expert freeze,
    causal timing, and provider-quality review all pass.
    """

    root = Path(r1_dir)
    manifest_path = root / "r1_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("stage") != "sample_frozen":
        raise ValueError(
            "R1 finalization requires a human-reviewed sample_frozen manifest"
        )
    if not reviewed_by.strip():
        raise ValueError("R1 finalization requires a non-empty reviewer")
    if len(annotation_paths) < 2:
        raise ValueError("R1 finalization requires at least two expert annotation files")

    candidates_path = _resolve_r1_path(root, manifest["paths"]["candidates"])
    frames_path = _resolve_r1_path(root, manifest["paths"]["label_frames"])
    candidates = pd.read_csv(candidates_path)
    imported = load_annotations(
        annotation_paths,
        candidates=candidates,
        require_genuine_human=True,
    )
    target_sequences = int(manifest["config"]["target_sequences"])
    full_double = bool(manifest["config"]["require_full_double_rating"])
    gate = ReliabilityGate(
        min_genuine_raters=2,
        min_sequences=target_sequences,
        min_overlap_frame_fraction=1.0 if full_double else 0.25,
        min_overlap_items=20,
        min_availability_alpha=0.60,
        min_candidate_coverage=1.0,
    )
    reliability = reliability_report(
        imported.dataframe,
        candidates=candidates,
        gate=gate,
        bootstrap_iterations=bootstrap_iterations,
        seed=seed,
    )
    reliability["annotation_import"] = imported.report.to_dict()
    reliability["annotation_inputs"] = [
        {"path": str(Path(path)), "sha256": sha256_file(path)}
        for path in annotation_paths
    ]
    reliability["candidate_input"] = {
        "path": str(candidates_path),
        "sha256": sha256_file(candidates_path),
    }
    reliability_path = _write_json(root / "reliability_report.json", reliability)

    genuine = imported.dataframe[imported.dataframe["is_genuine_human"]].copy()
    queue = build_adjudication_queue(genuine)
    queue_path = root / "adjudication_queue.csv"
    queue.to_csv(queue_path, index=False)
    base_status: dict[str, Any] = {
        "schema_version": "r1-finalization-status-v1",
        "reviewed_by": reviewed_by.strip(),
        "reliability": {
            "established": bool(reliability["established"]),
            "status": reliability["status"],
            "availability_alpha": (
                None
                if reliability.get("agreement") is None
                else reliability["agreement"]["availability"]["alpha"]
            ),
            "report": str(reliability_path),
        },
        "adjudication": {
            "disagreement_items": int(len(queue)),
            "queue": str(queue_path),
        },
        "benchmark": {"complete": False, "path": None},
        "claim_state": "no_empirical_model_claim_yet",
    }
    if not reliability["established"]:
        base_status["stage"] = "reliability_not_established"
        base_status["reasons"] = reliability.get("reasons", [])
        return _write_json(root / "r1_finalization_status.json", base_status)

    decisions: pd.DataFrame | None = None
    adjudication_file: Path | None = None
    if not queue.empty:
        if adjudication_path is None:
            base_status["stage"] = "needs_adjudication"
            base_status["reasons"] = [
                f"{len(queue)} expert disagreements require explicit adjudication."
            ]
            return _write_json(root / "r1_finalization_status.json", base_status)
        adjudication_file = Path(adjudication_path)
        decisions = pd.read_csv(adjudication_file)
    consensus = build_consensus_labels(
        genuine,
        candidates,
        decisions,
        min_candidate_coverage=1.0,
    )
    consensus_path = root / "consensus_labels.csv"
    consensus.to_csv(consensus_path, index=False)

    benchmark_config_path = Path(benchmark_config_path)
    benchmark_config = load_benchmark_config(benchmark_config_path)
    observed_providers = set(consensus["source_provider"].dropna().astype(str))
    unapproved = observed_providers - set(benchmark_config.dynamic_eligible_providers)
    if unapproved:
        raise ValueError(
            "R1 benchmark dynamic provider allowlist does not cover the frozen sample: "
            f"{sorted(unapproved)}"
        )
    causal_path = write_causal_contract(
        candidates_path,
        benchmark_config_path,
        root / "causal_feature_contract.json",
        reviewed_by=reviewed_by,
    )
    expert_freeze_path = root / "pilot_expert_freeze.json"
    freeze_pilot(
        frames_path=frames_path,
        candidates_path=candidates_path,
        annotation_paths=annotation_paths,
        protocol_path="docs/ANNOTATION_GUIDE.md",
        reliability_report_path=reliability_path,
        adjudication_path=adjudication_file,
        consensus_path=consensus_path,
        causal_feature_contract_path=causal_path,
        benchmark_config_path=benchmark_config_path,
        output_path=expert_freeze_path,
    )
    freeze_failures = verify_pilot_freeze(expert_freeze_path)
    if freeze_failures:
        raise ValueError(f"R1 expert freeze verification failed: {freeze_failures}")

    base_status["expert_freeze"] = str(expert_freeze_path)
    base_status["consensus"] = str(consensus_path)
    base_status["causal_feature_contract"] = str(causal_path)
    if provider_review_config_path is None:
        base_status["stage"] = "expert_pilot_frozen_needs_provider_review"
        base_status["reasons"] = [
            "Expert labels are frozen, but the provider-quality reviewer has not signed an accept/reject decision."
        ]
        return _write_json(root / "r1_finalization_status.json", base_status)

    quality_review_path = build_provider_quality_review(
        pilot_freeze_path=expert_freeze_path,
        benchmark_config_path=benchmark_config_path,
        review_config_path=provider_review_config_path,
        reviewer=reviewed_by,
        output_path=root / "provider_quality_review.json",
    )
    base_status["provider_quality_review"] = str(quality_review_path)
    if not run_benchmark:
        base_status["stage"] = "benchmark_ready"
        return _write_json(root / "r1_finalization_status.json", base_status)

    benchmark_dir = root / "benchmark"
    benchmark_manifest = run_action_menu_benchmark(
        consensus_path,
        benchmark_dir,
        config=benchmark_config,
        pilot_freeze_path=expert_freeze_path,
        config_source_path=benchmark_config_path,
        provider_quality_review_path=quality_review_path,
    )
    base_status["stage"] = "benchmark_complete"
    base_status["claim_state"] = "empirical_benchmark_complete"
    base_status["benchmark"] = {
        "complete": True,
        "path": str(benchmark_manifest),
        "metrics": str(benchmark_dir / "metrics.csv"),
        "bootstrap_intervals": str(benchmark_dir / "bootstrap_intervals.json"),
        "prespecified_contrasts": str(benchmark_dir / "prespecified_contrasts.json"),
    }
    return _write_json(root / "r1_finalization_status.json", base_status)
