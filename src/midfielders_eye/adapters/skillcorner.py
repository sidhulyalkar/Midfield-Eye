from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ..schema import EventState, FrameState, PlayerState, Team
from .base import AdapterResult
from .normalization import CoordinateTransformer, canonical_team, enrich_kinematics, nearest_player_id, parse_clock_seconds


def _read_jsonl(path: str | Path) -> list[dict]:
    records = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                records.append(json.loads(line))
    return records


def _extract_pitch(match_payload: dict | None, default_length: float, default_width: float) -> tuple[float, float]:
    if not match_payload:
        return default_length, default_width
    candidates = [
        match_payload.get("pitch"),
        match_payload.get("pitch_size"),
        match_payload.get("field"),
    ]
    for candidate in candidates:
        if isinstance(candidate, dict):
            length = candidate.get("length") or candidate.get("pitch_length")
            width = candidate.get("width") or candidate.get("pitch_width")
            if length and width:
                return float(length), float(width)
    return default_length, default_width


def _lineup_team_map(match_payload: dict | None) -> dict[str, Team]:
    mapping: dict[str, Team] = {}
    if not match_payload:
        return mapping
    for key, team in (("home_team", "home"), ("away_team", "away"), ("home", "home"), ("away", "away")):
        payload = match_payload.get(key)
        if not isinstance(payload, dict):
            continue
        for player in payload.get("players", payload.get("lineup", [])):
            player_id = player.get("id") or player.get("player_id")
            if player_id is not None:
                mapping[str(player_id)] = team  # type: ignore[assignment]
    return mapping


def load_skillcorner_open(
    tracking_path: str | Path,
    match_path: str | Path | None = None,
    dynamic_events_path: str | Path | None = None,
    match_id: str | None = None,
    pitch_length: float = 105.0,
    pitch_width: float = 68.0,
    y_axis_up: bool = True,
) -> AdapterResult:
    """Load SkillCorner open broadcast tracking JSONL.

    Observed and extrapolated players remain distinct so downstream experiments can quantify
    how much tactical value depends on off-camera completion.
    """
    match_payload = None
    if match_path:
        match_payload = json.loads(Path(match_path).read_text(encoding="utf-8"))
        pitch_length, pitch_width = _extract_pitch(match_payload, pitch_length, pitch_width)
    source_match_id = match_id or (Path(match_path).stem if match_path else Path(tracking_path).stem)
    sequence_id = f"skillcorner:{source_match_id}"
    transformer = CoordinateTransformer(
        pitch_length=pitch_length,
        pitch_width=pitch_width,
        origin="center",
        units="meters",
        y_axis="up" if y_axis_up else "down",
    )
    lineup_map = _lineup_team_map(match_payload)
    records = _read_jsonl(tracking_path)
    frames: list[FrameState] = []
    warnings: list[str] = []

    for row in records:
        possession = row.get("possession") or {}
        raw_group = possession.get("group") or possession.get("team")
        try:
            possession_team = canonical_team(raw_group)
        except ValueError:
            possession_team = "home"
            warnings.append("Missing or unknown possession group; defaulted affected frames to home")
        players: list[PlayerState] = []
        for player in row.get("player_data", []):
            source_id = str(player.get("player_id") or player.get("id"))
            raw_team = player.get("group") or player.get("team")
            team = lineup_map.get(source_id)
            if team is None and raw_team is not None:
                try:
                    team = canonical_team(raw_team)
                except ValueError:
                    team = None
            if team is None:
                continue
            x, y = transformer.point(float(player["x"]), float(player["y"]))
            is_detected = bool(player.get("is_detected", True))
            confidence = player.get("confidence")
            players.append(
                PlayerState(
                    player_id=f"sc:{source_id}",
                    source_player_id=source_id,
                    team=team,
                    x=x,
                    y=y,
                    role=player.get("role"),
                    jersey_number=player.get("number") or player.get("jersey_number"),
                    tracking_status="observed" if is_detected else "extrapolated",
                    confidence=float(confidence) if confidence is not None else None,
                    visible=is_detected,
                    metadata={"is_detected": is_detected},
                )
            )
        ball_data = row.get("ball_data") or {}
        if ball_data.get("x") is None or ball_data.get("y") is None or not players:
            continue
        ball_x, ball_y = transformer.point(float(ball_data["x"]), float(ball_data["y"]))
        carrier_source_id = possession.get("player_id")
        carrier_id = f"sc:{carrier_source_id}" if carrier_source_id is not None else None
        if not carrier_id or carrier_id not in {player.player_id for player in players}:
            carrier_id = nearest_player_id(players, ball_x, ball_y, team=possession_team)
        visibility = row.get("image_corners_projection") or []
        visibility_polygon = transformer.polygon(visibility) if visibility else None
        timestamp_s = parse_clock_seconds(row.get("timestamp", 0.0))
        frame = FrameState(
            sequence_id=sequence_id,
            frame_id=int(row.get("frame", len(frames))),
            timestamp_s=timestamp_s,
            possession_team=possession_team,
            ball_x=ball_x,
            ball_y=ball_y,
            ball_vx=0.0,
            ball_vy=0.0,
            ball_carrier_id=carrier_id,
            players=players,
            pitch_length=pitch_length,
            pitch_width=pitch_width,
            period=int(row.get("period", 1)),
            frame_rate_hz=10.0,
            visibility_polygon=visibility_polygon,
            source_provider="skillcorner",
            source_match_id=source_match_id,
            ball_confidence=float(ball_data["confidence"]) if ball_data.get("confidence") is not None else None,
            quality_flags=["partial_visibility"] if visibility_polygon else [],
            metadata={"partial_visibility": True, "raw_frame": row.get("frame")},
        )
        frame.validate()
        frames.append(frame)
    enrich_kinematics(frames, max_gap_s=0.35)

    events: list[EventState] = []
    if dynamic_events_path:
        dynamic = pd.read_csv(dynamic_events_path)
        for index, row in dynamic.iterrows():
            event_team = None
            for field in ("group", "team", "team_side"):
                if field in row and pd.notna(row[field]):
                    try:
                        event_team = canonical_team(row[field])
                    except ValueError:
                        pass
                    break
            timestamp = row.get("timestamp", row.get("start_time", row.get("time", 0.0)))
            events.append(
                EventState(
                    sequence_id=sequence_id,
                    event_id=str(row.get("event_id", index)),
                    timestamp_s=parse_clock_seconds(timestamp),
                    period=int(row.get("period", 1)),
                    event_type=str(row.get("event_type", row.get("type", "dynamic_event"))),
                    team=event_team,
                    actor_id=f"sc:{row['player_id']}" if "player_id" in row and pd.notna(row["player_id"]) else None,
                    source_provider="skillcorner",
                    source_match_id=source_match_id,
                    metadata={key: value for key, value in row.to_dict().items() if pd.notna(value)},
                )
            )

    return AdapterResult(
        frames=frames,
        events=events,
        provider_id="skillcorner",
        source_match_id=source_match_id,
        warnings=sorted(set(warnings)),
        metadata={"pitch_length": pitch_length, "pitch_width": pitch_width},
    )
