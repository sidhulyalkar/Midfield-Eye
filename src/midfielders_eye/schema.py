from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

import numpy as np

Team = Literal["home", "away"]
ActionKind = Literal["pass", "carry", "hold"]
TrackingStatus = Literal["observed", "extrapolated", "inferred", "interpolated", "unknown"]
VisibilityStatus = Literal["visible", "off_screen", "occluded", "interpolated", "unknown"]
BallStatus = Literal["observed", "tracked", "inferred", "sidecar", "dropped", "unknown"]


def _default_covariance() -> list[list[float]]:
    return [[1.0, 0.0], [0.0, 1.0]]


@dataclass(slots=True)
class PlayerState:
    """Canonical player state used by the tactical engine.

    The first positional fields intentionally preserve the v0.1/v0.2 constructor contract.
    New perception-facing fields are appended so existing adapters and user code remain valid.
    Coordinates are always canonical metric coordinates with origin at the top-left of the pitch.
    """

    player_id: str
    team: Team
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    body_angle: float = 0.0
    head_angle: float | None = None
    gaze_angle: float | None = None
    role: str | None = None
    jersey_number: int | None = None
    source_player_id: str | None = None
    tracking_status: TrackingStatus = "observed"
    confidence: float | None = None
    visible: bool | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    observation_id: str | None = None
    track_id: str | None = None
    ax: float = 0.0
    ay: float = 0.0
    turning_rate: float = 0.0
    trajectory_confidence: float | None = None
    calibration_confidence: float | None = None
    position_covariance: list[list[float]] = field(default_factory=_default_covariance)
    visibility: VisibilityStatus = "unknown"
    image_bbox: list[float] | None = None
    provenance_flags: list[str] = field(default_factory=list)

    @property
    def position(self) -> np.ndarray:
        return np.array([self.x, self.y], dtype=float)

    @property
    def velocity(self) -> np.ndarray:
        return np.array([self.vx, self.vy], dtype=float)

    @property
    def acceleration(self) -> np.ndarray:
        return np.array([self.ax, self.ay], dtype=float)

    @property
    def speed(self) -> float:
        return float(np.linalg.norm(self.velocity))

    @property
    def view_angle(self) -> float:
        if self.gaze_angle is not None:
            return self.gaze_angle
        if self.head_angle is not None:
            return self.head_angle
        return self.body_angle

    @property
    def covariance_matrix(self) -> np.ndarray:
        covariance = np.asarray(self.position_covariance, dtype=float)
        if covariance.shape != (2, 2):
            raise ValueError(f"player {self.player_id} covariance must be 2x2")
        return covariance

    @property
    def uncertainty_radius_m(self) -> float:
        eigenvalues = np.linalg.eigvalsh(self.covariance_matrix)
        return float(np.sqrt(max(float(eigenvalues.max()), 0.0)))

    # Canonical-contract aliases used by integration code and exported payloads.
    @property
    def x_m(self) -> float:
        return self.x

    @property
    def y_m(self) -> float:
        return self.y

    @property
    def vx_mps(self) -> float:
        return self.vx

    @property
    def vy_mps(self) -> float:
        return self.vy

    @property
    def body_heading_rad(self) -> float:
        return self.body_angle

    @property
    def team_id(self) -> Team:
        return self.team

    def validate(self, pitch_length: float, pitch_width: float) -> None:
        if not 0 <= self.x <= pitch_length or not 0 <= self.y <= pitch_width:
            raise ValueError(f"player {self.player_id} outside pitch")
        for name, value in {
            "confidence": self.confidence,
            "trajectory_confidence": self.trajectory_confidence,
            "calibration_confidence": self.calibration_confidence,
        }.items():
            if value is not None and not 0 <= value <= 1:
                raise ValueError(f"player {self.player_id} {name} outside [0, 1]")
        covariance = self.covariance_matrix
        if not np.allclose(covariance, covariance.T, atol=1e-8):
            raise ValueError(f"player {self.player_id} covariance must be symmetric")
        if float(np.linalg.eigvalsh(covariance).min()) < -1e-8:
            raise ValueError(f"player {self.player_id} covariance must be positive semidefinite")


@dataclass(slots=True)
class BallState:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    confidence: float | None = None
    status: BallStatus = "unknown"
    carrier_id: str | None = None
    possession_probability: float | None = None
    position_covariance: list[list[float]] = field(default_factory=_default_covariance)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def position(self) -> np.ndarray:
        return np.array([self.x, self.y], dtype=float)

    @property
    def velocity(self) -> np.ndarray:
        return np.array([self.vx, self.vy], dtype=float)


