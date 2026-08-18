from __future__ import annotations

from dataclasses import replace

from midfielders_eye.r1_metrica import build_metrica_receipt_source
from midfielders_eye.schema import EventState
from midfielders_eye.synthetic import generate_sequence


def test_metrica_r1_receipt_uses_pass_actor_then_recipient() -> None:
    frames = generate_sequence(0, frames=70, fps=25.0, seed=103)
    actor_id = "Home_06"
    recipient_id = "Home_07"
    converted = []
    for frame in frames:
        synthetic_carrier_id = "H06" if frame.frame_id < 20 else "H07"
        carrier = frame.player(synthetic_carrier_id)
        players = [
            replace(
                player,
                player_id=(
                    f"Home_{player.player_id[1:]}"
                    if player.team == "home"
                    else f"Away_{player.player_id[1:]}"
                ),
                source_player_id=player.player_id[1:],
            )
            for player in frame.players
        ]
        converted.append(
            replace(
                frame,
                sequence_id="match-1",
                source_provider="metrica",
                source_match_id="match-1",
                ball_carrier_id=actor_id if frame.frame_id < 20 else recipient_id,
                ball_x=carrier.x,
                ball_y=carrier.y,
                ball_vx=carrier.vx,
                ball_vy=carrier.vy,
                players=players,
                quality_flags=["inferred_ball_carrier"],
            )
        )
    event = EventState(
        sequence_id="match-1",
        event_id="pass-1",
        timestamp_s=18 / 25.0,
        period=1,
        event_type="PASS",
        team="home",
        actor_id=actor_id,
        source_provider="metrica",
        source_match_id="match-1",
        metadata={
            "start_frame": 18,
            "end_frame": 20,
            "recipient_source_id": "07",
            "raw_team": "Home",
        },
    )

    source, report = build_metrica_receipt_source(
        converted,
        [event],
        match_id="match-1",
        minimum_control_s=0.45,
    )

    assert report.pass_events == 1
    assert report.eligible_receipts == 1
    assert source
    before = [frame for frame in source if frame.frame_id <= 18]
    after = [frame for frame in source if frame.frame_id >= 20]
    assert before and after
    assert all(frame.ball_carrier_id == actor_id for frame in before)
    assert all(frame.ball_carrier_id == recipient_id for frame in after)
    assert all(frame.possession_team == "home" for frame in source)
    assert all("inferred_ball_carrier" not in frame.quality_flags for frame in source)
    assert all("event_supported_ball_carrier" in frame.quality_flags for frame in source)
    assert all(
        frame.metadata["r1_window_selection_semantics"]
        == "retrospective_window_selection_not_model_feature"
        for frame in source
    )
