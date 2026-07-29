from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
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


def _normalize_direction_map(payload: Any) -> dict[int, dict[str, int]]:
    if not isinstance(payload, dict):
        return {}
    normalized: dict[int, dict[str, int]] = {}
    for raw_period, raw_directions in payload.items():
        if not isinstance(raw_directions, dict):
            continue
        try:
            period = int(str(raw_period).replace("period_", "").replace("half_", ""))
            home = int(raw_directions["home"])
            away = int(raw_directions["away"])
        except (KeyError, TypeError, ValueError):
            continue
        normalized[period] = {"home": home, "away": away}
    return normalized


def validate_skillcorner_attacking_directions(
    periods: set[int],
    *,
    match_payload: dict | None = None,
    expected_directions: dict[int, dict[str, int]] | None = None,
) -> tuple[dict[int, dict[str, int]], str, list[str]]:
    """Validate half-specific directions without modifying provider coordinates.

    SkillCorner's official open-data contract defines a fixed, centre-origin metric field but
    does not publish an attacking-direction field. A caller may supply a match-specific direction
    ledger (or one may be carried in local metadata). Missing evidence remains explicitly
    inconclusive; this function never infers direction from a short run of ball movement.
    """
    metadata_directions = _normalize_direction_map(
        (match_payload or {}).get("attacking_directions")
        or (match_payload or {}).get("period_attacking_directions")
    )
    supplied = expected_directions or metadata_directions
    directions = _normalize_direction_map(supplied)
    warnings: list[str] = []
    if not directions:
        warnings.append(
            "SkillCorner attacking direction is inconclusive: official open data uses fixed "
            "centre-origin coordinates but does not declare half-specific attack direction"
        )
        return {}, "inconclusive", warnings
    invalid_periods = [
        period
        for period, values in directions.items()
        if values["home"] not in {-1, 1}
        or values["away"] not in {-1, 1}
        or values["home"] == values["away"]
    ]
    if invalid_periods:
        warnings.append(
            f"Invalid SkillCorner attacking-direction evidence for periods {invalid_periods}; "
            "directions must be opposite signs"
        )
        return directions, "failed", warnings
    missing = sorted(periods - set(directions))
    if missing:
        warnings.append(f"SkillCorner attacking direction missing for periods {missing}")
        return directions, "inconclusive", warnings
    if {1, 2}.issubset(periods) and directions[1]["home"] == directions[2]["home"]:
        warnings.append(
            "SkillCorner half-direction validation failed: home direction does not switch at halftime"
        )
        return directions, "failed", warnings
    return directions, "validated_external_evidence", warnings


def _checked_point(
    transformer: CoordinateTransformer,
    x: float,
    y: float,
    *,
    pitch_length: float,
    pitch_width: float,
    warnings: list[str],
    context: str,
) -> tuple[float, float]:
    canonical_x, canonical_y = transformer.point(x, y, clip=False)
    if not (0.0 <= canonical_x <= pitch_length and 0.0 <= canonical_y <= pitch_width):
        warnings.append(f"{context} fell outside pitch bounds and was explicitly clipped")
        canonical_x = float(np.clip(canonical_x, 0.0, pitch_length))
        canonical_y = float(np.clip(canonical_y, 0.0, pitch_width))
    return canonical_x, canonical_y


