"""Evidence-aware empirical data layer for Midfielder's Eye."""

from .alignment import (
    AlignedGazeSample,
    ClockFit,
    ScanEvent,
    align_gaze_to_frames,
    detect_gaze_scan_events,
    fit_linear_clock,
    summarize_alignment,
)
from .capture import (
    CaptureProtocol,
    default_midfield_capture_protocol,
    protocol_from_dict,
    validate_capture_protocol,
    write_capture_protocol,
)
from .registry import SourceRegistry, load_source_registry
from .schemas import (
    AccessMode,
    DatasetSource,
    EvidenceRecord,
    EvidenceTier,
    SignalModality,
)
from .validation import ClaimBoundaryError, validate_claim

__all__ = [
    "AccessMode",
    "AlignedGazeSample",
    "CaptureProtocol",
    "ClockFit",
    "ClaimBoundaryError",
    "DatasetSource",
    "EvidenceRecord",
    "EvidenceTier",
    "ScanEvent",
    "SignalModality",
    "SourceRegistry",
    "align_gaze_to_frames",
    "default_midfield_capture_protocol",
    "detect_gaze_scan_events",
    "fit_linear_clock",
    "load_source_registry",
    "protocol_from_dict",
    "summarize_alignment",
    "validate_capture_protocol",
    "validate_claim",
    "write_capture_protocol",
]
