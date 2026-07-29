from __future__ import annotations

import math

import numpy as np


def combine_confidences(*values: float | None, default: float = 0.5) -> float:
    """Combine independent confidence signals conservatively using a geometric mean."""
    usable = [float(np.clip(value, 1e-6, 1.0)) for value in values if value is not None]
    if not usable:
        return default
    return float(math.exp(sum(math.log(value) for value in usable) / len(usable)))


def covariance_from_confidence(
    detection_confidence: float | None,
    tracking_confidence: float | None,
    calibration_confidence: float | None,
    base_sigma_m: float = 0.35,
    calibration_sigma_m: float = 2.5,
) -> list[list[float]]:
    """Map perception confidence to a transparent 2D localization covariance.

    This is a calibrated heuristic, not a claim that detector scores are probabilities. The
    mapping intentionally inflates uncertainty when camera calibration is weak because small
    image-space errors can become large pitch-space errors.
    """
    observation = combine_confidences(detection_confidence, tracking_confidence)
    calibration = combine_confidences(calibration_confidence, default=0.5)
    sigma = base_sigma_m + (1.0 - observation) * 1.5 + (1.0 - calibration) * calibration_sigma_m
    variance = float(sigma**2)
    return [[variance, 0.0], [0.0, variance]]


def trajectory_confidence(
    observation_confidence: float | None,
    gap_frames: int = 0,
    interpolation: bool = False,
) -> float:
    base = 0.5 if observation_confidence is None else float(np.clip(observation_confidence, 0, 1))
    decay = math.exp(-0.35 * max(gap_frames, 0))
    if interpolation:
        decay *= 0.75
    return float(np.clip(base * decay, 0.0, 1.0))
