from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..schema import EventState, FrameState, PlayerState, Team
from .base import AdapterResult
from .normalization import CoordinateTransformer


def _load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _team_name(payload: dict | None) -> str | None:
    if not payload:
        return None
    return payload.get("name") or str(payload.get("id"))


def _event_seconds(event: dict) -> float:
    minute = float(event.get("minute", 0))
    second = float(event.get("second", 0))
    timestamp = event.get("timestamp")
    if timestamp and isinstance(timestamp, str):
        parts = timestamp.split(":")
        if len(parts) == 3:
            second = float(parts[2])
    return minute * 60.0 + second


def load_statsbomb_360(
    events_path: str | Path,
    three_sixty_path: str | Path,
    match_id: str | None = None,
    home_team_name: str | None = None,
    pitch_length: float = 105.0,
    pitch_width: float = 68.0,
) -> AdapterResult:
    """Load event-centered StatsBomb 360 snapshots into the canonical contract.

    StatsBomb 360 is not continuous tracking. Non-actor identities are therefore deliberately
    event-local, velocities remain zero, and every frame is marked as partial visibility.
    """
    events_payload = _load_json(events_path)
    freeze_payload = _load_json(three_sixty_path)
    freeze_by_event = {str(item["event_uuid"]): item for item in freeze_payload}
    transformer = CoordinateTransformer(
        pitch_length=pitch_length,
        pitch_width=pitch_width,
        origin="top_left",
        units="meters",
        y_axis="down",
        native_length=120.0,
        native_width=80.0,
    )

    team_names: list[str] = []
    for event in events_payload:
        name = _team_name(event.get("team"))
        if name and name not in team_names:
            team_names.append(name)
    if home_team_name is None and team_names:
        home_team_name = team_names[0]
    team_map: dict[str, Team] = {
        name: ("home" if name == home_team_name else "away") for name in team_names
    }

    source_match_id = match_id or Path(events_path).stem
    sequence_id = f"statsbomb:{source_match_id}"
    frames: list[FrameState] = []
    parsed_events: list[EventState] = []
    warnings: list[str] = []

    for event_index, event in enumerate(events_payload):
        event_id = str(event.get("id", event_index))
        team_name = _team_name(event.get("team"))
        team = team_map.get(team_name or "")
        actor = event.get("player") or {}
        actor_source_id = str(actor.get("id") or actor.get("name") or f"actor:{event_id}")
        actor_id = f"sb:{actor_source_id}"
        location = event.get("location")
        if not location or team is None:
            continue
        start_x, start_y = transformer.point(float(location[0]), float(location[1]))
        event_type = (event.get("type") or {}).get("name", "Unknown")
        end_location = None
        for nested_name in ("pass", "carry", "shot", "dribble", "clearance"):
            nested = event.get(nested_name)
            if isinstance(nested, dict) and nested.get("end_location"):
                end_location = nested["end_location"]
                break
        end_x = end_y = None
        if end_location:
            end_x, end_y = transformer.point(float(end_location[0]), float(end_location[1]))
        timestamp_s = _event_seconds(event)
        parsed_events.append(
            EventState(
                sequence_id=sequence_id,
                event_id=event_id,
                timestamp_s=timestamp_s,
                period=int(event.get("period", 1)),
                event_type=event_type,
                team=team,
                actor_id=actor_id,
                start_x=start_x,
                start_y=start_y,
                end_x=end_x,
                end_y=end_y,
                outcome=str(event.get("outcome", "")) or None,
                source_provider="statsbomb360",
                source_match_id=source_match_id,
                metadata={"raw_team": team_name, "possession": event.get("possession")},
            )
        )

        snapshot = freeze_by_event.get(event_id)
        if not snapshot:
            continue
        players: list[PlayerState] = []
        actor_found = False
        teammate_index = 0
        opponent_index = 0
        for item in snapshot.get("freeze_frame", []):
            point = item.get("location")
            if not point:
                continue
            x, y = transformer.point(float(point[0]), float(point[1]))
            item_team: Team = team if item.get("teammate") else ("away" if team == "home" else "home")
            if item.get("actor"):
                player_id = actor_id
                actor_found = True
            elif item_team == team:
                player_id = f"sb:{event_id}:teammate:{teammate_index}"
                teammate_index += 1
            else:
                player_id = f"sb:{event_id}:opponent:{opponent_index}"
                opponent_index += 1
            players.append(
                PlayerState(
                    player_id=player_id,
                    team=item_team,
                    x=x,
                    y=y,
                    role="goalkeeper" if item.get("keeper") else "player",
                    source_player_id=None,
                    tracking_status="observed",
                    visible=True,
                    metadata={"event_local_identity": not item.get("actor", False)},
                )
            )
        if not actor_found:
            players.append(
                PlayerState(
                    player_id=actor_id,
                    team=team,
                    x=start_x,
                    y=start_y,
                    source_player_id=actor_source_id,
                    tracking_status="inferred",
                    visible=True,
                )
            )
            warnings.append(f"Actor inserted at event location for event {event_id}")
        visible_area = transformer.polygon(snapshot.get("visible_area", []))
        frame = FrameState(
            sequence_id=sequence_id,
            frame_id=event_index,
            timestamp_s=timestamp_s,
            possession_team=team,
            ball_x=start_x,
            ball_y=start_y,
            ball_vx=0.0,
            ball_vy=0.0,
            ball_carrier_id=actor_id,
            players=players,
            pitch_length=pitch_length,
            pitch_width=pitch_width,
            period=int(event.get("period", 1)),
            visibility_polygon=visible_area or None,
            source_provider="statsbomb360",
            source_match_id=source_match_id,
            quality_flags=["event_snapshot", "no_velocity", "partial_visibility", "ephemeral_non_actor_ids"],
            metadata={
                "partial_visibility": True,
                "state_semantics": "event_freeze_frame",
                "event_id": event_id,
                "event_type": event_type,
            },
        )
        frame.validate()
        frames.append(frame)

    if not frames:
        warnings.append("No event UUIDs overlapped between events and 360 files")
    return AdapterResult(
        frames=frames,
        events=parsed_events,
        provider_id="statsbomb360",
        source_match_id=source_match_id,
        warnings=sorted(set(warnings)),
        metadata={"team_map": team_map, "snapshot_count": len(frames)},
    )
