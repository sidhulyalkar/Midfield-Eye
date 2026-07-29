from midfielders_eye.io import read_frames_jsonl, write_frames_jsonl
from midfielders_eye.synthetic import generate_sequence


def test_frame_round_trip(tmp_path):
    frames = generate_sequence(2, frames=3)
    path = write_frames_jsonl(frames, tmp_path / "frames.jsonl")
    restored = read_frames_jsonl(path)
    assert len(restored) == 3
    assert restored[0].sequence_id == frames[0].sequence_id
    assert restored[0].ball_carrier_id == frames[0].ball_carrier_id
