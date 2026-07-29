from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from .adapters.catalog import get_provider
from .io import read_frames_jsonl
from .pilot import canonical_sha256, sha256_file, verify_pilot_freeze
from .quality import assess_frames

QUALITY_REVIEW_SCHEMA = "provider-quality-review-v1"
QUALITY_CONFIG_SCHEMA = "provider-quality-review-config-v1"
QUALITY_POLICY_SCHEMA = "provider-quality-policy-v1"
APPROVED_QUALITY_POLICY_PATH = (
    Path(__file__).resolve().parents[2] / "configs" / "provider_quality_policy_v1.yaml"
)
THRESHOLD_KEYS = {
    "min_mean_players_per_frame",
    "max_p95_carrier_ball_distance_m",
    "min_observed_player_fraction",
    "max_extrapolated_player_fraction",
    "max_causal_feature_missing_fraction",
    "min_candidate_frame_coverage",
}


def _single_input(manifest: dict[str, Any], kind: str) -> dict[str, Any]:
    records = [record for record in manifest.get("inputs", []) if record.get("kind") == kind]
    if len(records) != 1:
        raise ValueError(f"Pilot freeze must contain exactly one {kind!r} input")
    return records[0]


def _resolve_input(record: dict[str, Any], manifest_path: Path) -> Path:
    path = Path(record["path"])
    if path.is_absolute():
        return path
    choices = [path, manifest_path.parent / path]
    return next((choice for choice in choices if choice.exists()), path)


def _threshold_result(
    *,
    name: str,
    observed: float | None,
    threshold: float,
) -> dict[str, Any]:
    if name.startswith("min_"):
        passed = observed is not None and observed >= threshold
        operator = ">="
    elif name.startswith("max_"):
        passed = observed is not None and observed <= threshold
        operator = "<="
    else:  # pragma: no cover - protected by config validation
        raise ValueError(f"Unknown threshold direction: {name}")
    return {
        "metric": name,
        "observed": observed,
        "operator": operator,
        "threshold": threshold,
        "passed": bool(passed),
    }


def _load_approved_policy() -> dict[str, Any]:
    payload = yaml.safe_load(
        APPROVED_QUALITY_POLICY_PATH.read_text(encoding="utf-8")
    ) or {}
    if payload.get("schema_version") != QUALITY_POLICY_SCHEMA:
        raise ValueError("Repository provider-quality policy has an unsupported schema_version")
    if not str(payload.get("policy_id", "")).strip():
        raise ValueError("Repository provider-quality policy needs a non-empty policy_id")
    bounds = payload.get("threshold_bounds")
    if not isinstance(bounds, dict) or set(bounds) != THRESHOLD_KEYS:
        raise ValueError(
            "Repository provider-quality policy must define exactly the approved thresholds"
        )
    for name, declaration in bounds.items():
        if not isinstance(declaration, dict):
            raise ValueError(f"Repository quality-policy bound for {name!r} must be a mapping")
        expected_key = "floor" if name.startswith("min_") else "ceiling"
        if set(declaration) != {expected_key}:
            raise ValueError(
                f"Repository quality-policy bound for {name!r} must use {expected_key!r}"
            )
        if not np.isfinite(float(declaration[expected_key])):
            raise ValueError(f"Repository quality-policy bound for {name!r} is not finite")
    return payload


