from __future__ import annotations

import copy
import math
from dataclasses import asdict, dataclass, field

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from .affordance import AffordanceEngine
from .geometry import local_pressure
from .schema import ActionOption, FrameState, PlayerState
from .state.state_completion import apply_camera_crop


@dataclass(slots=True)
class DegradationConfig:
    name: str = "custom"
    position_noise_std_m: float = 0.0
    missing_player_rate: float = 0.0
    id_switch_rate: float = 0.0
    calibration_drift_x_m: float = 0.0
    calibration_drift_y_m: float = 0.0
    camera_crop_width_m: float | None = None
    camera_crop_height_m: float | None = None
    delay_frames: int = 0
    ball_dropout_rate: float = 0.0
    seed: int = 7

    def validate(self) -> None:
        for name in ("missing_player_rate", "id_switch_rate", "ball_dropout_rate"):
            value = getattr(self, name)
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be in [0, 1]")
        if self.position_noise_std_m < 0 or self.delay_frames < 0:
            raise ValueError("noise and delay must be non-negative")


@dataclass(slots=True)
class DegradationResult:
    frames: list[FrameState]
    config: DegradationConfig
    counts: dict[str, int] = field(default_factory=dict)

    def summary(self) -> dict:
        return {"config": asdict(self.config), "counts": self.counts, "frames": len(self.frames)}


def _identity(player: PlayerState) -> str:
    return (
        player.source_player_id
        or player.metadata.get("synthetic_original_player_id")
        or player.track_id
        or player.player_id
    )


def degrade_frames(frames: list[FrameState], config: DegradationConfig) -> DegradationResult:
    """Apply controlled perception failures while preserving explicit provenance."""
    config.validate()
    rng = np.random.default_rng(config.seed)
    output = copy.deepcopy(sorted(frames, key=lambda frame: (frame.sequence_id, frame.timestamp_s)))
    counts = {
        "position_noised": 0,
        "players_missing": 0,
        "id_switches": 0,
        "camera_crops": 0,
        "delayed_observations": 0,
        "ball_dropouts": 0,
    }
    history: dict[tuple[str, str], list[PlayerState]] = {}

    for frame_index, frame in enumerate(output):
        original_players = copy.deepcopy(frame.players)
        for player in original_players:
            history.setdefault((frame.sequence_id, _identity(player)), []).append(copy.deepcopy(player))

        if config.delay_frames > 0:
            for player in frame.players:
                track_history = history.get((frame.sequence_id, _identity(player)), [])
                if len(track_history) > config.delay_frames:
                    delayed = track_history[-config.delay_frames - 1]
                    player.x, player.y = delayed.x, delayed.y
                    player.vx, player.vy = delayed.vx, delayed.vy
                    player.provenance_flags.append(f"delayed_{config.delay_frames}_frames")
                    counts["delayed_observations"] += 1
            frame.quality_flags.append("delayed_observations")

        for player in frame.players:
            if config.position_noise_std_m > 0:
                noise = rng.normal(0.0, config.position_noise_std_m, size=2)
                player.x += float(noise[0])
                player.y += float(noise[1])
                covariance = player.covariance_matrix + np.eye(2) * config.position_noise_std_m**2
                player.position_covariance = covariance.tolist()
                player.provenance_flags.append("synthetic_position_noise")
                counts["position_noised"] += 1
            player.x += config.calibration_drift_x_m
            player.y += config.calibration_drift_y_m
            player.x = float(np.clip(player.x, 0.0, frame.pitch_length))
            player.y = float(np.clip(player.y, 0.0, frame.pitch_width))
        if config.calibration_drift_x_m or config.calibration_drift_y_m:
            frame.quality_flags.append("synthetic_calibration_drift")

        if config.camera_crop_width_m and config.camera_crop_height_m:
            carrier = frame.carrier
            half_width = config.camera_crop_width_m / 2
            half_height = config.camera_crop_height_m / 2
            left = float(np.clip(carrier.x - half_width, 0.0, frame.pitch_length))
            right = float(np.clip(carrier.x + half_width, 0.0, frame.pitch_length))
            top = float(np.clip(carrier.y - half_height, 0.0, frame.pitch_width))
            bottom = float(np.clip(carrier.y + half_height, 0.0, frame.pitch_width))
            frame = apply_camera_crop(frame, [[left, top], [right, top], [right, bottom], [left, bottom]])
            counts["camera_crops"] += 1

        if config.missing_player_rate > 0:
            kept = []
            for player in frame.players:
                if player.player_id == frame.ball_carrier_id or rng.random() >= config.missing_player_rate:
                    kept.append(player)
                else:
                    counts["players_missing"] += 1
            frame.players = kept
            frame.quality_flags.append("synthetic_missing_players")

        if config.id_switch_rate > 0:
            for team in ("home", "away"):
                candidates = [player for player in frame.players if player.team == team and player.player_id != frame.ball_carrier_id]
                rng.shuffle(candidates)
                for first, second in zip(candidates[::2], candidates[1::2]):
                    if rng.random() >= config.id_switch_rate:
                        continue
                    first.metadata.setdefault("synthetic_original_player_id", first.player_id)
                    second.metadata.setdefault("synthetic_original_player_id", second.player_id)
                    first.player_id, second.player_id = second.player_id, first.player_id
                    first.track_id, second.track_id = second.track_id, first.track_id
                    first.provenance_flags.append("synthetic_id_switch")
                    second.provenance_flags.append("synthetic_id_switch")
                    counts["id_switches"] += 1
            frame.quality_flags.append("synthetic_id_switches")

        if rng.random() < config.ball_dropout_rate:
            frame.ball_status = "dropped"
            frame.ball_confidence = 0.0
            frame.quality_flags.append("synthetic_ball_dropout")
            counts["ball_dropouts"] += 1

        frame.quality_flags = sorted(set(frame.quality_flags + [f"degradation:{config.name}"]))
        frame.metadata["degradation_config"] = asdict(config)
        frame.validate()
        # apply_camera_crop returns a copied frame, so replace the current object in output.
        output[frame_index] = frame

    return DegradationResult(frames=output, config=config, counts=counts)


