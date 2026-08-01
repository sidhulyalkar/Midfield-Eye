from __future__ import annotations

import copy
from pathlib import Path

import pytest

from midfielders_eye.adapters.metrica import load_metrica_open, read_metrica_tracking_csv
from midfielders_eye.adapters.skillcorner import (
    load_skillcorner_open,
    validate_skillcorner_attacking_directions,
)
from midfielders_eye.adapters.statsbomb import (
    label_statsbomb_selected_options,
    load_statsbomb_360,
)
from midfielders_eye.affordance import AffordanceEngine
from midfielders_eye.synthetic import generate_sequence

FIXTURES = Path(__file__).parent / "fixtures"


def test_metrica_raw_three_row_parser_and_event_synchronization() -> None:
    table, header_format = read_metrica_tracking_csv(FIXTURES / "metrica_raw_three_row.csv")
    assert header_format == "official_three_row"
    assert {"Home_1_x", "Home_1_y", "ball_x", "ball_y"} <= set(table.columns)

    result = load_metrica_open(
        FIXTURES / "metrica_raw_three_row.csv",
        FIXTURES / "metrica_events.csv",
        sequence_id="metrica:test",
        away_tracking_path=FIXTURES / "metrica_raw_three_row_away.csv",
    )
    assert len(result.frames) == 2
    assert result.frames[0].metadata["native_coordinate_system"]["origin"] == "top_left"
    assert result.frames[0].player("Home_1").x == 52.5
    assert result.frames[0].player("Away_11").x == pytest.approx(55.65)
    assert "inferred_ball_carrier" in result.frames[0].quality_flags
    alignment = result.events[0].metadata["tracking_alignment"]
    assert alignment["matched"] is True
    assert alignment["method"] == "provider_start_frame"
    assert alignment["frame_id"] == 100
    assert result.events[0].end_x == 68.25


def test_skillcorner_direction_evidence_is_validated_without_coordinate_flip() -> None:
    expected = {
        1: {"home": 1, "away": -1},
        2: {"home": -1, "away": 1},
    }
    result = load_skillcorner_open(
        FIXTURES / "skillcorner_two_halves.jsonl",
        match_path=FIXTURES / "skillcorner_match.json",
        match_id="sc-direction",
        expected_attacking_directions=expected,
    )
    assert result.metadata["attacking_direction_validation"]["status"] == "validated_external_evidence"
    assert result.metadata["coordinates_flipped_by_adapter"] is False
    assert result.frames[0].attacking_direction == expected[1]
    assert result.frames[1].attacking_direction == expected[2]
    assert result.frames[0].player("sc:1").x == 52.7
    assert result.frames[0].metadata["native_coordinate_system"]["coordinates_flipped_by_adapter"] is False


def test_skillcorner_missing_or_invalid_direction_evidence_stays_explicit() -> None:
    directions, status, warnings = validate_skillcorner_attacking_directions({1, 2})
    assert directions == {}
    assert status == "inconclusive"
    assert warnings

    _, status, warnings = validate_skillcorner_attacking_directions(
        {1, 2},
        expected_directions={
            1: {"home": 1, "away": -1},
            2: {"home": 1, "away": -1},
        },
    )
    assert status == "failed"
    assert "does not switch" in warnings[0]


def test_visible_area_mask_preserves_outside_physical_candidates() -> None:
    frame = copy.deepcopy(generate_sequence(0, frames=1)[0])
    carrier = frame.carrier
    teammates = frame.teammates()
    inside = teammates[0]
    outside = teammates[1]
    inside.x, inside.y = carrier.x + 3.0, carrier.y
    outside.x, outside.y = carrier.x + 20.0, carrier.y
    frame.visibility_polygon = [
        [carrier.x - 2.0, carrier.y - 5.0],
        [carrier.x + 10.0, carrier.y - 5.0],
        [carrier.x + 10.0, carrier.y + 5.0],
        [carrier.x - 2.0, carrier.y + 5.0],
    ]
    options = AffordanceEngine().generate(frame)
    inside_option = next(option for option in options if option.target_player_id == inside.player_id)
    outside_option = next(option for option in options if option.target_player_id == outside.player_id)
    assert inside_option.features["visible_area_mask"] == 1.0
    assert outside_option.features["visible_area_mask"] == 0.0
    assert outside_option.features["physical_candidate_retained"] == 1.0
    assert outside_option.label_available is None


def test_statsbomb_pass_receiver_is_event_local_and_labels_selection_only() -> None:
    result = load_statsbomb_360(
        FIXTURES / "statsbomb_events.json",
        FIXTURES / "statsbomb_360.json",
        match_id="sb-selected",
        home_team_name="Home FC",
    )
    frame = result.frames[0]
    selected = frame.metadata["selected_action"]
    assert selected["kind"] == "pass"
    assert selected["receiver_mapping"] == "event_local_nearest_freeze_frame_teammate_to_pass_end"
    assert selected["receiver_player_id"].startswith("sb:event-1:teammate:")
    assert selected["receiver_source_id"] == "102"
    receiver = frame.player(selected["receiver_player_id"])
    assert receiver.source_player_id is None
    assert receiver.metadata["identity_scope"] == "event"

    options = AffordanceEngine().generate(frame)
    labeled = label_statsbomb_selected_options(options, result.frames)
    selected_options = [option for option in labeled if option.label_selected]
    assert len(selected_options) == 1
    assert selected_options[0].target_player_id == selected["receiver_player_id"]
    assert all(option.label_available is None for option in labeled)
    assert frame.metadata["selected_action"]["selected_action_is_not_complete_action_menu"] is True
