from __future__ import annotations

import math
from typing import Any

import numpy as np

from ..schema import ActionOption, FrameState, PlayerState
from .gaze import angular_distance, angle_to


def _unit(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    return vector / norm if norm > 1e-9 else np.zeros_like(vector, dtype=float)


def body_mechanics_source(player: PlayerState) -> str:
    source = str(player.metadata.get("body_mechanics_source", "")).strip()
    if source:
        return source
    if player.metadata.get("pose_observed"):
        return "pose_observed"
    if player.metadata.get("synthetic_subject"):
        return "synthetic"
    if player.metadata.get("body_angle_source") in {"observed", "pose_inferred"}:
        return str(player.metadata["body_angle_source"])
    return "kinematic_proxy"


def frame_body_mechanics(frame: FrameState, options: list[ActionOption]) -> dict[str, Any]:
    carrier = frame.carrier
    body_vector = np.array([math.cos(carrier.body_angle), math.sin(carrier.body_angle)], dtype=float)
    velocity_unit = _unit(carrier.velocity)
    acceleration = carrier.acceleration
    acceleration_mag = float(np.linalg.norm(acceleration))
    forward_acceleration = float(np.dot(acceleration, body_vector))
    lateral_acceleration = float(abs(body_vector[0] * acceleration[1] - body_vector[1] * acceleration[0]))
    braking_intensity = 0.0
    if carrier.speed > 0.2:
        braking_intensity = max(0.0, -float(np.dot(acceleration, velocity_unit)))
    movement_heading = carrier.body_angle if carrier.speed < 0.2 else math.atan2(carrier.vy, carrier.vx)
    separation = angular_distance(carrier.body_angle, movement_heading)
    teammate_angles = [angle_to(carrier.position, teammate.position) for teammate in frame.teammates()]
    open_access = sum(angular_distance(carrier.body_angle, angle) <= math.radians(85) for angle in teammate_angles)
    rear_access = sum(angular_distance(carrier.body_angle, angle) > math.radians(120) for angle in teammate_angles)
    pass_options = [option for option in options if option.kind == "pass"]
    action_types = {option.kind for option in options}
    option_angles = [angle_to(carrier.position, np.array([option.target_x, option.target_y])) for option in pass_options]
    if option_angles:
        radians = np.asarray(option_angles)
        circular_spread = 1.0 - float(np.hypot(np.mean(np.cos(radians)), np.mean(np.sin(radians))))
    else:
        circular_spread = 0.0
    turning_load = min(1.0, abs(float(carrier.turning_rate)) / 3.5)
    braking_load = min(1.0, braking_intensity / 7.0)
    lateral_load = min(1.0, lateral_acceleration / 7.0)
    acceleration_load = min(1.0, acceleration_mag / 9.0)
    balance_reserve = float(np.clip(1.0 - 0.30 * turning_load - 0.30 * braking_load - 0.25 * lateral_load - 0.15 * acceleration_load, 0.0, 1.0))
    open_body_score = float(np.clip((open_access + 0.5 * circular_spread * max(len(pass_options), 1)) / max(len(frame.teammates()), 1), 0.0, 1.0))
    multi_action_readiness = float(np.clip(0.45 * balance_reserve + 0.30 * open_body_score + 0.25 * min(len(action_types) / 3.0, 1.0), 0.0, 1.0))
    transfer_vector = acceleration if acceleration_mag > 0.15 else carrier.velocity
    return {
        "frame_id": frame.frame_id,
        "timestamp_s": float(frame.timestamp_s),
        "source": body_mechanics_source(carrier),
        "body_angle_rad": float(carrier.body_angle),
        "movement_heading_rad": float(movement_heading),
        "body_movement_separation_deg": math.degrees(separation),
        "forward_acceleration_mps2": forward_acceleration,
        "lateral_load_proxy": lateral_load,
        "braking_load_proxy": braking_load,
        "turning_load_proxy": turning_load,
        "balance_reserve_proxy": balance_reserve,
        "open_body_score": open_body_score,
        "rear_access_count": int(rear_access),
        "multi_action_readiness": multi_action_readiness,
        "action_type_count": len(action_types),
        "option_angular_spread": circular_spread,
        "weight_transfer_vector": [float(transfer_vector[0]), float(transfer_vector[1])],
        "metric_status": "kinematic_or_pose_proxy_not_direct_force_plate_measurement",
    }


def sequence_body_summary(
    frames: list[FrameState],
    options_by_frame: dict[int, list[ActionOption]],
) -> dict[str, Any]:
    timeline = [frame_body_mechanics(frame, options_by_frame.get(frame.frame_id, [])) for frame in frames]
    keys = [
        "body_movement_separation_deg",
        "lateral_load_proxy",
        "braking_load_proxy",
        "turning_load_proxy",
        "balance_reserve_proxy",
        "open_body_score",
        "multi_action_readiness",
        "option_angular_spread",
    ]
    summary = {
        key: float(np.mean([float(row[key]) for row in timeline])) if timeline else 0.0
        for key in keys
    }
    summary["peak_turning_load_proxy"] = max([float(row["turning_load_proxy"]) for row in timeline], default=0.0)
    summary["minimum_balance_reserve_proxy"] = min([float(row["balance_reserve_proxy"]) for row in timeline], default=0.0)
    return {
        "timeline": timeline,
        "summary": summary,
        "interpretation_guardrail": "Body-weight and balance values are kinematic proxies unless pose or force data are explicitly attached.",
    }
