from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, field

import numpy as np

from .schema import FrameState


@dataclass(slots=True)
class QualityIssue:
    severity: str
    code: str
    message: str
    count: int = 1


@dataclass(slots=True)
class QualityReport:
    provider_id: str
    frame_count: int
    sequence_count: int
    metrics: dict[str, float | int | None]
    issues: list[QualityIssue] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "provider_id": self.provider_id,
            "frame_count": self.frame_count,
            "sequence_count": self.sequence_count,
            "metrics": self.metrics,
            "issues": [asdict(issue) for issue in self.issues],
            "recommendations": self.recommendations,
        }


def assess_frames(frames: list[FrameState], provider_id: str | None = None) -> QualityReport:
    if not frames:
        return QualityReport(provider_id or "unknown", 0, 0, {}, [QualityIssue("error", "empty", "No frames were loaded")])

    provider = provider_id or frames[0].source_provider
    issues: list[QualityIssue] = []
    timestamps: dict[str, list[float]] = defaultdict(list)
    player_counts: list[int] = []
    carrier_distances: list[float] = []
    total_players = 0
    observed = 0
    extrapolated = 0
    inferred = 0
    interpolated = 0
    orientation_covered = 0
    confidence_covered = 0
    covariance_covered = 0
    calibration_covered = 0
    uncertainty_radii: list[float] = []
    partial_frames = 0
    camera_cuts = 0
    continuity_misses = 0
    previous_ids: dict[str, set[str]] = {}

    for frame in frames:
        timestamps[frame.sequence_id].append(frame.timestamp_s)
        player_counts.append(len(frame.players))
        total_players += len(frame.players)
        carrier_distances.append(float(np.linalg.norm(frame.carrier.position - frame.ball_position)))
        if frame.visibility_polygon or frame.metadata.get("partial_visibility"):
            partial_frames += 1
        camera_cuts += int("camera_cut" in frame.quality_flags)
        ids = {player.player_id for player in frame.players}
        previous = previous_ids.get(frame.sequence_id)
        if previous:
            continuity_misses += len(previous - ids)
        previous_ids[frame.sequence_id] = ids
        for player in frame.players:
            observed += int(player.tracking_status == "observed")
            extrapolated += int(player.tracking_status == "extrapolated")
            inferred += int(player.tracking_status == "inferred")
            interpolated += int(player.tracking_status == "interpolated")
            orientation_covered += int(abs(player.body_angle) > 1e-8 or player.speed > 0.5)
            confidence_covered += int(player.confidence is not None)
            calibration_covered += int(player.calibration_confidence is not None)
            try:
                uncertainty_radii.append(player.uncertainty_radius_m)
                covariance_covered += 1
            except ValueError:
                pass

    deltas: list[float] = []
    for values in timestamps.values():
        ordered = sorted(values)
        deltas.extend(
            right - left for left, right in zip(ordered[:-1], ordered[1:], strict=False) if right > left
        )
    median_dt = float(np.median(deltas)) if deltas else None
    inferred_fps = 1.0 / median_dt if median_dt and median_dt > 0 else None
    mean_carrier_distance = float(np.mean(carrier_distances))
    p95_carrier_distance = float(np.quantile(carrier_distances, 0.95))

    if p95_carrier_distance > 4.0:
        issues.append(QualityIssue("warning", "carrier_far_from_ball", f"95th percentile carrier-ball distance is {p95_carrier_distance:.2f} m"))
    if partial_frames / len(frames) > 0.5:
        issues.append(QualityIssue("info", "partial_visibility", "Most frames expose only a camera-visible subset of players"))
    if total_players and (extrapolated + inferred + interpolated) / total_players > 0.25:
        issues.append(QualityIssue("warning", "heavy_inference", "More than 25% of player states are extrapolated, inferred, or interpolated"))
    if total_players and orientation_covered / total_players < 0.2:
        issues.append(QualityIssue("info", "orientation_sparse", "Body orientation is mostly unavailable or inferred from motion"))
    if np.mean(player_counts) < 12:
        issues.append(QualityIssue("warning", "low_player_coverage", "Mean player count is below 12 per frame"))

    recommendations = []
    if partial_frames:
        recommendations.append("Condition option recall on the visible-area polygon and report hidden-player uncertainty.")
    if extrapolated or inferred or interpolated:
        recommendations.append("Run sensitivity analyses with non-observed players removed and uncertainty-weighted.")
    if mean_carrier_distance > 2.0:
        recommendations.append("Review possession and carrier inference before using selected-action labels.")
    if not deltas:
        recommendations.append("This source is snapshot-like; disable velocity claims and temporal rank-stability metrics.")

    metrics: dict[str, float | int | None] = {
        "median_dt_s": median_dt,
        "inferred_rate_hz": inferred_fps,
        "mean_players_per_frame": float(np.mean(player_counts)),
        "min_players_per_frame": int(np.min(player_counts)),
        "max_players_per_frame": int(np.max(player_counts)),
        "observed_player_fraction": observed / total_players if total_players else None,
        "extrapolated_player_fraction": extrapolated / total_players if total_players else None,
        "inferred_player_fraction": inferred / total_players if total_players else None,
        "interpolated_player_fraction": interpolated / total_players if total_players else None,
        "orientation_coverage": orientation_covered / total_players if total_players else None,
        "confidence_coverage": confidence_covered / total_players if total_players else None,
        "calibration_confidence_coverage": calibration_covered / total_players if total_players else None,
        "position_covariance_coverage": covariance_covered / total_players if total_players else None,
        "mean_uncertainty_radius_m": float(np.mean(uncertainty_radii)) if uncertainty_radii else None,
        "p95_uncertainty_radius_m": float(np.quantile(uncertainty_radii, 0.95)) if uncertainty_radii else None,
        "partial_visibility_fraction": partial_frames / len(frames),
        "mean_carrier_ball_distance_m": mean_carrier_distance,
        "p95_carrier_ball_distance_m": p95_carrier_distance,
        "identity_drop_count": continuity_misses,
        "camera_cut_count": camera_cuts,
        "ball_confidence_coverage": sum(frame.ball_confidence is not None for frame in frames) / len(frames),
        "possession_confidence_coverage": sum(frame.possession_confidence is not None for frame in frames) / len(frames),
    }
    return QualityReport(provider, len(frames), len(timestamps), metrics, issues, recommendations)
