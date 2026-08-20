from __future__ import annotations

import math
import re
from copy import deepcopy
from dataclasses import dataclass
from typing import Literal

from .affordance import AffordanceEngine
from .schema import ActionOption, FrameState, PlayerState

CandidateSupport = Literal["intersection", "left_only", "right_only"]

MIN_EARLIER_RUN_SPEED_MPS = 0.25
MIN_EARLIER_RUN_DISPLACEMENT_M = 1e-6
DEFAULT_EARLIER_RUN_SECONDS = 0.75
EARLIER_RUN_LEAD_PRESETS = (0.5, 0.75, 1.0)

_CARRY_ID_PATTERN = re.compile(r":carry:([+-](?:\d+(?:\.\d*)?|\.\d+))$")


@dataclass(frozen=True, slots=True)
class EarlierRunIntervention:
    id: str
    player_id: str
    lead_seconds: float
    speed_mps: float
    displacement_m: float
    from_position: tuple[float, float]
    to_position: tuple[float, float]
    baseline_frame: FrameState
    alternative_frame: FrameState


@dataclass(frozen=True, slots=True)
class CandidateComparison:
    comparison_option_key: str
    support: CandidateSupport
    left: ActionOption | None
    right: ActionOption | None
    geometric_score_delta: float | None


@dataclass(frozen=True, slots=True)
class CandidateComparisonSummary:
    intersection: int
    left_only: int
    right_only: int
    union: int


@dataclass(frozen=True, slots=True)
class CounterfactualMenuComparison:
    intervention: EarlierRunIntervention
    left_condition_id: str
    right_condition_id: str
    left_options: tuple[ActionOption, ...]
    right_options: tuple[ActionOption, ...]
    comparisons: tuple[CandidateComparison, ...]
    summary: CandidateComparisonSummary


def _finite_velocity(player: PlayerState) -> tuple[float, float] | None:
    vx = float(player.vx)
    vy = float(player.vy)
    if not math.isfinite(vx) or not math.isfinite(vy):
        return None
    return vx, vy


def _clip(value: float, maximum: float) -> float:
    return max(0.0, min(float(maximum), float(value)))


def build_earlier_run_intervention(
    frame: FrameState,
    lead_seconds: float = DEFAULT_EARLIER_RUN_SECONDS,
) -> EarlierRunIntervention | None:
    """Build the v1.3/v1.4 earlier-run teaching intervention in Python.

    The intervention uses only the focal frame. It selects the fastest feasible
    off-ball possession teammate after clipping the proposed arrival to the
    declared pitch. Only that player's current X/Y position changes.
    """

    frame.validate()
    if not math.isfinite(lead_seconds) or not 0.0 < lead_seconds <= 2.0:
        raise ValueError("lead_seconds must be finite and within (0, 2]")

    candidates: list[
        tuple[
            float,
            str,
            tuple[float, float],
            tuple[float, float],
            float,
        ]
    ] = []
    for player in frame.players:
        if (
            player.team != frame.possession_team
            or player.player_id == frame.ball_carrier_id
        ):
            continue
        velocity = _finite_velocity(player)
        if velocity is None:
            continue
        vx, vy = velocity
        speed_mps = math.hypot(vx, vy)
        if speed_mps < MIN_EARLIER_RUN_SPEED_MPS:
            continue
        origin = (float(player.x), float(player.y))
        target = (
            _clip(origin[0] + vx * lead_seconds, frame.pitch_length),
            _clip(origin[1] + vy * lead_seconds, frame.pitch_width),
        )
        displacement_m = math.hypot(
            target[0] - origin[0], target[1] - origin[1]
        )
        if displacement_m < MIN_EARLIER_RUN_DISPLACEMENT_M:
            continue
        candidates.append(
            (-speed_mps, player.player_id, origin, target, displacement_m)
        )

    if not candidates:
        return None
    candidates.sort(key=lambda candidate: (candidate[0], candidate[1]))
    negative_speed, player_id, origin, target, displacement_m = candidates[0]
    speed_mps = -negative_speed

    alternative = deepcopy(frame)
    moved = alternative.player(player_id)
    moved.x = target[0]
    moved.y = target[1]
    alternative.quality_flags = [
        *alternative.quality_flags,
        "teaching_position_intervention",
    ]
    alternative.metadata = {
        **alternative.metadata,
        "teaching_intervention": "earlier_run",
        "teaching_intervention_player": player_id,
        "teaching_intervention_seconds": float(lead_seconds),
    }
    alternative.validate()

    return EarlierRunIntervention(
        id=f"earlier-run:{player_id}:{lead_seconds:.2f}",
        player_id=player_id,
        lead_seconds=float(lead_seconds),
        speed_mps=float(speed_mps),
        displacement_m=float(displacement_m),
        from_position=origin,
        to_position=target,
        baseline_frame=frame,
        alternative_frame=alternative,
    )


