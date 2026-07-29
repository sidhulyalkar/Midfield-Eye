from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Iterable, Sequence

import numpy as np

from .adapters import GazeSample


@dataclass(frozen=True)
class ClockFit:
    """Linear mapping from a sensor clock into the canonical match clock."""

    offset_s: float
    scale: float
    drift_ppm: float
    rmse_ms: float
    max_error_ms: float
    anchor_count: int

    def map_time(self, sensor_timestamp_s: float) -> float:
        return float(self.offset_s + self.scale * sensor_timestamp_s)

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


@dataclass(frozen=True)
class AlignedGazeSample:
    frame_index: int
    frame_timestamp_s: float
    sensor_timestamp_s: float | None
    canonical_sensor_timestamp_s: float | None
    delta_ms: float | None
    yaw_rad: float | None
    pitch_rad: float | None
    depth_m: float | None
    source: str
    confidence: float
    status: str

    def to_dict(self) -> dict[str, float | int | str | None]:
        return asdict(self)


@dataclass(frozen=True)
class ScanEvent:
    start_timestamp_s: float
    end_timestamp_s: float
    peak_angular_velocity_deg_s: float
    angular_displacement_deg: float
    source: str
    confidence: float

    def to_dict(self) -> dict[str, float | str]:
        return asdict(self)


def fit_linear_clock(
    sensor_anchor_timestamps_s: Sequence[float],
    canonical_anchor_timestamps_s: Sequence[float],
) -> ClockFit:
    """Estimate offset and drift from paired synchronization anchors.

    At least two anchors are required because a single marker cannot identify drift.
    The function is intentionally small and deterministic so the mapping can be
    serialized in the evidence manifest and reproduced by the frontend.
    """

    sensor = np.asarray(sensor_anchor_timestamps_s, dtype=float)
    canonical = np.asarray(canonical_anchor_timestamps_s, dtype=float)
    if sensor.shape != canonical.shape:
        raise ValueError("sensor and canonical anchor arrays must have equal length")
    if sensor.ndim != 1 or sensor.size < 2:
        raise ValueError("at least two one-dimensional synchronization anchors are required")
    if not np.all(np.isfinite(sensor)) or not np.all(np.isfinite(canonical)):
        raise ValueError("synchronization anchors must be finite")
    if np.any(np.diff(sensor) <= 0) or np.any(np.diff(canonical) <= 0):
        raise ValueError("synchronization anchors must be strictly increasing")

    design = np.column_stack([np.ones_like(sensor), sensor])
    offset, scale = np.linalg.lstsq(design, canonical, rcond=None)[0]
    predicted = offset + scale * sensor
    errors_ms = (predicted - canonical) * 1000.0
    return ClockFit(
        offset_s=float(offset),
        scale=float(scale),
        drift_ppm=float((scale - 1.0) * 1_000_000.0),
        rmse_ms=float(np.sqrt(np.mean(errors_ms**2))),
        max_error_ms=float(np.max(np.abs(errors_ms))),
        anchor_count=int(sensor.size),
    )


def _nearest_index(sorted_values: np.ndarray, query: float) -> int:
    position = int(np.searchsorted(sorted_values, query, side="left"))
    if position <= 0:
        return 0
    if position >= sorted_values.size:
        return int(sorted_values.size - 1)
    before = position - 1
    return before if abs(sorted_values[before] - query) <= abs(sorted_values[position] - query) else position


