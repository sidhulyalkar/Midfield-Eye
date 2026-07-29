from midfielders_eye.affordance import AffordanceEngine
from midfielders_eye.synthetic import generate_sequence


def test_engine_generates_pass_carry_and_hold_options():
    frame = generate_sequence(0, frames=1)[0]
    options = AffordanceEngine().generate(frame)
    kinds = {option.kind for option in options}
    assert kinds == {"pass", "carry", "hold"}
    assert len([option for option in options if option.kind == "pass"]) == 9
    assert len([option for option in options if option.kind == "carry"]) == 5
    assert all(option.features for option in options)


def test_option_scores_are_finite():
    frame = generate_sequence(0, frames=1)[0]
    options = AffordanceEngine().generate(frame)
    assert all(-5.0 < option.geometric_score < 5.0 for option in options)


def test_pass_score_propagates_target_localization_uncertainty():
    import copy

    frame = generate_sequence(0, frames=1)[0]
    target_id = frame.teammates()[0].player_id
    clean = next(
        option
        for option in AffordanceEngine().generate(frame)
        if option.kind == "pass" and option.target_player_id == target_id
    )

    uncertain_frame = copy.deepcopy(frame)
    uncertain_frame.player(target_id).position_covariance = [[16.0, 0.0], [0.0, 16.0]]
    uncertain = next(
        option
        for option in AffordanceEngine().generate(uncertain_frame)
        if option.kind == "pass" and option.target_player_id == target_id
    )

    assert uncertain.features["target_uncertainty_m"] > clean.features["target_uncertainty_m"]
    assert (
        uncertain.features["uncertainty_adjusted_clearance_m"]
        < clean.features["uncertainty_adjusted_clearance_m"]
    )
    assert uncertain.geometric_score < clean.geometric_score
