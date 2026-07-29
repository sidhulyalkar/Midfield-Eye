from __future__ import annotations

import math
from typing import Any

import numpy as np

from ..schema import ActionOption, FrameState, PlayerState


def _closing_speed(player: PlayerState, target: np.ndarray) -> float:
    delta = target - player.position
    distance = float(np.linalg.norm(delta))
    if distance < 1e-8:
        return 0.0
    return float(np.dot(player.velocity, delta / distance))


def _entropy(values: list[float]) -> float:
    if not values:
        return 0.0
    array = np.asarray(values, dtype=float)
    array = np.exp(array - float(np.max(array)))
    probs = array / max(float(array.sum()), 1e-12)
    return float(-(probs * np.log2(np.clip(probs, 1e-12, 1.0))).sum())


def frame_relational_metrics(frame: FrameState, options: list[ActionOption]) -> dict[str, Any]:
    carrier = frame.carrier
    teammates = frame.teammates()
    opponents = frame.opponents()
    pass_options = [option for option in options if option.kind == "pass"]
    scores = [float(option.geometric_score) for option in pass_options]
    option_creation = [float(option.features.get("option_creation", 0.0)) for option in pass_options]
    progressive = [float(option.features.get("xt_gain", 0.0)) for option in pass_options]
    close_opponents = [opponent for opponent in opponents if float(np.linalg.norm(opponent.position - carrier.position)) <= 9.0]
    closing = [max(0.0, _closing_speed(opponent, carrier.position)) for opponent in close_opponents]
    pressure_attraction = float(np.clip((len(close_opponents) + sum(closing) / 4.0) / 5.0, 0.0, 1.0))
    teammate_motion = []
    for teammate in teammates:
        distance = float(np.linalg.norm(teammate.position - carrier.position))
        relative_speed = float(np.linalg.norm(teammate.velocity - carrier.velocity))
        teammate_motion.append(relative_speed / max(distance, 2.0))
    support_reactivity = float(np.clip(np.mean(teammate_motion) * 2.5, 0.0, 1.0)) if teammate_motion else 0.0
    menu_entropy = _entropy(scores)
    max_entropy = math.log2(max(len(scores), 2))
    network_brokerage = float(np.clip(menu_entropy / max_entropy, 0.0, 1.0)) if scores else 0.0
    option_enablement = float(np.clip(max(option_creation, default=0.0), 0.0, 1.0))
    progressive_access = float(np.clip(max(progressive, default=0.0) * 4.0, 0.0, 1.0))
    action_diversity = len({option.kind for option in options}) / 3.0
    role_adaptability = float(np.clip(0.45 * action_diversity + 0.30 * support_reactivity + 0.25 * network_brokerage, 0.0, 1.0))
    directive_influence = float(np.clip(0.28 * pressure_attraction + 0.24 * option_enablement + 0.24 * network_brokerage + 0.24 * progressive_access, 0.0, 1.0))
    return {
        "frame_id": frame.frame_id,
        "timestamp_s": float(frame.timestamp_s),
        "pressure_attraction": pressure_attraction,
        "nearby_opponents": len(close_opponents),
        "support_reactivity": support_reactivity,
        "network_brokerage": network_brokerage,
        "option_enablement": option_enablement,
        "progressive_access": progressive_access,
        "action_diversity": action_diversity,
        "role_adaptability": role_adaptability,
        "directive_influence": directive_influence,
        "menu_entropy_bits": menu_entropy,
        "metric_status": "relational_geometry_proxy_requires_context_normalization_for_real_player_comparison",
    }


def _best_lag(left: np.ndarray, right: np.ndarray, max_lag: int = 4) -> tuple[int, float]:
    if left.size < 4 or right.size != left.size or float(np.std(left)) < 1e-9 or float(np.std(right)) < 1e-9:
        return 0, 0.0
    best = (0, -1.0)
    for lag in range(-max_lag, max_lag + 1):
        if lag < 0:
            a, b = left[-lag:], right[:lag]
        elif lag > 0:
            a, b = left[:-lag], right[lag:]
        else:
            a, b = left, right
        if a.size < 3:
            continue
        corr = float(np.corrcoef(a, b)[0, 1])
        if np.isfinite(corr) and corr > best[1]:
            best = (lag, corr)
    return best


def sequence_relational_summary(
    frames: list[FrameState],
    options_by_frame: dict[int, list[ActionOption]],
) -> dict[str, Any]:
    timeline = [frame_relational_metrics(frame, options_by_frame.get(frame.frame_id, [])) for frame in frames]
    keys = [
        "pressure_attraction",
        "support_reactivity",
        "network_brokerage",
        "option_enablement",
        "progressive_access",
        "role_adaptability",
        "directive_influence",
        "menu_entropy_bits",
    ]
    summary = {key: float(np.mean([float(row[key]) for row in timeline])) if timeline else 0.0 for key in keys}
    influence = np.asarray([row["directive_influence"] for row in timeline], dtype=float)
    support = np.asarray([row["support_reactivity"] for row in timeline], dtype=float)
    lag_frames, correlation = _best_lag(influence, support)
    frame_rate = float(frames[0].frame_rate_hz or 1.0) if frames else 1.0
    summary.update(
        {
            "coadaptation_lag_frames": lag_frames,
            "coadaptation_lag_s": lag_frames / max(float(frame_rate), 1e-6),
            "coadaptation_correlation": correlation,
            "peak_directive_influence": max([float(row["directive_influence"]) for row in timeline], default=0.0),
        }
    )
    return {
        "timeline": timeline,
        "summary": summary,
        "interpretation_guardrail": "Relational-control values describe geometry and response timing, not leadership or intent without corroborating evidence.",
    }
