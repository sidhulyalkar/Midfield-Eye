from __future__ import annotations

import math

import pytest

from midfielders_eye.affordance import AffordanceEngine
from midfielders_eye.counterfactual_menu import (
    build_earlier_run_intervention,
    compare_candidate_options,
    comparison_option_key,
    generate_counterfactual_menu_comparison,
)
from midfielders_eye.schema import ActionOption, FrameState, PlayerState


def player(
    player_id: str,
    team: str,
    x: float,
    y: float,
    vx: float,
    vy: float,
) -> PlayerState:
    return PlayerState(
        player_id=player_id,
        team=team,  # type: ignore[arg-type]
        x=x,
        y=y,
        vx=vx,
        vy=vy,
    )


def frame(players: list[PlayerState]) -> FrameState:
    return FrameState(
        sequence_id="test-sequence",
        frame_id=4,
        timestamp_s=1.2,
        possession_team="home",
        ball_x=30.0,
        ball_y=20.0,
        ball_vx=0.0,
        ball_vy=0.0,
        ball_carrier_id="carrier",
        players=players,
        source_provider="synthetic",
    )


def option(
    option_id: str,
    kind: str,
    score: float,
    *,
    target_player_id: str | None = None,
    target_x: float = 40.0,
    target_y: float = 30.0,
    features: dict[str, float] | None = None,
) -> ActionOption:
    return ActionOption(
        sequence_id="test-sequence",
        frame_id=4,
        option_id=option_id,
        kind=kind,  # type: ignore[arg-type]
        actor_id="carrier",
        target_player_id=target_player_id,
        target_x=target_x,
        target_y=target_y,
        features=features or {},
        geometric_score=score,
        source_provider="synthetic",
    )


def test_python_earlier_run_matches_v13_fastest_feasible_contract():
    original = frame(
        [
            player("carrier", "home", 30, 20, 0.3, 0),
            player("runner-a", "home", 45, 30, 2, 0),
            player("runner-b", "home", 50, 35, 1, 1),
            player("defender", "away", 55, 32, 4, 0),
        ]
    )

    result = build_earlier_run_intervention(original, 0.75)

    assert result is not None
    assert result.player_id == "runner-a"
    assert result.from_position == (45.0, 30.0)
    assert result.to_position == (46.5, 30.0)
    assert result.displacement_m == pytest.approx(1.5)
    assert result.baseline_frame is original
    assert result.alternative_frame is not original
    moved = result.alternative_frame.player("runner-a")
    assert (moved.x, moved.y, moved.vx, moved.vy) == (46.5, 30.0, 2.0, 0.0)
    assert original.player("runner-a").x == 45.0
    assert result.alternative_frame.player("runner-b").position.tolist() == [50.0, 35.0]
    assert "teaching_position_intervention" in result.alternative_frame.quality_flags
    assert result.alternative_frame.metadata["teaching_intervention_player"] == "runner-a"


def test_earlier_run_breaks_equal_speed_ties_by_player_id():
    result = build_earlier_run_intervention(
        frame(
            [
                player("carrier", "home", 30, 20, 0, 0),
                player("z-runner", "home", 45, 30, 1, 0),
                player("a-runner", "home", 42, 28, 1, 0),
            ]
        )
    )
    assert result is not None
    assert result.player_id == "a-runner"


def test_earlier_run_clips_to_pitch_and_skips_blocked_faster_candidate():
    clipped = build_earlier_run_intervention(
        frame(
            [
                player("carrier", "home", 30, 20, 0, 0),
                player("runner", "home", 104.5, 67.5, 3, 3),
            ]
        ),
        0.75,
    )
    assert clipped is not None
    assert clipped.to_position == (105.0, 68.0)
    assert clipped.displacement_m == pytest.approx(math.sqrt(0.5))

    fallback = build_earlier_run_intervention(
        frame(
            [
                player("carrier", "home", 30, 20, 0, 0),
                player("blocked", "home", 105, 40, 4, 0),
                player("feasible", "home", 70, 30, 1.5, 0),
            ]
        ),
        0.75,
    )
    assert fallback is not None
    assert fallback.player_id == "feasible"
    assert fallback.to_position == (71.125, 30.0)


def test_earlier_run_fails_closed_without_feasible_focal_motion():
    result = build_earlier_run_intervention(
        frame(
            [
                player("carrier", "home", 30, 20, 1, 0),
                player("still", "home", 42, 28, 0.1, 0.1),
                player("blocked", "home", 105, 35, 2, 0),
                player("opponent", "away", 48, 28, 5, 0),
            ]
        )
    )
    assert result is None

    non_finite = frame(
        [
            player("carrier", "home", 30, 20, 0, 0),
            player("nan-runner", "home", 42, 28, float("nan"), 1),
        ]
    )
    assert build_earlier_run_intervention(non_finite) is None


def test_earlier_run_rejects_invalid_lead_duration():
    input_frame = frame(
        [
            player("carrier", "home", 30, 20, 0, 0),
            player("runner", "home", 42, 28, 1, 0),
        ]
    )
    with pytest.raises(ValueError, match="within"):
        build_earlier_run_intervention(input_frame, 0)
    with pytest.raises(ValueError, match="within"):
        build_earlier_run_intervention(input_frame, 2.1)
    with pytest.raises(ValueError, match="within"):
        build_earlier_run_intervention(input_frame, float("nan"))


