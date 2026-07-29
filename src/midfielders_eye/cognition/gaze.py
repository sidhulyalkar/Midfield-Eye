from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Literal

import numpy as np

from ..schema import ActionOption, FrameState, PlayerState

GazeSource = Literal["observed", "pose_inferred", "motion_proxy", "synthetic", "unknown"]


def wrap_angle(angle: float) -> float:
    return float((angle + math.pi) % (2.0 * math.pi) - math.pi)


def angular_distance(left: float, right: float) -> float:
    return abs(wrap_angle(left - right))


def angle_to(origin: np.ndarray, target: np.ndarray) -> float:
    delta = np.asarray(target, dtype=float) - np.asarray(origin, dtype=float)
    return float(math.atan2(float(delta[1]), float(delta[0])))


def gaze_source(player: PlayerState) -> GazeSource:
    declared = str(player.metadata.get("gaze_source", "")).strip().lower()
    if declared in {"observed", "pose_inferred", "motion_proxy", "synthetic", "unknown"}:
        return declared  # type: ignore[return-value]
    if player.metadata.get("synthetic_subject") or player.metadata.get("gaze_synthetic"):
        return "synthetic"
    if player.gaze_angle is not None and player.metadata.get("gaze_observed"):
        return "observed"
    if player.gaze_angle is not None or player.head_angle is not None:
        return "pose_inferred"
    if abs(player.body_angle) > 1e-8 or player.speed > 0.4:
        return "motion_proxy"
    return "unknown"


def gaze_confidence(player: PlayerState) -> float:
    explicit = player.metadata.get("gaze_confidence")
    if explicit is not None:
        return float(np.clip(float(explicit), 0.0, 1.0))
    defaults = {
        "observed": 0.95,
        "pose_inferred": 0.62,
        "motion_proxy": 0.30,
        "synthetic": 1.0,
        "unknown": 0.10,
    }
    return defaults[gaze_source(player)]


def point_in_view(
    player: PlayerState,
    target: np.ndarray,
    *,
    half_width_deg: float = 55.0,
    max_distance_m: float = 45.0,
) -> bool:
    delta = np.asarray(target, dtype=float) - player.position
    distance = float(np.linalg.norm(delta))
    if distance > max_distance_m or distance < 1e-9:
        return False
    half_width = math.radians(half_width_deg)
    return angular_distance(angle_to(player.position, target), player.view_angle) <= half_width


def _cone_polygon(
    player: PlayerState,
    *,
    half_width_deg: float,
    radius_m: float,
    samples: int = 32,
) -> list[list[float]]:
    half_width = math.radians(half_width_deg)
    angles = np.linspace(player.view_angle - half_width, player.view_angle + half_width, samples)
    points = [[float(player.x), float(player.y)]]
    points.extend(
        [
            float(player.x + radius_m * math.cos(float(angle))),
            float(player.y + radius_m * math.sin(float(angle))),
        ]
        for angle in angles
    )
    points.append([float(player.x), float(player.y)])
    return points


def view_cone_polygons(player: PlayerState) -> dict[str, dict[str, Any]]:
    """Return frontend-ready nested fields of view.

    These are geometric visualization bands, not claims about exact human visual acuity.
    """
    confidence = gaze_confidence(player)
    source = gaze_source(player)
    return {
        "foveal": {
            "half_width_deg": 15.0,
            "radius_m": 28.0,
            "polygon": _cone_polygon(player, half_width_deg=15.0, radius_m=28.0),
            "source": source,
            "confidence": confidence,
        },
        "actionable": {
            "half_width_deg": 55.0,
            "radius_m": 45.0,
            "polygon": _cone_polygon(player, half_width_deg=55.0, radius_m=45.0),
            "source": source,
            "confidence": confidence,
        },
        "peripheral": {
            "half_width_deg": 85.0,
            "radius_m": 32.0,
            "polygon": _cone_polygon(player, half_width_deg=85.0, radius_m=32.0),
            "source": source,
            "confidence": confidence,
        },
    }


