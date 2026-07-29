from pathlib import Path

import pandas as pd

from midfielders_eye.adapters.kloppy_bridge import frames_from_kloppy_dataframe
from midfielders_eye.adapters.metrica import load_metrica_csv
from midfielders_eye.adapters.skillcorner import load_skillcorner_open
from midfielders_eye.adapters.soccernet import load_soccernet_gsr
from midfielders_eye.adapters.soccertrack import load_soccertrack_v2
from midfielders_eye.adapters.statsbomb import load_statsbomb_360

FIXTURES = Path(__file__).parent / "fixtures"


def test_metrica_adapter_marks_provider() -> None:
    frames = load_metrica_csv(FIXTURES / "metrica_normalized.csv", sequence_id="m1")
    assert len(frames) == 2
    assert frames[0].source_provider == "metrica"
    assert frames[0].pitch_length == 105.0
    assert frames[0].ball_carrier_id.startswith("Home_")


def test_statsbomb_360_is_explicit_snapshot() -> None:
    result = load_statsbomb_360(
        FIXTURES / "statsbomb_events.json",
        FIXTURES / "statsbomb_360.json",
        match_id="sb1",
        home_team_name="Home FC",
    )
    assert len(result.frames) == 1
    assert len(result.events) == 2
    frame = result.frames[0]
    assert frame.source_provider == "statsbomb360"
    assert "event_snapshot" in frame.quality_flags
    assert frame.visibility_polygon
    assert frame.carrier.player_id == "sb:101"


def test_skillcorner_preserves_extrapolation_and_velocity() -> None:
    result = load_skillcorner_open(
        FIXTURES / "skillcorner_tracking.jsonl",
        match_path=FIXTURES / "skillcorner_match.json",
        match_id="sc1",
    )
    assert len(result.frames) == 2
    assert any(player.tracking_status == "extrapolated" for player in result.frames[0].players)
    assert result.frames[1].carrier.vx > 0
    assert result.frames[0].visibility_polygon


def test_soccertrack_uses_bas_to_create_ball_state() -> None:
    result = load_soccertrack_v2(
        FIXTURES / "soccertrack_gsr.json",
        FIXTURES / "soccertrack_bas.json",
        half=1,
    )
    assert len(result.frames) == 1
    frame = result.frames[0]
    assert frame.ball_carrier_id == "stv2:P9"
    assert frame.ball_x == frame.carrier.x
    assert frame.source_provider == "soccertrack_v2"


def test_soccernet_requires_explicit_possession_sidecar() -> None:
    result = load_soccernet_gsr(
        FIXTURES / "soccernet_labels.json",
        FIXTURES / "soccernet_possession.csv",
        match_id="sn1",
    )
    assert len(result.frames) == 1
    frame = result.frames[0]
    assert frame.ball_carrier_id == "sngs:1"
    assert "external_possession_sidecar" in frame.quality_flags


def test_kloppy_dataframe_bridge() -> None:
    dataframe = pd.DataFrame(
        [
            {
                "period_id": 1,
                "timestamp": 0.0,
                "frame_id": 1,
                "ball_owning_team_id": "H",
                "ball_x": 50.0,
                "ball_y": 34.0,
                "p1_x": 50.1,
                "p1_y": 34.0,
                "p2_x": 65.0,
                "p2_y": 34.0,
                "p3_x": 53.0,
                "p3_y": 34.0,
                "p4_x": 80.0,
                "p4_y": 34.0,
            }
        ]
    )
    result = frames_from_kloppy_dataframe(
        dataframe,
        home_player_ids=["p1", "p2"],
        away_player_ids=["p3", "p4"],
        team_id_map={"H": "home", "A": "away"},
        match_id="k1",
    )
    assert result.frames[0].ball_carrier_id == "kloppy:p1"
