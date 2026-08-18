from __future__ import annotations

from dataclasses import replace

import pandas as pd
import pytest

from midfielders_eye.annotation_app import (
    causal_history_for_frame,
    load_assignment_plan,
)
from midfielders_eye.synthetic import generate_sequence


def test_assignment_plan_filters_one_rater_and_requires_blinding(tmp_path) -> None:
    frames = generate_sequence(0, frames=5, fps=5.0, seed=91)
    assignments = pd.DataFrame(
        [
            {
                "annotator_id": rater,
                "display_order": index + 1,
                "sequence_id": frame.sequence_id,
                "frame_id": frame.frame_id,
                "outcome_blinded": True,
                "model_score_blinded": True,
            }
            for rater in ("expert_a", "expert_b")
            for index, frame in enumerate(reversed(frames))
        ]
    )
    path = tmp_path / "assignments.csv"
    assignments.to_csv(path, index=False)

    selected = load_assignment_plan(path, frames=frames, annotator_id="expert_a")
    assert len(selected) == len(frames)
    assert selected["display_order"].tolist() == list(range(1, len(frames) + 1))
    assert set(selected["annotator_id"]) == {"expert_a"}

    assignments.loc[0, "model_score_blinded"] = False
    assignments.to_csv(path, index=False)
    with pytest.raises(ValueError, match="model-score blinded"):
        load_assignment_plan(path, frames=frames, annotator_id="expert_a")


def test_causal_history_never_shows_future_or_other_sequence() -> None:
    frames = generate_sequence(0, frames=6, fps=5.0, seed=92)
    focal = frames[4]
    other = replace(frames[0], sequence_id="different-sequence")
    history = causal_history_for_frame([*frames, other], focal, maximum_frames=3)

    assert [frame.frame_id for frame in history] == [1, 2, 3]
    assert all(frame.timestamp_s < focal.timestamp_s for frame in history)
    assert all(frame.sequence_id == focal.sequence_id for frame in history)