def test_semantic_candidate_identity_uses_player_and_carry_angle_not_coordinates():
    pass_a = option(
        "test:4:pass:receiver",
        "pass",
        0.4,
        target_player_id="receiver",
        target_x=40,
    )
    pass_b = option(
        "other-frame-id",
        "pass",
        0.7,
        target_player_id="receiver",
        target_x=52,
    )
    assert comparison_option_key(pass_a) == "pass:receiver"
    assert comparison_option_key(pass_b) == "pass:receiver"

    carry_legacy = option("test:4:carry:-22.5", "carry", 0.4)
    carry_explicit = option(
        "test:4:carry:+22.5",
        "carry",
        0.5,
        features={"carry_angle_offset_deg": 22.5},
    )
    assert comparison_option_key(carry_legacy) == "carry:-22.5"
    assert comparison_option_key(carry_explicit) == "carry:+22.5"
    assert comparison_option_key(option("test:4:hold", "hold", 0.2)) == "hold"


def test_carry_identity_fails_closed_on_missing_or_conflicting_semantics():
    with pytest.raises(ValueError, match="lacks explicit semantic angle identity"):
        comparison_option_key(option("opaque-carry", "carry", 0.2))
    with pytest.raises(ValueError, match="disagrees"):
        comparison_option_key(
            option(
                "test:4:carry:+22.5",
                "carry",
                0.2,
                features={"carry_angle_offset_deg": -22.5},
            )
        )


def test_candidate_comparison_preserves_exact_options_and_only_scores_intersection():
    pass_left = option(
        "test:4:pass:r",
        "pass",
        0.2,
        target_player_id="r",
        target_x=40,
    )
    pass_right = option(
        "test-alt:4:pass:r",
        "pass",
        0.55,
        target_player_id="r",
        target_x=48,
    )
    left_only = option("test:4:carry:-45.0", "carry", 0.3)
    right_only = option("test-alt:4:carry:+45.0", "carry", 0.6)

    comparisons, summary = compare_candidate_options(
        [left_only, pass_left],
        [right_only, pass_right],
        left_condition_id="baseline",
        right_condition_id="earlier-run:r:0.75",
    )

    assert [item.comparison_option_key for item in comparisons] == [
        "pass:r",
        "carry:-45.0",
        "carry:+45.0",
    ]
    shared, only_left, only_right = comparisons
    assert shared.support == "intersection"
    assert shared.left is pass_left
    assert shared.right is pass_right
    assert shared.geometric_score_delta == pytest.approx(0.35)
    assert only_left.support == "left_only"
    assert only_left.geometric_score_delta is None
    assert only_right.support == "right_only"
    assert only_right.geometric_score_delta is None
    assert summary.intersection == 1
    assert summary.left_only == 1
    assert summary.right_only == 1
    assert summary.union == 3


def test_candidate_comparison_rejects_duplicate_semantic_identity_and_nonfinite_scores():
    duplicate_a = option(
        "test:4:pass:r",
        "pass",
        0.2,
        target_player_id="r",
    )
    duplicate_b = option(
        "different-id",
        "pass",
        0.4,
        target_player_id="r",
    )
    with pytest.raises(ValueError, match="duplicate semantic candidate"):
        compare_candidate_options([duplicate_a, duplicate_b], [])

    bad_score = option("test:4:hold", "hold", float("nan"))
    with pytest.raises(ValueError, match="non-finite geometric score"):
        compare_candidate_options([bad_score], [])


def test_regeneration_uses_alternative_frame_and_is_independent_of_baseline_option_mutation():
    input_frame = frame(
        [
            player("carrier", "home", 30, 20, 0, 0),
            player("runner", "home", 42, 28, 2, 0),
            player("support", "home", 52, 36, 0.8, 0.2),
            player("d1", "away", 48, 30, 0, 0),
            player("d2", "away", 60, 38, 0, 0),
        ]
    )
    result = generate_counterfactual_menu_comparison(
        input_frame,
        0.75,
        engine=AffordanceEngine(),
    )
    assert result is not None
    assert result.intervention.player_id == "runner"
    assert result.left_options
    assert result.right_options

    left_pass = next(
        candidate
        for candidate in result.left_options
        if candidate.kind == "pass" and candidate.target_player_id == "runner"
    )
    right_pass = next(
        candidate
        for candidate in result.right_options
        if candidate.kind == "pass" and candidate.target_player_id == "runner"
    )
    assert right_pass is not left_pass
    assert right_pass.target_x != pytest.approx(left_pass.target_x)

    original_right_score = right_pass.geometric_score
    left_pass.geometric_score = 999.0
    assert right_pass.geometric_score == original_right_score

    shared = next(
        candidate
        for candidate in result.comparisons
        if candidate.comparison_option_key == "pass:runner"
    )
    assert shared.right is right_pass
    assert shared.geometric_score_delta is not None
