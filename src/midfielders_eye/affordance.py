from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .geometry import (
    angular_alignment,
    assess_passing_corridor,
    future_space_score,
    local_pressure,
    normalized_goal_progress,
    option_creation_delta,
    simple_expected_threat,
    unit,
    visibility_score,
)
from .schema import ActionOption, FrameState


DEFAULT_WEIGHTS = {
    "lane_clearance": 0.14,
    "interception_margin": 0.17,
    "receiver_space": 0.15,
    "future_space": 0.13,
    "forward_progress": 0.10,
    "xt_gain": 0.13,
    "body_orientation": 0.06,
    "visibility": 0.07,
    "option_creation": 0.05,
    "state_confidence": 0.04,
    "distance_penalty": -0.04,
}


@dataclass(slots=True)
class AffordanceConfig:
    carry_distance_m: float = 7.0
    carry_angle_offsets_deg: tuple[float, ...] = (-45.0, -22.5, 0.0, 22.5, 45.0)
    include_hold: bool = True
    ball_speed_mps: float = 16.0
    visibility_half_fov_deg: float = 55.0
    weights: dict[str, float] | None = None


class AffordanceEngine:
    """Generate and score the action menu available to the current ball carrier."""

    feature_names = (
        "distance_m",
        "lane_clearance_m",
        "interception_margin_s",
        "pressure_shadow",
        "receiver_pressure",
        "receiver_space",
        "future_space",
        "forward_progress",
        "xt_start",
        "xt_end",
        "xt_gain",
        "body_orientation",
        "visibility",
        "target_motion_alignment",
        "option_creation",
        "uncertainty_adjusted_clearance_m",
        "target_uncertainty_m",
        "defender_uncertainty_m",
        "visible_pitch_fraction",
        "state_confidence",
    )

    def __init__(self, config: AffordanceConfig | None = None):
        self.config = config or AffordanceConfig()
        self.weights = self.config.weights or DEFAULT_WEIGHTS

    def generate(self, frame: FrameState) -> list[ActionOption]:
        frame.validate()
        options: list[ActionOption] = []
        carrier = frame.carrier
        defenders = frame.opponents()

        for teammate in frame.teammates():
            options.append(self._pass_option(frame, teammate, defenders))

        facing = carrier.body_angle
        for offset in self.config.carry_angle_offsets_deg:
            angle = facing + math.radians(offset)
            target = carrier.position + self.config.carry_distance_m * np.array(
                [math.cos(angle), math.sin(angle)]
            )
            target[0] = float(np.clip(target[0], 0.0, frame.pitch_length))
            target[1] = float(np.clip(target[1], 0.0, frame.pitch_width))
            options.append(self._carry_option(frame, target, offset, defenders))

        if self.config.include_hold:
            options.append(self._hold_option(frame, defenders))
        return options

    def _base_features(
        self,
        frame: FrameState,
        target: np.ndarray,
        defenders,
        target_velocity: np.ndarray | None = None,
        target_uncertainty_m: float = 0.0,
    ) -> dict[str, float]:
        carrier = frame.carrier
        delta = target - carrier.position
        distance = float(np.linalg.norm(delta))
        corridor = assess_passing_corridor(
            carrier,
            target,
            defenders,
            ball_speed=self.config.ball_speed_mps,
        )
        pressure = local_pressure(target, defenders)
        future_space = future_space_score(target, defenders)
        xt_start = simple_expected_threat(frame, carrier.position, carrier.team)
        xt_end = simple_expected_threat(frame, target, carrier.team)
        target_motion_alignment = 0.5
        if target_velocity is not None and float(np.linalg.norm(target_velocity)) > 0.1:
            target_motion_alignment = float((np.dot(unit(delta), unit(target_velocity)) + 1.0) / 2.0)
        defender_uncertainties = [defender.uncertainty_radius_m for defender in defenders]
        defender_uncertainty = (
            float(np.mean(defender_uncertainties)) if defender_uncertainties else 0.0
        )
        robust_clearance = corridor.minimum_clearance - target_uncertainty_m - 0.5 * defender_uncertainty
        visible_fraction = 1.0
        if frame.visibility_polygon:
            polygon = np.asarray(frame.visibility_polygon, dtype=float)
            if polygon.ndim == 2 and polygon.shape[1] == 2:
                x, y = polygon[:, 0], polygon[:, 1]
                area = 0.5 * abs(float(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1))))
                visible_fraction = float(np.clip(area / (frame.pitch_length * frame.pitch_width), 0.0, 1.0))
        confidence_values = [
            value
            for value in [
                carrier.confidence,
                carrier.trajectory_confidence,
                frame.calibration_confidence,
            ]
            if value is not None
        ]
        state_confidence = float(np.mean(confidence_values)) if confidence_values else 0.5
        state_confidence *= max(visible_fraction, 0.25)
        return {
            "distance_m": distance,
            "lane_clearance_m": corridor.minimum_clearance,
            "interception_margin_s": corridor.interception_margin_s,
            "pressure_shadow": corridor.pressure_shadow,
            "receiver_pressure": pressure,
            "receiver_space": 1.0 / (1.0 + pressure),
            "future_space": future_space,
            "forward_progress": normalized_goal_progress(frame, carrier.position, target),
            "xt_start": xt_start,
            "xt_end": xt_end,
            "xt_gain": xt_end - xt_start,
            "body_orientation": angular_alignment(carrier.body_angle, carrier.position, target),
            "visibility": visibility_score(
                carrier, target, half_fov_degrees=self.config.visibility_half_fov_deg
            ),
            "target_motion_alignment": target_motion_alignment,
            "option_creation": 0.0,
            "uncertainty_adjusted_clearance_m": robust_clearance,
            "target_uncertainty_m": target_uncertainty_m,
            "defender_uncertainty_m": defender_uncertainty,
            "visible_pitch_fraction": visible_fraction,
            "state_confidence": state_confidence,
        }

    def _pass_option(self, frame: FrameState, teammate, defenders) -> ActionOption:
        lead_time = min(0.7, float(np.linalg.norm(teammate.position - frame.carrier.position)) / 25.0)
        target = teammate.position + lead_time * teammate.velocity
        target[0] = float(np.clip(target[0], 0.0, frame.pitch_length))
        target[1] = float(np.clip(target[1], 0.0, frame.pitch_width))
        features = self._base_features(
            frame,
            target,
            defenders,
            teammate.velocity,
            target_uncertainty_m=teammate.uncertainty_radius_m,
        )
        run_target = target + 4.0 * unit(teammate.velocity if teammate.speed > 0.2 else target - teammate.position)
        features["option_creation"] = option_creation_delta(
            frame, teammate, run_target, defenders
        )
        score = self.score(features)
        return ActionOption(
            sequence_id=frame.sequence_id,
            frame_id=frame.frame_id,
            option_id=f"{frame.sequence_id}:{frame.frame_id}:pass:{teammate.player_id}",
            kind="pass",
            actor_id=frame.ball_carrier_id,
            target_player_id=teammate.player_id,
            target_x=float(target[0]),
            target_y=float(target[1]),
            features=features,
            geometric_score=score,
            source_provider=frame.source_provider,
            source_match_id=frame.source_match_id,
        )

    def _carry_option(self, frame: FrameState, target: np.ndarray, offset: float, defenders) -> ActionOption:
        features = self._base_features(
            frame, target, defenders, target_uncertainty_m=frame.carrier.uncertainty_radius_m
        )
        score = self.score(features) - 0.03 * abs(offset) / 45.0
        return ActionOption(
            sequence_id=frame.sequence_id,
            frame_id=frame.frame_id,
            option_id=f"{frame.sequence_id}:{frame.frame_id}:carry:{offset:+.1f}",
            kind="carry",
            actor_id=frame.ball_carrier_id,
            target_player_id=None,
            target_x=float(target[0]),
            target_y=float(target[1]),
            features=features,
            geometric_score=float(score),
            source_provider=frame.source_provider,
            source_match_id=frame.source_match_id,
        )

    def _hold_option(self, frame: FrameState, defenders) -> ActionOption:
        target = frame.carrier.position
        features = self._base_features(
            frame, target, defenders, target_uncertainty_m=frame.carrier.uncertainty_radius_m
        )
        features["lane_clearance_m"] = 0.0
        features["interception_margin_s"] = -local_pressure(target, defenders)
        features["visibility"] = 1.0
        score = self.score(features) - 0.1
        return ActionOption(
            sequence_id=frame.sequence_id,
            frame_id=frame.frame_id,
            option_id=f"{frame.sequence_id}:{frame.frame_id}:hold",
            kind="hold",
            actor_id=frame.ball_carrier_id,
            target_player_id=None,
            target_x=float(target[0]),
            target_y=float(target[1]),
            features=features,
            geometric_score=float(score),
            source_provider=frame.source_provider,
            source_match_id=frame.source_match_id,
        )

    def score(self, features: dict[str, float]) -> float:
        normalized = {
            "lane_clearance": np.tanh(
                features.get("uncertainty_adjusted_clearance_m", features["lane_clearance_m"]) / 4.0
            ),
            "interception_margin": np.tanh(features["interception_margin_s"] / 1.5),
            "receiver_space": features["receiver_space"],
            "future_space": features["future_space"],
            "forward_progress": np.tanh(features["forward_progress"] * 4.0),
            "xt_gain": np.tanh(features["xt_gain"] * 5.0),
            "body_orientation": features["body_orientation"],
            "visibility": features["visibility"],
            "option_creation": np.tanh(features["option_creation"]),
            "state_confidence": features.get("state_confidence", 0.5),
            "distance_penalty": min(features["distance_m"] / 45.0, 1.0),
        }
        score = sum(self.weights[name] * float(value) for name, value in normalized.items())
        return float(score)
