"""Normalize a pair of Metrica-style home/away tracking tables.

Raw sample formats differ across games. This script supports the common two-header CSV layout and
exports stable columns for `midfielders_eye.adapters.metrica.load_metrica_csv`.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def read_tracking(path: Path, prefix: str) -> pd.DataFrame:
    raw = pd.read_csv(path, header=[0, 1, 2])
    columns = []
    for top, middle, bottom in raw.columns:
        tokens = [str(value).strip() for value in (top, middle, bottom) if str(value) != "nan"]
        joined = "_".join(tokens).lower()
        if "frame" in joined:
            columns.append("frame")
        elif "time" in joined:
            columns.append("time_s")
        elif "period" in joined:
            columns.append("period")
        elif "ball" in joined and joined.endswith("x"):
            columns.append("ball_x")
        elif "ball" in joined and joined.endswith("y"):
            columns.append("ball_y")
        else:
            axis = "x" if joined.endswith("x") else "y" if joined.endswith("y") else None
            player_tokens = [token for token in tokens if token.isdigit()]
            if axis and player_tokens:
                columns.append(f"{prefix}_{int(player_tokens[-1])}_{axis}")
            else:
                columns.append(f"drop_{len(columns)}")
    raw.columns = columns
    return raw[[column for column in raw.columns if not column.startswith("drop_")]]


def add_velocities(data: pd.DataFrame) -> pd.DataFrame:
    output = data.copy()
    dt = output["time_s"].diff().replace(0, np.nan)
    for column in list(output.columns):
        if column.endswith("_x") or column.endswith("_y"):
            if column.startswith("ball_"):
                prefix = "ball"
                axis = column[-1]
            else:
                prefix = column[:-2]
                axis = column[-1]
            output[f"{prefix}_v{axis}"] = output[column].diff() / dt
    return output.bfill().fillna(0.0)


def main(home_path: Path, away_path: Path, output_path: Path) -> None:
    home = read_tracking(home_path, "Home")
    away = read_tracking(away_path, "Away")
    shared = [column for column in ("frame", "time_s", "period", "ball_x", "ball_y") if column in home]
    away_only = [column for column in away.columns if column not in shared]
    combined = pd.concat([home[shared + [c for c in home.columns if c not in shared]], away[away_only]], axis=1)
    combined = add_velocities(combined)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(output_path, index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--away", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.home, args.away, args.output)
