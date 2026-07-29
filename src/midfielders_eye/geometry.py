from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .schema import FrameState, PlayerState

EPS = 1e-9


def unit(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    return vector / max(norm, EPS)


def angle_wrap(angle: float) -> float:
    return (angle + math.pi) % (2 * math.pi) - math.pi


def angle_to(source: np.ndarray, target: np.ndarray) -> float:
    delta = target - source
    return float(math.atan2(delta[1], delta[0]))


def angular_alignment(facing_angle: float, source: np.ndarray, target: np.ndarray) -> float:
    error = abs(angle_wrap(angle_to(source, target) - facing_angle))
    return float((math.cos(error) + 1.0) / 2.0)


def point_to_segment_distance(point: np.ndarray, start: np.ndarray, end: np.ndarray) -> float:
    segment = end - start
    denom = float(np.dot(segment, segment))
    if denom <= EPS:
        return float(np.linalg.norm(point - start))
    t = float(np.clip(np.dot(point - start, segment) / denom, 0.0, 1.0))
    projection = start + t * segment
    return float(np.linalg.norm(point - projection))


def segment_progress(point: np.ndarray, start: np.ndarray, end: np.ndarray) -> float:
    segment = end - start
    denom = float(np.dot(segment, segment))
    if denom <= EPS:
        return 0.0
    return float(np.clip(np.dot(point - start, segment) / denom, 0.0, 1.0))


def time_to_reach(
    player: PlayerState,
    target: np.ndarray,
    max_speed: float = 7.0,
    reaction_time: float = 0.15,
) -> float:
    displacement = target - player.position
    direction = unit(displacement)
    projected_speed = max(0.0, float(np.dot(player.velocity, direction)))
    effective_speed = max(1.0, min(max_speed, 0.65 * max_speed + 0.35 * projected_speed))
    return reaction_time + float(np.linalg.norm(displacement)) / effective_speed


def pass_travel_time(distance: float, ball_speed: float = 16.0) -> float:
    return distance / max(ball_speed, EPS)


@dataclass(slots=True)
class CorridorAssessment:
    minimum_clearance: float
    interception_margin_s: float
    pressure_shadow: float
    blocker_id: str | None


def assess_passing_corridor(
    passer: PlayerState,
    target: np.ndarray,
    defenders: list[PlayerState],
    ball_speed: float = 16.0,
    corridor_radius: float = 1.25,
) -> CorridorAssessment:
    distance = float(np.linalg.norm(target - passer.position))
    if not defenders:
        return CorridorAssessment(distance, 10.0, 0.0, None)

    minimum_clearance = float("inf")
    minimum_margin = float("inf")
    blocker_id: str | None = None
    shadow = 0.0

    for defender in defenders:
        clearance = point_to_segment_distance(defender.position, passer.position, target)
        progress = segment_progress(defender.position, passer.position, target)
        intercept_point = passer.position + progress * (target - passer.position)
        ball_t = pass_travel_time(progress * distance, ball_speed)
        defender_t = time_to_reach(defender, intercept_point)
        margin = defender_t - ball_t
        anisotropy = 1.0 + 0.5 * max(0.0, float(np.dot(unit(defender.velocity), unit(target - passer.position))))
        local_shadow = math.exp(-0.5 * (clearance / max(corridor_radius, EPS)) ** 2) * anisotropy
        shadow += local_shadow
        if clearance < minimum_clearance:
            minimum_clearance = clearance
            blocker_id = defender.player_id
        minimum_margin = min(minimum_margin, margin)

    return CorridorAssessment(
        minimum_clearance=float(minimum_clearance),
        interception_margin_s=float(minimum_margin),
        pressure_shadow=float(shadow),
        blocker_id=blocker_id,
    )


def local_pressure(
    point: np.ndarray,
    defenders: list[PlayerState],
    horizon_s: float = 0.0,
    sigma_front: float = 5.0,
    sigma_side: float = 3.0,
) -> float:
    pressure = 0.0
    for defender in defenders:
        future = defender.position + horizon_s * defender.velocity
        delta = point - future
        if defender.speed > 0.2:
            forward = unit(defender.velocity)
        else:
            forward = np.array([math.cos(defender.body_angle), math.sin(defender.body_angle)])
        lateral = np.array([-forward[1], forward[0]])
        front_component = float(np.dot(delta, forward))
        side_component = float(np.dot(delta, lateral))
        sigma_longitudinal = sigma_front if front_component >= 0 else sigma_front * 0.7
        exponent = -0.5 * (
            (front_component / sigma_longitudinal) ** 2 + (side_component / sigma_side) ** 2
        )
        momentum_gain = 1.0 + min(defender.speed, 8.0) / 8.0
        pressure += momentum_gain * math.exp(exponent)
    return float(pressure)


def future_space_score(
    point: np.ndarray,
    defenders: list[PlayerState],
    horizons_s: tuple[float, ...] = (0.0, 0.5, 1.0),
) -> float:
    pressures = [local_pressure(point, defenders, horizon_s=h) for h in horizons_s]
    mean_pressure = float(np.mean(pressures))
    trend = pressures[-1] - pressures[0]
    return float(1.0 / (1.0 + mean_pressure) - 0.15 * max(0.0, trend))


def visibility_score(
    viewer: PlayerState,
    target: np.ndarray,
    half_fov_degrees: float = 55.0,
) -> float:
    error = abs(angle_wrap(angle_to(viewer.position, target) - viewer.view_angle))
    half_fov = math.radians(half_fov_degrees)
    if error >= half_fov * 1.8:
        return 0.0
    return float(np.clip(1.0 - error / (half_fov * 1.8), 0.0, 1.0))


def normalized_goal_progress(frame: FrameState, start: np.ndarray, end: np.ndarray) -> float:
    direction = frame.attacking_direction[frame.possession_team]
    return float(direction * (end[0] - start[0]) / frame.pitch_length)


def simple_expected_threat(frame: FrameState, point: np.ndarray, team: str) -> float:
    direction = frame.attacking_direction[team]
    x_progress = point[0] / frame.pitch_length if direction > 0 else 1.0 - point[0] / frame.pitch_length
    center_bonus = 1.0 - abs(point[1] - frame.pitch_width / 2.0) / (frame.pitch_width / 2.0)
    box_proximity = 1.0 / (1.0 + math.exp(-10.0 * (x_progress - 0.72)))
    return float(np.clip(0.65 * x_progress**2 + 0.25 * box_proximity + 0.10 * center_bonus, 0.0, 1.0))


def option_creation_delta(
    frame: FrameState,
    mover: PlayerState,
    run_target: np.ndarray,
    defenders: list[PlayerState],
    horizon_s: float = 1.0,
) -> float:
    """Approximate how an off-ball run changes defensive shape and opens lanes.

    Defenders are softly attracted toward the predicted runner position. The returned value is
    the reduction in pressure around the current ball carrier plus the runner's future space.
    """
    before = local_pressure(frame.carrier.position, defenders, horizon_s=0.0)
    runner_future = mover.position + horizon_s * unit(run_target - mover.position) * min(6.5, mover.speed + 2.0)
    shifted: list[PlayerState] = []
    for defender in defenders:
        distance = float(np.linalg.norm(defender.position - runner_future))
        attention = math.exp(-distance / 12.0)
        displacement = attention * 1.2 * unit(runner_future - defender.position)
        shifted.append(
            PlayerState(
                player_id=defender.player_id,
                team=defender.team,
                x=float(defender.x + displacement[0]),
                y=float(defender.y + displacement[1]),
                vx=defender.vx,
                vy=defender.vy,
                body_angle=defender.body_angle,
            )
        )
    after = local_pressure(frame.carrier.position, shifted, horizon_s=0.0)
    runner_space = future_space_score(runner_future, shifted)
    return float((before - after) + 0.5 * runner_space)
