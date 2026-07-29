from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pandas as pd
import pytest
import yaml

from midfielders_eye.affordance import AffordanceEngine
from midfielders_eye.frozen_benchmark import (
    DEFAULT_B3_FEATURES,
    FrozenBenchmarkConfig,
    _provider_spec_evidence,
    evaluate_benchmark_rankings,
    run_frozen_benchmark,
    verify_frozen_benchmark,
)
from midfielders_eye.io import options_to_dataframe, write_frames_jsonl
from midfielders_eye.models.baselines import add_baseline_scores
from midfielders_eye.pilot import (
    build_consensus_labels,
    canonical_sha256,
    candidate_generator_source_records,
    freeze_pilot,
    load_annotations,
    sha256_file,
    validate_causal_feature_contract,
)
from midfielders_eye.reliability import reliability_report
from midfielders_eye.provider_quality_review import (
    build_provider_quality_review,
    validate_provider_quality_review_config,
    verify_provider_quality_review,
)
from midfielders_eye.synthetic import build_bootstrap_options, generate_dataset


def _synthetic_options(path: Path) -> pd.DataFrame:
    frames = generate_dataset(sequences=6, frames=3, seed=19)
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


def _established_empirical_fixture(
    tmp_path: Path,
) -> tuple[Path, Path, Path, Path]:
    frames = generate_dataset(sequences=10, frames=2, seed=23)
    for frame in frames:
        sequence_number = int(frame.sequence_id.rsplit("_", 1)[1])
        frame.source_provider = "metrica" if sequence_number < 5 else "sportec_open"
        frame.source_match_id = f"match_{sequence_number:02d}"
    frames_path = write_frames_jsonl(frames, tmp_path / "frames.jsonl")
    options = [
        option for frame in frames for option in AffordanceEngine().generate(frame)
    ]
    candidates = options_to_dataframe(options)
    candidates_path = tmp_path / "candidates.csv"
    candidates.to_csv(candidates_path, index=False)

    annotations = pd.concat(
        [
            candidates.assign(annotator_id="expert_a"),
            candidates.assign(annotator_id="expert_b"),
        ],
        ignore_index=True,
    )
    item_number = annotations.groupby("annotator_id").cumcount()
    annotations["label_available"] = item_number.mod(3).map(
        {0: "yes", 1: "yes", 2: "no"}
    )
    annotations["label_value_ordinal"] = item_number.mod(5)
    annotations["label_visibility"] = "yes"
    annotations["label_confidence"] = 0.9
    annotations["provenance"] = "human-annotation-v2"
    annotations_path = tmp_path / "annotations.csv"
    annotations.to_csv(annotations_path, index=False)
    imported = load_annotations([annotations_path], candidates=candidates)

    report = reliability_report(
        imported.dataframe,
        candidates=candidates,
        bootstrap_iterations=10,
        seed=13,
    )
    report["annotation_import"] = imported.report.to_dict()
    report["annotation_inputs"] = [
        {"path": str(annotations_path), "sha256": sha256_file(annotations_path)}
    ]
    report["candidate_input"] = {
        "path": str(candidates_path),
        "sha256": sha256_file(candidates_path),
    }
    report_path = tmp_path / "reliability.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    consensus = build_consensus_labels(
        imported.dataframe,
        candidates,
        pd.DataFrame(),
    )
    consensus_path = tmp_path / "consensus.csv"
    consensus.to_csv(consensus_path, index=False)

    config = FrozenBenchmarkConfig(
        sequence_splits=2,
        bootstrap_iterations=10,
        dynamic_eligible_providers=("metrica", "sportec_open"),
    )
    config_payload = json.loads(json.dumps(asdict(config)))
    config_path = tmp_path / "benchmark.yaml"
    config_path.write_text(yaml.safe_dump(config_payload, sort_keys=False), encoding="utf-8")

    contract_features = sorted(set(DEFAULT_B3_FEATURES) | set(AffordanceEngine.feature_names))
    features = {
        feature: {
            "timing": (
                "forecast_from_focal_state"
                if feature
                in {"interception_margin_s", "future_space", "option_creation"}
                else "focal_frame"
            ),
            "dependencies": [],
            "justification": "Frozen test declaration from focal state.",
        }
        for feature in contract_features
    }
    features["geometric_score"] = {
        "timing": "derived_from_declared_causal_features",
        "dependencies": list(AffordanceEngine.feature_names),
        "justification": "Derived only from the declared causal features.",
    }
    causal_path = tmp_path / "causal_contract.json"
    causal_path.write_text(
        json.dumps(
            {
                "schema_version": "causal-feature-contract-v1",
                "reviewed_by": "test_researcher",
                "candidate_sha256": sha256_file(candidates_path),
                "benchmark_config_sha256": sha256_file(config_path),
                "generator_sources": candidate_generator_source_records(),
                "features": features,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    freeze_path = freeze_pilot(
        frames_path=frames_path,
        candidates_path=candidates_path,
        annotation_paths=[annotations_path],
        protocol_path=Path("docs/ANNOTATION_GUIDE.md"),
        reliability_report_path=report_path,
        consensus_path=consensus_path,
        causal_feature_contract_path=causal_path,
        benchmark_config_path=config_path,
        output_path=tmp_path / "pilot_freeze.json",
    )
    review_config_path = tmp_path / "quality_review.yaml"
    review_config_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "provider-quality-review-config-v1",
                "thresholds": {
                    "min_mean_players_per_frame": 12.0,
                    "max_p95_carrier_ball_distance_m": 4.0,
                    "min_observed_player_fraction": 0.60,
                    "max_extrapolated_player_fraction": 0.40,
                    "max_causal_feature_missing_fraction": 0.0,
                    "min_candidate_frame_coverage": 1.0,
                },
                "providers": {
                    "metrica": {
                        "decision": "accept",
                        "rationale": "Fixture full-tracking metrics pass every frozen threshold.",
                    },
                    "sportec_open": {
                        "decision": "accept",
                        "rationale": "Fixture replication metrics pass every frozen threshold.",
                    },
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    quality_review_path = build_provider_quality_review(
        pilot_freeze_path=freeze_path,
        benchmark_config_path=config_path,
        review_config_path=review_config_path,
        reviewer="test_quality_reviewer",
        output_path=tmp_path / "provider_quality_review.json",
    )
    return consensus_path, config_path, freeze_path, quality_review_path


def test_frozen_benchmark_runs_identical_grouped_protocols(tmp_path: Path) -> None:
    options_path = tmp_path / "synthetic_options.csv"
    source = _synthetic_options(options_path)
    config = FrozenBenchmarkConfig(
        sequence_splits=3,
        bootstrap_iterations=20,
        allow_synthetic_software_validation=True,
    )
    manifest_path = run_frozen_benchmark(
        options_path,
        tmp_path / "results",
        config=config,
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    folds = json.loads((manifest_path.parent / "folds.json").read_text(encoding="utf-8"))
    metrics = pd.read_csv(manifest_path.parent / "metrics.csv")
    predictions = pd.read_csv(manifest_path.parent / "predictions.csv")

    assert manifest["evidence_status"] == "synthetic_software_validation_only"
    assert set(folds) == {"sequence_held_out", "provider_held_out"}
    for protocol_folds in folds.values():
        for fold in protocol_folds:
            assert not set(fold["train_sequences"]) & set(fold["test_sequences"])
    assert set(metrics["model"]) == {
        "B0_naive",
        "B1_static",
        "B2_dynamic",
        "B3_learned",
    }
    assert len(predictions) == 2 * len(source)
    assert (manifest_path.parent / "provider_quality.csv").exists()
    assert (manifest_path.parent / "provider_shift.csv").exists()
    assert (manifest_path.parent / "prespecified_contrasts.json").exists()
    assert verify_frozen_benchmark(manifest_path) == []


def test_empirical_mode_refuses_synthetic_or_pseudo_labels(tmp_path: Path) -> None:
    options_path = tmp_path / "synthetic_options.csv"
    _synthetic_options(options_path)

    with pytest.raises(ValueError, match="requires pilot_freeze_path"):
        run_frozen_benchmark(options_path, tmp_path / "results")


def test_empirical_benchmark_requires_and_binds_established_pilot(
    tmp_path: Path,
) -> None:
    (
        consensus_path,
        config_path,
        freeze_path,
        quality_review_path,
    ) = _established_empirical_fixture(tmp_path)
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    for key in ("protocols", "dynamic_eligible_providers", "b3_features"):
        payload[key] = tuple(payload[key])
    config = FrozenBenchmarkConfig(**payload)

    manifest_path = run_frozen_benchmark(
        consensus_path,
        tmp_path / "empirical_results",
        config=config,
        pilot_freeze_path=freeze_path,
        config_source_path=config_path,
        provider_quality_review_path=quality_review_path,
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["evidence_status"] == "empirical_human_annotated_evaluation"
    assert manifest["empirical_pilot_binding"]["consensus_sha256"] == sha256_file(
        consensus_path
    )
    assert {
        row["provider_id"] for row in manifest["provider_reports"]["catalog_spec_evidence"]
    } == {"metrica", "sportec_open"}
    assert "not inferred" in manifest["feature_timing"]["validation_scope"]
    assert verify_provider_quality_review(quality_review_path) == []
    assert verify_frozen_benchmark(manifest_path) == []
    quality_payload = json.loads(quality_review_path.read_text(encoding="utf-8"))
    quality_payload["providers"][0]["accepted_for_dynamic_evaluation"] = False
    quality_review_path.write_text(json.dumps(quality_payload, indent=2), encoding="utf-8")
    assert verify_provider_quality_review(quality_review_path)
    assert any(
        "provider quality" in failure or "provider_quality_review" in failure
        for failure in verify_frozen_benchmark(manifest_path)
    )
    consensus_path.unlink()
    assert any(
        "missing input" in failure or "missing original input" in failure
        for failure in verify_frozen_benchmark(manifest_path)
    )


@pytest.mark.parametrize(
    ("threshold_name", "weakened_value"),
    [
        ("min_mean_players_per_frame", 11.99),
        ("max_p95_carrier_ball_distance_m", 4.01),
    ],
)
def test_provider_quality_config_cannot_weaken_repository_policy(
    tmp_path: Path,
    threshold_name: str,
    weakened_value: float,
) -> None:
    payload = yaml.safe_load(
        Path("configs/provider_quality_review_v1.yaml").read_text(encoding="utf-8")
    )
    payload["thresholds"][threshold_name] = weakened_value
    path = tmp_path / f"weakened_{threshold_name}.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="weaker than repository policy"):
        validate_provider_quality_review_config(path)


def test_provider_quality_review_rejects_causal_feature_omission_or_extra(
    tmp_path: Path,
) -> None:
    _, _, _, review_path = _established_empirical_fixture(tmp_path)
    original = json.loads(review_path.read_text(encoding="utf-8"))
    audited = list(original["causal_features_audited"])
    assert "geometric_score" in audited

    for tampered_features in (audited[1:], sorted([*audited, "target_x"])):
        tampered = json.loads(json.dumps(original))
        tampered["causal_features_audited"] = tampered_features
        tampered["bindings"]["causal_features_audited_sha256"] = canonical_sha256(
            tampered_features
        )
        tampered.pop("manifest_content_sha256")
        tampered["manifest_content_sha256"] = canonical_sha256(tampered)
        review_path.write_text(json.dumps(tampered, indent=2), encoding="utf-8")

        failures = verify_provider_quality_review(review_path)
        assert any(
            "causal_features_audited does not exactly match" in failure
            for failure in failures
        )


def test_uncertain_availability_nulls_frame_recall() -> None:
    frame = pd.DataFrame(
        {
            "sequence_id": ["s"] * 3,
            "frame_id": [1] * 3,
            "label_value": [1.0, 0.5, 0.0],
            "label_available": ["yes", "uncertain", "no"],
            "score": [0.9, 1.0, 0.1],
        }
    )
    result = evaluate_benchmark_rankings(
        frame,
        "score",
        value_column="label_value",
        k=1,
    )
    assert pd.isna(result["recall@1"])
    assert result["recall_null_uncertain_frames"] == 1


def test_empirical_benchmark_rejects_unapproved_provider_before_folds(
    tmp_path: Path,
) -> None:
    (
        consensus_path,
        config_path,
        freeze_path,
        accepted_review_path,
    ) = _established_empirical_fixture(tmp_path)
    accepted = json.loads(accepted_review_path.read_text(encoding="utf-8"))
    rejected_config = {
        "schema_version": "provider-quality-review-config-v1",
        "thresholds": accepted["thresholds"],
        "providers": {
            "metrica": {
                "decision": "reject",
                "rationale": "Deliberate negative fixture decision before evaluation.",
            },
            "sportec_open": {
                "decision": "accept",
                "rationale": "Fixture metrics pass the frozen thresholds.",
            },
        },
    }
    rejected_config_path = tmp_path / "rejected_quality.yaml"
    rejected_config_path.write_text(
        yaml.safe_dump(rejected_config, sort_keys=False),
        encoding="utf-8",
    )
    rejected_review_path = build_provider_quality_review(
        pilot_freeze_path=freeze_path,
        benchmark_config_path=config_path,
        review_config_path=rejected_config_path,
        reviewer="test_quality_reviewer",
        output_path=tmp_path / "rejected_quality.json",
    )
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    for key in ("protocols", "dynamic_eligible_providers", "b3_features"):
        payload[key] = tuple(payload[key])

    with pytest.raises(ValueError, match="lack pre-evaluation quality approval"):
        run_frozen_benchmark(
            consensus_path,
            tmp_path / "must_not_run_models",
            config=FrozenBenchmarkConfig(**payload),
            pilot_freeze_path=freeze_path,
            config_source_path=config_path,
            provider_quality_review_path=rejected_review_path,
        )
    assert not (tmp_path / "must_not_run_models" / "folds.json").exists()


def test_frozen_b0_and_b1_exclude_dynamic_and_viewpoint_features() -> None:
    base = pd.DataFrame(
        {
            "kind": ["pass", "pass"],
            "distance_m": [10.0, 10.0],
            "forward_progress": [0.0, 0.0],
            "lane_clearance_m": [3.0, 3.0],
            "receiver_space": [0.5, 0.5],
            "receiver_pressure": [0.4, 0.4],
            "xt_gain": [0.1, 0.1],
            "body_orientation": [0.0, 1.0],
            "future_space": [0.0, 1.0],
        }
    )
    scored = add_baseline_scores(base)

    assert scored.loc[0, "naive_score"] == pytest.approx(scored.loc[1, "naive_score"])
    assert scored.loc[0, "static_score"] == pytest.approx(scored.loc[1, "static_score"])


def test_provider_catalog_rejects_statsbomb_dynamic_evaluation() -> None:
    dataframe = pd.DataFrame({"source_provider": ["statsbomb360"]})
    config = FrozenBenchmarkConfig(dynamic_eligible_providers=("statsbomb360",))

    with pytest.raises(ValueError, match="categorically prohibited"):
        _provider_spec_evidence(dataframe, config)


def test_causal_contract_rejects_retrospective_or_label_dependencies() -> None:
    payload = {
        "schema_version": "causal-feature-contract-v1",
        "reviewed_by": "researcher",
        "candidate_sha256": "a" * 64,
        "features": {
            "distance_m": {
                "timing": "focal_frame",
                "dependencies": ["label_selected"],
                "justification": "Invalid test declaration.",
            },
            "geometric_score": {
                "timing": "derived_from_declared_causal_features",
                "dependencies": ["distance_m"],
                "justification": "Derived.",
            },
        },
    }
    with pytest.raises(ValueError, match="label-derived or retrospective"):
        validate_causal_feature_contract(
            payload,
            candidate_sha256="a" * 64,
            required_features=["distance_m"],
        )
