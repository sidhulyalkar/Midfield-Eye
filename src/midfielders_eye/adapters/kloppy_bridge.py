from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pandas as pd

from ..schema import FrameState, PlayerState, Team
from .base import AdapterResult
from .normalization import nearest_player_id


def frames_from_kloppy_dataframe(
    dataframe: pd.DataFrame,
    home_player_ids: Iterable[str],
    away_player_ids: Iterable[str],
    team_id_map: dict[str, Team] | None = None,
    provider_id: str = "kloppy",
    match_id: str = "match",
    sequence_id: str | None = None,
    pitch_length: float = 105.0,
    pitch_width: float = 68.0,
) -> AdapterResult:
    """Convert a Kloppy-style wide tracking DataFrame into canonical frames.

    Expected player columns are `<id>_x`, `<id>_y`; optional `<id>_s` speed and `<id>_d`
    direction are preserved in metadata. This bridge intentionally accepts the DataFrame rather
    than depending on private provider internals.
    """
    sequence_id = sequence_id or f"{provider_id}:{match_id}"
    home_ids = {str(value) for value in home_player_ids}
    away_ids = {str(value) for value in away_player_ids}
    all_ids = sorted(home_ids | away_ids)
    team_id_map = team_id_map or {}
    frames: list[FrameState] = []
    warnings: list[str] = []

    for row_index, row in dataframe.iterrows():
        players: list[PlayerState] = []
        for source_id in all_ids:
            x_key = f"{source_id}_x"
            y_key = f"{source_id}_y"
            if x_key not in row or y_key not in row or pd.isna(row[x_key]) or pd.isna(row[y_key]):
                continue
            team: Team = "home" if source_id in home_ids else "away"
            player = PlayerState(
                player_id=f"{provider_id}:{source_id}",
                source_player_id=source_id,
                team=team,
                x=float(row[x_key]),
                y=float(row[y_key]),
                tracking_status="observed",
                metadata={
                    "speed_native": row.get(f"{source_id}_s"),
                    "direction_native": row.get(f"{source_id}_d"),
                },
            )
            players.append(player)
        if not players or pd.isna(row.get("ball_x")) or pd.isna(row.get("ball_y")):
            continue
        owning_team_id = str(row.get("ball_owning_team_id", ""))
        possession_team = team_id_map.get(owning_team_id)
        if possession_team is None:
            possession_team = "home"
            warnings.append("Unknown ball_owning_team_id; defaulted affected frames to home")
        ball_x = float(row["ball_x"])
        ball_y = float(row["ball_y"])
        carrier_id = nearest_player_id(players, ball_x, ball_y, team=possession_team)
        frame = FrameState(
            sequence_id=sequence_id,
            frame_id=int(row.get("frame_id", row_index)),
            timestamp_s=float(row.get("timestamp", row_index)),
            possession_team=possession_team,
            ball_x=ball_x,
            ball_y=ball_y,
            ball_vx=0.0,
            ball_vy=0.0,
            ball_carrier_id=carrier_id,
            players=players,
            pitch_length=pitch_length,
            pitch_width=pitch_width,
            period=int(row.get("period_id", 1)),
            source_provider=provider_id,
            source_match_id=match_id,
            metadata={"ball_state": row.get("ball_state")},
        )
        frame.validate()
        frames.append(frame)
    return AdapterResult(frames, provider_id=provider_id, source_match_id=match_id, warnings=sorted(set(warnings)))


def load_sportec_open(
    match_id: str,
    limit: int | None = None,
    sample_rate: float | None = None,
) -> AdapterResult:
    """Load one of the seven Sportec open matches through the optional Kloppy package."""
    try:
        from kloppy import sportec
    except ImportError as exc:  # pragma: no cover - optional integration
        raise RuntimeError("Install the provider extra: pip install -e '.[providers]'") from exc

    dataset = sportec.load_open_tracking_data(match_id=match_id, limit=limit, sample_rate=sample_rate)
    dataframe = dataset.to_df()
    metadata: Any = dataset.metadata
    teams = list(metadata.teams)
    if len(teams) != 2:
        raise ValueError("Expected exactly two teams in Sportec metadata")
    home_team, away_team = teams
    home_ids = [str(player.player_id) for player in home_team.players]
    away_ids = [str(player.player_id) for player in away_team.players]
    team_id_map = {str(home_team.team_id): "home", str(away_team.team_id): "away"}
    return frames_from_kloppy_dataframe(
        dataframe,
        home_ids,
        away_ids,
        team_id_map=team_id_map,
        provider_id="sportec_open",
        match_id=match_id,
    )
