from __future__ import annotations

import copy

import pytest

from midfielders_eye.empirical.adapters import GazeSample
from midfielders_eye.empirical.alignment import (
    align_gaze_to_frames,
    detect_gaze_scan_events,
    fit_linear_clock,
    summarize_alignment,
)
from midfielders_eye.empirical.capture import (
    default_midfield_capture_protocol,
    protocol_from_dict,
    validate_capture_protocol,
)


def test_linear_clock_fit_recovers_offset_and_drift() -> None:
    sensor = [0.0, 10.0, 20.0, 30.0]
    canonical = [0.125, 10.126, 20.127, 30.128]
    fit = fit_linear_clock(sensor, canonical)
    assert fit.offset_s == pytest.approx(0.125, abs=1e-9)
    assert fit.drift_ppm == pytest.approx(100.0, abs=1e-6)
    assert fit.rmse_ms < 1e-8
    assert fit.map_time(5.0) == pytest.approx(5.1255)


def test_gaze_alignment_preserves_missing_intervals() -> None:
    samples = [
        GazeSample(1.00, 0.1, 0.0, 3.0, "ego_exo4d_personalized", 0.95),
        GazeSample(1.04, 0.2, 0.0, 3.2, "ego_exo4d_personalized", 0.96),
    ]
    aligned = align_gaze_to_frames(samples, [1.00, 1.04, 1.20], tolerance_s=0.03)
    assert [row.status for row in aligned] == ["aligned", "aligned", "outside_tolerance"]
    assert aligned[-1].yaw_rad is None
    summary = summarize_alignment(aligned)
    assert summary["coverage"] == pytest.approx(2 / 3)


def test_scan_detector_is_explicit_threshold_baseline() -> None:
    samples = [
        GazeSample(0.00, 0.0, 0.0, None, "observed", 0.9),
        GazeSample(0.05, 0.3, 0.0, None, "observed", 0.9),
        GazeSample(0.10, 0.31, 0.0, None, "observed", 0.9),
    ]
    events = detect_gaze_scan_events(samples, angular_velocity_threshold_deg_s=100.0)
    assert len(events) == 1
    assert events[0].source == "observed"
    assert events[0].peak_angular_velocity_deg_s > 300.0


def test_default_capture_protocol_passes_governance_checks() -> None:
    protocol = default_midfield_capture_protocol("study-001")
    assert validate_capture_protocol(protocol) == []
    assert protocol.consent.public_identifiable_media is False
    assert any(sensor.modality == "binocular_eye_gaze" for sensor in protocol.sensors)
    assert len(protocol.task_blocks) >= 5


def test_capture_protocol_rejects_missing_drift_and_consent() -> None:
    payload = default_midfield_capture_protocol().to_dict()
    invalid = copy.deepcopy(payload)
    invalid["synchronization_anchor_count"] = 1
    invalid["post_block_drift_check"] = False
    invalid["consent"]["research_analysis"] = False
    errors = validate_capture_protocol(protocol_from_dict(invalid))
    assert any("two synchronization anchors" in error for error in errors)
    assert any("drift check" in error for error in errors)
    assert any("Research-analysis consent" in error for error in errors)
