import math

import numpy as np

from midfielders_eye.geometry import (
    assess_passing_corridor,
    local_pressure,
    point_to_segment_distance,
    visibility_score,
)
from midfielders_eye.schema import PlayerState


def player(player_id: str, team: str, x: float, y: float, vx: float = 0.0, vy: float = 0.0):
    return PlayerState(player_id, team, x, y, vx, vy, body_angle=0.0)


def test_point_to_segment_distance():
    assert point_to_segment_distance(np.array([5.0, 3.0]), np.array([0.0, 0.0]), np.array([10.0, 0.0])) == 3.0


def test_corridor_detects_central_blocker():
    passer = player("H1", "home", 0.0, 0.0)
    defender = player("A1", "away", 5.0, 0.4)
    result = assess_passing_corridor(passer, np.array([10.0, 0.0]), [defender])
    assert result.minimum_clearance < 0.5
    assert result.blocker_id == "A1"
    assert result.pressure_shadow > 0.5


def test_pressure_increases_near_defender():
    defender = player("A1", "away", 10.0, 10.0, vx=2.0)
    near = local_pressure(np.array([11.0, 10.0]), [defender])
    far = local_pressure(np.array([30.0, 30.0]), [defender])
    assert near > far


def test_visibility_respects_facing_direction():
    viewer = player("H1", "home", 10.0, 10.0)
    viewer.gaze_angle = 0.0
    ahead = visibility_score(viewer, np.array([20.0, 10.0]))
    behind = visibility_score(viewer, np.array([0.0, 10.0]))
    assert ahead > 0.9
    assert behind == 0.0


def test_visibility_can_use_head_angle():
    viewer = player("H1", "home", 10.0, 10.0)
    viewer.head_angle = math.pi / 2
    assert visibility_score(viewer, np.array([10.0, 20.0])) > 0.9
