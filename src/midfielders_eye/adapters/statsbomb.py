from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from ..schema import ActionOption, EventState, FrameState, PlayerState, Team
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


def _checked_point(
    transformer: CoordinateTransformer,
    point: list[float],
    warnings: list[str],
    *,
    context: str,
) -> tuple[float, float]:
    native_x, native_y = float(point[0]), float(point[1])
    if not (0.0 <= native_x <= 120.0 and 0.0 <= native_y <= 80.0):
        warnings.append(f"{context} fell outside StatsBomb 120x80 bounds and was explicitly clipped")
        native_x = float(np.clip(native_x, 0.0, 120.0))
        native_y = float(np.clip(native_y, 0.0, 80.0))
    return transformer.point(native_x, native_y, clip=False)


def _checked_polygon(
    transformer: CoordinateTransformer,
    points: list[float] | list[list[float]],
    warnings: list[str],
    *,
    context: str,
) -> list[list[float]]:
    if not points:
        return []
    pairs = (
        list(zip(points[::2], points[1::2], strict=True))
        if isinstance(points[0], (int, float))
        else points
    )
    return [
        list(_checked_point(transformer, [float(x), float(y)], warnings, context=context))
        for x, y in pairs
    ]


def load_statsbomb_360(
    events_path: str | Path,
    three_sixty_path: str | Path,
    match_id: str | None = None,
    home_team_name: str | None = None,
    pitch_length: float = 105.0,
    pitch_width: float = 68.0,
    receiver_match_tolerance_m: float = 4.0,
    receiver_ambiguity_margin_m: float = 0.75,
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
        start_x, start_y = _checked_point(
            transformer,
            location,
            warnings,
            context=f"StatsBomb event {event_id} start",
        )
        event_type = (event.get("type") or {}).get("name", "Unknown")
        end_location = None
        for nested_name in ("pass", "carry", "shot", "dribble", "clearance"):
            nested = event.get(nested_name)
            if isinstance(nested, dict) and nested.get("end_location"):
                end_location = nested["end_location"]
                break
        end_x = end_y = None
        if end_location:
            end_x, end_y = _checked_point(
                transformer,
                end_location,
                warnings,
                context=f"StatsBomb event {event_id} end",
            )
        timestamp_s = _event_seconds(event)
        nested_event = event.get(event_type.lower()) if isinstance(event_type, str) else None
        if not isinstance(nested_event, dict):
            nested_event = {}
        nested_outcome = nested_event.get("outcome") or event.get("outcome")
        recipient = nested_event.get("recipient") if event_type.lower() == "pass" else None
        recipient_source_id = (
            str(recipient.get("id") or recipient.get("name"))
            if isinstance(recipient, dict) and (recipient.get("id") or recipient.get("name"))
            else None
        )
        parsed_event = EventState(
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
            outcome=str(
                nested_outcome.get("name") if isinstance(nested_outcome, dict) else nested_outcome
            )
            if nested_outcome
            else None,
            source_provider="statsbomb360",
            source_match_id=source_match_id,
            metadata={
                "raw_team": team_name,
                "possession": event.get("possession"),
                "recipient_source_id": recipient_source_id,
                "selected_action_is_not_complete_action_menu": True,
            },
        )
        parsed_events.append(parsed_event)

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
            x, y = _checked_point(
                transformer,
                point,
                warnings,
                context=f"StatsBomb event {event_id} freeze-frame player",
            )
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
                    source_player_id=actor_source_id if item.get("actor") else None,
                    tracking_status="observed",
                    visible=True,
                    visibility="visible",
                    observation_id=f"sb360:{event_id}:{len(players)}",
                    provenance_flags=["event_freeze_frame_observation"],
                    metadata={
                        "event_local_identity": not item.get("actor", False),
                        "identity_scope": "event" if not item.get("actor", False) else "event_actor",
                    },
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
                    visibility="visible",
                    provenance_flags=["actor_inserted_at_event_location"],
                )
            )
            warnings.append(f"Actor inserted at event location for event {event_id}")
        visible_area = _checked_polygon(
            transformer,
            snapshot.get("visible_area", []),
            warnings,
            context=f"StatsBomb event {event_id} visible-area vertex",
        )
        selected_action: dict[str, Any] = {
            "event_id": event_id,
            "kind": event_type.lower(),
            "end_x": end_x,
            "end_y": end_y,
            "receiver_source_id": recipient_source_id,
            "receiver_player_id": None,
            "receiver_mapping": "not_applicable",
            "receiver_distance_m": None,
            "selected_action_is_not_complete_action_menu": True,
        }
        if event_type.lower() == "pass":
            selected_action["receiver_mapping"] = "unmapped"
            if end_x is not None and end_y is not None:
                target = np.array([end_x, end_y], dtype=float)
                candidates = sorted(
                    (
                        (float(np.linalg.norm(player.position - target)), player)
                        for player in players
                        if player.team == team and player.player_id != actor_id
                    ),
                    key=lambda item: item[0],
                )
                if candidates:
                    nearest_distance, nearest = candidates[0]
                    second_distance = candidates[1][0] if len(candidates) > 1 else float("inf")
                    selected_action["receiver_distance_m"] = nearest_distance
                    if (
                        nearest_distance <= receiver_match_tolerance_m
                        and second_distance - nearest_distance >= receiver_ambiguity_margin_m
                    ):
                        selected_action["receiver_player_id"] = nearest.player_id
                        selected_action["receiver_mapping"] = (
                            "event_local_nearest_freeze_frame_teammate_to_pass_end"
                        )
                    elif nearest_distance > receiver_match_tolerance_m:
                        selected_action["receiver_mapping"] = "unmapped_no_teammate_within_tolerance"
                    else:
                        selected_action["receiver_mapping"] = "unmapped_ambiguous_nearest_teammates"
            if selected_action["receiver_player_id"] is None:
                warnings.append(f"Selected receiver could not be mapped for StatsBomb event {event_id}")
        parsed_event.metadata["selected_action"] = selected_action
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
                "selected_action": selected_action,
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