def load_skillcorner_open(
    tracking_path: str | Path,
    match_path: str | Path | None = None,
    dynamic_events_path: str | Path | None = None,
    match_id: str | None = None,
    pitch_length: float = 105.0,
    pitch_width: float = 68.0,
    y_axis_up: bool = True,
    expected_attacking_directions: dict[int, dict[str, int]] | None = None,
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
    periods = {int(row.get("period", 1)) for row in records}
    direction_by_period, direction_status, direction_warnings = (
        validate_skillcorner_attacking_directions(
            periods,
            match_payload=match_payload,
            expected_directions=expected_attacking_directions,
        )
    )
    warnings.extend(direction_warnings)

    for row in records:
        possession = row.get("possession") or {}
        raw_group = possession.get("group") or possession.get("team")
        possession_inferred = False
        try:
            possession_team = canonical_team(raw_group)
        except ValueError:
            possession_team = "home"
            possession_inferred = True
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
                warnings.append(
                    f"SkillCorner player {source_id} frame {row.get('frame')} has unknown team and was omitted"
                )
                continue
            native_x, native_y = float(player["x"]), float(player["y"])
            x, y = _checked_point(
                transformer,
                native_x,
                native_y,
                pitch_length=pitch_length,
                pitch_width=pitch_width,
                warnings=warnings,
                context=f"SkillCorner player {source_id} frame {row.get('frame')}",
            )
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
                    visibility="visible" if is_detected else "off_screen",
                    provenance_flags=["provider_detected" if is_detected else "provider_extrapolated"],
                    metadata={
                        "is_detected": is_detected,
                        "native_x": native_x,
                        "native_y": native_y,
                    },
                )
            )
        ball_data = row.get("ball_data") or {}
        if ball_data.get("x") is None or ball_data.get("y") is None or not players:
            warnings.append(
                f"SkillCorner frame {row.get('frame')} omitted because ball coordinates or players were missing"
            )
            continue
        ball_x, ball_y = _checked_point(
            transformer,
            float(ball_data["x"]),
            float(ball_data["y"]),
            pitch_length=pitch_length,
            pitch_width=pitch_width,
            warnings=warnings,
            context=f"SkillCorner ball frame {row.get('frame')}",
        )
        carrier_source_id = possession.get("player_id")
        carrier_id = f"sc:{carrier_source_id}" if carrier_source_id is not None else None
        carrier_inferred = False
        if not carrier_id or carrier_id not in {player.player_id for player in players}:
            carrier_id = nearest_player_id(players, ball_x, ball_y, team=possession_team)
            carrier_inferred = True
        visibility = row.get("image_corners_projection") or []
        visibility_polygon = (
            [
                list(
                    _checked_point(
                        transformer,
                        float(point[0]),
                        float(point[1]),
                        pitch_length=pitch_length,
                        pitch_width=pitch_width,
                        warnings=warnings,
                        context=f"SkillCorner visible-area vertex frame {row.get('frame')}",
                    )
                )
                for point in visibility
            ]
            if visibility
            else None
        )
        timestamp_s = parse_clock_seconds(row.get("timestamp", 0.0))
        period = int(row.get("period", 1))
        attacking_direction = direction_by_period.get(period, {"home": 1, "away": -1})
        quality_flags = ["partial_visibility"] if visibility_polygon else []
        if direction_status != "validated_external_evidence":
            quality_flags.append("attacking_direction_unverified")
        if possession_inferred:
            quality_flags.append("possession_team_inferred")
        if carrier_inferred:
            quality_flags.append("inferred_ball_carrier")
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
            attacking_direction=attacking_direction,
            period=period,
            frame_rate_hz=10.0,
            visibility_polygon=visibility_polygon,
            source_provider="skillcorner",
            source_match_id=source_match_id,
            ball_confidence=float(ball_data["confidence"]) if ball_data.get("confidence") is not None else None,
            ball_status="observed" if ball_data.get("is_detected", True) else "inferred",
            possession_confidence=(
                0.25 if possession_inferred else (0.6 if carrier_inferred else 1.0)
            ),
            quality_flags=quality_flags,
            metadata={
                "partial_visibility": True,
                "raw_frame": row.get("frame"),
                "native_coordinate_system": {
                    "origin": "pitch_center",
                    "units": "meters",
                    "x_axis": "pitch_long_axis_fixed",
                    "y_axis": "pitch_short_axis_up" if y_axis_up else "pitch_short_axis_down",
                    "coordinates_flipped_by_adapter": False,
                },
                "attacking_direction_validation": {
                    "status": direction_status,
                    "evidence": "caller_or_match_metadata"
                    if direction_by_period
                    else "not_available_in_official_open_contract",
                    "period": period,
                },
                "possession_source": (
                    "fallback_home" if possession_inferred else "provider_possession_group"
                ),
                "ball_carrier_source": (
                    "nearest_possession_team_player"
                    if carrier_inferred
                    else "provider_possession_player_id"
                ),
            },
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
        metadata={
            "pitch_length": pitch_length,
            "pitch_width": pitch_width,
            "native_coordinate_system": "fixed_pitch_center_metric",
            "coordinates_flipped_by_adapter": False,
            "attacking_direction_validation": {
                "status": direction_status,
                "directions": direction_by_period,
            },
        },
    )
