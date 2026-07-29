from __future__ import annotations

from dataclasses import asdict, dataclass

from .schema import EventState, FrameState


@dataclass(slots=True)
class EventFrameAlignment:
    event_id: str
    sequence_id: str
    event_timestamp_s: float
    frame_id: int | None
    frame_timestamp_s: float | None
    absolute_error_s: float | None
    matched: bool

    def to_dict(self) -> dict:
        return asdict(self)


def align_events_to_frames(
    events: list[EventState],
    frames: list[FrameState],
    tolerance_s: float = 0.12,
) -> list[EventFrameAlignment]:
    by_sequence_period: dict[tuple[str, int], list[FrameState]] = {}
    for frame in frames:
        by_sequence_period.setdefault((frame.sequence_id, frame.period), []).append(frame)
    for values in by_sequence_period.values():
        values.sort(key=lambda frame: frame.timestamp_s)

    alignments: list[EventFrameAlignment] = []
    for event in events:
        candidates = by_sequence_period.get((event.sequence_id, event.period), [])
        if not candidates:
            alignments.append(
                EventFrameAlignment(event.event_id, event.sequence_id, event.timestamp_s, None, None, None, False)
            )
            continue
        best = min(candidates, key=lambda frame: abs(frame.timestamp_s - event.timestamp_s))
        error = abs(best.timestamp_s - event.timestamp_s)
        alignments.append(
            EventFrameAlignment(
                event.event_id,
                event.sequence_id,
                event.timestamp_s,
                best.frame_id if error <= tolerance_s else None,
                best.timestamp_s if error <= tolerance_s else None,
                error,
                error <= tolerance_s,
            )
        )
    return alignments


def event_centered_windows(
    events: list[EventState],
    frames: list[FrameState],
    before_s: float = 2.0,
    after_s: float = 1.0,
) -> dict[str, list[FrameState]]:
    windows: dict[str, list[FrameState]] = {}
    for event in events:
        windows[event.event_id] = [
            frame
            for frame in frames
            if frame.sequence_id == event.sequence_id
            and frame.period == event.period
            and event.timestamp_s - before_s <= frame.timestamp_s <= event.timestamp_s + after_s
        ]
    return windows
