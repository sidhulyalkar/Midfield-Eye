from __future__ import annotations

import math
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Sequence

from .adapters.metrica import load_metrica_open
from .io import write_frames_jsonl
from .schema import EventState, FrameState


@dataclass(frozen=True)
class MetricaR1SourceReport:
    match_id: str
    pass_events: int
    eligible_receipts: int
    emitted_frames: int
    rejected_missing_recipient: int
    rejected_missing_tracking: int
    rejected_ball_distance: int
    rejected_short_control: int
    carrier_source: str = "metrica_pass_actor_and_recipient"
    possession_source: str = "metrica_pass_team"
    selection_semantics: str = "retrospective_window_selection_not_model_feature"

    def to_dict(self) -> dict[str, int | str]:
        return {
            "match_id": self.match_id,
            "pass_events": self.pass_events,
            "eligible_receipts": self.eligible_receipts,
            "emitted_frames": self.emitted_frames,
            "rejected_missing_recipient": self.rejected_missing_recipient,
            "rejected_missing_tracking": self.rejected_missing_tracking,
            "rejected_ball_distance": self.rejected_ball_distance,
            "rejected_short_control": self.rejected_short_control,
            "carrier_source": self.carrier_source,
            "possession_source": self.possession_source,
            "selection_semantics": self.selection_semantics,
        }


def _canonical_recipient_id(event: EventState) -> str | None:
    recipient = event.metadata.get("recipient_source_id")
    raw_team = event.metadata.get("raw_team")
    if recipient is None or raw_team is None:
        return None
    return f"{str(raw_team).strip().title()}_{str(recipient).strip()}"


def _frame_index(frames: Sequence[FrameState]) -> dict[tuple[int, int], FrameState]:
    indexed: dict[tuple[int, int], FrameState] = {}
    for frame in frames:
        key = (frame.period, frame.frame_id)
        if key in indexed:
            raise ValueError(f"Duplicate Metrica tracking frame key {key}")
        indexed[key] = frame
    return indexed


def _event_start_frame(event: EventState) -> int | None:
    value = event.metadata.get("start_frame")
    return None if value is None else int(value)


def _event_end_frame(event: EventState) -> int | None:
    value = event.metadata.get("end_frame")
    return None if value is None else int(value)


def _carrier_distance(frame: FrameState, player_id: str) -> float | None:
    try:
        player = frame.player(player_id)
    except KeyError:
        return None
    return math.hypot(player.x - frame.ball_x, player.y - frame.ball_y)


def _sample_context_frames(
    frames: Sequence[FrameState],
    *,
    maximum_frames: int = 3,
) -> list[FrameState]:
    """Keep sparse, time-spanning snapshots so context cannot become a label window."""

    ordered = sorted(frames, key=lambda frame: (frame.timestamp_s, frame.frame_id))
    if len(ordered) <= maximum_frames:
        return list(ordered)
    if maximum_frames <= 1:
        return [ordered[-1]]
    indices = [
        round(index * (len(ordered) - 1) / (maximum_frames - 1))
        for index in range(maximum_frames)
    ]
    return [ordered[index] for index in dict.fromkeys(indices)]


def _event_supported_frame(
    frame: FrameState,
    *,
    sequence_id: str,
    carrier_id: str,
    possession_team: str,
    event_id: str,
    phase: str,
) -> FrameState:
    carrier = frame.player(carrier_id)
    if carrier.team != possession_team:
        raise ValueError(
            f"Metrica event carrier {carrier_id!r} does not belong to {possession_team!r}"
        )
    quality_flags = [
        flag for flag in frame.quality_flags if flag != "inferred_ball_carrier"
    ]
    quality_flags.append("event_supported_ball_carrier")
    metadata = dict(frame.metadata)
    metadata.update(
        {
            "r1_metrica_receipt_event_id": event_id,
            "r1_metrica_receipt_phase": phase,
            "r1_possession_source": "metrica_pass_team",
            "r1_ball_carrier_source": (
                "metrica_pass_actor_before_end_frame"
                if phase == "causal_context"
                else "metrica_pass_recipient_at_or_after_end_frame"
            ),
            "r1_window_selection_semantics": "source_event_window_selection_not_feature",
            "r1_original_sequence_id": frame.sequence_id,
        }
    )
    return replace(
        frame,
        sequence_id=sequence_id,
        possession_team=possession_team,
        ball_carrier_id=carrier_id,
        possession_confidence=1.0,
        quality_flags=quality_flags,
        metadata=metadata,
    )


