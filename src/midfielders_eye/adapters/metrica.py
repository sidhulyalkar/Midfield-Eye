from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd

from ..fusion import EventFrameAlignment, align_events_to_frames
from ..schema import EventState, FrameState, PlayerState
from .base import AdapterResult
from .normalization import canonical_team


def _player_ids(columns: list[str]) -> list[str]:
    ids = set()
    for column in columns:
        if column.endswith("_x") and column.startswith(("Home_", "Away_")):
            ids.add(column[:-2])
    return sorted(ids)


def _clean_header(value: object) -> str:
    return str(value).strip().lstrip("\ufeff")


def _raw_metrica_headers(rows: list[list[str]]) -> list[str]:
    """Combine Metrica's team, shirt-number, and axis header rows.

    Official sample tracking CSVs use three physical header rows. The provider coordinate
    convention is fixed, normalized ``[0, 1]`` with a top-left origin; this function only names
    the columns and never flips or stretches a half.
    """
    if len(rows) < 3:
        raise ValueError("Raw Metrica tracking CSV must contain three header rows")
    width = max(len(row) for row in rows[:3])
    padded = [row + [""] * (width - len(row)) for row in rows[:3]]
    team_row, identity_row, axis_row = padded
    columns: list[str] = []
    active_group = ""
    active_identity = ""
    for index in range(width):
        team_cell = _clean_header(team_row[index])
        identity_cell = _clean_header(identity_row[index])
        axis_cell = _clean_header(axis_row[index]).lower()
        if index < 3:
            base = identity_cell or axis_cell or team_cell
            normalized = base.lower().replace(" ", "").replace("[s]", "")
            aliases = {
                "period": "period",
                "frame": "frame",
                "time": "time_s",
                "times": "time_s",
            }
            columns.append(aliases.get(normalized, base or f"metadata_{index}"))
            continue

        if team_cell:
            active_group = team_cell
            if team_cell.lower() != "ball":
                active_identity = ""
        if identity_cell:
            active_identity = identity_cell
        provider_name = axis_cell.lower()
        if provider_name.startswith("ball"):
            active_group = "Ball"
            active_identity = ""
        elif provider_name.startswith("player") and not active_identity:
            active_identity = provider_name.removeprefix("player")
        axis = axis_cell if axis_cell in {"x", "y"} else ("x" if index % 2 else "y")
        if active_group.lower() == "ball":
            columns.append(f"ball_{axis}")
        elif active_group.lower() in {"home", "away"} and active_identity:
            columns.append(f"{active_group.title()}_{active_identity}_{axis}")
        else:
            columns.append(f"unmapped_{index}_{axis}")
    if len(columns) != len(set(columns)):
        raise ValueError("Raw Metrica headers produced duplicate canonical columns")
    return columns


def read_metrica_tracking_csv(path: str | Path) -> tuple[pd.DataFrame, str]:
    """Read normalized or official raw three-row Metrica tracking CSV."""
    source = Path(path)
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header_rows = []
        for _ in range(3):
            try:
                header_rows.append(next(reader))
            except StopIteration:
                break
    if not header_rows:
        raise ValueError("Metrica tracking CSV is empty")
    first = {_clean_header(value).lower() for value in header_rows[0]}
    if {"frame", "time_s", "ball_x", "ball_y"}.issubset(first):
        return pd.read_csv(source), "normalized_single_header"
    if len(header_rows) < 3:
        raise ValueError("Metrica tracking CSV is neither normalized nor a raw three-row file")
    columns = _raw_metrica_headers(header_rows)
    data = pd.read_csv(source, skiprows=3, header=None, names=columns)
    for column in data.columns:
        data[column] = pd.to_numeric(data[column], errors="coerce")
    required = {"frame", "time_s", "ball_x", "ball_y"}
    if not required.issubset(data.columns):
        raise ValueError(f"Raw Metrica CSV missing required columns: {sorted(required - set(data.columns))}")
    data = data.dropna(subset=["frame", "time_s", "ball_x", "ball_y"]).reset_index(drop=True)
    return data, "official_three_row"