@dataclass(slots=True)
class FrameState:
    sequence_id: str
    frame_id: int
    timestamp_s: float
    possession_team: Team
    ball_x: float
    ball_y: float
    ball_vx: float
    ball_vy: float
    ball_carrier_id: str
    players: list[PlayerState]
    pitch_length: float = 105.0
    pitch_width: float = 68.0
    attacking_direction: dict[str, int] = field(
        default_factory=lambda: {"home": 1, "away": -1}
    )
    period: int = 1
    frame_rate_hz: float | None = None
    visibility_polygon: list[list[float]] | None = None
    source_provider: str = "unknown"
    source_match_id: str | None = None
    ball_confidence: float | None = None
    quality_flags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    ball_status: BallStatus = "unknown"
    possession_confidence: float | None = None
    calibration_confidence: float | None = None
    camera_id: str | None = None
    state_version: str = "0.5"

    @property
    def ball_position(self) -> np.ndarray:
        return np.array([self.ball_x, self.ball_y], dtype=float)

    @property
    def ball(self) -> BallState:
        covariance = self.metadata.get("ball_position_covariance", _default_covariance())
        return BallState(
            x=self.ball_x,
            y=self.ball_y,
            vx=self.ball_vx,
            vy=self.ball_vy,
            confidence=self.ball_confidence,
            status=self.ball_status,
            carrier_id=self.ball_carrier_id,
            possession_probability=self.possession_confidence,
            position_covariance=covariance,
            metadata=self.metadata.get("ball_metadata", {}),
        )

    @property
    def match_id(self) -> str:
        return self.source_match_id or self.sequence_id

    @property
    def pitch_length_m(self) -> float:
        return self.pitch_length

    @property
    def pitch_width_m(self) -> float:
        return self.pitch_width

    @property
    def visible_pitch_polygon(self) -> list[list[float]] | None:
        return self.visibility_polygon

    @property
    def source(self) -> str:
        return self.source_provider

    def player(self, player_id: str) -> PlayerState:
        for player in self.players:
            if player.player_id == player_id:
                return player
        raise KeyError(f"Unknown player_id={player_id!r}")

    @property
    def carrier(self) -> PlayerState:
        return self.player(self.ball_carrier_id)

    def teammates(self, player_id: str | None = None) -> list[PlayerState]:
        player_id = player_id or self.ball_carrier_id
        subject = self.player(player_id)
        return [p for p in self.players if p.team == subject.team and p.player_id != player_id]

    def opponents(self, player_id: str | None = None) -> list[PlayerState]:
        player_id = player_id or self.ball_carrier_id
        subject = self.player(player_id)
        return [p for p in self.players if p.team != subject.team]

    def validate(self) -> None:
        if self.pitch_length <= 0 or self.pitch_width <= 0:
            raise ValueError("pitch dimensions must be positive")
        if not 0 <= self.ball_x <= self.pitch_length:
            raise ValueError("ball_x outside pitch")
        if not 0 <= self.ball_y <= self.pitch_width:
            raise ValueError("ball_y outside pitch")
        ids = [p.player_id for p in self.players]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate player IDs")
        if self.ball_carrier_id not in ids:
            raise ValueError("ball carrier missing from players")
        if self.possession_team != self.carrier.team:
            raise ValueError("possession_team differs from ball carrier team")
        for player in self.players:
            player.validate(self.pitch_length, self.pitch_width)
        for name, value in {
            "ball_confidence": self.ball_confidence,
            "possession_confidence": self.possession_confidence,
            "calibration_confidence": self.calibration_confidence,
        }.items():
            if value is not None and not 0 <= value <= 1:
                raise ValueError(f"{name} outside [0, 1]")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_canonical_dict(self) -> dict[str, Any]:
        """Export the nested v0.4 perception-to-tactics contract."""
        return {
            "match_id": self.match_id,
            "sequence_id": self.sequence_id,
            "period": self.period,
            "timestamp_s": self.timestamp_s,
            "frame_id": self.frame_id,
            "pitch_length_m": self.pitch_length,
            "pitch_width_m": self.pitch_width,
            "attacking_direction": self.attacking_direction,
            "ball": asdict(self.ball),
            "players": [asdict(player) for player in self.players],
            "visible_pitch_polygon": self.visibility_polygon,
            "source": self.source_provider,
            "source_match_id": self.source_match_id,
            "quality_flags": self.quality_flags,
            "metadata": self.metadata,
            "state_version": self.state_version,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "FrameState":
        payload = dict(payload)
        payload["players"] = [PlayerState(**player) for player in payload["players"]]
        return cls(**payload)


# Public name used by the integration contract. FrameState remains for backwards compatibility.
GameStateFrame = FrameState


@dataclass(slots=True)
class EventState:
    sequence_id: str
    event_id: str
    timestamp_s: float
    period: int
    event_type: str
    team: Team | None = None
    actor_id: str | None = None
    start_x: float | None = None
    start_y: float | None = None
    end_x: float | None = None
    end_y: float | None = None
    outcome: str | None = None
    source_provider: str = "unknown"
    source_match_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ActionOption:
    sequence_id: str
    frame_id: int
    option_id: str
    kind: ActionKind
    actor_id: str
    target_player_id: str | None
    target_x: float
    target_y: float
    features: dict[str, float]
    geometric_score: float = 0.0
    learned_score: float | None = None
    label_available: bool | None = None
    label_value: float | None = None
    label_selected: bool | None = None
    label_visibility: str | None = None
    label_confidence: float | None = None
    label_failure_reason: str | None = None
    annotator_id: str | None = None
    source_provider: str | None = None
    source_match_id: str | None = None
    provenance: str = "generated"

    @property
    def target(self) -> np.ndarray:
        return np.array([self.target_x, self.target_y], dtype=float)

    def to_flat_dict(self) -> dict[str, Any]:
        row = {
            "sequence_id": self.sequence_id,
            "frame_id": self.frame_id,
            "option_id": self.option_id,
            "kind": self.kind,
            "actor_id": self.actor_id,
            "target_player_id": self.target_player_id,
            "target_x": self.target_x,
            "target_y": self.target_y,
            "geometric_score": self.geometric_score,
            "learned_score": self.learned_score,
            "label_available": self.label_available,
            "label_value": self.label_value,
            "label_selected": self.label_selected,
            "label_visibility": self.label_visibility,
            "label_confidence": self.label_confidence,
            "label_failure_reason": self.label_failure_reason,
            "annotator_id": self.annotator_id,
            "source_provider": self.source_provider,
            "source_match_id": self.source_match_id,
            "provenance": self.provenance,
        }
        row.update(self.features)
        return row
