from __future__ import annotations

import math
from dataclasses import replace

import numpy as np

from .affordance import AffordanceEngine
from .schema import ActionOption, FrameState, PlayerState


def _formation(team: str, direction: int) -> list[tuple[float, float]]:
    if direction > 0:
        xs = [8, 25, 25, 25, 42, 42, 42, 62, 62, 78]
    else:
        xs = [97, 80, 80, 80, 63, 63, 63, 43, 43, 27]
    ys = [34, 10, 34, 58, 12, 34, 56, 20, 48, 34]
    return list(zip(xs, ys, strict=True))


def generate_sequence(
    sequence_index: int,
    frames: int = 16,
    fps: float = 5.0,
    seed: int = 7,
) -> list[FrameState]:
    rng = np.random.default_rng(seed + sequence_index)
    home_positions = _formation("home", 1)
    away_positions = _formation("away", -1)
    carrier_slot = 5
    sequence: list[FrameState] = []

    home_velocities = rng.normal(0.0, 1.2, size=(10, 2))
    away_velocities = rng.normal(0.0, 1.2, size=(10, 2))
    home_velocities[:, 0] += 0.8
    away_velocities[:, 0] -= 0.6

    for frame_id in range(frames):
        t = frame_id / fps
        players: list[PlayerState] = []
        for idx, ((x, y), velocity) in enumerate(zip(home_positions, home_velocities, strict=True)):
            oscillation = np.array([0.4 * math.sin(t + idx), 0.6 * math.cos(0.7 * t + idx)])
            position = np.array([x, y]) + t * velocity + oscillation
            position = np.clip(position, [0.5, 0.5], [104.5, 67.5])
            angle = math.atan2(velocity[1], velocity[0])
            players.append(
                PlayerState(
                    player_id=f"H{idx + 1:02d}",
                    team="home",
                    x=float(position[0]),
                    y=float(position[1]),
                    vx=float(velocity[0]),
                    vy=float(velocity[1]),
                    body_angle=float(angle),
                    head_angle=float(angle + rng.normal(0.0, 0.18)),
                    gaze_angle=float(angle + rng.normal(0.0, 0.12)),
                )
            )
        for idx, ((x, y), velocity) in enumerate(zip(away_positions, away_velocities, strict=True)):
            oscillation = np.array([0.4 * math.cos(t + idx), 0.6 * math.sin(0.6 * t + idx)])
            position = np.array([x, y]) + t * velocity + oscillation
            position = np.clip(position, [0.5, 0.5], [104.5, 67.5])
            angle = math.atan2(velocity[1], velocity[0])
            players.append(
                PlayerState(
                    player_id=f"A{idx + 1:02d}",
                    team="away",
                    x=float(position[0]),
                    y=float(position[1]),
                    vx=float(velocity[0]),
                    vy=float(velocity[1]),
                    body_angle=float(angle),
                )
            )
        carrier = players[carrier_slot]
        carrier.body_angle = 0.1 * math.sin(t)
        carrier.head_angle = carrier.body_angle + 0.15 * math.sin(2 * t)
        carrier.gaze_angle = carrier.head_angle + 0.10 * math.cos(1.5 * t)
        sequence.append(
            FrameState(
                sequence_id=f"synthetic_{sequence_index:02d}",
                frame_id=frame_id,
                timestamp_s=t,
                possession_team="home",
                ball_x=carrier.x,
                ball_y=carrier.y,
                ball_vx=carrier.vx,
                ball_vy=carrier.vy,
                ball_carrier_id=carrier.player_id,
                players=players,
                source_provider="synthetic",
                source_match_id=f"synthetic_{sequence_index:02d}",
                metadata={"source": "synthetic", "annotation_status": "bootstrap"},
            )
        )
    return sequence


def generate_dataset(sequences: int = 10, frames: int = 16, seed: int = 7) -> list[FrameState]:
    return [
        frame
        for sequence_index in range(sequences)
        for frame in generate_sequence(sequence_index, frames=frames, seed=seed)
    ]


def bootstrap_labels(options: list[ActionOption], seed: int = 7) -> list[ActionOption]:
    """Create reproducible pseudo-labels for a smoke-test dataset.

    These are explicitly not human ground truth. They create a runnable benchmark and exercise
    the full training path before the ten real sequences are annotated.
    """
    rng = np.random.default_rng(seed)
    grouped: dict[tuple[str, int], list[ActionOption]] = {}
    for option in options:
        grouped.setdefault((option.sequence_id, option.frame_id), []).append(option)
    labeled: list[ActionOption] = []
    for frame_options in grouped.values():
        latent = np.array(
            [
                0.45 * option.geometric_score
                + 0.20 * option.features["visibility"]
                + 0.18 * option.features["future_space"]
                + 0.12 * np.tanh(option.features["xt_gain"] * 6)
                + 0.08 * option.features["target_motion_alignment"]
                + rng.normal(0.0, 0.025)
                for option in frame_options
            ]
        )
        scaled = (latent - latent.min()) / max(float(np.ptp(latent)), 1e-8)
        available_cut = float(np.quantile(scaled, 0.58))
        selected_index = int(np.argmax(scaled))
        for index, (option, value) in enumerate(zip(frame_options, scaled, strict=True)):
            labeled.append(
                replace(
                    option,
                    label_available=bool(value >= available_cut),
                    label_value=float(value),
                    label_selected=index == selected_index,
                    provenance="bootstrap-pseudo-label",
                )
            )
    return labeled


def build_bootstrap_options(frames: list[FrameState], engine: AffordanceEngine | None = None):
    engine = engine or AffordanceEngine()
    options = [option for frame in frames for option in engine.generate(frame)]
    return bootstrap_labels(options)
