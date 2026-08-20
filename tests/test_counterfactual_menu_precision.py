from midfielders_eye.counterfactual_menu import comparison_option_key
from midfielders_eye.schema import ActionOption


def carry(option_id: str, angle: float) -> ActionOption:
    return ActionOption(
        sequence_id="sequence",
        frame_id=4,
        option_id=option_id,
        kind="carry",
        actor_id="carrier",
        target_player_id=None,
        target_x=40.0,
        target_y=30.0,
        features={"carry_angle_offset_deg": angle},
        geometric_score=0.3,
    )


def test_custom_carry_angles_do_not_collapse_to_one_decimal_identity():
    first = comparison_option_key(carry("opaque-a", 22.54))
    second = comparison_option_key(carry("opaque-b", 22.55))
    assert first == "carry:+22.54"
    assert second == "carry:+22.55"
    assert first != second


def test_integer_carry_angles_keep_readable_decimal_identity():
    assert comparison_option_key(carry("opaque", 45.0)) == "carry:+45.0"
    assert comparison_option_key(carry("opaque-zero", 0.0)) == "carry:+0.0"