def align_gaze_to_frames(
    samples: Sequence[GazeSample],
    frame_timestamps_s: Sequence[float],
    *,
    clock_fit: ClockFit | None = None,
    tolerance_s: float = 0.040,
    minimum_confidence: float = 0.0,
) -> list[AlignedGazeSample]:
    """Nearest-neighbor align gaze without inventing samples across missing intervals."""

    if tolerance_s <= 0:
        raise ValueError("tolerance_s must be positive")
    frames = np.asarray(frame_timestamps_s, dtype=float)
    if frames.ndim != 1 or not np.all(np.isfinite(frames)):
        raise ValueError("frame timestamps must be a finite one-dimensional sequence")
    if frames.size and np.any(np.diff(frames) <= 0):
        raise ValueError("frame timestamps must be strictly increasing")

    accepted = [sample for sample in samples if sample.confidence >= minimum_confidence]
    if accepted:
        canonical_times = np.asarray(
            [clock_fit.map_time(sample.timestamp_s) if clock_fit else sample.timestamp_s for sample in accepted],
            dtype=float,
        )
        order = np.argsort(canonical_times)
        canonical_times = canonical_times[order]
        accepted = [accepted[int(index)] for index in order]
    else:
        canonical_times = np.asarray([], dtype=float)

    aligned: list[AlignedGazeSample] = []
    for frame_index, frame_timestamp in enumerate(frames):
        if canonical_times.size == 0:
            aligned.append(
                AlignedGazeSample(
                    frame_index=frame_index,
                    frame_timestamp_s=float(frame_timestamp),
                    sensor_timestamp_s=None,
                    canonical_sensor_timestamp_s=None,
                    delta_ms=None,
                    yaw_rad=None,
                    pitch_rad=None,
                    depth_m=None,
                    source="unknown",
                    confidence=0.0,
                    status="missing",
                )
            )
            continue
        index = _nearest_index(canonical_times, float(frame_timestamp))
        delta = float(canonical_times[index] - frame_timestamp)
        sample = accepted[index]
        within_tolerance = abs(delta) <= tolerance_s
        aligned.append(
            AlignedGazeSample(
                frame_index=frame_index,
                frame_timestamp_s=float(frame_timestamp),
                sensor_timestamp_s=float(sample.timestamp_s) if within_tolerance else None,
                canonical_sensor_timestamp_s=float(canonical_times[index]) if within_tolerance else None,
                delta_ms=delta * 1000.0 if within_tolerance else None,
                yaw_rad=float(sample.yaw_rad) if within_tolerance else None,
                pitch_rad=float(sample.pitch_rad) if within_tolerance else None,
                depth_m=sample.depth_m if within_tolerance else None,
                source=sample.source if within_tolerance else "unknown",
                confidence=float(sample.confidence) if within_tolerance else 0.0,
                status="aligned" if within_tolerance else "outside_tolerance",
            )
        )
    return aligned


def _angular_displacement(left: GazeSample, right: GazeSample) -> float:
    """Small-angle spherical displacement in radians."""

    delta_yaw = (right.yaw_rad - left.yaw_rad + math.pi) % (2.0 * math.pi) - math.pi
    delta_pitch = right.pitch_rad - left.pitch_rad
    return float(math.hypot(delta_yaw * math.cos((left.pitch_rad + right.pitch_rad) / 2.0), delta_pitch))


def detect_gaze_scan_events(
    samples: Sequence[GazeSample],
    *,
    angular_velocity_threshold_deg_s: float = 110.0,
    minimum_displacement_deg: float = 8.0,
    maximum_gap_s: float = 0.120,
) -> list[ScanEvent]:
    """Detect candidate scan movements from direct or calibrated gaze samples.

    This is a transparent threshold baseline. It should be validated against human
    annotations before being described as a physiological saccade detector.
    """

    if angular_velocity_threshold_deg_s <= 0 or minimum_displacement_deg <= 0:
        raise ValueError("scan thresholds must be positive")
    ordered = sorted(samples, key=lambda sample: sample.timestamp_s)
    events: list[ScanEvent] = []
    for left, right in zip(ordered, ordered[1:]):
        dt = right.timestamp_s - left.timestamp_s
        if dt <= 0 or dt > maximum_gap_s:
            continue
        displacement_deg = math.degrees(_angular_displacement(left, right))
        velocity = displacement_deg / dt
        if velocity < angular_velocity_threshold_deg_s or displacement_deg < minimum_displacement_deg:
            continue
        events.append(
            ScanEvent(
                start_timestamp_s=float(left.timestamp_s),
                end_timestamp_s=float(right.timestamp_s),
                peak_angular_velocity_deg_s=float(velocity),
                angular_displacement_deg=float(displacement_deg),
                source=right.source,
                confidence=float(min(left.confidence, right.confidence)),
            )
        )
    return events


def summarize_alignment(rows: Iterable[AlignedGazeSample]) -> dict[str, float | int | str]:
    materialized = list(rows)
    aligned = [row for row in materialized if row.status == "aligned"]
    deltas = np.asarray([abs(float(row.delta_ms)) for row in aligned if row.delta_ms is not None], dtype=float)
    return {
        "frame_count": len(materialized),
        "aligned_count": len(aligned),
        "coverage": len(aligned) / max(len(materialized), 1),
        "median_absolute_delta_ms": float(np.median(deltas)) if deltas.size else 0.0,
        "p95_absolute_delta_ms": float(np.percentile(deltas, 95)) if deltas.size else 0.0,
        "status": "direct_alignment_summary_not_tactical_interpretation",
    }
