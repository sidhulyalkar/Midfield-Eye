from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import combinations
from typing import Any, Callable

import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score

from .pilot import ITEM_COLUMNS


@dataclass(frozen=True)
class ReliabilityGate:
    min_genuine_raters: int = 2
    min_sequences: int = 10
    min_overlap_frame_fraction: float = 0.25
    min_overlap_items: int = 20
    min_availability_alpha: float = 0.60
    min_candidate_coverage: float = 1.0


def _nominal_distance(left: Any, right: Any, _: dict[Any, int]) -> float:
    return float(left != right)


def _ordinal_distance(left: Any, right: Any, frequencies: dict[Any, int]) -> float:
    if left == right:
        return 0.0
    categories = sorted(frequencies)
    left_index = categories.index(left)
    right_index = categories.index(right)
    lower, upper = sorted((left_index, right_index))
    cumulative = sum(frequencies[categories[index]] for index in range(lower, upper + 1))
    edge_adjustment = (
        frequencies[categories[lower]] + frequencies[categories[upper]]
    ) / 2.0
    return float((cumulative - edge_adjustment) ** 2)


def krippendorff_alpha(
    dataframe: pd.DataFrame,
    value_column: str,
    *,
    level: str,
    item_columns: list[str] | tuple[str, ...] = tuple(ITEM_COLUMNS),
) -> float:
    """Krippendorff alpha with missing ratings and arbitrary rater counts.

    Nominal distance is used for categorical availability. The ordinal distance follows
    Krippendorff's cumulative-category-frequency definition, rather than treating the 0-4 scale as
    interval data.
    """

    if level not in {"nominal", "ordinal"}:
        raise ValueError("level must be nominal or ordinal")
    groups: list[list[Any]] = []
    for _, group in dataframe.dropna(subset=[value_column]).groupby(
        list(item_columns), sort=False, dropna=False
    ):
        ratings = group[value_column].tolist()
        if len(ratings) >= 2:
            groups.append(ratings)
    if not groups:
        return float("nan")

    pooled = [rating for ratings in groups for rating in ratings]
    frequencies = pd.Series(pooled, dtype="object").value_counts().to_dict()
    distance: Callable[[Any, Any, dict[Any, int]], float]
    distance = _nominal_distance if level == "nominal" else _ordinal_distance

    observed_numerator = 0.0
    observed_denominator = 0
    for ratings in groups:
        count = len(ratings)
        observed_numerator += sum(
            2.0 * distance(left, right, frequencies) / (count - 1)
            for left, right in combinations(ratings, 2)
        )
        observed_denominator += count
    observed = observed_numerator / observed_denominator

    total = len(pooled)
    if total < 2:
        return float("nan")
    expected_numerator = sum(
        2.0 * distance(left, right, frequencies)
        for left, right in combinations(pooled, 2)
    )
    expected = expected_numerator / (total * (total - 1))
    if np.isclose(expected, 0.0):
        return 1.0 if np.isclose(observed, 0.0) else float("nan")
    return float(1.0 - observed / expected)


