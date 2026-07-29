from pathlib import Path

import yaml


def test_media_discovery_plan_covers_all_candidates_and_forbids_youtube_analysis():
    payload = yaml.safe_load(Path("data/showcase/media_discovery_plan.yaml").read_text(encoding="utf-8"))
    assert len(payload["players"]) == 100
    assert all(player["queries"] for player in payload["players"])
    assert all(player["analysis_allowed_from_youtube_result"] is False for player in payload["players"])


def test_discovery_plan_includes_gaze_and_failure_balance():
    payload = yaml.safe_load(Path("data/showcase/media_discovery_plan.yaml").read_text(encoding="utf-8"))
    assert "pre_reception_scan" in payload["clip_taxonomy"]
    assert "unsuccessful_or_neutral" in payload["clip_taxonomy"]
    assert payload["balance_requirements"]["failed_actions"] >= 1
    assert all(player["rights_cleared_analysis_required"] for player in payload["players"])