def load_metrica_csv(
    tracking_path: str | Path,
    sequence_id: str,
    possession_team: str = "home",
    pitch_length: float = 105.0,
    pitch_width: float = 68.0,
    ball_carrier_id: str | None = None,
    away_tracking_path: str | Path | None = None,
    coordinate_units: Literal["auto", "normalized", "meters"] = "auto",
) -> list[FrameState]:
    """Load normalized or official three-row Metrica tracking CSV.

    Expected columns: frame, time_s, ball_x, ball_y and paired `Home_1_x`, `Home_1_y`,
    `Away_1_x`, `Away_1_y` columns. Official raw coordinates are normalized [0,1] with
    a top-left origin. Normalized single-header inputs may be metric or normalized.
    Velocity columns are optional.
    """
    data, header_format = read_metrica_tracking_csv(tracking_path)
    if away_tracking_path is not None:
        away_data, away_header_format = read_metrica_tracking_csv(away_tracking_path)
        join_keys = ["period", "frame", "time_s"]
        if not set(join_keys).issubset(data.columns) or not set(join_keys).issubset(away_data.columns):
            raise ValueError("Metrica home/away raw files require period, frame, and time columns")
        duplicate_payload = [
            column
            for column in away_data.columns
            if column in data.columns and column not in join_keys
        ]
        away_data = away_data.drop(columns=duplicate_payload)
        data = data.merge(away_data, on=join_keys, how="inner", validate="one_to_one")
        header_format = f"{header_format}+{away_header_format}"
        if data.empty:
            raise ValueError("Metrica home/away raw files have no synchronized frame rows")
    players = _player_ids(list(data.columns))
    if not players:
        raise ValueError("No normalized player coordinate columns found")
    official_raw = "official_three_row" in header_format
    if official_raw and coordinate_units == "meters":
        raise ValueError("Official raw Metrica tracking coordinates are normalized, not metric")
    if official_raw:
        normalized = True
        coordinate_units_source = "official_metrica_contract"
    elif coordinate_units == "auto":
        normalized = max(
            float(data[[f"{pid}_x" for pid in players]].max().max()),
            float(data[[f"{pid}_y" for pid in players]].max().max()),
        ) <= 1.5
        coordinate_units_source = "magnitude_inference"
    else:
        normalized = coordinate_units == "normalized"
        coordinate_units_source = "adapter_argument"

    frames: list[FrameState] = []
    velocity_columns_present = any(column.endswith(("_vx", "_vy")) for column in data.columns)
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
            states.append(
                PlayerState(
                    pid,
                    team,
                    x,
                    y,
                    vx,
                    vy,
                    source_player_id=pid.split("_", 1)[1],
                    tracking_status="observed",
                    metadata={"provider_coordinate_origin": "top_left"},
                )
            )
        ball_x = float(row.ball_x) * (pitch_length if normalized else 1.0)
        ball_y = float(row.ball_y) * (pitch_width if normalized else 1.0)
        carrier = ball_carrier_id
        if carrier is None:
            eligible = [p for p in states if p.team == possession_team]
            if not eligible:
                raise ValueError(f"No {possession_team} players available for carrier inference")
            carrier = min(eligible, key=lambda p: np.linalg.norm(p.position - [ball_x, ball_y])).player_id
        quality_flags = ["inferred_ball_carrier"] if ball_carrier_id is None else []
        if not velocity_columns_present:
            quality_flags.append("no_velocity")
        if not any(player.team == "home" for player in states) or not any(
            player.team == "away" for player in states
        ):
            quality_flags.append("single_team_tracking")
        ball_vx = float(getattr(row, "ball_vx", 0.0))
        ball_vy = float(getattr(row, "ball_vy", 0.0))
        if normalized:
            ball_vx *= pitch_length
            ball_vy *= pitch_width
        frame = FrameState(
            sequence_id=sequence_id,
            frame_id=int(row.frame),
            timestamp_s=float(row.time_s),
            possession_team=possession_team,
            ball_x=ball_x,
            ball_y=ball_y,
            ball_vx=ball_vx,
            ball_vy=ball_vy,
            ball_carrier_id=carrier,
            players=states,
            period=int(getattr(row, "period", 1)),
            frame_rate_hz=25.0,
            source_provider="metrica",
            source_match_id=sequence_id,
            ball_status="observed",
            possession_confidence=1.0 if ball_carrier_id is not None else 0.5,
            quality_flags=quality_flags,
            metadata={
                "source": f"metrica-{header_format}",
                "native_coordinate_system": {
                    "origin": "top_left",
                    "units": "normalized" if normalized else "meters",
                    "x_axis": "left_to_right",
                    "y_axis": "top_to_bottom",
                    "units_source": coordinate_units_source,
                },
                "ball_carrier_source": "explicit" if ball_carrier_id is not None else "nearest_player_in_requested_possession_team",
                "possession_team_source": "adapter_argument",
            },
        )
        frame.validate()
        frames.append(frame)
    return frames