def label_statsbomb_selected_options(
    options: list[ActionOption],
    frames: list[FrameState],
    *,
    carry_target_tolerance_m: float = 4.0,
) -> list[ActionOption]:
    """Apply event-supported selection labels while leaving action-menu labels untouched.

    Pass receivers are event-local matches from freeze-frame geometry. They must not be reused as
    persistent player identities. If the receiver mapping is ambiguous, selection remains unknown
    instead of manufacturing a negative label for every generated option.
    """
    frame_lookup = {(frame.sequence_id, frame.frame_id): frame for frame in frames}
    by_frame: dict[tuple[str, int], list[ActionOption]] = {}
    for option in options:
        by_frame.setdefault((option.sequence_id, option.frame_id), []).append(option)
    for key, frame_options in by_frame.items():
        frame = frame_lookup.get(key)
        selected = frame.metadata.get("selected_action") if frame else None
        if not isinstance(selected, dict):
            continue
        kind = selected.get("kind")
        chosen: ActionOption | None = None
        confidence = 1.0
        if kind == "pass" and selected.get("receiver_player_id"):
            chosen = next(
                (
                    option
                    for option in frame_options
                    if option.kind == "pass"
                    and option.target_player_id == selected["receiver_player_id"]
                ),
                None,
            )
            confidence = 0.75
        elif kind == "carry" and selected.get("end_x") is not None and selected.get("end_y") is not None:
            target = np.array([selected["end_x"], selected["end_y"]], dtype=float)
            carry_options = [option for option in frame_options if option.kind == "carry"]
            if carry_options:
                candidate = min(
                    carry_options,
                    key=lambda option: float(np.linalg.norm(option.target - target)),
                )
                if float(np.linalg.norm(candidate.target - target)) <= carry_target_tolerance_m:
                    chosen = candidate
                    confidence = 0.65
        if chosen is None:
            continue
        for option in frame_options:
            option.label_selected = option is chosen
            option.label_confidence = confidence
    return options