def _legacy_carry_offset(option: ActionOption) -> float | None:
    match = _CARRY_ID_PATTERN.search(option.option_id)
    return float(match.group(1)) if match else None


def _carry_offset(option: ActionOption) -> float:
    feature_value = option.features.get("carry_angle_offset_deg")
    feature_offset: float | None = None
    if feature_value is not None:
        feature_offset = float(feature_value)
        if not math.isfinite(feature_offset):
            raise ValueError(
                f"carry option {option.option_id!r} has non-finite "
                "carry_angle_offset_deg"
            )

    id_offset = _legacy_carry_offset(option)
    if feature_offset is None and id_offset is None:
        raise ValueError(
            f"carry option {option.option_id!r} lacks explicit semantic angle identity"
        )
    if (
        feature_offset is not None
        and id_offset is not None
        and not math.isclose(feature_offset, id_offset, abs_tol=1e-9)
    ):
        raise ValueError(
            f"carry option {option.option_id!r} disagrees with carry_angle_offset_deg"
        )
    offset = feature_offset if feature_offset is not None else id_offset
    assert offset is not None
    return 0.0 if math.isclose(offset, 0.0, abs_tol=1e-12) else float(offset)


def _format_carry_offset(offset: float) -> str:
    token = f"{offset:+.12f}".rstrip("0").rstrip(".")
    if "." not in token:
        token = f"{token}.0"
    return token


def ensure_comparison_identity_metadata(
    options: list[ActionOption] | tuple[ActionOption, ...],
) -> tuple[ActionOption, ...]:
    """Stamp explicit semantic identity metadata onto generated carry options.

    Existing v1.3 bundles encode carry angle in the authoritative generated
    option ID. v1.4 artifacts migrate that legacy suffix into an explicit,
    non-scoring feature so downstream cross-condition identity does not depend
    on target coordinates or future string parsing.
    """

    result = tuple(options)
    for option in result:
        if option.kind == "carry" and "carry_angle_offset_deg" not in option.features:
            offset = _legacy_carry_offset(option)
            if offset is None:
                raise ValueError(
                    f"carry option {option.option_id!r} cannot be migrated to "
                    "explicit semantic identity"
                )
            option.features = {
                **option.features,
                "carry_angle_offset_deg": 0.0
                if math.isclose(offset, 0.0, abs_tol=1e-12)
                else float(offset),
            }
        comparison_option_key(option)
    return result


def comparison_option_key(option: ActionOption) -> str:
    """Return semantic cross-condition identity independent of target coordinates."""

    if option.kind == "pass":
        if not option.target_player_id:
            raise ValueError(
                f"pass option {option.option_id!r} is missing target_player_id"
            )
        return f"pass:{option.target_player_id}"
    if option.kind == "carry":
        if option.target_player_id is not None:
            raise ValueError(
                f"carry option {option.option_id!r} must not target a player"
            )
        return f"carry:{_format_carry_offset(_carry_offset(option))}"
    if option.kind == "hold":
        if option.target_player_id is not None:
            raise ValueError(
                f"hold option {option.option_id!r} must not target a player"
            )
        return "hold"
    raise ValueError(f"unsupported action kind {option.kind!r}")


def _candidate_sort_key(key: str) -> tuple[int, object]:
    if key.startswith("pass:"):
        return (0, key.removeprefix("pass:"))
    if key.startswith("carry:"):
        return (1, float(key.removeprefix("carry:")))
    if key == "hold":
        return (2, "")
    raise ValueError(f"unsupported comparison option key {key!r}")