def _event_value(row: pd.Series, *names: str, default: Any = None) -> Any:
    lower = {str(column).strip().lower(): column for column in row.index}
    for name in names:
        column = lower.get(name.lower())
        if column is not None and pd.notna(row[column]):
            return row[column]
    return default


def _identity_text(value: Any) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    return str(int(numeric)) if numeric.is_integer() else str(value)


def load_metrica_events_csv(
    events_path: str | Path,
    sequence_id: str,
    *,
    pitch_length: float = 105.0,
    pitch_width: float = 68.0,
    coordinate_units: Literal["normalized", "meters"] = "normalized",
) -> list[EventState]:
    """Parse official Metrica events without assuming event/tracking row equality."""
    data = pd.read_csv(events_path)
    events: list[EventState] = []
    for index, row in data.iterrows():
        raw_team = _event_value(row, "Team")
        team = canonical_team(raw_team) if raw_team is not None else None
        event_type = str(_event_value(row, "Type", default="Unknown"))
        subtype = _event_value(row, "Subtype")
        period = int(_event_value(row, "Period", default=1))
        timestamp_s = float(_event_value(row, "Start Time [s]", "Start Time", "time_s", default=0.0))

        def coordinate(axis: str, scale: float) -> float | None:
            value = _event_value(row, f"Start {axis}", f"{axis.lower()}")
            if value is None:
                return None
            numeric = float(value)
            canonical = numeric * scale if coordinate_units == "normalized" else numeric
            if not 0.0 <= canonical <= scale:
                raise ValueError(f"Metrica event {index} Start {axis} outside pitch bounds")
            return canonical

        def end_coordinate(axis: str, scale: float) -> float | None:
            value = _event_value(row, f"End {axis}", f"end_{axis.lower()}")
            if value is None:
                return None
            numeric = float(value)
            canonical = numeric * scale if coordinate_units == "normalized" else numeric
            if not 0.0 <= canonical <= scale:
                raise ValueError(f"Metrica event {index} End {axis} outside pitch bounds")
            return canonical

        actor = _event_value(row, "From", "Actor")
        events.append(
            EventState(
                sequence_id=sequence_id,
                event_id=str(_event_value(row, "event_id", "Index", default=index)),
                timestamp_s=timestamp_s,
                period=period,
                event_type=event_type,
                team=team,
                actor_id=f"{str(raw_team).title()}_{_identity_text(actor)}"
                if raw_team is not None and actor is not None
                else None,
                start_x=coordinate("X", pitch_length),
                start_y=coordinate("Y", pitch_width),
                end_x=end_coordinate("X", pitch_length),
                end_y=end_coordinate("Y", pitch_width),
                outcome=str(subtype) if subtype is not None else None,
                source_provider="metrica",
                source_match_id=sequence_id,
                metadata={
                    "start_frame": int(_event_value(row, "Start Frame"))
                    if _event_value(row, "Start Frame") is not None
                    else None,
                    "end_frame": int(_event_value(row, "End Frame"))
                    if _event_value(row, "End Frame") is not None
                    else None,
                    "recipient_source_id": _identity_text(_event_value(row, "To"))
                    if _event_value(row, "To") is not None
                    else None,
                    "raw_team": raw_team,
                    "native_coordinates": f"{coordinate_units}_top_left",
                },
            )
        )
    return events


