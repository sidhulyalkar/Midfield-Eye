from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from midfielders_eye.affordance import AffordanceEngine
from midfielders_eye.io import options_to_dataframe, write_frames_jsonl
from midfielders_eye.pilot import (
    AnnotationValidationError,
    apply_adjudication,
    build_adjudication_queue,
    build_consensus_labels,
    candidate_generator_source_records,
    freeze_pilot,
    load_annotations,
    verify_pilot_freeze,
    validate_candidate_generator_sources,
    validate_regenerated_candidates,
)
from midfielders_eye.reliability import ReliabilityGate, reliability_report
from midfielders_eye.synthetic import generate_dataset


def _expert_annotation_table(sequences: int = 10) -> pd.DataFrame:
    rows = []
    for sequence in range(sequences):
        for option in range(3):
            for rater in ("expert_a", "expert_b"):
                rows.append(
                    {
                        "sequence_id": f"sequence_{sequence:02d}",
                        "frame_id": 10,
                        "option_id": f"sequence_{sequence:02d}:10:pass:{option}",
                        "kind": "pass",
                        "annotator_id": rater,
                        "label_available": "yes" if option < 2 else "no",
                        "label_value_ordinal": 4 - option,
                        "label_visibility": "yes",
                        "label_confidence": 0.9,
                        "label_failure_reason": None,
                        "source_provider": "rights_cleared_tracking",
                        "provenance": "human-annotation-v2",
                    }
                )
    return pd.DataFrame(rows)


def _candidate_table(annotations: pd.DataFrame) -> pd.DataFrame:
    return annotations.drop_duplicates(
        ["sequence_id", "frame_id", "option_id"]
    ).reset_index(drop=True)


def test_annotation_import_rejects_pseudo_labels(tmp_path: Path) -> None:
    table = _expert_annotation_table(sequences=1)
    table["source_provider"] = "synthetic"
    table["provenance"] = "bootstrap-pseudo-label"
    path = tmp_path / "annotations.csv"
    table.to_csv(path, index=False)

    with pytest.raises(AnnotationValidationError, match="Non-human or synthetic"):
        load_annotations([path])


def test_reliability_gate_establishes_only_sufficient_human_overlap(
    tmp_path: Path,
) -> None:
    path = tmp_path / "annotations.csv"
    _expert_annotation_table().to_csv(path, index=False)
    imported = load_annotations([path])
    report = reliability_report(
        imported.dataframe,
        candidates=_candidate_table(imported.dataframe),
        bootstrap_iterations=30,
    )

    assert report["established"] is True
    assert report["coverage"]["sequences"] == 10
    assert report["coverage"]["overlap_frame_fraction"] == 1.0
    assert report["agreement"]["availability"]["alpha"] == pytest.approx(1.0)
    assert report["agreement"]["value"]["alpha"] == pytest.approx(1.0)
    assert report["bootstrap"]["availability_alpha"]["valid_replicates"] == 30


def test_reliability_gate_reports_not_established_without_enough_sequences(
    tmp_path: Path,
) -> None:
    path = tmp_path / "annotations.csv"
    _expert_annotation_table(sequences=2).to_csv(path, index=False)
    imported = load_annotations([path])
    report = reliability_report(
        imported.dataframe,
        candidates=_candidate_table(imported.dataframe),
        bootstrap_iterations=10,
    )

    assert report["established"] is False
    assert report["gate_checks"]["sequences"]["passed"] is False
    assert "not_established" == report["status"]


def test_reliability_coverage_uses_all_frozen_candidate_frames(
    tmp_path: Path,
) -> None:
    table = _expert_annotation_table(sequences=1)
    candidates = _candidate_table(table)
    extra = candidates.iloc[[0]].copy()
    extra["frame_id"] = 11
    extra["option_id"] = "sequence_00:11:pass:extra"
    candidates = pd.concat([candidates, extra], ignore_index=True)
    path = tmp_path / "annotations.csv"
    table.to_csv(path, index=False)
    imported = load_annotations([path], candidates=candidates)

    report = reliability_report(
        imported.dataframe,
        candidates=candidates,
        gate=ReliabilityGate(
            min_sequences=1,
            min_overlap_items=1,
            min_overlap_frame_fraction=0.5,
            min_candidate_coverage=1.0,
        ),
        bootstrap_iterations=5,
    )

    assert report["coverage"]["frozen_candidate_frames"] == 2
    assert report["coverage"]["overlap_frame_fraction"] == 0.5
    assert report["coverage"]["candidate_coverage"] == 0.75
    assert report["gate_checks"]["candidate_coverage"]["passed"] is False


