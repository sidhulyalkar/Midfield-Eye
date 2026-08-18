from __future__ import annotations

import numpy as np
import pandas as pd


def add_baseline_scores(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Add the frozen, interpretable B0/B1/B2/B2-V scores.

    B2 intentionally excludes body/viewpoint cues. B2-V adds those cues on top
    of the exact same dynamic geometry score so the viewpoint ablation has a
    literal interpretation.

    Optional dynamic and viewpoint columns default to neutral values. This keeps
    B0/B1-only fixtures and older provider exports readable without inventing a
    positive dynamic or perceptual signal.
    """

    output = dataframe.copy()

    def column(name: str, default: float = 0.0) -> pd.Series:
        if name in output.columns:
            return output[name].fillna(default)
        return pd.Series(default, index=output.index, dtype=float)

    kind = output["kind"].astype(str)
    distance = column("distance_m").to_numpy(float)
    progress = column("forward_progress").to_numpy(float)
    lane_clearance = column("lane_clearance_m")
    receiver_space = column("receiver_space").to_numpy(float)
    receiver_pressure = column("receiver_pressure").to_numpy(float)
    xt_gain = column("xt_gain").to_numpy(float)

    # B0: the frozen naive control. Passes use distance only; carries use progress only.
    output["naive_score"] = np.where(
        kind.eq("pass"),
        -distance / 45.0,
        np.where(kind.eq("carry"), progress, -0.15),
    )

    # B1: static geometry. It excludes velocity, future-space, body/viewpoint, and creation cues.
    output["static_score"] = (
        0.22 * np.tanh(lane_clearance.to_numpy(float) / 4.0)
        + 0.18 * receiver_space
        - 0.18 * receiver_pressure
        + 0.20 * np.tanh(progress * 4.0)
        + 0.24 * np.tanh(xt_gain * 5.0)
        - 0.08 * np.minimum(distance / 45.0, 1.0)
    )

    # B2: dynamic geometry. These weights mirror the default affordance engine
    # except for body-orientation and visibility terms, which are reserved for B2-V.
    robust_clearance = column(
        "uncertainty_adjusted_clearance_m",
        default=0.0,
    )
    if "uncertainty_adjusted_clearance_m" not in output.columns:
        robust_clearance = lane_clearance
    interception_margin = column("interception_margin_s").to_numpy(float)
    future_space = column("future_space").to_numpy(float)
    option_creation = column("option_creation").to_numpy(float)
    state_confidence = column("state_confidence", default=0.5).to_numpy(float)

    output["dynamic_score"] = (
        0.14 * np.tanh(robust_clearance.to_numpy(float) / 4.0)
        + 0.17 * np.tanh(interception_margin / 1.5)
        + 0.15 * receiver_space
        + 0.13 * future_space
        + 0.10 * np.tanh(progress * 4.0)
        + 0.13 * np.tanh(xt_gain * 5.0)
        + 0.05 * np.tanh(option_creation)
        + 0.04 * state_confidence
        - 0.04 * np.minimum(distance / 45.0, 1.0)
    )

    # B2-V: same dynamic geometry plus carrier body orientation and perceptual
    # visibility. Camera visibility remains an evidence/uncertainty signal in
    # the underlying features rather than being mistaken for literal player gaze.
    body_orientation = column("body_orientation").to_numpy(float)
    if "perceptual_visibility_proxy" in output.columns:
        perceptual_visibility = column("perceptual_visibility_proxy").to_numpy(float)
    else:
        perceptual_visibility = column("visibility").to_numpy(float)
    output["viewpoint_score"] = (
        output["dynamic_score"].to_numpy(float)
        + 0.06 * body_orientation
        + 0.07 * perceptual_visibility
    )
    return output