def _option_distance(left: ActionOption, right: ActionOption) -> float:
    if left.kind != right.kind:
        return math.inf
    return float(np.linalg.norm(left.target - right.target))


def _match_options(
    oracle: list[ActionOption], degraded: list[ActionOption], tolerance_m: float = 4.0
) -> list[tuple[ActionOption, ActionOption]]:
    candidates = []
    used = set()
    for oracle_option in oracle:
        distances = [
            (_option_distance(oracle_option, option), index, option)
            for index, option in enumerate(degraded)
            if index not in used
        ]
        if not distances:
            continue
        distance, index, option = min(distances, key=lambda item: item[0])
        if distance <= tolerance_m:
            candidates.append((oracle_option, option))
            used.add(index)
    return candidates


def pressure_map(frame: FrameState, grid_x: int = 36, grid_y: int = 24) -> np.ndarray:
    x_values = np.linspace(0, frame.pitch_length, grid_x)
    y_values = np.linspace(0, frame.pitch_width, grid_y)
    defenders = frame.opponents()
    return np.array(
        [[local_pressure(np.array([x, y]), defenders) for x in x_values] for y in y_values],
        dtype=float,
    )


def pressure_map_iou(oracle: FrameState, degraded: FrameState, quantile: float = 0.7) -> float:
    oracle_map = pressure_map(oracle)
    degraded_map = pressure_map(degraded)
    threshold = float(np.quantile(oracle_map, quantile))
    oracle_mask = oracle_map >= threshold
    degraded_mask = degraded_map >= threshold
    union = np.logical_or(oracle_mask, degraded_mask).sum()
    return 1.0 if union == 0 else float(np.logical_and(oracle_mask, degraded_mask).sum() / union)


def _visible_pitch_fraction(frame: FrameState) -> float:
    if not frame.visibility_polygon:
        return 1.0
    polygon = np.asarray(frame.visibility_polygon, dtype=float)
    if polygon.ndim != 2 or polygon.shape[1] != 2 or len(polygon) < 3:
        return math.nan
    x, y = polygon[:, 0], polygon[:, 1]
    area = 0.5 * abs(float(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1))))
    return float(np.clip(area / max(frame.pitch_length * frame.pitch_width, 1e-6), 0.0, 1.0))


def _sequence_identity_metrics(
    oracle_frames: list[FrameState], degraded_frames: list[FrameState]
) -> dict[str, float]:
    oracle_assignments: dict[str, list[tuple[int, str]]] = {}
    degraded_assignments: dict[str, list[tuple[int, str]]] = {}
    for frame in oracle_frames:
        for player in frame.players:
            identity = (
                player.source_player_id
                or player.metadata.get("synthetic_original_player_id")
                or player.player_id
            )
            oracle_assignments.setdefault(identity, []).append(
                (frame.frame_id, player.track_id or player.player_id)
            )
    for frame in degraded_frames:
        for player in frame.players:
            identity = (
                player.source_player_id
                or player.metadata.get("synthetic_original_player_id")
                or player.player_id
            )
            degraded_assignments.setdefault(identity, []).append(
                (frame.frame_id, player.track_id or player.player_id)
            )

    correct = 0
    total = 0
    switches = 0
    fragments = []
    for identity, oracle_track in oracle_assignments.items():
        oracle_by_frame = dict(oracle_track)
        degraded_track = sorted(degraded_assignments.get(identity, []))
        previous_track = None
        unique_tracks = set()
        for frame_id, track_id in degraded_track:
            unique_tracks.add(track_id)
            if frame_id in oracle_by_frame:
                total += 1
                correct += int(track_id == oracle_by_frame[frame_id])
            if previous_track is not None and track_id != previous_track:
                switches += 1
            previous_track = track_id
        if degraded_track:
            fragments.append(len(unique_tracks))
    return {
        "identity_assignment_accuracy": correct / max(total, 1),
        "id_switch_count": float(switches),
        "track_fragments_per_identity": float(np.mean(fragments)) if fragments else math.nan,
    }


