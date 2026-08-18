from __future__ import annotations

import numpy as np
import pandas as pd


def add_baseline_scores(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Add the frozen, interpretable B0/B1/B2/B2-V scores.

    B2 intentionally excludes body/viewpoint cues. B2-V adds those cues on top
    of the exact same dynamic geometry score so the viewpoint ablation has a
    literal interpretation.
    """

    output = dataframe.copy()
    kind = output["kind"].astype(str)
    distance = output["distance_m"].fillna(0.0).to_numpy(float)
    progress = output["forward_progress"].fillna(0.0).to_numpy(float)

    # B0: the frozen naive control. Passes use distance only; carries use progress only.
    output["naive_score"] = np.where(
        kind.eq("pass"),
        -distance / 45.0,
        np.where(kind.eq("carry"), progress, -0.15),
    )

    # B1: static geometry. It excludes velocity, future-space, body/viewpoint, and creation cues.
    output["static_score"] = (
        0.22 * np.tanh(output["lane_clearance_m"].fillna(0.0).to_numpy(float) / 4.0)
        + 0.18 * output["receiver_space"].fillna(0.0).to_numpy(float)
        - 0.18 * output["receiver_pressure"].fillna(0.0).to_numpy(float)
        + 0.20 * np.tanh(output["forward_progress"].fillna(0.0).to_numpy(float) * 4.0)
        + 0.24 * np.tanh(output["xt_gain"].fillna(0.0).to_numpy(float) * 5.0)
        - 0.08 * np.minimum(distance / 45.0, 1.0)
    )

    # B2: dynamic geometry. These weights mirror the default affordance engine
    # except for body-orientation and visibility terms, which are reserved for B2-V.
    robust_clearance = output.get(
        "uncertainty_adjusted_clearance_m",
        output["lane_clearance_m"],
    ).fillna(0.0)
    interception_margin = output["interception_margin_s"].fillna(0.0).to_numpy(float)
    future_space = output["future_space"].fillna(0.0).to_numpy(float)
    option_creation = output["option_creation"].fillna(0.0).to_numpy(float)
    state_confidence = output.get(
        "state_confidence",
        pd.Series(0.5, index=output.index),
    ).fillna(0.5)

    output["dynamic_score"] = (
        0.14 * np.tanh(robust_clearance.to_numpy(float) / 4.0)
        + 0.17 * np.tanh(interception_margin / 1.5)
        + 0.15 * output["receiver_space"].fillna(0.0).to_numpy(float)
        + 0.13 * future_space
        + 0.10 * np.tanh(progress * 4.0)
        + 0.13 * np.tanh(output["xt_gain"].fillna(0.0).to_numpy(float) * 5.0)
        + 0.05 * np.tanh(option_creation)
        + 0.04 * state_confidence.to_numpy(float)
        - 0.04 * np.minimum(distance / 45.0, 1.0)
    )

    # B2-V: same dynamic geometry plus carrier body orientation and perceptual
    # visibility. Camera visibility remains an evidence/uncertainty signal in
    # the underlying features rather than being mistaken for literal player gaze.
    body_orientation = output["body_orientation"].fillna(0.0).to_numpy(float)
    perceptual_visibility = output.get(
        "perceptual_visibility_proxy",
        output["visibility"],
    ).fillna(0.0)
    output["viewpoint_score"] = (
        output["dynamic_score"].to_numpy(float)
        + 0.06 * body_orientation
        + 0.07 * perceptual_visibility.to_numpy(float)
    )
    return output
