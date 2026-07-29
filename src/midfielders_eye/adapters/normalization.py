from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Literal

import numpy as np

from ..schema import FrameState, PlayerState, Team

Origin = Literal["top_left", "center"]
Units = Literal["normalized", "meters"]
YAxis = Literal["down", "up"]


@dataclass(frozen=True, slots=True)
class CoordinateTransformer:
    pitch_length: float = 105.0
    pitch_width: float = 68.0
    origin: Origin = "top_left"
    units: Units = "meters"
    y_axis: YAxis = "down"
    native_length: float | None = None
    native_width: float | None = None

    def point(self, x: float, y: float, clip: bool = True) -> tuple[float, float]:
        if self.units == "normalized":
            native_length = self.native_length or 1.0
            native_width = self.native_width or 1.0
            x = x / native_length * self.pitch_length
            y = y / native_width * self.pitch_width
        elif self.native_length and self.native_width:
            x = x / self.native_length * self.pitch_length
            y = y / self.native_width * self.pitch_width

        if self.origin == "center":
            x += self.pitch_length / 2.0
            y = self.pitch_width / 2.0 - y if self.y_axis == "up" else y + self.pitch_width / 2.0
        elif self.y_axis == "up":
            y = self.pitch_width - y

        if clip:
            x = float(np.clip(x, 0.0, self.pitch_length))
            y = float(np.clip(y, 0.0, self.pitch_width))
        return float(x), float(y)

    def polygon(self, points: list[float] | list[list[float]]) -> list[list[float]]:
        if not points:
            return []
        if isinstance(points[0], (int, float)):
            flat = list(points)  # type: ignore[arg-type]
            pairs = list(zip(flat[::2], flat[1::2], strict=True))
        else:
            pairs = points  # type: ignore[assignment]
        return [list(self.point(float(x), float(y))) for x, y in pairs]


def parse_clock_seconds(value: str | float | int) -> float:
    if isinstance(value, (float, int)):
        return float(value)
    text = value.strip()
    if not text:
        return 0.0
    parts = text.split(":")
    try:
        if len(parts) == 3:
            hours, minutes, seconds = parts
            return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
        if len(parts) == 2:
            minutes, seconds = parts
            return int(minutes) * 60 + float(seconds)
        return float(text)
    except ValueError as exc:
        raise ValueError(f"Unsupported timestamp {value!r}") from exc


def canonical_team(value: str | int | None, home_values: set[str] | None = None) -> Team:
    normalized = str(value).strip().lower()
    home_values = home_values or {"home", "left", "1", "team_home"}
    if normalized in home_values:
        return "home"
    if normalized in {"away", "right", "2", "team_away"}:
        return "away"
    raise ValueError(f"Cannot map team value {value!r} to home/away")


def nearest_player_id(
    players: list[PlayerState],
    x: float,
    y: float,
    team: Team | None = None,
    max_distance_m: float | None = None,
) -> str:
    eligible = [player for player in players if team is None or player.team == team]
    if not eligible:
        raise ValueError("No eligible players available for ball-carrier inference")
    point = np.array([x, y], dtype=float)
    player = min(eligible, key=lambda item: float(np.linalg.norm(item.position - point)))
    distance = float(np.linalg.norm(player.position - point))
    if max_distance_m is not None and distance > max_distance_m:
        raise ValueError(
            f"Nearest player is {distance:.2f} m from the ball, above {max_distance_m:.2f} m"
        )
    return player.player_id


def enrich_kinematics(
    frames: list[FrameState],
    max_gap_s: float = 0.5,
    orientation_speed_threshold: float = 0.5,
) -> list[FrameState]:
    """Infer causal velocity and body orientation from the previous observation.

    The function mutates and returns the supplied frames. It never looks ahead.
    """
    previous_by_sequence: dict[str, dict[str, tuple[float, float, float]]] = defaultdict(dict)
    previous_ball: dict[str, tuple[float, float, float]] = {}
    for frame in sorted(frames, key=lambda item: (item.sequence_id, item.timestamp_s, item.frame_id)):
        previous_players = previous_by_sequence[frame.sequence_id]
        for player in frame.players:
            previous = previous_players.get(player.player_id)
            if previous:
                previous_t, previous_x, previous_y = previous
                dt = frame.timestamp_s - previous_t
                if 0 < dt <= max_gap_s:
                    player.vx = (player.x - previous_x) / dt
                    player.vy = (player.y - previous_y) / dt
                    if player.speed >= orientation_speed_threshold:
                        player.body_angle = math.atan2(player.vy, player.vx)
            previous_players[player.player_id] = (frame.timestamp_s, player.x, player.y)

        previous = previous_ball.get(frame.sequence_id)
        if previous:
            previous_t, previous_x, previous_y = previous
            dt = frame.timestamp_s - previous_t
            if 0 < dt <= max_gap_s:
                frame.ball_vx = (frame.ball_x - previous_x) / dt
                frame.ball_vy = (frame.ball_y - previous_y) / dt
        previous_ball[frame.sequence_id] = (frame.timestamp_s, frame.ball_x, frame.ball_y)
    return frames
