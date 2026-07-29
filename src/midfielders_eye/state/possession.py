from __future__ import annotations

import copy
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from ..schema import FrameState, Team


@dataclass(slots=True)
class PossessionEstimate:
    frame_id: int
    carrier_id: str | None
    team: Team | None
    probability: float
    state: str
    nearest_distance_m: float | None


@dataclass(slots=True)
class PassEvent:
    sequence_id: str
    start_frame_id: int
    end_frame_id: int
    passer_id: str
    receiver_id: str
    team: Team
    duration_s: float
    distance_m: float
    confidence: float


def estimate_possession(
    frames: list[FrameState],
    *,
    control_radius_m: float = 2.2,
    temperature_m: float = 0.8,
    loose_ball_threshold: float = 0.45,
) -> list[PossessionEstimate]:
    """Estimate possession from an observed ball and player states.

    This helper is appropriate only when a ball track exists. It never fabricates a ball from
    player detections and returns a loose-ball state when no player is sufficiently close.
    """
    estimates: list[PossessionEstimate] = []
    for frame in frames:
        distances = np.array(
            [float(np.linalg.norm(player.position - frame.ball_position)) for player in frame.players],
            dtype=float,
        )
        if len(distances) == 0 or frame.ball_status == "dropped":
            estimates.append(PossessionEstimate(frame.frame_id, None, None, 0.0, "unknown", None))
            continue
        logits = -distances / max(temperature_m, 1e-6)
        probabilities = np.exp(logits - logits.max())
        probabilities /= probabilities.sum()
        index = int(np.argmax(probabilities))
        player = frame.players[index]
        probability = float(probabilities[index])
        distance = float(distances[index])
        controlled = distance <= control_radius_m and probability >= loose_ball_threshold
        estimates.append(
            PossessionEstimate(
                frame_id=frame.frame_id,
                carrier_id=player.player_id if controlled else None,
                team=player.team if controlled else None,
                probability=probability,
                state="controlled" if controlled else "loose_ball",
                nearest_distance_m=distance,
            )
        )
    return estimates


def apply_possession_estimates(
    frames: list[FrameState], estimates: list[PossessionEstimate]
) -> list[FrameState]:
    output = copy.deepcopy(frames)
    by_frame = {estimate.frame_id: estimate for estimate in estimates}
    for frame in output:
        estimate = by_frame.get(frame.frame_id)
        if estimate is None or estimate.carrier_id is None or estimate.team is None:
            frame.quality_flags = sorted(set(frame.quality_flags + ["possession_unresolved"]))
            continue
        frame.ball_carrier_id = estimate.carrier_id
        frame.possession_team = estimate.team
        frame.possession_confidence = estimate.probability
        frame.metadata["possession_inference"] = asdict(estimate)
        frame.quality_flags = sorted(set(frame.quality_flags + ["possession_inferred_from_ball_distance"]))
        frame.validate()
    return output


def detect_pass_events(
    frames: list[FrameState],
    *,
    max_duration_s: float = 3.0,
    minimum_distance_m: float = 3.0,
) -> list[PassEvent]:
    events: list[PassEvent] = []
    ordered = sorted(frames, key=lambda frame: (frame.sequence_id, frame.timestamp_s))
    for previous, current in zip(ordered, ordered[1:]):
        if previous.sequence_id != current.sequence_id:
            continue
        if previous.ball_carrier_id == current.ball_carrier_id:
            continue
        if previous.possession_team != current.possession_team:
            continue
        duration = current.timestamp_s - previous.timestamp_s
        if not 0 < duration <= max_duration_s:
            continue
        passer = previous.carrier
        receiver = current.carrier
        distance = float(np.linalg.norm(receiver.position - passer.position))
        if distance < minimum_distance_m:
            continue
        confidence = float(
            min(
                previous.possession_confidence or previous.ball_confidence or 0.5,
                current.possession_confidence or current.ball_confidence or 0.5,
            )
        )
        events.append(
            PassEvent(
                sequence_id=previous.sequence_id,
                start_frame_id=previous.frame_id,
                end_frame_id=current.frame_id,
                passer_id=passer.player_id,
                receiver_id=receiver.player_id,
                team=passer.team,
                duration_s=float(duration),
                distance_m=distance,
                confidence=confidence,
            )
        )
    return events


def write_possession_sidecar_template(
    frame_ids: list[int],
    output_path: str | Path,
    *,
    fps: float = 25.0,
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    dataframe = pd.DataFrame(
        {
            "frame_id": frame_ids,
            "timestamp_s": [frame_id / fps for frame_id in frame_ids],
            "ball_x": np.nan,
            "ball_y": np.nan,
            "ball_vx": np.nan,
            "ball_vy": np.nan,
            "ball_confidence": np.nan,
            "ball_status": "unknown",
            "possession_team": "",
            "ball_carrier_id": "",
            "possession_confidence": np.nan,
            "period": 1,
        }
    )
    dataframe.to_csv(output, index=False)
    return output
