from __future__ import annotations

from dataclasses import replace

import json
import pandas as pd

from midfielders_eye.io import write_frames_jsonl
from midfielders_eye.r1 import prepare_real_pilot
from midfielders_eye.r1_finalize import finalize_r1_pilot
from midfielders_eye.synthetic import generate_dataset


def _metrica_shaped_frames():
    frames = generate_dataset(sequences=12, frames=10, seed=121)
    return [
        replace(
            frame,
            source_provider="metrica",
            source_match_id=f"fixture-{frame.sequence_id}",
            quality_flags=[],
            metadata={"source": "provider-shaped-test-fixture"},
        )
        for frame in frames
    ]


def _write_identical_human_ratings(candidates_path, output, annotator_id: str) -> None:
    candidates = pd.read_csv(candidates_path)
    rows = candidates.copy()
    positions = pd.Series(range(len(rows)), index=rows.index)
    rows["label_available"] = positions.map(lambda value: "no" if value % 3 == 0 else "yes")
    rows["label_value_ordinal"] = positions % 5
    rows["label_value"] = rows["label_value_ordinal"] / 4.0
    rows["label_visibility"] = positions.map(
        lambda value: "uncertain" if value % 4 == 0 else "yes"
    )
    rows["label_confidence"] = 0.9
    rows["annotator_id"] = annotator_id
    rows["provenance"] = "human-annotation-action-menu-v1"
    rows["blinded_to_outcome"] = True
    rows["model_score_blinded"] = True
    rows.to_csv(output, index=False)


def test_r1_finalizer_establishes_expert_freeze_then_waits_for_quality_review(tmp_path) -> None:
    source = write_frames_jsonl(_metrica_shaped_frames(), tmp_path / "frames.jsonl")
    r1_dir = tmp_path / "r1"
    manifest_path = prepare_real_pilot(
        source,
        r1_dir,
        rater_ids=["expert_a", "expert_b"],
        reviewed_by="research_lead",
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    candidates_path = manifest["paths"]["candidates"]
    expert_a = tmp_path / "expert_a.csv"
    expert_b = tmp_path / "expert_b.csv"
    _write_identical_human_ratings(candidates_path, expert_a, "expert_a")
    _write_identical_human_ratings(candidates_path, expert_b, "expert_b")

    status_path = finalize_r1_pilot(
        r1_dir,
        [expert_a, expert_b],
        reviewed_by="research_lead",
        benchmark_config_path="configs/r1_benchmark.yaml",
        bootstrap_iterations=20,
        run_benchmark=False,
    )
    status = json.loads(status_path.read_text(encoding="utf-8"))

    assert status["reliability"]["established"] is True
    assert status["adjudication"]["disagreement_items"] == 0
    assert status["stage"] == "expert_pilot_frozen_needs_provider_review"
    assert status["claim_state"] == "no_empirical_model_claim_yet"
    assert (r1_dir / "consensus_labels.csv").exists()
    assert (r1_dir / "causal_feature_contract.json").exists()
    assert (r1_dir / "pilot_expert_freeze.json").exists()
    assert not (r1_dir / "benchmark").exists()
