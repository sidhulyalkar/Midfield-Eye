import math

from midfielders_eye.affordance import AffordanceEngine
from midfielders_eye.cognition.adaptation import frame_relational_metrics, sequence_relational_summary
from midfielders_eye.cognition.body import frame_body_mechanics, sequence_body_summary
from midfielders_eye.cognition.gaze import frame_gaze_metrics, point_in_view, sequence_gaze_summary, view_cone_polygons
from midfielders_eye.showcase.scenarios import build_scenario_frames


def test_gaze_fields_and_source_are_explicit():
    frame = build_scenario_frames("rodri-pivot", frame_count=8)[3]
    options = AffordanceEngine().generate(frame)
    payload = frame_gaze_metrics(frame, options)
    assert payload["gaze_source"] == "synthetic"
    assert payload["gaze_confidence"] == 1.0
    assert set(payload["view_cones"]) == {"foveal", "actionable", "peripheral"}
    assert 0 <= payload["visible_option_recall"] <= 1
    cones = view_cone_polygons(frame.carrier)
    assert len(cones["actionable"]["polygon"]) >= 30


def test_point_in_view_respects_heading():
    frame = build_scenario_frames("olise-half-space", frame_count=8)[0]
    player = frame.carrier
    ahead = player.position + 10 * __import__("numpy").array([math.cos(player.view_angle), math.sin(player.view_angle)])
    behind = player.position - 10 * __import__("numpy").array([math.cos(player.view_angle), math.sin(player.view_angle)])
    assert point_in_view(player, ahead)
    assert not point_in_view(player, behind)


def test_sequence_cognition_summaries_are_frontend_ready():
    frames = build_scenario_frames("pedri-third-man", frame_count=10)
    engine = AffordanceEngine()
    options = {frame.frame_id: engine.generate(frame) for frame in frames}
    gaze = sequence_gaze_summary(frames, options)
    body = sequence_body_summary(frames, options)
    relation = sequence_relational_summary(frames, options)
    assert len(gaze["timeline"]) == 10
    assert gaze["summary"]["scan_rate_hz"] >= 0
    assert 0 <= body["summary"]["balance_reserve_proxy"] <= 1
    assert -4 <= relation["summary"]["coadaptation_lag_frames"] <= 4


def test_frame_body_and_relational_metrics_are_bounded():
    frame = build_scenario_frames("musiala-pressure-magnet", frame_count=8)[4]
    options = AffordanceEngine().generate(frame)
    body = frame_body_mechanics(frame, options)
    relation = frame_relational_metrics(frame, options)
    for key in ["balance_reserve_proxy", "open_body_score", "multi_action_readiness"]:
        assert 0 <= body[key] <= 1
    for key in ["pressure_attraction", "support_reactivity", "network_brokerage", "directive_influence"]:
        assert 0 <= relation[key] <= 1