def perception_frame_metrics(oracle: FrameState, degraded: FrameState) -> dict[str, float]:
    oracle_by_id = {_identity(player): player for player in oracle.players}
    degraded_by_id = {_identity(player): player for player in degraded.players}
    common = sorted(set(oracle_by_id) & set(degraded_by_id))
    displacement_vectors = [
        degraded_by_id[key].position - oracle_by_id[key].position for key in common
    ]
    pitch_errors = [float(np.linalg.norm(vector)) for vector in displacement_vectors]
    velocity_errors = [
        float(np.linalg.norm(oracle_by_id[key].velocity - degraded_by_id[key].velocity)) for key in common
    ]
    acceleration_errors = [
        float(np.linalg.norm(oracle_by_id[key].acceleration - degraded_by_id[key].acceleration))
        for key in common
    ]
    heading_errors = []
    for key in common:
        left = oracle_by_id[key].body_angle
        right = degraded_by_id[key].body_angle
        heading_errors.append(abs((left - right + math.pi) % (2 * math.pi) - math.pi))
    team_accuracy = [float(oracle_by_id[key].team == degraded_by_id[key].team) for key in common]
    ball_available = float(degraded.ball_status != "dropped" and degraded.ball_confidence != 0.0)
    return {
        "player_recall": len(common) / max(len(oracle_by_id), 1),
        "pitch_error_m": float(np.mean(pitch_errors)) if pitch_errors else math.nan,
        "velocity_error_mps": float(np.mean(velocity_errors)) if velocity_errors else math.nan,
        "acceleration_error_mps2": (
            float(np.mean(acceleration_errors)) if acceleration_errors else math.nan
        ),
        "heading_error_rad": float(np.mean(heading_errors)) if heading_errors else math.nan,
        "team_accuracy": float(np.mean(team_accuracy)) if team_accuracy else math.nan,
        "calibration_offset_error_m": (
            float(np.linalg.norm(np.median(np.asarray(displacement_vectors), axis=0)))
            if displacement_vectors
            else math.nan
        ),
        "visible_pitch_fraction": _visible_pitch_fraction(degraded),
        "ball_state_available": ball_available,
        "actionable_affordance_state": ball_available * float(degraded.ball_carrier_id in {p.player_id for p in degraded.players}),
    }


def _is_line_breaking(frame: FrameState, option: ActionOption) -> bool:
    if option.kind != "pass":
        return False
    direction = frame.attacking_direction[frame.possession_team]
    if direction * (option.target_x - frame.carrier.x) <= 0:
        return False
    defender_x = [player.x for player in frame.opponents()]
    if not defender_x:
        return False
    line = float(np.median(defender_x))
    return direction * (option.target_x - line) > 0


