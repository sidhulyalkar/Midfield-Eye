from pathlib import Path

from midfielders_eye.integrations.soccernet_gsr import load_tracker_state_gsr
from midfielders_eye.io import write_frames_jsonl
from midfielders_eye.quality import assess_frames
from midfielders_eye.state.temporal_smoothing import reconstruct_trajectories

fixtures = Path(__file__).parents[1] / "tests" / "fixtures"
result = load_tracker_state_gsr(
    fixtures / "soccernet_tracker_state.csv",
    fixtures / "soccernet_possession.csv",
    visibility_path=fixtures / "soccernet_visibility.json",
    match_id="fixture",
)
frames = reconstruct_trajectories(result.frames)
write_frames_jsonl(frames, "artifacts/soccernet_quickstart.jsonl")
print(assess_frames(frames).to_dict())