def _load_review_config(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if payload.get("schema_version") != QUALITY_CONFIG_SCHEMA:
        raise ValueError("Provider quality config has an unsupported schema_version")
    thresholds = payload.get("thresholds")
    if not isinstance(thresholds, dict) or set(thresholds) != THRESHOLD_KEYS:
        raise ValueError(
            f"Provider quality thresholds must be exactly {sorted(THRESHOLD_KEYS)}"
        )
    for name, value in thresholds.items():
        numeric = float(value)
        if not np.isfinite(numeric):
            raise ValueError(f"Provider quality threshold {name!r} is not finite")
    policy = _load_approved_policy()
    for name, declaration in policy["threshold_bounds"].items():
        configured = float(thresholds[name])
        if name.startswith("min_"):
            floor = float(declaration["floor"])
            if configured < floor:
                raise ValueError(
                    f"Provider quality threshold {name!r}={configured} is weaker than "
                    f"repository policy floor {floor}"
                )
        else:
            ceiling = float(declaration["ceiling"])
            if configured > ceiling:
                raise ValueError(
                    f"Provider quality threshold {name!r}={configured} is weaker than "
                    f"repository policy ceiling {ceiling}"
                )
    decisions = payload.get("providers")
    if not isinstance(decisions, dict):
        raise ValueError("Provider quality config needs a providers mapping")
    return payload


def validate_provider_quality_review_config(path: str | Path) -> dict[str, Any]:
    """Validate a run config against the immutable repository policy bounds."""

    return _load_review_config(Path(path))


def _compute_provider_rows(
    *,
    frames_path: Path,
    candidates_path: Path,
    benchmark_config_path: Path,
    review_config_path: Path,
    reviewer: str,
    causal_features: list[str],
) -> tuple[list[dict[str, Any]], dict[str, float]]:
    if not reviewer.strip():
        raise ValueError("Provider quality review requires a non-empty reviewer")
    review_config = _load_review_config(review_config_path)
    benchmark_config = yaml.safe_load(
        benchmark_config_path.read_text(encoding="utf-8")
    ) or {}
    dynamic_providers = set(benchmark_config.get("dynamic_eligible_providers", []))
    if not dynamic_providers:
        raise ValueError("Benchmark config has no dynamic_eligible_providers")
    frames = read_frames_jsonl(frames_path)
    candidates = pd.read_csv(candidates_path)
    frame_providers = {frame.source_provider for frame in frames}
    candidate_providers = set(candidates["source_provider"].dropna().astype(str))
    if frame_providers != candidate_providers:
        raise ValueError(
            "Provider quality review requires identical frame and candidate provider coverage"
        )
    decisions = review_config["providers"]
    if set(decisions) != frame_providers:
        raise ValueError(
            "Provider quality config must contain exactly one decision for every frozen provider"
        )
    if not dynamic_providers.issubset(frame_providers):
        raise ValueError("Dynamic provider allowlist contains providers absent from the pilot")

    thresholds = {
        name: float(value) for name, value in review_config["thresholds"].items()
    }
    rows: list[dict[str, Any]] = []
    for provider_id in sorted(frame_providers):
        provider_frames = [frame for frame in frames if frame.source_provider == provider_id]
        provider_candidates = candidates[candidates["source_provider"] == provider_id]
        quality = assess_frames(provider_frames, provider_id).to_dict()
        frame_keys = {
            (frame.sequence_id, frame.frame_id) for frame in provider_frames
        }
        candidate_frame_keys = set(
            map(
                tuple,
                provider_candidates[["sequence_id", "frame_id"]].drop_duplicates().itertuples(
                    index=False, name=None
                ),
            )
        )
        missing_fraction = (
            float(provider_candidates[causal_features].isna().mean().max())
            if causal_features
            else 1.0
        )
        observed_metrics = {
            "min_mean_players_per_frame": quality["metrics"].get(
                "mean_players_per_frame"
            ),
            "max_p95_carrier_ball_distance_m": quality["metrics"].get(
                "p95_carrier_ball_distance_m"
            ),
            "min_observed_player_fraction": quality["metrics"].get(
                "observed_player_fraction"
            ),
            "max_extrapolated_player_fraction": quality["metrics"].get(
                "extrapolated_player_fraction"
            ),
            "max_causal_feature_missing_fraction": missing_fraction,
            "min_candidate_frame_coverage": (
                len(candidate_frame_keys) / len(frame_keys) if frame_keys else None
            ),
        }
        threshold_results = [
            _threshold_result(
                name=name,
                observed=(
                    None if observed_metrics[name] is None else float(observed_metrics[name])
                ),
                threshold=thresholds[name],
            )
            for name in sorted(thresholds)
        ]
        decision = decisions[provider_id]
        if not isinstance(decision, dict):
            raise ValueError(f"Provider decision for {provider_id!r} must be a mapping")
        requested_decision = str(decision.get("decision", "")).strip().casefold()
        if requested_decision not in {"accept", "reject"}:
            raise ValueError(
                f"Provider {provider_id!r} decision must be 'accept' or 'reject'"
            )
        rationale = str(decision.get("rationale", "")).strip()
        if not rationale or rationale.casefold() == "nan":
            raise ValueError(f"Provider {provider_id!r} needs a review rationale")
        spec = get_provider(provider_id)
        capability_passed = (
            provider_id != "statsbomb360"
            and spec.coverage in {"full_tracking", "partial_tracking"}
            and spec.capabilities.tracking
        )
        thresholds_passed = all(result["passed"] for result in threshold_results)
        accepted = (
            provider_id in dynamic_providers
            and requested_decision == "accept"
            and thresholds_passed
            and capability_passed
        )
        rows.append(
            {
                "provider_id": provider_id,
                "dynamic_evaluation_requested": provider_id in dynamic_providers,
                "explicit_decision": requested_decision,
                "reviewer": reviewer,
                "rationale": rationale,
                "thresholds_passed": thresholds_passed,
                "capability_passed": capability_passed,
                "accepted_for_dynamic_evaluation": accepted,
                "threshold_results": threshold_results,
                "quality_report": quality,
                "candidate_metrics": {
                    "options": len(provider_candidates),
                    "frames": len(candidate_frame_keys),
                    "causal_feature_missing_fraction": missing_fraction,
                },
                "provider_spec": spec.to_dict(),
                "provider_spec_sha256": canonical_sha256(spec.to_dict()),
            }
        )
    return rows, thresholds


def build_provider_quality_review(
    *,
    pilot_freeze_path: str | Path,
    benchmark_config_path: str | Path,
    review_config_path: str | Path,
    reviewer: str,
    output_path: str | Path,
) -> Path:
    pilot_path = Path(pilot_freeze_path)
    benchmark_path = Path(benchmark_config_path)
    review_path = Path(review_config_path)
    output = Path(output_path)
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite provider quality review: {output}")
    failures = verify_pilot_freeze(pilot_path)
    if failures:
        raise ValueError(f"Pilot freeze verification failed: {failures}")
    pilot = json.loads(pilot_path.read_text(encoding="utf-8"))
    if pilot.get("status") != "expert_annotations_frozen_reliability_established":
        raise ValueError("Provider quality review requires an established expert pilot freeze")
    candidate_record = _single_input(pilot, "action_candidates")
    frames_record = _single_input(pilot, "canonical_frames")
    config_record = _single_input(pilot, "benchmark_config")
    if sha256_file(benchmark_path) != config_record["sha256"]:
        raise ValueError("Provider quality review config is not bound by the pilot freeze")
    candidates_path = _resolve_input(candidate_record, pilot_path)
    frames_path = _resolve_input(frames_record, pilot_path)
    validated_causal_features = pilot["evidence_bindings"].get(
        "validated_causal_features"
    )
    if not isinstance(validated_causal_features, dict) or not validated_causal_features:
        raise ValueError("Pilot freeze has no validated causal-feature contract")
    causal_features = sorted(validated_causal_features)
    approved_policy = _load_approved_policy()
    provider_rows, thresholds = _compute_provider_rows(
        frames_path=frames_path,
        candidates_path=candidates_path,
        benchmark_config_path=benchmark_path,
        review_config_path=review_path,
        reviewer=reviewer,
        causal_features=causal_features,
    )
    inputs = [
        {
            "kind": "pilot_freeze",
            "path": pilot_path.as_posix(),
            "sha256": sha256_file(pilot_path),
        },
        {
            "kind": "action_candidates",
            "path": candidates_path.as_posix(),
            "sha256": sha256_file(candidates_path),
        },
        {
            "kind": "canonical_frames",
            "path": frames_path.as_posix(),
            "sha256": sha256_file(frames_path),
        },
        {
            "kind": "benchmark_config",
            "path": benchmark_path.as_posix(),
            "sha256": sha256_file(benchmark_path),
        },
        {
            "kind": "quality_review_config",
            "path": review_path.as_posix(),
            "sha256": sha256_file(review_path),
        },
        {
            "kind": "approved_quality_policy",
            "path": APPROVED_QUALITY_POLICY_PATH.resolve().as_posix(),
            "sha256": sha256_file(APPROVED_QUALITY_POLICY_PATH),
        },
    ]
    payload = {
        "schema_version": QUALITY_REVIEW_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "reviewer": reviewer,
        "bindings": {
            "pilot_freeze_sha256": sha256_file(pilot_path),
            "pilot_freeze_content_sha256": pilot["freeze_content_sha256"],
            "candidate_sha256": candidate_record["sha256"],
            "canonical_frames_sha256": frames_record["sha256"],
            "benchmark_config_sha256": config_record["sha256"],
            "quality_review_config_sha256": sha256_file(review_path),
            "approved_quality_policy_sha256": sha256_file(
                APPROVED_QUALITY_POLICY_PATH
            ),
            "approved_quality_policy_content_sha256": canonical_sha256(
                approved_policy
            ),
            "causal_features_audited_sha256": canonical_sha256(causal_features),
        },
        "approved_quality_policy": approved_policy,
        "thresholds": thresholds,
        "causal_features_audited": causal_features,
        "providers": provider_rows,
        "inputs": inputs,
    }
    payload["manifest_content_sha256"] = canonical_sha256(payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")
    return output


def verify_provider_quality_review(path: str | Path) -> list[str]:
    artifact_path = Path(path)
    failures: list[str] = []
    if not artifact_path.exists():
        return [f"missing provider quality review: {artifact_path}"]
    try:
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
        expected = payload.pop("manifest_content_sha256", None)
        if expected != canonical_sha256(payload):
            failures.append("provider quality review content hash mismatch")
        if payload.get("schema_version") != QUALITY_REVIEW_SCHEMA:
            failures.append("provider quality review schema mismatch")
        resolved: dict[str, Path] = {}
        input_records = payload.get("inputs", [])
        required_kinds = {
            "pilot_freeze",
            "action_candidates",
            "canonical_frames",
            "benchmark_config",
            "quality_review_config",
            "approved_quality_policy",
        }
        observed_kinds = [record.get("kind") for record in input_records]
        if set(observed_kinds) != required_kinds or len(observed_kinds) != len(
            required_kinds
        ):
            failures.append("provider quality review input coverage is invalid")
        for record in input_records:
            input_path = Path(record["path"])
            if not input_path.exists():
                failures.append(f"missing quality-review input: {record['kind']}:{input_path}")
                continue
            resolved[record["kind"]] = input_path
            if sha256_file(input_path) != record["sha256"]:
                failures.append(
                    f"quality-review input hash mismatch: {record['kind']}:{input_path}"
                )
        if failures:
            return failures
        if (
            resolved["approved_quality_policy"].resolve()
            != APPROVED_QUALITY_POLICY_PATH.resolve()
        ):
            failures.append(
                "provider quality review does not use the repository-approved policy path"
            )
            return failures
        failures.extend(
            f"pilot dependency: {failure}"
            for failure in verify_pilot_freeze(resolved["pilot_freeze"])
        )
        pilot_payload = json.loads(
            resolved["pilot_freeze"].read_text(encoding="utf-8")
        )
        validated_causal_features = (
            pilot_payload.get("evidence_bindings", {}).get(
                "validated_causal_features"
            )
        )
        if not isinstance(validated_causal_features, dict) or not validated_causal_features:
            failures.append("pilot dependency has no validated causal-feature contract")
            return failures
        expected_causal_features = sorted(validated_causal_features)
        if payload.get("causal_features_audited") != expected_causal_features:
            failures.append(
                "causal_features_audited does not exactly match the pilot contract"
            )
        approved_policy = _load_approved_policy()
        if canonical_sha256(payload.get("approved_quality_policy")) != canonical_sha256(
            approved_policy
        ):
            failures.append("approved provider-quality policy content does not recompute")
        expected_bindings = {
            "pilot_freeze_sha256": sha256_file(resolved["pilot_freeze"]),
            "pilot_freeze_content_sha256": pilot_payload["freeze_content_sha256"],
            "candidate_sha256": sha256_file(resolved["action_candidates"]),
            "canonical_frames_sha256": sha256_file(resolved["canonical_frames"]),
            "benchmark_config_sha256": sha256_file(resolved["benchmark_config"]),
            "quality_review_config_sha256": sha256_file(
                resolved["quality_review_config"]
            ),
            "approved_quality_policy_sha256": sha256_file(
                APPROVED_QUALITY_POLICY_PATH
            ),
            "approved_quality_policy_content_sha256": canonical_sha256(
                approved_policy
            ),
            "causal_features_audited_sha256": canonical_sha256(
                expected_causal_features
            ),
        }
        if payload.get("bindings") != expected_bindings:
            failures.append("provider quality review bindings do not recompute")
        recomputed_rows, recomputed_thresholds = _compute_provider_rows(
            frames_path=resolved["canonical_frames"],
            candidates_path=resolved["action_candidates"],
            benchmark_config_path=resolved["benchmark_config"],
            review_config_path=resolved["quality_review_config"],
            reviewer=str(payload["reviewer"]),
            causal_features=expected_causal_features,
        )
        if canonical_sha256(recomputed_thresholds) != canonical_sha256(
            payload.get("thresholds")
        ):
            failures.append("provider quality thresholds do not recompute")
        if canonical_sha256(recomputed_rows) != canonical_sha256(payload.get("providers")):
            failures.append("provider quality metrics or decisions do not recompute")
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        failures.append(f"invalid provider quality review: {exc}")
    return failures
