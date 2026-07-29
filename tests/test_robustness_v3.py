from __future__ import annotations

import numpy as np

from midfielders_eye.robustness import (
    DegradationConfig,
    benchmark_degradation,
    degrade_frames,
    tactical_frame_metrics,
)
from midfielders_eye.synthetic import generate_dataset


def test_identity_degradation_is_tactically_identical() -> None:
    frame = generate_dataset(sequences=1, frames=1, seed=10)[0]
    metrics = tactical_frame_metrics(frame, frame)
    assert metrics["option_set_recall_at_3"] == 1.0
    assert metrics["pressure_map_iou"] == 1.0
    assert abs(metrics["chosen_action_regret"]) < 1e-12


def test_degradation_is_deterministic_and_marks_provenance() -> None:
    frames = generate_dataset(sequences=1, frames=4, seed=11)
    config = DegradationConfig(
        name="test",
        position_noise_std_m=1.0,
        missing_player_rate=0.2,
        seed=12,
    )
    first = degrade_frames(frames, config)
    second = degrade_frames(frames, config)
    assert first.counts == second.counts
    assert np.isclose(first.frames[0].players[0].x, second.frames[0].players[0].x)
    assert "degradation:test" in first.frames[0].quality_flags


def test_benchmark_reports_perception_and_tactical_layers() -> None:
    frames = generate_dataset(sequences=1, frames=3, seed=13)
    metrics, _ = benchmark_degradation(
        frames,
        [
            DegradationConfig(name="identity", seed=1),
            DegradationConfig(name="noise", position_noise_std_m=1.5, seed=1),
        ],
    )
    assert set(metrics["degradation"]) == {"identity", "noise"}
    assert {
        "pitch_error_m",
        "velocity_error_mps",
        "calibration_offset_error_m",
        "visible_pitch_fraction",
        "identity_assignment_accuracy",
        "id_switch_count",
        "track_fragments_per_identity",
        "pressure_map_iou",
        "corridor_decision_flip_rate",
        "interception_margin_mae_s",
        "option_rank_spearman",
        "chosen_action_regret",
    }.issubset(metrics.columns)
    identity = metrics[metrics["degradation"] == "identity"]
    assert np.allclose(identity["pitch_error_m"], 0.0)


def test_id_switch_degradation_is_visible_in_identity_metrics() -> None:
    frames = generate_dataset(sequences=1, frames=8, seed=14)
    metrics, _ = benchmark_degradation(
        frames,
        [DegradationConfig(name="switch_all", id_switch_rate=1.0, seed=2)],
    )
    assert metrics["identity_assignment_accuracy"].mean() < 1.0
    assert metrics["id_switch_count"].max() > 0
    assert metrics["track_fragments_per_identity"].mean() > 1.0
