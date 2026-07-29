from __future__ import annotations

import numpy as np

from ..schema import FrameState


def _polygon_signature(polygon: list[list[float]] | None) -> tuple[np.ndarray, float] | None:
    if not polygon:
        return None
    points = np.asarray(polygon, dtype=float)
    if points.ndim != 2 or points.shape[1] != 2:
        return None
    centroid = points.mean(axis=0)
    x, y = points[:, 0], points[:, 1]
    area = 0.5 * abs(float(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1))))
    return centroid, area


def detect_camera_cuts(
    frames: list[FrameState],
    *,
    centroid_jump_m: float = 22.0,
    area_ratio_limit: float = 3.0,
    median_track_jump_m: float = 12.0,
) -> list[int]:
    cuts: list[int] = []
    for previous, current in zip(frames, frames[1:]):
        if previous.sequence_id != current.sequence_id:
            continue
        previous_signature = _polygon_signature(previous.visibility_polygon)
        current_signature = _polygon_signature(current.visibility_polygon)
        polygon_cut = False
        if previous_signature and current_signature:
            centroid_distance = float(np.linalg.norm(previous_signature[0] - current_signature[0]))
            area_ratio = max(previous_signature[1], current_signature[1]) / max(
                min(previous_signature[1], current_signature[1]), 1e-6
            )
            polygon_cut = centroid_distance > centroid_jump_m or area_ratio > area_ratio_limit

        prior = {player.track_id or player.player_id: player.position for player in previous.players}
        jumps = [
            float(np.linalg.norm(player.position - prior[player.track_id or player.player_id]))
            for player in current.players
            if (player.track_id or player.player_id) in prior
        ]
        track_cut = bool(jumps) and float(np.median(jumps)) > median_track_jump_m
        if polygon_cut or track_cut:
            cuts.append(current.frame_id)
            current.quality_flags = sorted(set(current.quality_flags + ["camera_cut"] ))
    return cuts
