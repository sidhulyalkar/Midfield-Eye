from __future__ import annotations


import numpy as np
import pandas as pd


def _identity(row: pd.Series) -> str:
    kind = str(row["kind"])
    if kind == "pass":
        return f"pass:{row.get('target_player_id')}"
    if kind == "hold":
        return "hold"
    return f"carry:{round(float(row['target_x']), 1)}:{round(float(row['target_y']), 1)}"


def temporal_rank_metrics(
    dataframe: pd.DataFrame,
    score_column: str = "geometric_score",
    top_k: int = 3,
) -> dict[str, float]:
    """Measure how violently the predicted action menu changes between adjacent frames."""
    overlaps: list[float] = []
    top1_switches: list[float] = []
    rank_correlations: list[float] = []
    for _, sequence in dataframe.groupby("sequence_id", sort=False):
        frames = []
        for frame_id, group in sequence.groupby("frame_id", sort=True):
            ordered = group.sort_values(score_column, ascending=False).copy()
            ordered["_identity"] = ordered.apply(_identity, axis=1)
            frames.append((frame_id, ordered))
        for (_, left), (_, right) in zip(frames[:-1], frames[1:], strict=False):
            left_top = left["_identity"].head(top_k).tolist()
            right_top = right["_identity"].head(top_k).tolist()
            union = set(left_top) | set(right_top)
            overlaps.append(len(set(left_top) & set(right_top)) / len(union) if union else 1.0)
            top1_switches.append(float(left_top[:1] != right_top[:1]))
            common = sorted(set(left["_identity"]) & set(right["_identity"]))
            if len(common) >= 2:
                left_rank = {value: rank for rank, value in enumerate(left["_identity"], start=1)}
                right_rank = {value: rank for rank, value in enumerate(right["_identity"], start=1)}
                a = np.array([left_rank[value] for value in common], dtype=float)
                b = np.array([right_rank[value] for value in common], dtype=float)
                correlation = np.corrcoef(a, b)[0, 1]
                if np.isfinite(correlation):
                    rank_correlations.append(float(correlation))
    return {
        f"top{top_k}_jaccard": float(np.mean(overlaps)) if overlaps else float("nan"),
        "top1_switch_rate": float(np.mean(top1_switches)) if top1_switches else float("nan"),
        "common_option_rank_correlation": float(np.mean(rank_correlations)) if rank_correlations else float("nan"),
    }


def option_lifetimes(dataframe: pd.DataFrame) -> pd.DataFrame:
    rows = dataframe.copy()
    rows["option_identity"] = rows.apply(_identity, axis=1)
    output = []
    for (sequence_id, identity), group in rows.groupby(["sequence_id", "option_identity"]):
        frame_ids = sorted(group["frame_id"].unique())
        runs: list[list[int]] = []
        current: list[int] = []
        for frame_id in frame_ids:
            if current and frame_id != current[-1] + 1:
                runs.append(current)
                current = []
            current.append(int(frame_id))
        if current:
            runs.append(current)
        for run_index, run in enumerate(runs):
            output.append(
                {
                    "sequence_id": sequence_id,
                    "option_identity": identity,
                    "run_index": run_index,
                    "start_frame": run[0],
                    "end_frame": run[-1],
                    "lifetime_frames": len(run),
                }
            )
    return pd.DataFrame(output)
