from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import linear_sum_assignment

from ..schema import FrameState


@dataclass(slots=True)
class TrackStitchProposal:
    source_track_id: str
    target_track_id: str
    team: str
    gap_s: float
    distance_m: float
    score: float


def propose_track_stitches(
    frames: list[FrameState],
    *,
    max_gap_s: float = 1.2,
    max_distance_m: float = 7.0,
) -> list[TrackStitchProposal]:
    endpoints: dict[str, tuple] = {}
    starts: dict[str, tuple] = {}
    for frame in sorted(frames, key=lambda item: item.timestamp_s):
        for player in frame.players:
            track = player.track_id or player.source_player_id or player.player_id
            starts.setdefault(track, (frame.timestamp_s, player))
            endpoints[track] = (frame.timestamp_s, player)
    ending = [(track, *value) for track, value in endpoints.items()]
    starting = [(track, *value) for track, value in starts.items()]
    if not ending or not starting:
        return []
    cost = np.full((len(ending), len(starting)), 1e6, dtype=float)
    for i, (source_id, end_time, source) in enumerate(ending):
        for j, (target_id, start_time, target) in enumerate(starting):
            gap = start_time - end_time
            if source_id == target_id or source.team != target.team or not 0 < gap <= max_gap_s:
                continue
            predicted = source.position + gap * source.velocity
            distance = float(np.linalg.norm(target.position - predicted))
            if distance <= max_distance_m:
                role_penalty = 2.0 if source.role and target.role and source.role != target.role else 0.0
                jersey_penalty = 3.0 if source.jersey_number and target.jersey_number and source.jersey_number != target.jersey_number else 0.0
                cost[i, j] = distance + role_penalty + jersey_penalty
    rows, columns = linear_sum_assignment(cost)
    proposals: list[TrackStitchProposal] = []
    for row, column in zip(rows, columns):
        if cost[row, column] >= 1e6:
            continue
        source_id, end_time, source = ending[row]
        target_id, start_time, target = starting[column]
        distance = float(np.linalg.norm(target.position - (source.position + (start_time - end_time) * source.velocity)))
        proposals.append(
            TrackStitchProposal(
                source_track_id=source_id,
                target_track_id=target_id,
                team=source.team,
                gap_s=float(start_time - end_time),
                distance_m=distance,
                score=float(np.exp(-distance / max(max_distance_m, 1e-6))),
            )
        )
    return proposals
