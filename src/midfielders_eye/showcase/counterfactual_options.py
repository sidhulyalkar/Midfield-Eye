from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping, Sequence

from .. import __version__
from ..affordance import AffordanceEngine
from ..counterfactual_menu import (
    EARLIER_RUN_LEAD_PRESETS,
    CandidateComparison,
    CounterfactualMenuComparison,
    build_earlier_run_intervention,
    compare_candidate_options,
    comparison_option_key,
    ensure_comparison_identity_metadata,
)
from ..schema import ActionOption, FrameState

COUNTERFACTUAL_OPTIONS_SCHEMA_VERSION = "1.4.0-b"
CANDIDATE_IDENTITY_CONTRACT = "semantic_action_candidate_v1"
INTERVENTION_CONTRACT = "earlier_run_focal_velocity_v1"


def serialize_action_option(option: ActionOption) -> dict[str, Any]:
    """Serialize one option in the canonical frontend/API transport shape."""

    return {
        "sequence_id": option.sequence_id,
        "frame_id": option.frame_id,
        "option_id": option.option_id,
        "kind": option.kind,
        "actor_id": option.actor_id,
        "target_player_id": option.target_player_id,
        "target_x": float(option.target_x),
        "target_y": float(option.target_y),
        "features": {
            key: float(value) for key, value in sorted(option.features.items())
        },
        "geometric_score": float(option.geometric_score),
        "learned_score": None
        if option.learned_score is None
        else float(option.learned_score),
        "source_provider": option.source_provider,
        "provenance": option.provenance,
        "label_available": option.label_available,
        "label_visible": option.label_visible,
        "label_selected": option.label_selected,
        "label_value": None
        if option.label_value is None
        else float(option.label_value),
        "failure_reason": option.failure_reason,
    }


def effective_engine_config(engine: AffordanceEngine) -> dict[str, Any]:
    config = engine.config
    return {
        "carry_distance_m": float(config.carry_distance_m),
        "carry_angle_offsets_deg": [
            float(value) for value in config.carry_angle_offsets_deg
        ],
        "include_hold": bool(config.include_hold),
        "ball_speed_mps": float(config.ball_speed_mps),
        "visibility_half_fov_deg": float(config.visibility_half_fov_deg),
        "weights": {
            key: float(value) for key, value in sorted(engine.weights.items())
        },
    }


