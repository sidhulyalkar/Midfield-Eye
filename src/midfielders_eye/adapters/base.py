from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from ..schema import EventState, FrameState

AccessLevel = Literal["open", "registration", "commercial", "owned"]
StateCoverage = Literal["full_tracking", "partial_tracking", "event_snapshot", "video_gsr", "auxiliary"]


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    tracking: bool
    events: bool
    persistent_identities: bool
    ball_tracking: bool
    possession: bool
    full_pitch: bool
    camera_visibility: bool
    body_orientation: bool = False
    gaze: bool = False


@dataclass(frozen=True, slots=True)
class ProviderSpec:
    provider_id: str
    display_name: str
    access: AccessLevel
    coverage: StateCoverage
    native_rate_hz: float | None
    capabilities: ProviderCapabilities
    license_note: str
    homepage: str
    recommended_use: str
    limitations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AdapterResult:
    frames: list[FrameState]
    events: list[EventState] = field(default_factory=list)
    provider_id: str = "unknown"
    source_match_id: str | None = None
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "source_match_id": self.source_match_id,
            "frames": len(self.frames),
            "events": len(self.events),
            "sequences": len({frame.sequence_id for frame in self.frames}),
            "warnings": self.warnings,
            "metadata": self.metadata,
        }