def test_adjudication_preserves_disagreements_and_requires_rationale(
    tmp_path: Path,
) -> None:
    table = _expert_annotation_table(sequences=1)
    table.loc[1, "label_available"] = "uncertain"
    table.loc[1, "label_value_ordinal"] = 2
    path = tmp_path / "annotations.csv"
    table.to_csv(path, index=False)
    annotations = load_annotations([path]).dataframe

    queue = build_adjudication_queue(annotations)
    assert len(queue) == 1
    decision = queue[["sequence_id", "frame_id", "option_id"]].copy()
    decision["adjudicator_id"] = "lead_expert"
    decision["adjudicated_available"] = "yes"
    decision["adjudicated_value_ordinal"] = 3
    decision["adjudication_rationale"] = "The passing lane remains controllable."
    adjudicated = apply_adjudication(annotations, decision)

    assert len(annotations) == 6
    assert adjudicated.iloc[0]["adjudication_provenance"] == "human-adjudication-v1"
    assert adjudicated.iloc[0]["adjudicated_value"] == 0.75
    consensus = build_consensus_labels(
        annotations,
        _candidate_table(annotations),
        decision,
    )
    assert len(consensus) == 3
    assert consensus["option_id"].is_unique
    assert consensus.loc[consensus["adjudicated"], "provenance"].iloc[0] == (
        "human-adjudication-v1"
    )


def test_consensus_and_adjudication_fail_closed(tmp_path: Path) -> None:
    table = _expert_annotation_table(sequences=1)
    path = tmp_path / "annotations.csv"
    table.to_csv(path, index=False)
    annotations = load_annotations([path]).dataframe
    candidates = _candidate_table(annotations)

    with pytest.raises(AnnotationValidationError, match="at least two genuine raters"):
        build_consensus_labels(
            annotations[annotations["annotator_id"] == "expert_a"],
            candidates,
        )

    table.loc[1, "label_available"] = "no"
    table.to_csv(path, index=False)
    disputed = load_annotations([path]).dataframe
    queue = build_adjudication_queue(disputed)
    decision = queue[["sequence_id", "frame_id", "option_id"]].copy()
    decision["adjudicator_id"] = None
    decision["adjudicated_available"] = "yes"
    decision["adjudicated_value_ordinal"] = 2.5
    decision["adjudication_rationale"] = None
    with pytest.raises(
        AnnotationValidationError,
        match="must be an integer",
    ):
        apply_adjudication(disputed, decision)
    decision["adjudicated_value_ordinal"] = 2
    with pytest.raises(AnnotationValidationError, match="adjudicator_id"):
        apply_adjudication(disputed, decision)


