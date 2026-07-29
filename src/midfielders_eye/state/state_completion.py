from __future__ import annotations

import copy
from collections import defaultdict
from dataclasses import dataclass, field

import numpy as np

from ..schema import FrameState, PlayerState, Team


@dataclass(slots=True)
class RolePrior:
    team: Team
    role: str
    mean_relative_position: list[float]
    covariance: list[list[float]]
    count: int


@dataclass(slots=True)
class FormationPriorCompleter:
    """Transparent baseline for hidden-player completion.

    The model predicts a role's mean position relative to the ball and emits uncertainty. It is a
    deliberately weak baseline for comparison with future graph or sequence completion models.
    """

    priors: dict[tuple[Team, str], RolePrior] = field(default_factory=dict)

    def fit(self, frames: list[FrameState]) -> "FormationPriorCompleter":
        samples: dict[tuple[Team, str], list[np.ndarray]] = defaultdict(list)
        for frame in frames:
            for player in frame.players:
                role = player.role or "outfield"
                samples[(player.team, role)].append(player.position - frame.ball_position)
        self.priors = {}
        for key, values in samples.items():
            matrix = np.vstack(values)
            covariance = np.cov(matrix.T).tolist() if len(matrix) > 1 else [[25.0, 0.0], [0.0, 25.0]]
            self.priors[key] = RolePrior(
                team=key[0],
                role=key[1],
                mean_relative_position=matrix.mean(axis=0).tolist(),
                covariance=covariance,
                count=len(matrix),
            )
        return self

    def complete(
        self,
        frame: FrameState,
        missing_slots: list[tuple[Team, str, str]],
    ) -> FrameState:
        output = copy.deepcopy(frame)
        for team, role, synthetic_id in missing_slots:
            prior = self.priors.get((team, role)) or self.priors.get((team, "outfield"))
            if prior is None:
                continue
            position = frame.ball_position + np.asarray(prior.mean_relative_position, dtype=float)
            position[0] = np.clip(position[0], 0.0, frame.pitch_length)
            position[1] = np.clip(position[1], 0.0, frame.pitch_width)
            output.players.append(
                PlayerState(
                    player_id=synthetic_id,
                    track_id=synthetic_id,
                    team=team,
                    x=float(position[0]),
                    y=float(position[1]),
                    role=role,
                    tracking_status="inferred",
                    visibility="off_screen",
                    visible=False,
                    confidence=0.25,
                    trajectory_confidence=0.2,
                    position_covariance=prior.covariance,
                    provenance_flags=["formation_prior_completion", "not_observed"],
                    metadata={"prior_count": prior.count},
                )
            )
        output.quality_flags = sorted(set(output.quality_flags + ["contains_completed_players"]))
        return output


def point_in_polygon(point: np.ndarray, polygon: list[list[float]]) -> bool:
    x, y = float(point[0]), float(point[1])
    inside = False
    j = len(polygon) - 1
    for i in range(len(polygon)):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        denominator = yj - yi
        if abs(denominator) < 1e-12:
            denominator = 1e-12 if denominator >= 0 else -1e-12
        intersects = (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / denominator + xi
        if intersects:
            inside = not inside
        j = i
    return inside


def apply_camera_crop(
    frame: FrameState,
    polygon: list[list[float]],
    *,
    preserve_carrier: bool = True,
) -> FrameState:
    output = copy.deepcopy(frame)
    kept = []
    hidden_ids = []
    for player in output.players:
        if point_in_polygon(player.position, polygon) or (preserve_carrier and player.player_id == output.ball_carrier_id):
            player.visible = True
            player.visibility = "visible"
            kept.append(player)
        else:
            hidden_ids.append(player.player_id)
    output.players = kept
    output.visibility_polygon = polygon
    output.quality_flags = sorted(set(output.quality_flags + ["synthetic_camera_crop", "partial_visibility"]))
    output.metadata["hidden_player_ids"] = hidden_ids
    output.validate()
    return output
