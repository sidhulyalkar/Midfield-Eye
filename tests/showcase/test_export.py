import json
from pathlib import Path

from midfielders_eye.showcase.export import build_showcase_bundle


def test_showcase_bundle_builds_static_frontend_contract(tmp_path: Path):
    manifest_path = build_showcase_bundle(
        tmp_path / "showcase",
        scenario_ids=["olise-half-space"],
        frame_count=8,
        render_dpi=80,
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["scenario_count"] == 1
    assert manifest["player_count"] == 100
    scenario = tmp_path / "showcase" / "scenarios" / "olise-half-space"
    assert (scenario / "frames.jsonl").exists()
    assert (scenario / "options.json").exists()
    assert (scenario / "visuals" / "tactical-lens-4k.png").exists()
    assert (scenario / "visuals" / "action-menu-timeline-4k.png").exists()
    assert (scenario / "gaze.json").exists()
    assert (scenario / "body_mechanics.json").exists()
    assert (scenario / "relational_control.json").exists()
    assert (scenario / "visuals" / "gaze-lab-4k.png").exists()
    assert (scenario / "visuals" / "body-mechanics-4k.png").exists()
    assert (scenario / "visuals" / "relational-control-4k.png").exists()
    assert (tmp_path / "showcase" / "players" / "rodri" / "profile.svg").exists()
    assert len(list((tmp_path / "showcase" / "players").glob("*/profile.svg"))) == 100
