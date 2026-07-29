from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ..schema import FrameState, PlayerState


def _player_ids(columns: list[str]) -> list[str]:
    ids = set()
    for column in columns:
        if column.endswith("_x") and column.startswith(("Home_", "Away_")):
            ids.add(column[:-2])
    return sorted(ids)


def load_metrica_csv(
    tracking_path: str | Path,
    sequence_id: str,
    possession_team: str = "home",
    pitch_length: float = 105.0,
    pitch_width: float = 68.0,
    ball_carrier_id: str | None = None,
) -> list[FrameState]:
    """Load a simplified, normalized Metrica-style tracking CSV.

    Expected columns: frame, time_s, ball_x, ball_y and paired `Home_1_x`, `Home_1_y`,
    `Away_1_x`, `Away_1_y` columns. Coordinates may be normalized [0,1] or metric.
    Velocity columns are optional. The exact raw Metrica headers differ by sample game, so
    use `scripts/normalize_metrica.py` first for a stable interface.
    """
    data = pd.read_csv(tracking_path)
    players = _player_ids(list(data.columns))
    if not players:
        raise ValueError("No normalized player coordinate columns found")
    normalized = max(
        float(data[[f"{pid}_x" for pid in players]].max().max()),
        float(data[[f"{pid}_y" for pid in players]].max().max()),
    ) <= 1.5

    frames: list[FrameState] = []
    for row in data.itertuples(index=False):
        states = []
        for pid in players:
            x = float(getattr(row, f"{pid}_x"))
            y = float(getattr(row, f"{pid}_y"))
            if np.isnan(x) or np.isnan(y):
                continue
            if normalized:
                x *= pitch_length
                y *= pitch_width
            team = "home" if pid.startswith("Home_") else "away"
            vx = float(getattr(row, f"{pid}_vx", 0.0))
            vy = float(getattr(row, f"{pid}_vy", 0.0))
            if normalized:
                vx *= pitch_length
                vy *= pitch_width
            states.append(PlayerState(pid, team, x, y, vx, vy))
        ball_x = float(row.ball_x) * (pitch_length if normalized else 1.0)
        ball_y = float(row.ball_y) * (pitch_width if normalized else 1.0)
        carrier = ball_carrier_id
        if carrier is None:
            eligible = [p for p in states if p.team == possession_team]
            carrier = min(eligible, key=lambda p: np.linalg.norm(p.position - [ball_x, ball_y])).player_id
        frame = FrameState(
            sequence_id=sequence_id,
            frame_id=int(row.frame),
            timestamp_s=float(row.time_s),
            possession_team=possession_team,
            ball_x=ball_x,
            ball_y=ball_y,
            ball_vx=float(getattr(row, "ball_vx", 0.0)),
            ball_vy=float(getattr(row, "ball_vy", 0.0)),
            ball_carrier_id=carrier,
            players=states,
            frame_rate_hz=None,
            source_provider="metrica",
            source_match_id=sequence_id,
            metadata={"source": "metrica-normalized"},
        )
        frame.validate()
        frames.append(frame)
    return frames
