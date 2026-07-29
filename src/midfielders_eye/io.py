from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import pandas as pd

from .schema import ActionOption, FrameState


def read_frames_jsonl(path: str | Path) -> list[FrameState]:
    frames: list[FrameState] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                frame = FrameState.from_dict(json.loads(line))
                frame.validate()
                frames.append(frame)
            except Exception as exc:  # pragma: no cover - error context
                raise ValueError(f"Invalid frame on line {line_number}: {exc}") from exc
    return frames


def write_frames_jsonl(frames: Iterable[FrameState], path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for frame in frames:
            frame.validate()
            handle.write(json.dumps(frame.to_dict(), sort_keys=True) + "\n")
    return output


def write_frames_parquet(frames: Iterable[FrameState], path: str | Path) -> Path:
    """Write canonical frames to Parquet without relying on nested-column inference.

    Each row stores searchable scalar columns plus an exact JSON payload. This keeps the
    serialization stable across Arrow versions and allows lossless reconstruction.
    Install the ``parquet`` optional dependency to enable this path.
    """
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for frame in frames:
        frame.validate()
        rows.append(
            {
                "sequence_id": frame.sequence_id,
                "frame_id": frame.frame_id,
                "timestamp_s": frame.timestamp_s,
                "period": frame.period,
                "source_provider": frame.source_provider,
                "source_match_id": frame.source_match_id,
                "payload_json": json.dumps(frame.to_dict(), sort_keys=True),
            }
        )
    try:
        pd.DataFrame(rows).to_parquet(output, index=False)
    except ImportError as exc:  # pragma: no cover - depends on optional engine
        raise RuntimeError(
            "Parquet support requires `pip install -e '.[parquet]'` (pyarrow)."
        ) from exc
    return output


def read_frames_parquet(path: str | Path) -> list[FrameState]:
    try:
        dataframe = pd.read_parquet(path)
    except ImportError as exc:  # pragma: no cover - depends on optional engine
        raise RuntimeError(
            "Parquet support requires `pip install -e '.[parquet]'` (pyarrow)."
        ) from exc
    if "payload_json" not in dataframe.columns:
        raise ValueError("Frame Parquet file must contain payload_json")
    frames = [FrameState.from_dict(json.loads(payload)) for payload in dataframe["payload_json"]]
    for frame in frames:
        frame.validate()
    return frames


def options_to_dataframe(options: Iterable[ActionOption]) -> pd.DataFrame:
    return pd.DataFrame([option.to_flat_dict() for option in options])


def write_options_csv(options: Iterable[ActionOption], path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    options_to_dataframe(options).to_csv(output, index=False)
    return output
