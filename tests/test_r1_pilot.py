from __future__ import annotations

import json

import pandas as pd

from midfielders_eye.io import write_frames_jsonl
from midfielders_eye.r1 import (
    DEFAULT_TARGET_COMPOSITION,
    R1PilotConfig,
    build_r1_status,
    prepare_real_pilot,
    protocol_ready_showcase_payload,
)
from midfielders_eye.synthetic import generate_dataset


def test_r1_prepare_freezes_non_overlapping_double_rated_sample(tmp_path) -> None:
    frames = generate_dataset(sequences=12, frames=12, seed=31)
    source = write_frames_jsonl(frames, tmp_path / "source.jsonl")
    output = tmp_path / "r1"

    manifest_path = prepare_real_pilot(
        source,
        output,
        rater_ids=["expert_a", "expert_b"],
        reviewed_by="research_lead",
        config=R1PilotConfig(),
        protocol_path="docs/ANNOTATION_GUIDE.md",
        allow_synthetic_software_validation=True,
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["stage"] == "sample_frozen"
    assert manifest["sample"]["selected_sequences"] == 10
    assert manifest["sample"]["source_frame_overlap"] is False
    assert manifest["sample"]["composition"] == DEFAULT_TARGET_COMPOSITION
    assert manifest["claim_state"] == "sampling_and_annotation_protocol_only_no_empirical_model_claim"

    assignments = pd.read_csv(output / "rater_assignments.csv")
    label_frames = manifest["sample"]["label_frames"]
    assert set(assignments["annotator_id"]) == {"expert_a", "expert_b"}
    assert len(assignments) == label_frames * 2
    for _, group in assignments.groupby("annotator_id"):
        assert len(group) == label_frames
        assert group[["sequence_id", "frame_id"]].duplicated().sum() == 0
        assert group["outcome_blinded"].all()
        assert group["model_score_blinded"].all()

    blinded = pd.read_csv(output / "pilot_candidates_blinded.csv")
    assert "geometric_score" not in blinded
    assert "learned_score" not in blinded
    assert not any(column.startswith("label_") for column in blinded.columns)
    assert (output / "pilot_candidates_freeze.json").exists()


def test_r1_protocol_ready_showcase_never_invents_metrics() -> None:
    payload = protocol_ready_showcase_payload()
    assert payload["stage"] == "protocol_ready"
    assert payload["claim_state"] == "no_empirical_model_claim_yet"
    assert payload["benchmark"] == {"complete": False, "metrics": {}}
    assert payload["evidence_ladder"][0]["complete"] is True
    assert all(
        not step["complete"] for step in payload["evidence_ladder"][1:]
    )


def test_r1_status_reads_prepared_manifest_without_promoting_claim(tmp_path) -> None:
    frames = generate_dataset(sequences=12, frames=12, seed=41)
    source = write_frames_jsonl(frames, tmp_path / "source.jsonl")
    output = tmp_path / "r1"
    prepare_real_pilot(
        source,
        output,
        rater_ids=["expert_a", "expert_b"],
        reviewed_by="research_lead",
        allow_synthetic_software_validation=True,
    )

    status = build_r1_status(output)
    assert status["stage"] == "sample_frozen"
    assert status["claim_state"] == "no_empirical_model_claim_yet"
    assert status["sample"]["selected_sequences"] == 10
    assert status["annotation"]["progress"]["rows"] == 0
    assert status["benchmark"]["complete"] is False
