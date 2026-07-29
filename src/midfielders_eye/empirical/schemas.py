from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class EvidenceTier(str, Enum):
    DIRECT_MEASUREMENT = "direct_measurement"
    PROVIDER_TRACKING = "provider_tracking"
    VIDEO_RECONSTRUCTION = "video_reconstruction"
    INFERRED_PROXY = "inferred_proxy"
    SYNTHETIC = "synthetic"
    EDITORIAL_HYPOTHESIS = "editorial_hypothesis"


class SignalModality(str, Enum):
    EYE_GAZE = "eye_gaze"
    HEAD_POSE = "head_pose"
    BODY_POSE_3D = "body_pose_3d"
    KINEMATICS = "kinematics"
    KINETICS = "kinetics"
    FULL_TRACKING = "full_tracking"
    PARTIAL_TRACKING = "partial_tracking"
    EVENT_360 = "event_360"
    VIDEO = "video"
    IMU = "imu"
    BALL = "ball"


class AccessMode(str, Enum):
    OPEN_REPOSITORY = "open_repository"
    OPEN_DOWNLOAD = "open_download"
    REGISTRATION = "registration"
    LICENSE_REQUEST = "license_request"
    COMMERCIAL_LICENSE = "commercial_license"
    PROSPECTIVE_CAPTURE = "prospective_capture"


@dataclass(frozen=True)
class DatasetSource:
    id: str
    name: str
    access: AccessMode
    modalities: tuple[SignalModality, ...]
    official_url: str
    license_name: str
    redistribution: str
    citation: str
    best_for: tuple[str, ...]
    caveats: tuple[str, ...]
    adapter: str | None = None
    download: dict[str, Any] = field(default_factory=dict)
    priority: int = 3

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DatasetSource":
        return cls(
            id=str(payload["id"]),
            name=str(payload["name"]),
            access=AccessMode(payload["access"]),
            modalities=tuple(SignalModality(value) for value in payload.get("modalities", [])),
            official_url=str(payload["official_url"]),
            license_name=str(payload["license_name"]),
            redistribution=str(payload["redistribution"]),
            citation=str(payload["citation"]),
            best_for=tuple(str(v) for v in payload.get("best_for", [])),
            caveats=tuple(str(v) for v in payload.get("caveats", [])),
            adapter=payload.get("adapter"),
            download=dict(payload.get("download", {})),
            priority=int(payload.get("priority", 3)),
        )

    @property
    def can_auto_download(self) -> bool:
        return self.access in {AccessMode.OPEN_REPOSITORY, AccessMode.OPEN_DOWNLOAD}

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["access"] = self.access.value
        payload["modalities"] = [item.value for item in self.modalities]
        return payload


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    source_id: str
    tier: EvidenceTier
    modalities: tuple[SignalModality, ...]
    subject_id: str | None
    sequence_id: str
    timestamp_start_s: float | None
    timestamp_end_s: float | None
    confidence: float
    measured_fields: tuple[str, ...]
    inferred_fields: tuple[str, ...] = ()
    source_files: tuple[str, ...] = ()
    citations: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be within [0, 1]")
        overlap = set(self.measured_fields) & set(self.inferred_fields)
        if overlap:
            raise ValueError(f"fields cannot be both measured and inferred: {sorted(overlap)}")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["tier"] = self.tier.value
        payload["modalities"] = [item.value for item in self.modalities]
        return payload
