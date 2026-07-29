from __future__ import annotations

import copy
import math

from midfielders_eye.state.orientation import estimate_body_orientation
from midfielders_eye.synthetic import generate_dataset


def test_motion_orientation_proxy_is_explicit() -> None:
    frame = generate_dataset(sequences=1, frames=1, seed=21)[0]
    player = frame.players[0]
    player.vx = 3.0
    player.vy = 0.0
    player.metadata.pop("body_angle_observed", None)
    player.trajectory_confidence = 0.9

    output = estimate_body_orientation([frame])[0]
    estimated = output.player(player.player_id)
    assert abs(estimated.body_angle) < 1e-6
    assert estimated.metadata["body_angle_source"] == "motion_proxy"
    assert 0.0 < estimated.metadata["body_heading_confidence"] <= 0.85
    assert "orientation_from_motion_proxy" in estimated.provenance_flags


def test_observed_orientation_is_never_overwritten() -> None:
    frame = generate_dataset(sequences=1, frames=1, seed=22)[0]
    player = frame.players[0]
    player.body_angle = math.pi / 2
    player.vx = 5.0
    player.vy = 0.0
    player.metadata["body_angle_observed"] = True

    output = estimate_body_orientation([copy.deepcopy(frame)])[0]
    estimated = output.player(player.player_id)
    assert estimated.body_angle == math.pi / 2
    assert estimated.metadata["body_angle_source"] == "observed"
