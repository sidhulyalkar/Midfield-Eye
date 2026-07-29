from __future__ import annotations

import json
from pathlib import Path

from midfielders_eye.integrations.soccernet_gsr import (
    load_tracker_state_gsr,
    read_tracker_state,
    write_tracker_state_manifest,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_tracker_state_reader_accepts_dataframe_export() -> None:
    bundle = read_tracker_state(
        FIXTURES / "soccernet_tracker_state.csv",
        match_id="sn-csv",
        visibility_path=FIXTURES / "soccernet_visibility.json",
    )
    assert len(bundle.frames) == 1
    assert bundle.observation_count == 4
    assert bundle.frames[0].camera_id == "main"
    assert bundle.frames[0].visible_pitch_polygon
    assert bundle.frames[0].observations[0].image_bbox == [100.0, 100.0, 30.0, 80.0]


def test_tracker_state_adapter_preserves_uncertainty() -> None:
    result = load_tracker_state_gsr(
        FIXTURES / "soccernet_tracker_state.csv",
        FIXTURES / "soccernet_possession.csv",
        visibility_path=FIXTURES / "soccernet_visibility.json",
        match_id="sn-csv",
    )
    frame = result.frames[0]
    assert frame.ball_status == "sidecar"
    assert frame.visibility_polygon
    assert frame.camera_id == "main"
    assert "frozen_tracker_state" in frame.quality_flags
    assert frame.carrier.track_id == "1"
    assert frame.carrier.uncertainty_radius_m > 0
    assert frame.carrier.observation_id == "sn-csv:10:1"


def test_tracker_state_manifest_hashes_input(tmp_path: Path) -> None:
    output = write_tracker_state_manifest(
        FIXTURES / "soccernet_tracker_state.csv",
        tmp_path / "manifest.json",
        dataset_version="1.3",
        model_versions={"detector": "example"},
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert len(payload["state_sha256"]) == 64
    assert payload["dataset_version"] == "1.3"
    assert payload["model_versions"]["detector"] == "example"