def synchronize_metrica_events(
    events: list[EventState],
    frames: list[FrameState],
    *,
    tolerance_s: float = 0.06,
) -> list[EventFrameAlignment]:
    """Attach exact-frame or period-aware nearest-time synchronization evidence."""
    by_key = {(frame.period, frame.frame_id): frame for frame in frames}
    nearest = {alignment.event_id: alignment for alignment in align_events_to_frames(events, frames, tolerance_s)}
    output: list[EventFrameAlignment] = []
    for event in events:
        start_frame = event.metadata.get("start_frame")
        exact = by_key.get((event.period, start_frame)) if start_frame is not None else None
        if exact is not None:
            alignment = EventFrameAlignment(
                event_id=event.event_id,
                sequence_id=event.sequence_id,
                event_timestamp_s=event.timestamp_s,
                frame_id=exact.frame_id,
                frame_timestamp_s=exact.timestamp_s,
                absolute_error_s=abs(exact.timestamp_s - event.timestamp_s),
                matched=True,
            )
            method = "provider_start_frame"
        else:
            alignment = nearest[event.event_id]
            method = "period_aware_nearest_timestamp"
        event.metadata["tracking_alignment"] = {
            "matched": alignment.matched,
            "frame_id": alignment.frame_id,
            "frame_timestamp_s": alignment.frame_timestamp_s,
            "absolute_error_s": alignment.absolute_error_s,
            "method": method,
            "tolerance_s": tolerance_s,
            "within_time_tolerance": (
                alignment.absolute_error_s is not None and alignment.absolute_error_s <= tolerance_s
            ),
        }
        output.append(alignment)
    return output


def load_metrica_open(
    tracking_path: str | Path,
    events_path: str | Path | None,
    sequence_id: str,
    *,
    possession_team: str = "home",
    pitch_length: float = 105.0,
    pitch_width: float = 68.0,
    ball_carrier_id: str | None = None,
    alignment_tolerance_s: float = 0.06,
    away_tracking_path: str | Path | None = None,
    tracking_coordinate_units: Literal["auto", "normalized", "meters"] = "auto",
    event_coordinate_units: Literal["normalized", "meters"] = "normalized",
) -> AdapterResult:
    """Load raw tracking plus synchronized events as one auditable adapter result."""
    frames = load_metrica_csv(
        tracking_path,
        sequence_id=sequence_id,
        possession_team=possession_team,
        pitch_length=pitch_length,
        pitch_width=pitch_width,
        ball_carrier_id=ball_carrier_id,
        away_tracking_path=away_tracking_path,
        coordinate_units=tracking_coordinate_units,
    )
    events = (
        load_metrica_events_csv(
            events_path,
            sequence_id,
            pitch_length=pitch_length,
            pitch_width=pitch_width,
            coordinate_units=event_coordinate_units,
        )
        if events_path
        else []
    )
    alignments = synchronize_metrica_events(events, frames, tolerance_s=alignment_tolerance_s)
    unmatched = [alignment.event_id for alignment in alignments if not alignment.matched]
    warnings = []
    if not events_path:
        warnings.append("No Metrica event file supplied; tracking is not event-enriched")
    if unmatched:
        warnings.append(f"{len(unmatched)} Metrica events did not align within tolerance")
    clock_conflicts = [
        event.event_id
        for event in events
        if event.metadata["tracking_alignment"]["matched"]
        and not event.metadata["tracking_alignment"]["within_time_tolerance"]
    ]
    if clock_conflicts:
        warnings.append(
            f"{len(clock_conflicts)} Metrica provider-frame matches exceeded clock tolerance"
        )
    return AdapterResult(
        frames=frames,
        events=events,
        provider_id="metrica",
        source_match_id=sequence_id,
        warnings=warnings,
        metadata={
            "alignment_tolerance_s": alignment_tolerance_s,
            "matched_events": len(alignments) - len(unmatched),
            "unmatched_events": unmatched,
            "clock_conflict_events": clock_conflicts,
            "native_coordinate_system": "normalized_top_left",
            "official_tracking_rate_hz": 25.0,
        },
    )
