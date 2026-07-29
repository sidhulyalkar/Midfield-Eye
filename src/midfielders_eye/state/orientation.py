from __future__ import annotations

import copy
import math
from collections import defaultdict

import numpy as np

from ..schema import FrameState, PlayerState


def _track_key(player: PlayerState) -> tuple[str, str]:
    return player.team, player.track_id or player.source_player_id or player.player_id


def _circular_blend(previous: float, current: float, weight: float) -> float:
    previous_vector = np.array([math.cos(previous), math.sin(previous)], dtype=float)
    current_vector = np.array([math.cos(current), math.sin(current)], dtype=float)
    vector = (1.0 - weight) * previous_vector + weight * current_vector
    if float(np.linalg.norm(vector)) < 1e-8:
        return current
    return float(math.atan2(vector[1], vector[0]))


def estimate_body_orientation(
    frames: list[FrameState],
    *,
    minimum_speed_mps: float = 0.6,
    smoothing_weight: float = 0.45,
    hold_seconds: float = 1.0,
    copy_frames: bool = True,
) -> list[FrameState]:
    """Estimate a conservative body-heading proxy from reconstructed motion.

    This is not a pose or gaze estimator. Observed orientation is never overwritten. When motion is
    sufficiently fast, velocity heading is used as a low-confidence proxy. At low speed, the most
    recent proxy may be held briefly with decaying confidence, then the original angle is retained.
    Every inferred value records its source and confidence in metadata and provenance flags.
    """
    output = copy.deepcopy(frames) if copy_frames else frames
    grouped: dict[str, list[FrameState]] = defaultdict(list)
    for frame in output:
        grouped[frame.sequence_id].append(frame)

    for sequence_frames in grouped.values():
        sequence_frames.sort(key=lambda frame: (frame.timestamp_s, frame.frame_id))
        history: dict[tuple[str, str], tuple[float, float, float]] = {}
        for frame in sequence_frames:
            for player in frame.players:
                if player.metadata.get("body_angle_observed", False):
                    player.metadata.setdefault("body_angle_source", "observed")
                    player.metadata.setdefault("body_heading_confidence", player.confidence or 1.0)
                    history[_track_key(player)] = (
                        player.body_angle,
                        frame.timestamp_s,
                        float(player.metadata["body_heading_confidence"]),
                    )
                    continue

                key = _track_key(player)
                speed = player.speed
                if speed >= minimum_speed_mps:
                    motion_heading = float(math.atan2(player.vy, player.vx))
                    previous = history.get(key)
                    heading = (
                        _circular_blend(previous[0], motion_heading, smoothing_weight)
                        if previous is not None
                        else motion_heading
                    )
                    speed_confidence = float(np.clip((speed - minimum_speed_mps) / 4.0, 0.0, 1.0))
                    trajectory_confidence = player.trajectory_confidence
                    if trajectory_confidence is None:
                        trajectory_confidence = player.confidence if player.confidence is not None else 0.5
                    confidence = float(np.clip((0.25 + 0.75 * speed_confidence) * trajectory_confidence, 0.0, 0.85))
                    player.body_angle = heading
                    player.metadata["body_angle_source"] = "motion_proxy"
                    player.metadata["body_heading_confidence"] = confidence
                    if "orientation_from_motion_proxy" not in player.provenance_flags:
                        player.provenance_flags.append("orientation_from_motion_proxy")
                    history[key] = (heading, frame.timestamp_s, confidence)
                    continue

                previous = history.get(key)
                if previous is not None and frame.timestamp_s - previous[1] <= hold_seconds:
                    elapsed = max(frame.timestamp_s - previous[1], 0.0)
                    confidence = float(previous[2] * math.exp(-elapsed / max(hold_seconds, 1e-6)))
                    player.body_angle = previous[0]
                    player.metadata["body_angle_source"] = "motion_proxy_hold"
                    player.metadata["body_heading_confidence"] = confidence
                    if "orientation_motion_hold" not in player.provenance_flags:
                        player.provenance_flags.append("orientation_motion_hold")
                else:
                    player.metadata.setdefault("body_angle_source", "unknown")
                    player.metadata.setdefault("body_heading_confidence", 0.0)
    return output