def frame_gaze_metrics(frame: FrameState, options: list[ActionOption]) -> dict[str, Any]:
    carrier = frame.carrier
    pass_options = [option for option in options if option.kind == "pass"]
    actionable_visible = [
        option
        for option in pass_options
        if point_in_view(carrier, np.array([option.target_x, option.target_y]), half_width_deg=55.0)
    ]
    foveal = [
        option
        for option in pass_options
        if point_in_view(carrier, np.array([option.target_x, option.target_y]), half_width_deg=15.0)
    ]
    peripheral = [
        option
        for option in pass_options
        if point_in_view(carrier, np.array([option.target_x, option.target_y]), half_width_deg=85.0)
    ]
    ranked = sorted(pass_options, key=lambda option: option.geometric_score, reverse=True)
    top = ranked[0] if ranked else None
    top_angle_error = None
    if top is not None:
        top_angle_error = angular_distance(
            carrier.view_angle,
            angle_to(carrier.position, np.array([top.target_x, top.target_y])),
        )
    angles = [angle_to(carrier.position, teammate.position) for teammate in frame.teammates()]
    visible_teammates = sum(angular_distance(carrier.view_angle, angle) <= math.radians(55.0) for angle in angles)
    head = carrier.head_angle if carrier.head_angle is not None else carrier.body_angle
    gaze = carrier.gaze_angle if carrier.gaze_angle is not None else head
    return {
        "frame_id": frame.frame_id,
        "timestamp_s": float(frame.timestamp_s),
        "gaze_angle_rad": float(gaze),
        "head_angle_rad": float(head),
        "body_angle_rad": float(carrier.body_angle),
        "gaze_source": gaze_source(carrier),
        "gaze_confidence": gaze_confidence(carrier),
        "head_body_dissociation_deg": math.degrees(angular_distance(head, carrier.body_angle)),
        "gaze_head_dissociation_deg": math.degrees(angular_distance(gaze, head)),
        "foveal_option_count": len(foveal),
        "actionable_visible_option_count": len(actionable_visible),
        "peripheral_option_count": len(peripheral),
        "blind_side_option_count": max(0, len(pass_options) - len(peripheral)),
        "visible_option_recall": len(actionable_visible) / max(len(pass_options), 1),
        "visible_teammate_count": int(visible_teammates),
        "top_option_id": None if top is None else top.option_id,
        "top_option_angle_error_deg": None if top_angle_error is None else math.degrees(top_angle_error),
        "top_option_in_actionable_view": False if top is None else top in actionable_visible,
        "view_cones": view_cone_polygons(carrier),
        "metric_status": "geometric_view_model_with_explicit_source_confidence",
    }


def _scan_events(timeline: list[dict[str, Any]], threshold_deg_s: float = 90.0) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for left, right in zip(timeline, timeline[1:]):
        dt = float(right["timestamp_s"]) - float(left["timestamp_s"])
        if dt <= 0:
            continue
        delta = math.degrees(angular_distance(float(right["head_angle_rad"]), float(left["head_angle_rad"])))
        velocity = delta / dt
        if velocity >= threshold_deg_s:
            events.append(
                {
                    "start_frame_id": left["frame_id"],
                    "end_frame_id": right["frame_id"],
                    "timestamp_s": right["timestamp_s"],
                    "angular_velocity_deg_s": velocity,
                    "source": right["gaze_source"],
                }
            )
    return events


def sequence_gaze_summary(
    frames: list[FrameState],
    options_by_frame: dict[int, list[ActionOption]],
) -> dict[str, Any]:
    timeline = [frame_gaze_metrics(frame, options_by_frame.get(frame.frame_id, [])) for frame in frames]
    events = _scan_events(timeline)
    duration = max(float(frames[-1].timestamp_s - frames[0].timestamp_s), 1e-6) if frames else 0.0
    acquisitions: dict[str, float] = {}
    dwell_by_option: defaultdict[str, float] = defaultdict(float)
    last_t: float | None = None
    for row in timeline:
        timestamp = float(row["timestamp_s"])
        option_id = row.get("top_option_id")
        if option_id and row.get("top_option_in_actionable_view"):
            acquisitions.setdefault(str(option_id), timestamp)
            if last_t is not None:
                dwell_by_option[str(option_id)] += max(0.0, timestamp - last_t)
        last_t = timestamp
    confidence = [float(row["gaze_confidence"]) for row in timeline]
    return {
        "timeline": timeline,
        "scan_events": events,
        "summary": {
            "scan_count": len(events),
            "scan_rate_hz": len(events) / duration if duration > 0 else 0.0,
            "mean_head_body_dissociation_deg": float(np.mean([row["head_body_dissociation_deg"] for row in timeline])) if timeline else 0.0,
            "mean_visible_option_recall": float(np.mean([row["visible_option_recall"] for row in timeline])) if timeline else 0.0,
            "mean_gaze_confidence": float(np.mean(confidence)) if confidence else 0.0,
            "top_option_first_acquisition_s": acquisitions,
            "top_option_visible_dwell_s": dict(dwell_by_option),
        },
        "interpretation_guardrail": "Scan events and view cones are source-sensitive proxies unless gaze_source is observed.",
    }
