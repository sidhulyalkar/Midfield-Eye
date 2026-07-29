from __future__ import annotations

import numpy as np
import pandas as pd


def add_baseline_scores(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Add honest non-learned baselines to an option dataframe."""
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
    return output
