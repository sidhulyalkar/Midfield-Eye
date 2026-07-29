from __future__ import annotations

import copy

from midfielders_eye.state.camera import detect_camera_cuts
from midfielders_eye.state.state_completion import FormationPriorCompleter, apply_camera_crop
from midfielders_eye.state.temporal_smoothing import interpolate_short_gaps, reconstruct_trajectories
from midfielders_eye.state.track_stitching import propose_track_stitches
from midfielders_eye.synthetic import generate_dataset


def test_causal_reconstruction_adds_kinematics_and_provenance() -> None:
    frames = generate_dataset(sequences=1, frames=5, seed=3)
    reconstructed = reconstruct_trajectories(frames)
    player = reconstructed[-1].players[0]
    assert "causal_kalman" in player.provenance_flags
    assert player.trajectory_confidence is not None
    assert "causal_trajectory_reconstruction" in reconstructed[-1].quality_flags


def test_offline_gap_interpolation_is_explicit() -> None:
    frames = generate_dataset(sequences=1, frames=3, seed=4)
    missing_id = frames[0].players[1].player_id
    frames[1].players = [player for player in frames[1].players if player.player_id != missing_id]
    interpolated = interpolate_short_gaps(frames, max_gap_frames=1)
    restored = interpolated[1].player(missing_id)
    assert restored.tracking_status == "interpolated"
    assert "uses_future_endpoint" in restored.provenance_flags
    assert restored.visible is False


def test_camera_cut_detects_visibility_jump() -> None:
    frames = generate_dataset(sequences=1, frames=2, seed=5)
    frames[0].visibility_polygon = [[0, 0], [30, 0], [30, 30], [0, 30]]
    frames[1].visibility_polygon = [[70, 30], [105, 30], [105, 68], [70, 68]]
    assert detect_camera_cuts(frames) == [frames[1].frame_id]
    assert "camera_cut" in frames[1].quality_flags


def test_camera_crop_and_formation_prior_completion() -> None:
    frames = generate_dataset(sequences=2, frames=3, seed=6)
    completer = FormationPriorCompleter().fit(frames)
    frame = copy.deepcopy(frames[0])
    cropped = apply_camera_crop(frame, [[0, 0], [60, 0], [60, 68], [0, 68]])
    assert len(cropped.players) <= len(frame.players)
    completed = completer.complete(cropped, [("away", "outfield", "hidden:1")])
    inferred = completed.player("hidden:1")
    assert inferred.tracking_status == "inferred"
    assert inferred.visibility == "off_screen"
    assert inferred.uncertainty_radius_m > 0


def test_track_stitch_proposal_uses_team_and_motion() -> None:
    frames = generate_dataset(sequences=1, frames=2, seed=9)
    first = frames[0]
    second = frames[1]
    source = first.players[1]
    target = copy.deepcopy(source)
    target.player_id = "new-track"
    target.track_id = "new-track"
    target.source_player_id = "new-track"
    target.x += 0.2
    second.players = [player for player in second.players if player.team != source.team]
    second.players.append(target)
    proposals = propose_track_stitches(frames, max_gap_s=2.0, max_distance_m=5.0)
    assert any(proposal.target_track_id == "new-track" for proposal in proposals)