def _condition_context(
    options: list[ActionOption] | tuple[ActionOption, ...],
    *,
    condition_id: str,
) -> tuple[str, int, str] | None:
    context: tuple[str, int, str] | None = None
    for option in options:
        current = (option.sequence_id, option.frame_id, option.actor_id)
        if context is None:
            context = current
        elif current != context:
            raise ValueError(
                f"condition {condition_id!r} mixes candidate sequence/frame/actor contexts"
            )
    return context


def _index_options(
    options: list[ActionOption] | tuple[ActionOption, ...],
    *,
    condition_id: str,
) -> dict[str, ActionOption]:
    indexed: dict[str, ActionOption] = {}
    for option in options:
        key = comparison_option_key(option)
        if key in indexed:
            raise ValueError(
                f"condition {condition_id!r} has duplicate semantic candidate {key!r}"
            )
        if not math.isfinite(float(option.geometric_score)):
            raise ValueError(
                f"condition {condition_id!r} candidate {key!r} has non-finite "
                "geometric score"
            )
        indexed[key] = option
    return indexed


def compare_candidate_options(
    left_options: list[ActionOption] | tuple[ActionOption, ...],
    right_options: list[ActionOption] | tuple[ActionOption, ...],
    *,
    left_condition_id: str = "baseline",
    right_condition_id: str = "counterfactual",
) -> tuple[tuple[CandidateComparison, ...], CandidateComparisonSummary]:
    if not left_condition_id or not right_condition_id:
        raise ValueError("candidate comparison condition IDs must be non-empty")
    left_context = _condition_context(left_options, condition_id=left_condition_id)
    right_context = _condition_context(right_options, condition_id=right_condition_id)
    if (
        left_context is not None
        and right_context is not None
        and left_context != right_context
    ):
        raise ValueError(
            "candidate conditions must share sequence_id, frame_id, and actor_id"
        )

    left = _index_options(left_options, condition_id=left_condition_id)
    right = _index_options(right_options, condition_id=right_condition_id)
    keys = sorted(set(left) | set(right), key=_candidate_sort_key)

    comparisons: list[CandidateComparison] = []
    intersection = 0
    left_only = 0
    right_only = 0
    for key in keys:
        left_option = left.get(key)
        right_option = right.get(key)
        if left_option is not None and right_option is not None:
            if left_option is right_option:
                raise ValueError(
                    f"candidate {key!r} reuses the same ActionOption object in A and B"
                )
            support: CandidateSupport = "intersection"
            delta = float(
                right_option.geometric_score - left_option.geometric_score
            )
            intersection += 1
        elif left_option is not None:
            support = "left_only"
            delta = None
            left_only += 1
        else:
            support = "right_only"
            delta = None
            right_only += 1
        comparisons.append(
            CandidateComparison(
                comparison_option_key=key,
                support=support,
                left=left_option,
                right=right_option,
                geometric_score_delta=delta,
            )
        )

    return (
        tuple(comparisons),
        CandidateComparisonSummary(
            intersection=intersection,
            left_only=left_only,
            right_only=right_only,
            union=len(comparisons),
        ),
    )


def generate_counterfactual_menu_comparison(
    frame: FrameState,
    lead_seconds: float = DEFAULT_EARLIER_RUN_SECONDS,
    *,
    engine: AffordanceEngine | None = None,
) -> CounterfactualMenuComparison | None:
    """Regenerate both candidate menus with one authoritative engine instance."""

    intervention = build_earlier_run_intervention(frame, lead_seconds)
    if intervention is None:
        return None
    engine = engine or AffordanceEngine()
    left_options = ensure_comparison_identity_metadata(
        engine.generate(intervention.baseline_frame)
    )
    right_options = ensure_comparison_identity_metadata(
        engine.generate(intervention.alternative_frame)
    )
    comparisons, summary = compare_candidate_options(
        left_options,
        right_options,
        left_condition_id="baseline",
        right_condition_id=intervention.id,
    )
    return CounterfactualMenuComparison(
        intervention=intervention,
        left_condition_id="baseline",
        right_condition_id=intervention.id,
        left_options=left_options,
        right_options=right_options,
        comparisons=comparisons,
        summary=summary,
    )
