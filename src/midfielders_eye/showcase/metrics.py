from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np

from ..schema import ActionOption, FrameState


def _softmax(values: np.ndarray) -> np.ndarray:
    if values.size == 0:
        return values
    shifted = values - float(np.max(values))
    exp = np.exp(shifted)
    return exp / max(float(exp.sum()), 1e-12)


def frame_showcase_metrics(frame: FrameState, options: list[ActionOption]) -> dict[str, float | int]:
    scores = np.array([option.geometric_score for option in options], dtype=float)
    probabilities = _softmax(scores * 4.0)
    entropy = float(-(probabilities * np.log2(np.clip(probabilities, 1e-12, 1.0))).sum())
    ranked = sorted(options, key=lambda item: item.geometric_score, reverse=True)
    best = ranked[0] if ranked else None
    second = ranked[1] if len(ranked) > 1 else None
    passing = [option for option in options if option.kind == "pass"]
    visible_options = sum(option.features.get("visibility", 0.0) >= 0.5 for option in passing)
    progressive = [option.features.get("xt_gain", 0.0) for option in passing]
    option_creation = [option.features.get("option_creation", 0.0) for option in passing]
    margins = [option.features.get("interception_margin_s", 0.0) for option in passing]
    state_confidence = [option.features.get("state_confidence", 0.5) for option in options]
    carrier_pressure = max(
        [option.features.get("receiver_pressure", 0.0) for option in options if option.kind == "hold"]
        or [0.0]
    )
    threshold = float(np.quantile(scores, 0.65)) if scores.size else 0.0
    return {
        "frame_id": frame.frame_id,
        "timestamp_s": float(frame.timestamp_s),
        "menu_breadth": int(np.sum(scores >= threshold)) if scores.size else 0,
        "visible_options": int(visible_options),
        "option_entropy_bits": entropy,
        "best_option_value": 0.0 if best is None else float(best.geometric_score),
        "best_option_gap": 0.0
        if best is None or second is None
        else float(best.geometric_score - second.geometric_score),
        "max_progressive_gain": float(max(progressive, default=0.0)),
        "max_option_creation": float(max(option_creation, default=0.0)),
        "best_interception_margin_s": float(max(margins, default=0.0)),
        "pressure_resilience": float(1.0 / (1.0 + carrier_pressure)),
        "state_confidence": float(np.mean(state_confidence)) if state_confidence else 0.5,
    }


def scenario_summary(
    frames: list[FrameState], options_by_frame: dict[int, list[ActionOption]]
) -> dict[str, Any]:
    timeline = [frame_showcase_metrics(frame, options_by_frame.get(frame.frame_id, [])) for frame in frames]
    numeric: dict[str, list[float]] = defaultdict(list)
    for row in timeline:
        for key, value in row.items():
            if key not in {"frame_id", "timestamp_s"}:
                numeric[key].append(float(value))
    aggregate = {
        key: {
            "mean": float(np.mean(values)),
            "max": float(np.max(values)),
            "min": float(np.min(values)),
        }
        for key, values in numeric.items()
    }
    return {
        "timeline": timeline,
        "aggregate": aggregate,
        "metric_status": "model_derived_from_illustrative_synthetic_state",
    }
