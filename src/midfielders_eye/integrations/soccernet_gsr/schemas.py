from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class TrackerObservation:
    frame_id: int
    track_id: str
    pitch_x: float
    pitch_y: float
    role: str | None = None
    team: str | None = None
    jersey_number: int | None = None
    detection_confidence: float | None = None
    tracking_confidence: float | None = None
    calibration_confidence: float | None = None
    image_bbox: list[float] | None = None
    embedding_ref: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PerceptionFrame:
    frame_id: int
    timestamp_s: float
    observations: list[TrackerObservation]
    period: int = 1
    visible_pitch_polygon: list[list[float]] | None = None
    camera_confidence: float | None = None
    camera_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TrackerStateBundle:
    frames: list[PerceptionFrame]
    source_path: str
    match_id: str
    fps: float
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def observation_count(self) -> int:
        return sum(len(frame.observations) for frame in self.frames)

    def summary(self) -> dict[str, Any]:
        return {
            "source_path": self.source_path,
            "match_id": self.match_id,
            "fps": self.fps,
            "frames": len(self.frames),
            "observations": self.observation_count,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class PossessionSidecarRecord:
    frame_id: int
    ball_x: float
    ball_y: float
    possession_team: str
    ball_carrier_id: str
    period: int = 1
    timestamp_s: float | None = None
    ball_vx: float = 0.0
    ball_vy: float = 0.0
    ball_confidence: float | None = None
    possession_confidence: float | None = None
    ball_status: str = "sidecar"
