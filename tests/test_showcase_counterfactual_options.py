from __future__ import annotations

from copy import deepcopy

import pytest

from midfielders_eye.affordance import AffordanceConfig, AffordanceEngine
from midfielders_eye.counterfactual_menu import ensure_comparison_identity_metadata
from midfielders_eye.schema import ActionOption, FrameState, PlayerState
from midfielders_eye.showcase.counterfactual_options import (
    COUNTERFACTUAL_OPTIONS_SCHEMA_VERSION,
    build_counterfactual_options_artifact,
    effective_engine_config,
    engine_config_sha256,
    serialize_action_option,
)


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


def frame(frame_id: int = 4) -> FrameState:
    return FrameState(
        sequence_id="scenario-test",
        frame_id=frame_id,
        timestamp_s=frame_id / 6.0,
        possession_team="home",
        ball_x=30.0,
        ball_y=20.0,
        ball_vx=0.0,
        ball_vy=0.0,
        ball_carrier_id="carrier",
        players=[
            player("carrier", "home", 30, 20, 0, 0),
            player("runner", "home", 42, 28, 2, 0),
            player("support", "home", 52, 36, 0.8, 0.2),
            player("defender-a", "away", 48, 30, 0, 0),
            player("defender-b", "away", 60, 38, 0, 0),
        ],
        source_provider="synthetic",
    )


def baseline_options(
    frames: list[FrameState],
    engine: AffordanceEngine,
) -> dict[int, list[ActionOption]]:
    return {current.frame_id: engine.generate(current) for current in frames}


def test_action_option_serializer_matches_nested_frontend_contract():
    candidate = ActionOption(
        sequence_id="scenario-test",
        frame_id=4,
        option_id="scenario-test:4:pass:runner",
        kind="pass",
        actor_id="carrier",
        target_player_id="runner",
        target_x=42.0,
        target_y=28.0,
        features={"distance_m": 12.3, "future_space": 0.7},
        geometric_score=0.55,
        learned_score=0.6,
        source_provider="synthetic",
        provenance="test-generator",
        label_available=True,
        label_visible=False,
        label_selected=None,
        label_value=0.8,
        failure_reason=None,
    )

    payload = serialize_action_option(candidate)

    assert payload["features"] == {"distance_m": 12.3, "future_space": 0.7}
    assert "distance_m" not in payload
    assert payload["geometric_score"] == pytest.approx(0.55)
    assert payload["learned_score"] == pytest.approx(0.6)
    assert payload["label_available"] is True
    assert payload["label_visible"] is False
    assert payload["label_selected"] is None
    assert payload["label_value"] == pytest.approx(0.8)
    assert payload["failure_reason"] is None


def test_engine_fingerprint_uses_effective_weights_and_is_stable():
    default_engine = AffordanceEngine()
    first = engine_config_sha256(default_engine)
    second = engine_config_sha256(default_engine)
    assert first == second
    assert len(first) == 64
    assert set(first) <= set("0123456789abcdef")
    assert effective_engine_config(default_engine)["weights"] == dict(
        sorted(default_engine.weights.items())
    )

    changed = AffordanceEngine(
        AffordanceConfig(weights={**default_engine.weights, "lane_clearance": 0.99})
    )
    assert engine_config_sha256(changed) != first


def test_artifact_reuses_authoritative_baseline_and_regenerates_b():
    engine = AffordanceEngine()
    frames = [frame(4)]
    options_by_frame = baseline_options(frames, engine)
    authoritative_pass = next(
        option
        for option in options_by_frame[4]
        if option.kind == "pass" and option.target_player_id == "runner"
    )
    authoritative_score = authoritative_pass.geometric_score
    authoritative_target = (authoritative_pass.target_x, authoritative_pass.target_y)

    artifact = build_counterfactual_options_artifact(
        "scenario-test",
        frames,
        options_by_frame,
        engine=engine,
    )

    assert artifact["schema_version"] == COUNTERFACTUAL_OPTIONS_SCHEMA_VERSION
    assert artifact["lead_presets"] == [0.5, 0.75, 1.0]
    assert artifact["generator"]["future_observed_frames_used"] is False
    assert artifact["generator"]["package_version"]
    assert len(artifact["generator"]["config_sha256"]) == 64

    frame_payload = artifact["frames"][0]
    baseline_runner = next(
        item
        for item in frame_payload["baseline_options"]
        if item["comparison_option_key"] == "pass:runner"
    )
    assert baseline_runner["option"]["geometric_score"] == pytest.approx(
        authoritative_score
    )
    assert (
        baseline_runner["option"]["target_x"],
        baseline_runner["option"]["target_y"],
    ) == pytest.approx(authoritative_target)

    condition = next(
        item for item in frame_payload["conditions"] if item["lead_seconds"] == 0.75
    )
    assert condition["status"] == "available"
    assert condition["reason"] is None
    assert condition["intervention"]["player_id"] == "runner"
    assert condition["intervention"]["status"] == (
        "synthetic_teaching_intervention_not_observed_or_causal"
    )
    right_runner = next(
        item
        for item in condition["condition_b_options"]
        if item["comparison_option_key"] == "pass:runner"
    )
    assert right_runner["option"]["target_x"] != pytest.approx(
        baseline_runner["option"]["target_x"]
    )
    comparison = next(
        item
        for item in condition["candidate_comparisons"]
        if item["comparison_option_key"] == "pass:runner"
    )
    assert comparison["support"] == "intersection"
    assert comparison["left_option_id"] == authoritative_pass.option_id
    assert comparison["right_option_id"] == right_runner["option"]["option_id"]
    assert comparison["geometric_score_delta"] is not None


