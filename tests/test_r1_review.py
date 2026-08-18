from __future__ import annotations

import json

from midfielders_eye.io import write_frames_jsonl
from midfielders_eye.r1 import prepare_real_pilot
from midfielders_eye.r1_review import accept_r1_sample
from midfielders_eye.synthetic import generate_dataset


def test_sample_review_promotes_without_regenerating_candidate_freeze(tmp_path) -> None:
    frames = generate_dataset(sequences=12, frames=12, seed=131)
    source = write_frames_jsonl(frames, tmp_path / "source.jsonl")
    r1_dir = tmp_path / "r1"
    manifest_path = prepare_real_pilot(
        source,
        r1_dir,
        rater_ids=["expert_a", "expert_b"],
        allow_synthetic_software_validation=True,
    )
    before = json.loads(manifest_path.read_text(encoding="utf-8"))
    freeze_bytes = (r1_dir / "pilot_candidates_freeze.json").read_bytes()

    review_path = accept_r1_sample(
        r1_dir,
        reviewed_by="research_lead",
        rationale="Frozen ten-window proposal passes the prespecified diversity and source-quality review.",
    )
    after = json.loads(manifest_path.read_text(encoding="utf-8"))
    review = json.loads(review_path.read_text(encoding="utf-8"))

    assert before["stage"] == "needs_sequence_review"
    assert after["stage"] == "sample_frozen"
    assert review["decision"] == "accept"
    assert len(review["selected_sequences"]) == 10
    assert (r1_dir / "pilot_candidates_freeze.json").read_bytes() == freeze_bytes
    assert after["sample_review"]["sha256"]
