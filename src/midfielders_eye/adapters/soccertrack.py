from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from ..schema import EventState, FrameState, PlayerState, Team
from .base import AdapterResult
from .normalization import CoordinateTransformer

SUPPORTED_POSSESSION_EVENTS = {"Pass", "Drive", "Header", "High Pass", "Cross", "Shot", "Free Kick"}


def load_soccertrack_v2(
    gsr_path: str | Path,
    bas_path: str | Path,
    match_id: str | None = None,
    half: int = 1,
    pitch_length: float = 105.0,
    pitch_width: float = 68.0,
) -> AdapterResult:
    """Create event-centered full-pitch snapshots from SoccerTrack v2 GSR + BAS.

    GSR contains players but no ball. BAS supplies actor, team and event time, so only event-aligned
    frames with an identifiable actor become canonical affordance frames.
    """
    records = json.loads(Path(gsr_path).read_text(encoding="utf-8"))
    bas = json.loads(Path(bas_path).read_text(encoding="utf-8"))
    source_match_id = match_id or str(bas.get("UrlLocal") or Path(gsr_path).stem.split("_")[0])
    sequence_id = f"soccertrack_v2:{source_match_id}:half{half}"
    transformer = CoordinateTransformer(
        pitch_length=pitch_length,
        pitch_width=pitch_width,
        origin="center",
        units="meters",
        y_axis="up",
    )
    by_frame: dict[int, list[dict]] = defaultdict(list)
    for record in records:
        by_frame[int(record["image_id"])].append(record)

    frames: list[FrameState] = []
    events: list[EventState] = []
    warnings: list[str] = []
    side_map: dict[str, Team] = {"left": "home", "right": "away"}
    frame_counter = 0

    for event_index, annotation in enumerate(bas.get("annotations", [])):
        game_time = str(annotation.get("gameTime", ""))
        try:
            event_half = int(game_time.split("-")[0].strip())
        except (ValueError, IndexError):
            event_half = half
        if event_half != half:
            continue
        label = str(annotation.get("label", "Unknown"))
        position_ms = int(annotation.get("position", 0))
        image_id = round(position_ms / 40.0)
        raw_team = annotation.get("team")
        team = side_map.get(str(raw_team).lower())
        actor_source_id = annotation.get("player_id")
        actor_id = f"stv2:{actor_source_id}" if actor_source_id is not None else None
        timestamp_s = position_ms / 1000.0
        event = EventState(
            sequence_id=sequence_id,
            event_id=f"{source_match_id}:{half}:{event_index}",
            timestamp_s=timestamp_s,
            period=half,
            event_type=label,
            team=team,
            actor_id=actor_id,
            source_provider="soccertrack_v2",
            source_match_id=source_match_id,
            metadata={"visibility": annotation.get("visibility"), "image_id": image_id},
        )
        events.append(event)
        if label not in SUPPORTED_POSSESSION_EVENTS or team is None or actor_id is None:
            continue
        entities = by_frame.get(image_id)
        if not entities:
            warnings.append(f"No GSR records for BAS frame {image_id}")
            continue
        players: list[PlayerState] = []
        for entity in entities:
            role = str(entity.get("role", "player"))
            raw_side = entity.get("team_side")
            entity_team = side_map.get(str(raw_side).lower()) if raw_side is not None else None
            if role not in {"player", "goalkeeper"} or entity_team is None:
                continue
            source_id = entity.get("player_id")
            if source_id is None:
                source_id = f"track:{entity.get('track_id')}"
            player_id = f"stv2:{source_id}"
            x, y = transformer.point(float(entity["x"]), float(entity["y"]))
            players.append(
                PlayerState(
                    player_id=player_id,
                    source_player_id=str(source_id),
                    team=entity_team,
                    x=x,
                    y=y,
                    role=role,
                    jersey_number=entity.get("jersey_number"),
                    tracking_status="observed",
                    visible=True,
                    metadata={"track_id": entity.get("track_id"), "bbox_image": entity.get("bbox_image")},
                )
            )
        actor = next((player for player in players if player.player_id == actor_id), None)
        if actor is None:
            warnings.append(f"Actor {actor_id} absent from GSR frame {image_id}")
            continue
        frame = FrameState(
            sequence_id=sequence_id,
            frame_id=frame_counter,
            timestamp_s=timestamp_s,
            possession_team=team,
            ball_x=actor.x,
            ball_y=actor.y,
            ball_vx=0.0,
            ball_vy=0.0,
            ball_carrier_id=actor_id,
            players=players,
            pitch_length=pitch_length,
            pitch_width=pitch_width,
            period=half,
            frame_rate_hz=25.0,
            source_provider="soccertrack_v2",
            source_match_id=source_match_id,
            quality_flags=["event_snapshot", "ball_inferred_from_actor", "no_velocity"],
            metadata={"image_id": image_id, "event_type": label, "full_pitch": True},
        )
        frame.validate()
        frames.append(frame)
        frame_counter += 1

    return AdapterResult(
        frames=frames,
        events=events,
        provider_id="soccertrack_v2",
        source_match_id=source_match_id,
        warnings=sorted(set(warnings)),
        metadata={"half": half, "side_map": side_map},
    )
