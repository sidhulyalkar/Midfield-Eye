from __future__ import annotations

import copy
import math
from collections import defaultdict

import numpy as np

from ..schema import FrameState, PlayerState
from .orientation import estimate_body_orientation


def trajectory_confidence(
    observation_confidence: float | None,
    gap_frames: int = 0,
    interpolation: bool = False,
) -> float:
    """Core trajectory-confidence decay without importing a provider adapter."""
    base = 0.5 if observation_confidence is None else float(np.clip(observation_confidence, 0, 1))
    decay = math.exp(-0.35 * max(gap_frames, 0))
    if interpolation:
        decay *= 0.75
    return float(np.clip(base * decay, 0.0, 1.0))


def _track_key(player: PlayerState) -> tuple[str, str]:
    return player.team, player.track_id or player.source_player_id or player.player_id


def _transition(dt: float) -> np.ndarray:
    return np.array(
        [[1.0, 0.0, dt, 0.0], [0.0, 1.0, 0.0, dt], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]],
        dtype=float,
    )


def _process_covariance(dt: float, process_noise: float) -> np.ndarray:
    q = process_noise**2
    return q * np.array(
        [
            [dt**4 / 4, 0.0, dt**3 / 2, 0.0],
            [0.0, dt**4 / 4, 0.0, dt**3 / 2],
            [dt**3 / 2, 0.0, dt**2, 0.0],
            [0.0, dt**3 / 2, 0.0, dt**2],
        ],
        dtype=float,
    )


def reconstruct_trajectories(
    frames: list[FrameState],
    *,
    process_noise: float = 2.0,
    max_speed_mps: float = 12.0,
) -> list[FrameState]:
    """Causally smooth trajectories and derive kinematics with a constant-velocity Kalman filter.

    Only current and previous observations are used. Offline interpolation is a separate function
    and is explicitly marked because it uses a future endpoint.
    """
    output = copy.deepcopy(frames)
    grouped: dict[str, list[FrameState]] = defaultdict(list)
    for frame in output:
        grouped[frame.sequence_id].append(frame)

    for sequence_frames in grouped.values():
        sequence_frames.sort(key=lambda frame: (frame.timestamp_s, frame.frame_id))
        filters: dict[tuple[str, str], tuple[np.ndarray, np.ndarray, float, np.ndarray]] = {}
        for frame in sequence_frames:
            for player in frame.players:
                key = _track_key(player)
                measurement = player.position
                measurement_cov = player.covariance_matrix
                if key not in filters:
                    state = np.array([player.x, player.y, player.vx, player.vy], dtype=float)
                    covariance = np.diag([measurement_cov[0, 0], measurement_cov[1, 1], 16.0, 16.0])
                    previous_velocity = state[2:].copy()
                    filters[key] = (state, covariance, frame.timestamp_s, previous_velocity)
                    player.trajectory_confidence = trajectory_confidence(player.confidence)
                    continue

                state, covariance, previous_time, previous_velocity = filters[key]
                dt = max(frame.timestamp_s - previous_time, 1e-3)
                transition = _transition(dt)
                state = transition @ state
                covariance = transition @ covariance @ transition.T + _process_covariance(dt, process_noise)
                observation = np.array([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]])
                innovation = measurement - observation @ state
                innovation_cov = observation @ covariance @ observation.T + measurement_cov
                gain = covariance @ observation.T @ np.linalg.pinv(innovation_cov)
                state = state + gain @ innovation
                covariance = (np.eye(4) - gain @ observation) @ covariance

                speed = float(np.linalg.norm(state[2:]))
                if speed > max_speed_mps:
                    state[2:] *= max_speed_mps / speed
                player.x = float(np.clip(state[0], 0.0, frame.pitch_length))
                player.y = float(np.clip(state[1], 0.0, frame.pitch_width))
                player.vx = float(state[2])
                player.vy = float(state[3])
                player.ax = float((state[2] - previous_velocity[0]) / dt)
                player.ay = float((state[3] - previous_velocity[1]) / dt)
                if speed > 0.2:
                    movement_heading = math.atan2(player.vy, player.vx)
                    previous_heading = float(player.metadata.get("movement_heading", movement_heading))
                    wrapped = (movement_heading - previous_heading + math.pi) % (2 * math.pi) - math.pi
                    player.turning_rate = float(wrapped / dt)
                    player.metadata["movement_heading"] = movement_heading
                player.position_covariance = covariance[:2, :2].tolist()
                player.trajectory_confidence = trajectory_confidence(player.confidence)
                if "causal_kalman" not in player.provenance_flags:
                    player.provenance_flags.append("causal_kalman")
                filters[key] = (state, covariance, frame.timestamp_s, state[2:].copy())
            if "causal_trajectory_reconstruction" not in frame.quality_flags:
                frame.quality_flags.append("causal_trajectory_reconstruction")
    return estimate_body_orientation(output, copy_frames=False)


def interpolate_short_gaps(
    frames: list[FrameState],
    *,
    max_gap_frames: int = 3,
    covariance_growth_m2: float = 1.5,
) -> list[FrameState]:
    """Offline linear interpolation for short gaps, always preserving inferred provenance."""
    output = copy.deepcopy(frames)
    grouped: dict[str, list[FrameState]] = defaultdict(list)
    for frame in output:
        grouped[frame.sequence_id].append(frame)

    for sequence_frames in grouped.values():
        sequence_frames.sort(key=lambda frame: (frame.timestamp_s, frame.frame_id))
        sightings: dict[tuple[str, str], list[tuple[int, PlayerState]]] = defaultdict(list)
        for index, frame in enumerate(sequence_frames):
            for player in frame.players:
                sightings[_track_key(player)].append((index, player))

        for key, track in sightings.items():
            for (left_index, left), (right_index, right) in zip(track, track[1:]):
                gap = right_index - left_index - 1
                if gap <= 0 or gap > max_gap_frames:
                    continue
                for offset in range(1, gap + 1):
                    frame_index = left_index + offset
                    frame = sequence_frames[frame_index]
                    if any(_track_key(existing) == key for existing in frame.players):
                        continue
                    fraction = offset / (gap + 1)
                    interpolated = copy.deepcopy(left)
                    interpolated.x = float((1 - fraction) * left.x + fraction * right.x)
                    interpolated.y = float((1 - fraction) * left.y + fraction * right.y)
                    dt = max(right.metadata.get("timestamp_s", frame.timestamp_s) - left.metadata.get("timestamp_s", sequence_frames[left_index].timestamp_s), 1e-3)
                    interpolated.vx = float((right.x - left.x) / dt)
                    interpolated.vy = float((right.y - left.y) / dt)
                    interpolated.tracking_status = "interpolated"
                    interpolated.visibility = "interpolated"
                    interpolated.visible = False
                    interpolated.observation_id = f"interpolated:{frame.sequence_id}:{frame.frame_id}:{key[1]}"
                    covariance = (1 - fraction) * left.covariance_matrix + fraction * right.covariance_matrix
                    covariance += np.eye(2) * covariance_growth_m2 * gap
                    interpolated.position_covariance = covariance.tolist()
                    interpolated.trajectory_confidence = trajectory_confidence(
                        min(left.confidence or 0.5, right.confidence or 0.5),
                        gap_frames=gap,
                        interpolation=True,
                    )
                    interpolated.provenance_flags = sorted(
                        set(interpolated.provenance_flags + ["offline_interpolation", "uses_future_endpoint"])
                    )
                    frame.players.append(interpolated)
                    frame.quality_flags = sorted(set(frame.quality_flags + ["contains_interpolated_players"]))
    return output