def test_candidate_pilot_freeze_hashes_sequences_and_candidates(
    tmp_path: Path,
) -> None:
    frames = generate_dataset(sequences=2, frames=2, seed=44)
    for frame in frames:
        frame.source_provider = "rights_cleared_tracking"
        frame.source_match_id = "fixture_match"
    options = [
        option
        for frame in frames
        for option in AffordanceEngine().generate(frame)
    ]
    frames_path = write_frames_jsonl(frames, tmp_path / "frames.jsonl")
    candidates = options_to_dataframe(options)
    candidates_path = tmp_path / "candidates.csv"
    candidates.to_csv(candidates_path, index=False)

    manifest_path = freeze_pilot(
        frames_path=frames_path,
        candidates_path=candidates_path,
        protocol_path=Path("docs/ANNOTATION_GUIDE.md"),
        output_path=tmp_path / "pilot_freeze.json",
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["status"] == "candidate_sequences_frozen_awaiting_expert_annotations"
    assert manifest["sequence_count"] == 2
    assert len(manifest["freeze_content_sha256"]) == 64
    assert verify_pilot_freeze(manifest_path) == []
    with pytest.raises(FileExistsError, match="immutable"):
        freeze_pilot(
            frames_path=frames_path,
            candidates_path=candidates_path,
            output_path=manifest_path,
        )
    candidates_path.unlink()
    assert any(
        "missing input" in failure for failure in verify_pilot_freeze(manifest_path)
    )


def test_candidate_freeze_rejects_unknown_frame(tmp_path: Path) -> None:
    frames = generate_dataset(sequences=2, frames=2, seed=45)
    frames_path = write_frames_jsonl(frames, tmp_path / "frames.jsonl")
    options = [
        option for frame in frames for option in AffordanceEngine().generate(frame)
    ]
    candidates = options_to_dataframe(options)
    candidates.loc[0, "frame_id"] = 9999
    candidates_path = tmp_path / "candidates.csv"
    candidates.to_csv(candidates_path, index=False)

    with pytest.raises(ValueError, match="absent from canonical frames"):
        freeze_pilot(
            frames_path=frames_path,
            candidates_path=candidates_path,
            output_path=tmp_path / "freeze.json",
        )


@pytest.mark.parametrize(
    ("state_location", "marker"),
    [
        ("provenance", "uses_future_endpoint"),
        ("metadata", "offline_interpolation"),
        ("tracking", "interpolated"),
    ],
)
def test_freeze_and_replay_reject_future_derived_player_state(
    tmp_path: Path,
    state_location: str,
    marker: str,
) -> None:
    frames = generate_dataset(sequences=1, frames=2, seed=451)
    options = [
        option for frame in frames for option in AffordanceEngine().generate(frame)
    ]
    candidates = options_to_dataframe(options)
    player = frames[0].players[0]
    if state_location == "provenance":
        player.provenance_flags.append(marker)
    elif state_location == "metadata":
        player.metadata["state_derivation"] = marker
    else:
        player.tracking_status = "interpolated"
    frames_path = write_frames_jsonl(frames, tmp_path / f"{state_location}.jsonl")
    candidates_path = tmp_path / f"{state_location}.csv"
    candidates.to_csv(candidates_path, index=False)

    with pytest.raises(ValueError, match="future-derived state"):
        freeze_pilot(
            frames_path=frames_path,
            candidates_path=candidates_path,
            output_path=tmp_path / f"{state_location}_freeze.json",
        )
    with pytest.raises(ValueError, match="future-derived state"):
        validate_regenerated_candidates(
            frames_path=frames_path,
            candidates=candidates,
            causal_features={"geometric_score", *AffordanceEngine.feature_names},
        )


def test_candidate_lineage_rejects_feature_or_key_tampering(tmp_path: Path) -> None:
    frames = generate_dataset(sequences=2, frames=2, seed=46)
    frames_path = write_frames_jsonl(frames, tmp_path / "frames.jsonl")
    options = [
        option for frame in frames for option in AffordanceEngine().generate(frame)
    ]
    candidates = options_to_dataframe(options)
    causal_features = {"geometric_score", *AffordanceEngine.feature_names}

    tampered_feature = candidates.copy()
    tampered_feature.loc[0, "future_space"] += 0.01
    with pytest.raises(ValueError, match="does not regenerate"):
        validate_regenerated_candidates(
            frames_path=frames_path,
            candidates=tampered_feature,
            causal_features=causal_features,
        )

    with pytest.raises(ValueError, match="keys do not exactly regenerate"):
        validate_regenerated_candidates(
            frames_path=frames_path,
            candidates=candidates.iloc[1:].copy(),
            causal_features=causal_features,
        )


def test_generator_source_contract_rejects_changed_dependency_hash() -> None:
    records = candidate_generator_source_records()
    records[0] = {**records[0], "sha256": "0" * 64}
    with pytest.raises(ValueError, match="source hash mismatch"):
        validate_candidate_generator_sources({"generator_sources": records})