def build_metrica_receipt_source(
    frames: Sequence[FrameState],
    events: Sequence[EventState],
    *,
    match_id: str,
    pre_context_s: float = 1.6,
    post_receipt_s: float = 1.6,
    minimum_control_s: float = 0.45,
    max_ball_carrier_distance_m: float = 3.5,
) -> tuple[list[FrameState], MetricaR1SourceReport]:
    """Build R1 source windows from Metrica PASS actor/recipient evidence.

    This function uses completed provider events only to *select* receipt windows
    and to establish current possession/carrier state at the event boundary. It
    never converts the selected pass into an availability/value label and never
    injects the event outcome into candidate features.

    Pre-pass frames are intentionally reduced to three time-spanning snapshots.
    They remain useful to the human creation label but cannot accidentally pass
    the R1 minimum-four-frame focal-window rule and become a second passer window.
    """

    if pre_context_s < 0 or post_receipt_s <= 0 or minimum_control_s <= 0:
        raise ValueError("R1 Metrica context/control durations are invalid")
    if max_ball_carrier_distance_m <= 0:
        raise ValueError("max_ball_carrier_distance_m must be positive")
    indexed = _frame_index(frames)
    by_period: dict[int, list[FrameState]] = {}
    for frame in frames:
        by_period.setdefault(frame.period, []).append(frame)
    for period_frames in by_period.values():
        period_frames.sort(key=lambda frame: (frame.timestamp_s, frame.frame_id))

    pass_events = [event for event in events if event.event_type.strip().upper() == "PASS"]
    ordered_events = sorted(
        events,
        key=lambda event: (event.period, event.timestamp_s, event.event_id),
    )
    next_start_by_event: dict[str, int | None] = {}
    for index, event in enumerate(ordered_events):
        next_frame = None
        for later in ordered_events[index + 1 :]:
            if later.period != event.period:
                break
            candidate = _event_start_frame(later)
            if candidate is not None:
                next_frame = candidate
                break
        next_start_by_event[event.event_id] = next_frame

    output: list[FrameState] = []
    counters = {
        "missing_recipient": 0,
        "missing_tracking": 0,
        "ball_distance": 0,
        "short_control": 0,
    }
    eligible = 0

    for event in pass_events:
        if event.team not in {"home", "away"} or event.actor_id is None:
            counters["missing_tracking"] += 1
            continue
        recipient_id = _canonical_recipient_id(event)
        if recipient_id is None:
            counters["missing_recipient"] += 1
            continue
        start_frame = _event_start_frame(event)
        end_frame = _event_end_frame(event)
        if start_frame is None or end_frame is None:
            counters["missing_tracking"] += 1
            continue
        start = indexed.get((event.period, start_frame))
        end = indexed.get((event.period, end_frame))
        if start is None or end is None:
            counters["missing_tracking"] += 1
            continue
        try:
            start.player(event.actor_id)
            end.player(recipient_id)
        except KeyError:
            counters["missing_tracking"] += 1
            continue
        end_distance = _carrier_distance(end, recipient_id)
        if end_distance is None or end_distance > max_ball_carrier_distance_m:
            counters["ball_distance"] += 1
            continue

        period_frames = by_period[event.period]
        context = _sample_context_frames(
            [
                frame
                for frame in period_frames
                if start.timestamp_s - pre_context_s
                <= frame.timestamp_s
                <= start.timestamp_s
            ],
            maximum_frames=3,
        )
        if not context:
            counters["missing_tracking"] += 1
            continue

        next_event_frame = next_start_by_event.get(event.event_id)
        receipt: list[FrameState] = []
        for frame in period_frames:
            if frame.frame_id < end_frame:
                continue
            if next_event_frame is not None and frame.frame_id >= next_event_frame:
                break
            if frame.timestamp_s > end.timestamp_s + post_receipt_s + 1e-9:
                break
            distance = _carrier_distance(frame, recipient_id)
            if distance is None:
                break
            if distance > max_ball_carrier_distance_m:
                if not receipt:
                    counters["ball_distance"] += 1
                break
            receipt.append(frame)
        if not receipt or receipt[-1].timestamp_s - receipt[0].timestamp_s < minimum_control_s:
            counters["short_control"] += 1
            continue

        sequence_id = f"r1-metrica-receipt-{match_id}-{event.event_id}"
        relabeled_context = [
            _event_supported_frame(
                frame,
                sequence_id=sequence_id,
                carrier_id=event.actor_id,
                possession_team=event.team,
                event_id=event.event_id,
                phase="causal_context",
            )
            for frame in context
            if event.actor_id in {player.player_id for player in frame.players}
        ]
        if not relabeled_context:
            counters["missing_tracking"] += 1
            continue
        relabeled_receipt = [
            _event_supported_frame(
                frame,
                sequence_id=sequence_id,
                carrier_id=recipient_id,
                possession_team=event.team,
                event_id=event.event_id,
                phase="receipt_control",
            )
            for frame in receipt
        ]
        output.extend(relabeled_context)
        output.extend(relabeled_receipt)
        eligible += 1

    output.sort(
        key=lambda frame: (
            frame.sequence_id,
            frame.period,
            frame.timestamp_s,
            frame.frame_id,
        )
    )
    return output, MetricaR1SourceReport(
        match_id=match_id,
        pass_events=len(pass_events),
        eligible_receipts=eligible,
        emitted_frames=len(output),
        rejected_missing_recipient=counters["missing_recipient"],
        rejected_missing_tracking=counters["missing_tracking"],
        rejected_ball_distance=counters["ball_distance"],
        rejected_short_control=counters["short_control"],
    )


def prepare_metrica_receipt_source(
    home_tracking_path: str | Path,
    away_tracking_path: str | Path,
    events_path: str | Path,
    output_path: str | Path,
    *,
    match_id: str,
    pre_context_s: float = 1.6,
    post_receipt_s: float = 1.6,
    minimum_control_s: float = 0.45,
    max_ball_carrier_distance_m: float = 3.5,
) -> MetricaR1SourceReport:
    result = load_metrica_open(
        home_tracking_path,
        events_path,
        sequence_id=match_id,
        away_tracking_path=away_tracking_path,
    )
    frames, report = build_metrica_receipt_source(
        result.frames,
        result.events,
        match_id=match_id,
        pre_context_s=pre_context_s,
        post_receipt_s=post_receipt_s,
        minimum_control_s=minimum_control_s,
        max_ball_carrier_distance_m=max_ball_carrier_distance_m,
    )
    if not frames:
        raise ValueError(
            "No event-supported Metrica receipt windows passed the R1 source gates"
        )
    write_frames_jsonl(frames, output_path)
    return report
