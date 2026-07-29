from __future__ import annotations

from copy import deepcopy

import numpy as np

from .affordance import AffordanceEngine
from .schema import FrameState, PlayerState


def option_set_value(options, top_k: int = 3) -> float:
    scores = sorted((option.geometric_score for option in options), reverse=True)
    return float(sum(scores[:top_k]))


def move_player(frame: FrameState, player_id: str, target: np.ndarray) -> FrameState:
    updated = deepcopy(frame)
    player = updated.player(player_id)
    player.x = float(np.clip(target[0], 0.0, frame.pitch_length))
    player.y = float(np.clip(target[1], 0.0, frame.pitch_width))
    return updated


def positioning_uplift(
    frame: FrameState,
    player_id: str,
    candidate_targets: list[np.ndarray],
    engine: AffordanceEngine | None = None,
) -> list[dict[str, float]]:
    """Estimate how alternate earlier positions change the ball carrier's future option menu."""
    engine = engine or AffordanceEngine()
    baseline = option_set_value(engine.generate(frame))
    results = []
    for target in candidate_targets:
        alternative = move_player(frame, player_id, target)
        value = option_set_value(engine.generate(alternative))
        results.append(
            {
                "target_x": float(target[0]),
                "target_y": float(target[1]),
                "option_set_value": value,
                "uplift": value - baseline,
            }
        )
    return results


def radial_candidate_positions(player: PlayerState, radii=(3.0, 6.0), angles=12) -> list[np.ndarray]:
    candidates: list[np.ndarray] = []
    for radius in radii:
        for angle in np.linspace(0.0, 2.0 * np.pi, angles, endpoint=False):
            candidates.append(player.position + radius * np.array([np.cos(angle), np.sin(angle)]))
    return candidates