def tactical_frame_metrics(oracle: FrameState, degraded: FrameState) -> dict[str, float]:
    engine = AffordanceEngine()
    oracle_options = engine.generate(oracle)
    degraded_options = engine.generate(degraded)
    matches = _match_options(oracle_options, degraded_options)
    oracle_top = sorted(oracle_options, key=lambda option: option.geometric_score, reverse=True)[:3]
    degraded_top = sorted(degraded_options, key=lambda option: option.geometric_score, reverse=True)[:3]
    top_matches = _match_options(oracle_top, degraded_top)
    if len(matches) >= 2:
        correlation = spearmanr(
            [left.geometric_score for left, _ in matches],
            [right.geometric_score for _, right in matches],
        ).statistic
        rank_correlation = 0.0 if np.isnan(correlation) else float(correlation)
    else:
        rank_correlation = 0.0
    best_oracle = max(oracle_options, key=lambda option: option.geometric_score)
    selected_degraded = max(degraded_options, key=lambda option: option.geometric_score)
    selected_match = min(oracle_options, key=lambda option: _option_distance(option, selected_degraded))
    if not math.isfinite(_option_distance(selected_match, selected_degraded)):
        regret = float(best_oracle.geometric_score)
    else:
        regret = float(best_oracle.geometric_score - selected_match.geometric_score)
    oracle_passes = [option for option in oracle_options if option.kind == "pass"]
    degraded_passes = [option for option in degraded_options if option.kind == "pass"]
    pass_matches = _match_options(oracle_passes, degraded_passes)
    line_agreements = [
        float(_is_line_breaking(oracle, left) == _is_line_breaking(degraded, right))
        for left, right in pass_matches
    ]
    interception_errors = [
        abs(left.features["interception_margin_s"] - right.features["interception_margin_s"])
        for left, right in pass_matches
    ]
    receiver_space_errors = [
        abs(left.features["receiver_space"] - right.features["receiver_space"])
        for left, right in pass_matches
    ]
    corridor_flips = []
    narrow_corridor_flips = []
    for left, right in pass_matches:
        left_open = (
            left.features["uncertainty_adjusted_clearance_m"] > 0.75
            and left.features["interception_margin_s"] > 0.0
        )
        right_open = (
            right.features["uncertainty_adjusted_clearance_m"] > 0.75
            and right.features["interception_margin_s"] > 0.0
        )
        flipped = float(left_open != right_open)
        corridor_flips.append(flipped)
        if abs(left.features["uncertainty_adjusted_clearance_m"] - 0.75) <= 1.5:
            narrow_corridor_flips.append(flipped)
    return {
        "option_set_recall_at_3": len(top_matches) / max(len(oracle_top), 1),
        "option_rank_spearman": rank_correlation,
        "chosen_action_regret": regret,
        "passing_corridor_recall": len(pass_matches) / max(len(oracle_passes), 1),
        "passing_corridor_precision": len(pass_matches) / max(len(degraded_passes), 1),
        "corridor_decision_flip_rate": float(np.mean(corridor_flips)) if corridor_flips else 0.0,
        "narrow_corridor_flip_rate": (
            float(np.mean(narrow_corridor_flips)) if narrow_corridor_flips else 0.0
        ),
        "interception_margin_mae_s": (
            float(np.mean(interception_errors)) if interception_errors else math.nan
        ),
        "receiver_space_mae": (
            float(np.mean(receiver_space_errors)) if receiver_space_errors else math.nan
        ),
        "line_breaking_agreement": float(np.mean(line_agreements)) if line_agreements else 0.0,
        "pressure_map_iou": pressure_map_iou(oracle, degraded),
    }


def benchmark_degradation(
    frames: list[FrameState], configs: list[DegradationConfig]
) -> tuple[pd.DataFrame, dict[str, DegradationResult]]:
    rows: list[dict] = []
    results: dict[str, DegradationResult] = {}
    oracle_by_key = {(frame.sequence_id, frame.frame_id): frame for frame in frames}
    for config in configs:
        result = degrade_frames(frames, config)
        results[config.name] = result
        sequence_metrics: dict[str, dict[str, float]] = {}
        sequence_ids = sorted({frame.sequence_id for frame in frames})
        for sequence_id in sequence_ids:
            oracle_sequence = [frame for frame in frames if frame.sequence_id == sequence_id]
            degraded_sequence = [frame for frame in result.frames if frame.sequence_id == sequence_id]
            sequence_metrics[sequence_id] = _sequence_identity_metrics(
                oracle_sequence, degraded_sequence
            )
        for degraded in result.frames:
            oracle = oracle_by_key[(degraded.sequence_id, degraded.frame_id)]
            rows.append(
                {
                    "degradation": config.name,
                    "sequence_id": degraded.sequence_id,
                    "frame_id": degraded.frame_id,
                    **perception_frame_metrics(oracle, degraded),
                    **sequence_metrics[degraded.sequence_id],
                    **tactical_frame_metrics(oracle, degraded),
                }
            )
    return pd.DataFrame(rows), results


def default_degradation_suite(seed: int = 7) -> list[DegradationConfig]:
    return [
        DegradationConfig(name="identity", seed=seed),
        DegradationConfig(name="position_noise_1m", position_noise_std_m=1.0, seed=seed),
        DegradationConfig(name="missing_20pct", missing_player_rate=0.2, seed=seed),
        DegradationConfig(name="id_switch_15pct", id_switch_rate=0.15, seed=seed),
        DegradationConfig(name="calibration_drift", calibration_drift_x_m=1.5, calibration_drift_y_m=-1.0, seed=seed),
        DegradationConfig(name="broadcast_crop", camera_crop_width_m=55.0, camera_crop_height_m=48.0, seed=seed),
        DegradationConfig(name="delay_2frames", delay_frames=2, seed=seed),
        DegradationConfig(name="ball_dropout_20pct", ball_dropout_rate=0.2, seed=seed),
        DegradationConfig(
            name="compound",
            position_noise_std_m=1.0,
            missing_player_rate=0.15,
            id_switch_rate=0.1,
            camera_crop_width_m=60.0,
            camera_crop_height_m=50.0,
            delay_frames=1,
            ball_dropout_rate=0.1,
            seed=seed,
        ),
    ]