def engine_config_sha256(engine: AffordanceEngine) -> str:
    canonical = json.dumps(
        effective_engine_config(engine),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _serialize_intervention(
    comparison: CounterfactualMenuComparison,
) -> dict[str, Any]:
    intervention = comparison.intervention
    return {
        "id": intervention.id,
        "player_id": intervention.player_id,
        "lead_seconds": float(intervention.lead_seconds),
        "speed_mps": float(intervention.speed_mps),
        "displacement_m": float(intervention.displacement_m),
        "from": [float(value) for value in intervention.from_position],
        "to": [float(value) for value in intervention.to_position],
        "status": "synthetic_teaching_intervention_not_observed_or_causal",
    }


def _serialize_candidate_comparison(
    comparison: CandidateComparison,
) -> dict[str, Any]:
    return {
        "comparison_option_key": comparison.comparison_option_key,
        "support": comparison.support,
        "left_option_id": None
        if comparison.left is None
        else comparison.left.option_id,
        "right_option_id": None
        if comparison.right is None
        else comparison.right.option_id,
        "geometric_score_delta": comparison.geometric_score_delta,
    }


def _serialize_option_with_identity(option: ActionOption) -> dict[str, Any]:
    return {
        "comparison_option_key": comparison_option_key(option),
        "option": serialize_action_option(option),
    }


def _validate_frames(frames: Sequence[FrameState]) -> None:
    seen: set[int] = set()
    previous: int | None = None
    for frame in frames:
        frame.validate()
        if frame.frame_id in seen:
            raise ValueError(
                f"duplicate frame_id {frame.frame_id} in showcase sequence"
            )
        if previous is not None and frame.frame_id <= previous:
            raise ValueError("showcase frames must be strictly ordered by frame_id")
        seen.add(frame.frame_id)
        previous = frame.frame_id


def _validate_scenario_inputs(
    scenario_id: str,
    frames: Sequence[FrameState],
    options_by_frame: Mapping[int, Sequence[ActionOption]],
) -> None:
    expected_frame_ids = {frame.frame_id for frame in frames}
    actual_frame_ids = set(options_by_frame)
    if actual_frame_ids != expected_frame_ids:
        missing = sorted(expected_frame_ids - actual_frame_ids)
        extra = sorted(actual_frame_ids - expected_frame_ids)
        raise ValueError(
            "authoritative baseline frame map does not match showcase frames: "
            f"missing={missing}, extra={extra}"
        )
    for frame in frames:
        if frame.sequence_id != scenario_id:
            raise ValueError(
                f"frame {frame.frame_id} sequence_id {frame.sequence_id!r} "
                f"does not match scenario_id {scenario_id!r}"
            )


def _baseline_options_for_frame(
    frame: FrameState,
    options_by_frame: Mapping[int, Sequence[ActionOption]],
) -> tuple[ActionOption, ...]:
    if frame.frame_id not in options_by_frame:
        raise ValueError(
            f"missing authoritative baseline options for frame {frame.frame_id}"
        )
    baseline = ensure_comparison_identity_metadata(
        tuple(options_by_frame[frame.frame_id])
    )
    if not baseline:
        raise ValueError(
            f"authoritative baseline options are empty for frame {frame.frame_id}"
        )
    semantic_keys: set[str] = set()
    for option in baseline:
        if option.frame_id != frame.frame_id:
            raise ValueError(
                f"baseline option {option.option_id!r} has wrong frame_id"
            )
        if option.sequence_id != frame.sequence_id:
            raise ValueError(
                f"baseline option {option.option_id!r} has wrong sequence_id"
            )
        if option.actor_id != frame.ball_carrier_id:
            raise ValueError(
                f"baseline option {option.option_id!r} has wrong actor_id"
            )
        key = comparison_option_key(option)
        if key in semantic_keys:
            raise ValueError(
                f"baseline frame {frame.frame_id} has duplicate semantic candidate {key!r}"
            )
        semantic_keys.add(key)
    return baseline


def _condition_payload(
    frame: FrameState,
    baseline: tuple[ActionOption, ...],
    lead_seconds: float,
    engine: AffordanceEngine,
) -> dict[str, Any]:
    intervention = build_earlier_run_intervention(frame, lead_seconds)
    if intervention is None:
        return {
            "lead_seconds": float(lead_seconds),
            "status": "unavailable",
            "reason": "no_feasible_earlier_run_intervention",
            "intervention": None,
            "condition_b_options": [],
            "candidate_comparisons": [],
            "summary": None,
        }

    right_options = ensure_comparison_identity_metadata(
        tuple(engine.generate(intervention.alternative_frame))
    )
    comparisons, summary = compare_candidate_options(
        baseline,
        right_options,
        left_condition_id="baseline",
        right_condition_id=intervention.id,
    )
    wrapped = CounterfactualMenuComparison(
        intervention=intervention,
        left_condition_id="baseline",
        right_condition_id=intervention.id,
        left_options=baseline,
        right_options=right_options,
        comparisons=comparisons,
        summary=summary,
    )
    return {
        "lead_seconds": float(lead_seconds),
        "status": "available",
        "reason": None,
        "intervention": _serialize_intervention(wrapped),
        "condition_b_options": [
            _serialize_option_with_identity(option) for option in right_options
        ],
        "candidate_comparisons": [
            _serialize_candidate_comparison(item) for item in comparisons
        ],
        "summary": {
            "intersection": summary.intersection,
            "left_only": summary.left_only,
            "right_only": summary.right_only,
            "union": summary.union,
        },
    }


def build_counterfactual_options_artifact(
    scenario_id: str,
    frames: Sequence[FrameState],
    options_by_frame: Mapping[int, Sequence[ActionOption]],
    *,
    engine: AffordanceEngine,
    lead_presets: Sequence[float] = EARLIER_RUN_LEAD_PRESETS,
) -> dict[str, Any]:
    """Build deterministic A/B candidate artifacts from authoritative baseline menus."""

    if not scenario_id.strip():
        raise ValueError("scenario_id must be non-empty")
    _validate_frames(frames)
    _validate_scenario_inputs(scenario_id, frames, options_by_frame)
    leads = tuple(float(value) for value in lead_presets)
    if not leads:
        raise ValueError("lead_presets must not be empty")
    if len(set(leads)) != len(leads):
        raise ValueError("lead_presets must be unique")
    if any(
        not math.isfinite(value) or not 0.0 < value <= 2.0 for value in leads
    ):
        raise ValueError("lead_presets must be finite and within (0, 2]")
    if tuple(sorted(leads)) != leads:
        raise ValueError("lead_presets must be strictly ascending")

    frame_payloads: list[dict[str, Any]] = []
    for frame in frames:
        baseline = _baseline_options_for_frame(frame, options_by_frame)
        frame_payloads.append(
            {
                "frame_id": frame.frame_id,
                "timestamp_s": float(frame.timestamp_s),
                "baseline_options": [
                    _serialize_option_with_identity(option) for option in baseline
                ],
                "conditions": [
                    _condition_payload(frame, baseline, lead, engine)
                    for lead in leads
                ],
            }
        )

    return {
        "schema_version": COUNTERFACTUAL_OPTIONS_SCHEMA_VERSION,
        "scenario_id": scenario_id,
        "generator": {
            "name": "AffordanceEngine",
            "module": "midfielders_eye.affordance",
            "package_version": __version__,
            "config": effective_engine_config(engine),
            "config_sha256": engine_config_sha256(engine),
            "candidate_identity_contract": CANDIDATE_IDENTITY_CONTRACT,
            "intervention_contract": INTERVENTION_CONTRACT,
            "future_observed_frames_used": False,
        },
        "lead_presets": list(leads),
        "frames": frame_payloads,
    }
