from midfielders_eye.affordance import AffordanceEngine
from midfielders_eye.showcase.metrics import frame_showcase_metrics, scenario_summary
from midfielders_eye.showcase.scenarios import SCENARIOS, build_scenario_frames


def test_all_scenarios_are_explicitly_illustrative():
    for scenario_id in SCENARIOS:
        frames = build_scenario_frames(scenario_id, frame_count=8)
        assert len(frames) == 8
        assert all(frame.metadata["evidence_status"] == "illustrative_synthetic_reconstruction" for frame in frames)
        assert all(frame.ball_carrier_id == "SUBJECT" for frame in frames)


def test_showcase_metrics_are_frontend_ready():
    frames = build_scenario_frames("pedri-third-man", frame_count=8)
    engine = AffordanceEngine()
    options_by_frame = {frame.frame_id: engine.generate(frame) for frame in frames}
    metric = frame_showcase_metrics(frames[0], options_by_frame[frames[0].frame_id])
    assert metric["visible_options"] >= 0
    assert 0 <= metric["state_confidence"] <= 1
    summary = scenario_summary(frames, options_by_frame)
    assert len(summary["timeline"]) == 8
    assert summary["metric_status"].startswith("model_derived")
