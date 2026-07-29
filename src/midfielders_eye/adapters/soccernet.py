from __future__ import annotations

from pathlib import Path

from ..integrations.soccernet_gsr.adapter import load_tracker_state_gsr
from .base import AdapterResult


def load_soccernet_gsr(
    labels_path: str | Path,
    possession_sidecar_path: str | Path,
    sequence_id: str | None = None,
    match_id: str | None = None,
    fps: float = 25.0,
    pitch_length: float = 105.0,
    pitch_width: float = 68.0,
) -> AdapterResult:
    """Backward-compatible official JSON adapter.

    v0.3 routes official prediction/annotation JSON through the same frozen tracker-state reader
    used for CSV, JSONL, Parquet, and trusted TrackLab dataframe exports.
    """
    if pitch_length != 105.0 or pitch_width != 68.0:
        # The expanded adapter supports standard SoccerNet coordinates. Non-standard pitches
        # should be normalized upstream to avoid silently applying the wrong projection.
        raise ValueError("SoccerNet GSR adapter currently requires a 105 x 68 m pitch")
    return load_tracker_state_gsr(
        labels_path,
        possession_sidecar_path,
        match_id=match_id,
        sequence_id=sequence_id,
        fps=fps,
        coordinates="soccernet_center",
    )


__all__ = ["load_soccernet_gsr", "load_tracker_state_gsr"]
