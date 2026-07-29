from __future__ import annotations

from copy import deepcopy

from .schema import FrameState
from .synthetic import generate_dataset


def _clone(frame: FrameState) -> FrameState:
    return FrameState.from_dict(deepcopy(frame.to_dict()))


def generate_provider_views(
    sequences: int = 4,
    frames_per_sequence: int = 12,
    seed: int = 7,
) -> dict[str, list[FrameState]]:
    """Create four provider-shaped views of identical synthetic football scenes.

    These views validate software behavior under modality differences. They are not substitutes
    for real provider data and must never be reported as football evidence.
    """
    base = generate_dataset(sequences=sequences, frames=frames_per_sequence, seed=seed)
    full: list[FrameState] = []
    broadcast: list[FrameState] = []
    snapshots: list[FrameState] = []
    gsr: list[FrameState] = []

    for frame in base:
        complete = _clone(frame)
        complete.source_provider = "metrica_demo"
        complete.source_match_id = complete.sequence_id
        full.append(complete)

        partial = _clone(frame)
        partial.source_provider = "skillcorner_demo"
        partial.source_match_id = partial.sequence_id
        partial.visibility_polygon = [[18.0, 4.0], [92.0, 4.0], [92.0, 64.0], [18.0, 64.0]]
        partial.metadata["partial_visibility"] = True
        partial.quality_flags.append("simulated_broadcast_visibility")
        for player in partial.players:
            visible = 18 <= player.x <= 92 and 4 <= player.y <= 64
            player.visible = visible
            player.tracking_status = "observed" if visible else "extrapolated"
            player.confidence = 0.97 if visible else 0.68
        broadcast.append(partial)

        if frame.frame_id % 4 == 0:
            snapshot = _clone(frame)
            snapshot.source_provider = "statsbomb360_demo"
            snapshot.source_match_id = snapshot.sequence_id
            keep_teammates = sorted(snapshot.teammates(), key=lambda p: p.x, reverse=True)[:5]
            keep_opponents = sorted(
                snapshot.opponents(), key=lambda p: (p.x - snapshot.carrier.x) ** 2 + (p.y - snapshot.carrier.y) ** 2
            )[:6]
            kept_ids = {snapshot.ball_carrier_id} | {p.player_id for p in keep_teammates + keep_opponents}
            snapshot.players = [player for player in snapshot.players if player.player_id in kept_ids]
            snapshot.visibility_polygon = [[26.0, 6.0], [104.0, 6.0], [104.0, 62.0], [26.0, 62.0]]
            snapshot.metadata["partial_visibility"] = True
            snapshot.metadata["state_semantics"] = "event_freeze_frame"
            snapshot.quality_flags.extend(["event_snapshot", "no_velocity", "partial_visibility"])
            snapshot.frame_id = frame.frame_id // 4
            for player in snapshot.players:
                player.vx = 0.0
                player.vy = 0.0
                player.head_angle = None
                player.gaze_angle = None
            snapshot.ball_vx = 0.0
            snapshot.ball_vy = 0.0
            snapshots.append(snapshot)

        if frame.frame_id % 2 == 0:
            video_state = _clone(frame)
            video_state.source_provider = "soccertrack_v2_demo"
            video_state.source_match_id = video_state.sequence_id
            video_state.frame_id = frame.frame_id // 2
            video_state.quality_flags.extend(["ball_inferred_from_actor", "no_velocity"])
            for player in video_state.players:
                player.vx = 0.0
                player.vy = 0.0
                player.body_angle = 0.0
                player.head_angle = None
                player.gaze_angle = None
            video_state.ball_vx = 0.0
            video_state.ball_vy = 0.0
            gsr.append(video_state)

    return {
        "metrica_demo": full,
        "skillcorner_demo": broadcast,
        "statsbomb360_demo": snapshots,
        "soccertrack_v2_demo": gsr,
    }