def _paired_kappas(
    dataframe: pd.DataFrame,
    value_column: str,
    *,
    weights: str | None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    raters = sorted(dataframe["annotator_id"].unique())
    for left, right in combinations(raters, 2):
        left_rows = dataframe[dataframe["annotator_id"] == left][
            ITEM_COLUMNS + [value_column]
        ]
        right_rows = dataframe[dataframe["annotator_id"] == right][
            ITEM_COLUMNS + [value_column]
        ]
        paired = left_rows.merge(
            right_rows,
            on=ITEM_COLUMNS,
            suffixes=("_left", "_right"),
        ).dropna()
        if paired.empty:
            continue
        combined_categories = pd.concat(
            [
                paired[f"{value_column}_left"],
                paired[f"{value_column}_right"],
            ],
            ignore_index=True,
        ).nunique()
        if combined_categories < 2:
            kappa = float("nan")
        else:
            try:
                kappa = float(
                    cohen_kappa_score(
                        paired[f"{value_column}_left"],
                        paired[f"{value_column}_right"],
                        weights=weights,
                    )
                )
            except (TypeError, ValueError):
                kappa = float("nan")
        rows.append(
            {
                "annotator_a": left,
                "annotator_b": right,
                "overlap_items": len(paired),
                "kappa": kappa if np.isfinite(kappa) else None,
            }
        )
    return rows


def _sequence_bootstrap(
    dataframe: pd.DataFrame,
    metric: Callable[[pd.DataFrame], float],
    *,
    iterations: int,
    seed: int,
) -> dict[str, Any]:
    point_raw = metric(dataframe)
    point = float(point_raw) if np.isfinite(point_raw) else None
    sequences = sorted(dataframe["sequence_id"].unique())
    if len(sequences) < 2:
        return {
            "point": point,
            "lower_95": None,
            "upper_95": None,
            "iterations": iterations,
            "valid_replicates": 0,
            "reason": "At least two sequences are required for a sequence bootstrap interval.",
        }
    rng = np.random.default_rng(seed)
    samples: list[float] = []
    for _ in range(iterations):
        selected = rng.choice(sequences, size=len(sequences), replace=True)
        pieces: list[pd.DataFrame] = []
        for replicate, sequence_id in enumerate(selected):
            piece = dataframe[dataframe["sequence_id"] == sequence_id].copy()
            piece["sequence_id"] = f"bootstrap:{replicate}:{sequence_id}"
            pieces.append(piece)
        value = metric(pd.concat(pieces, ignore_index=True))
        if np.isfinite(value):
            samples.append(float(value))
    if not samples:
        return {
            "point": point,
            "lower_95": None,
            "upper_95": None,
            "iterations": iterations,
            "valid_replicates": 0,
            "reason": "No bootstrap replicate contained enough overlapping ratings.",
        }
    return {
        "point": point,
        "lower_95": float(np.quantile(samples, 0.025)),
        "upper_95": float(np.quantile(samples, 0.975)),
        "iterations": iterations,
        "valid_replicates": len(samples),
        "reason": None,
    }


def _metric_summary(dataframe: pd.DataFrame) -> dict[str, Any]:
    availability_alpha = krippendorff_alpha(
        dataframe,
        "label_available",
        level="nominal",
    )
    value_alpha = krippendorff_alpha(
        dataframe,
        "label_value_ordinal",
        level="ordinal",
    )
    availability_pairs = _paired_kappas(
        dataframe,
        "label_available",
        weights=None,
    )
    value_pairs = _paired_kappas(
        dataframe,
        "label_value_ordinal",
        weights="quadratic",
    )
    return {
        "availability": {
            "primary_metric": "krippendorff_alpha_nominal",
            "alpha": availability_alpha if np.isfinite(availability_alpha) else None,
            "pairwise_cohen_kappa": availability_pairs,
        },
        "value": {
            "primary_metric": "krippendorff_alpha_ordinal",
            "alpha": value_alpha if np.isfinite(value_alpha) else None,
            "pairwise_quadratic_weighted_cohen_kappa": value_pairs,
        },
    }


def reliability_report(
    annotations: pd.DataFrame,
    *,
    candidates: pd.DataFrame,
    gate: ReliabilityGate | None = None,
    bootstrap_iterations: int = 1000,
    seed: int = 7,
) -> dict[str, Any]:
    """Compute agreement and a fail-closed readiness decision from normalized annotations."""

    gate = gate or ReliabilityGate()
    candidate_required = {*ITEM_COLUMNS}
    candidate_missing = sorted(candidate_required - set(candidates.columns))
    if candidate_missing:
        raise ValueError(f"Frozen candidates are missing columns: {candidate_missing}")
    if candidates.empty or candidates.duplicated(ITEM_COLUMNS).any():
        raise ValueError("Frozen candidates must contain one unique row per option")
    required = {
        *ITEM_COLUMNS,
        "annotator_id",
        "label_available",
        "label_value_ordinal",
        "label_confidence",
        "is_genuine_human",
    }
    missing = sorted(required - set(annotations.columns))
    if missing:
        raise ValueError(f"Normalized annotations are missing columns: {missing}")

    frozen_candidate_keys = candidates[ITEM_COLUMNS].drop_duplicates()
    frozen_candidate_frames = candidates[["sequence_id", "frame_id"]].drop_duplicates()
    membership = annotations[ITEM_COLUMNS].drop_duplicates().merge(
        frozen_candidate_keys,
        on=ITEM_COLUMNS,
        how="left",
        indicator=True,
    )
    if (membership["_merge"] == "left_only").any():
        raise ValueError("Annotations contain items outside the frozen candidate set")
    genuine = annotations[annotations["is_genuine_human"].astype(bool)].copy()
    if genuine.empty:
        return {
            "schema_version": "inter-rater-reliability-v1",
            "bootstrap_seed": seed,
            "status": "not_established",
            "established": False,
            "reasons": ["No genuine human annotations passed provenance validation."],
            "gate": asdict(gate),
            "coverage": {
                "rows": 0,
                "items": 0,
                "frames": 0,
                "sequences": 0,
                "annotators": 0,
                "frozen_candidate_items": len(frozen_candidate_keys),
                "frozen_candidate_frames": len(frozen_candidate_frames),
                "candidate_coverage": 0.0,
            },
            "agreement": None,
            "bootstrap": None,
            "per_action_kind": [],
        }

    item_counts = genuine.groupby(ITEM_COLUMNS)["annotator_id"].nunique()
    frame_raters = genuine.groupby(["sequence_id", "frame_id"])["annotator_id"].nunique()
    total_items = len(item_counts)
    overlap_items = int((item_counts >= 2).sum())
    total_frames = len(frame_raters)
    overlap_frames = int((frame_raters >= 2).sum())
    frozen_items = len(frozen_candidate_keys)
    frozen_frames = len(frozen_candidate_frames)
    candidate_coverage = total_items / frozen_items if frozen_items else 0.0
    sequence_count = int(genuine["sequence_id"].nunique())
    overlap_frame_fraction = overlap_frames / frozen_frames if frozen_frames else 0.0
    annotators = int(genuine["annotator_id"].nunique())
    expected_matrix_cells = total_items * annotators
    actual_matrix_cells = len(genuine)
    coverage = {
        "rows": len(genuine),
        "items": total_items,
        "frozen_candidate_items": frozen_items,
        "candidate_coverage": candidate_coverage,
        "overlap_items": overlap_items,
        "overlap_item_fraction": overlap_items / frozen_items if frozen_items else 0.0,
        "frames": total_frames,
        "frozen_candidate_frames": frozen_frames,
        "overlap_frames": overlap_frames,
        "overlap_frame_fraction": overlap_frame_fraction,
        "sequences": sequence_count,
        "annotators": annotators,
        "ratings_per_annotator": {
            str(key): int(value)
            for key, value in genuine["annotator_id"].value_counts().sort_index().items()
        },
        "rating_matrix_missing_fraction": (
            1.0 - actual_matrix_cells / expected_matrix_cells
            if expected_matrix_cells
            else None
        ),
        "availability_uncertain_fraction": float(
            genuine["label_available"].eq("uncertain").mean()
        ),
        "mean_label_confidence": float(genuine["label_confidence"].mean()),
        "low_confidence_fraction": float(genuine["label_confidence"].lt(0.5).mean()),
    }
    agreement = _metric_summary(genuine)
    bootstrap = {
        "unit": "sequence",
        "availability_alpha": _sequence_bootstrap(
            genuine,
            lambda frame: krippendorff_alpha(
                frame, "label_available", level="nominal"
            ),
            iterations=bootstrap_iterations,
            seed=seed,
        ),
        "value_alpha": _sequence_bootstrap(
            genuine,
            lambda frame: krippendorff_alpha(
                frame, "label_value_ordinal", level="ordinal"
            ),
            iterations=bootstrap_iterations,
            seed=seed + 1,
        ),
    }

    per_kind: list[dict[str, Any]] = []
    if "kind" in genuine:
        for kind, group in genuine.groupby("kind", sort=True):
            kind_items = group.groupby(ITEM_COLUMNS)["annotator_id"].nunique()
            per_kind.append(
                {
                    "kind": str(kind),
                    "items": len(kind_items),
                    "overlap_items": int((kind_items >= 2).sum()),
                    **_metric_summary(group),
                }
            )

    availability_alpha = agreement["availability"]["alpha"]
    checks: dict[str, dict[str, Any]] = {
        "genuine_raters": {
            "observed": annotators,
            "required": gate.min_genuine_raters,
            "passed": annotators >= gate.min_genuine_raters,
        },
        "sequences": {
            "observed": sequence_count,
            "required": gate.min_sequences,
            "passed": sequence_count >= gate.min_sequences,
        },
        "overlap_frame_fraction": {
            "observed": overlap_frame_fraction,
            "required": gate.min_overlap_frame_fraction,
            "passed": overlap_frame_fraction >= gate.min_overlap_frame_fraction,
        },
        "overlap_items": {
            "observed": overlap_items,
            "required": gate.min_overlap_items,
            "passed": overlap_items >= gate.min_overlap_items,
        },
        "availability_alpha": {
            "observed": availability_alpha,
            "required": gate.min_availability_alpha,
            "passed": bool(
                availability_alpha is not None
                and availability_alpha >= gate.min_availability_alpha
            ),
        },
        "candidate_coverage": {
            "observed": candidate_coverage,
            "required": gate.min_candidate_coverage,
            "passed": candidate_coverage >= gate.min_candidate_coverage,
        },
    }
    reasons = [
        f"{name} gate failed: observed {check['observed']!r}, required {check['required']!r}."
        for name, check in checks.items()
        if not check["passed"]
    ]
    established = not reasons
    return {
        "schema_version": "inter-rater-reliability-v1",
        "bootstrap_seed": seed,
        "status": "established" if established else "not_established",
        "established": established,
        "reasons": reasons,
        "gate": asdict(gate),
        "gate_checks": checks,
        "coverage": coverage,
        "agreement": agreement,
        "bootstrap": bootstrap,
        "per_action_kind": per_kind,
        "interpretation": (
            "Agreement describes expert consistency on overlapping action-menu labels. It does "
            "not validate the affordance model or turn selected actions into availability labels."
        ),
    }
