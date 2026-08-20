from __future__ import annotations

import pytest

from midfielders_eye.affordance import AffordanceEngine
from midfielders_eye.counterfactual_menu import (
    compare_candidate_options,
    ensure_comparison_identity_metadata,
    generate_counterfactual_menu_comparison,
)
from midfielders_eye.schema import ActionOption, FrameState, PlayerState


def option(
    option_id: str,
    kind: str,
    score: float,
    *,
    sequence_id: str = "sequence",
    frame_id: int = 4,
    actor_id: str = "carrier",
    target_player_id: str | None = None,
) -> ActionOption:
    return ActionOption(
        sequence_id=sequence_id,
        frame_id=frame_id,
        option_id=option_id,
        kind=kind,  # type: ignore[arg-type]
        actor_id=actor_id,
        target_player_id=target_player_id,
        target_x=40.0,
        target_y=30.0,
        features={},
        geometric_score=score,
    )


def test_candidate_comparison_rejects_same_object_reused_as_a_and_b():
    shared_object = option(
        "sequence:4:pass:receiver",
        "pass",
        0.4,
        target_player_id="receiver",
    )
    with pytest.raises(ValueError, match="same ActionOption object"):
        compare_candidate_options([shared_object], [shared_object])


def test_candidate_comparison_rejects_mixed_or_incompatible_condition_contexts():
    baseline = option(
        "sequence:4:pass:receiver",
        "pass",
        0.4,
        target_player_id="receiver",
    )
    mixed = option(
        "sequence:5:hold",
        "hold",
        0.2,
        frame_id=5,
    )
    with pytest.raises(ValueError, match="mixes candidate sequence/frame/actor contexts"):
        compare_candidate_options([baseline, mixed], [])

    alternative_other_actor = option(
        "sequence:4:pass:receiver",
        "pass",
        0.5,
        actor_id="other-carrier",
        target_player_id="receiver",
    )
    with pytest.raises(ValueError, match="must share sequence_id, frame_id, and actor_id"):
        compare_candidate_options([baseline], [alternative_other_actor])


def test_legacy_generated_carry_identity_is_migrated_to_explicit_feature():
    carry = option("sequence:4:carry:-22.5", "carry", 0.3)
    migrated = ensure_comparison_identity_metadata([carry])
    assert migrated[0] is carry
    assert carry.features["carry_angle_offset_deg"] == pytest.approx(-22.5)


def test_authoritative_regeneration_stamps_explicit_carry_identity_on_both_sides():
    input_frame = FrameState(
        sequence_id="sequence",
        frame_id=4,
        timestamp_s=1.0,
        possession_team="home",
        ball_x=30.0,
        ball_y=20.0,
        ball_vx=0.0,
        ball_vy=0.0,
        ball_carrier_id="carrier",
        players=[
            PlayerState("carrier", "home", 30, 20, 0, 0),
            PlayerState("runner", "home", 42, 28, 2, 0),
            PlayerState("support", "home", 50, 36, 0.6, 0.2),
            PlayerState("defender-a", "away", 48, 30, 0, 0),
            PlayerState("defender-b", "away", 58, 38, 0, 0),
        ],
        source_provider="synthetic",
    )

    result = generate_counterfactual_menu_comparison(
        input_frame,
        0.75,
        engine=AffordanceEngine(),
    )
    assert result is not None
    left_carries = [option for option in result.left_options if option.kind == "carry"]
    right_carries = [option for option in result.right_options if option.kind == "carry"]
    assert left_carries and right_carries
    assert all("carry_angle_offset_deg" in option.features for option in left_carries)
    assert all("carry_angle_offset_deg" in option.features for option in right_carries)