def test_artifact_stamps_explicit_carry_identity_on_baseline_and_b():
    engine = AffordanceEngine()
    frames = [frame(4)]
    options_by_frame = baseline_options(frames, engine)

    artifact = build_counterfactual_options_artifact(
        "scenario-test",
        frames,
        options_by_frame,
        engine=engine,
    )

    baseline_carries = [
        item
        for item in artifact["frames"][0]["baseline_options"]
        if item["option"]["kind"] == "carry"
    ]
    assert baseline_carries
    assert all(
        "carry_angle_offset_deg" in item["option"]["features"]
        for item in baseline_carries
    )
    for condition in artifact["frames"][0]["conditions"]:
        if condition["status"] != "available":
            continue
        carries = [
            item
            for item in condition["condition_b_options"]
            if item["option"]["kind"] == "carry"
        ]
        assert carries
        assert all(
            "carry_angle_offset_deg" in item["option"]["features"]
            for item in carries
        )


def test_artifact_is_deterministic_for_identical_inputs():
    engine_a = AffordanceEngine()
    engine_b = AffordanceEngine()
    frames_a = [frame(4), frame(5)]
    frames_b = deepcopy(frames_a)
    options_a = baseline_options(frames_a, engine_a)
    options_b = baseline_options(frames_b, engine_b)

    first = build_counterfactual_options_artifact(
        "scenario-test",
        frames_a,
        options_a,
        engine=engine_a,
    )
    second = build_counterfactual_options_artifact(
        "scenario-test",
        frames_b,
        options_b,
        engine=engine_b,
    )
    assert first == second


def test_unavailable_intervention_is_explicit_not_empty_available():
    current = frame(4)
    for candidate in current.teammates():
        candidate.vx = 0.0
        candidate.vy = 0.0
    engine = AffordanceEngine()
    options_by_frame = baseline_options([current], engine)

    artifact = build_counterfactual_options_artifact(
        "scenario-test",
        [current],
        options_by_frame,
        engine=engine,
    )
    for condition in artifact["frames"][0]["conditions"]:
        assert condition == {
            "lead_seconds": condition["lead_seconds"],
            "status": "unavailable",
            "reason": "no_feasible_earlier_run_intervention",
            "intervention": None,
            "condition_b_options": [],
            "candidate_comparisons": [],
            "summary": None,
        }


def test_artifact_fails_closed_on_frame_and_baseline_contract_errors():
    engine = AffordanceEngine()
    current = frame(4)
    options = baseline_options([current], engine)

    with pytest.raises(ValueError, match="duplicate frame_id"):
        build_counterfactual_options_artifact(
            "scenario-test",
            [current, deepcopy(current)],
            options,
            engine=engine,
        )
    with pytest.raises(ValueError, match="baseline frame map"):
        build_counterfactual_options_artifact(
            "scenario-test",
            [current],
            {},
            engine=engine,
        )
    with pytest.raises(ValueError, match="baseline frame map"):
        build_counterfactual_options_artifact(
            "scenario-test",
            [current],
            {**options, 99: options[4]},
            engine=engine,
        )
    wrong_scenario = deepcopy(current)
    wrong_scenario.sequence_id = "other-scenario"
    wrong_options = baseline_options([wrong_scenario], engine)
    with pytest.raises(ValueError, match="does not match scenario_id"):
        build_counterfactual_options_artifact(
            "scenario-test",
            [wrong_scenario],
            wrong_options,
            engine=engine,
        )
    with pytest.raises(ValueError, match="strictly ascending"):
        misordered = [frame(5), frame(4)]
        build_counterfactual_options_artifact(
            "scenario-test",
            misordered,
            baseline_options(misordered, engine),
            engine=engine,
        )


def test_baseline_option_objects_remain_authoritative_after_identity_migration():
    engine = AffordanceEngine()
    current = frame(4)
    options = baseline_options([current], engine)
    baseline_ids = [id(option) for option in options[4]]
    original_scores = [option.geometric_score for option in options[4]]

    build_counterfactual_options_artifact(
        "scenario-test",
        [current],
        options,
        engine=engine,
    )

    assert [id(option) for option in options[4]] == baseline_ids
    assert [option.geometric_score for option in options[4]] == original_scores
    migrated = ensure_comparison_identity_metadata(options[4])
    assert all(
        option.kind != "carry" or "carry_angle_offset_deg" in option.features
        for option in migrated
    )
