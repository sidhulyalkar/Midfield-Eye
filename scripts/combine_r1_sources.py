from __future__ import annotations

import argparse
import json
from pathlib import Path

from midfielders_eye.io import read_frames_jsonl, write_frames_jsonl
from midfielders_eye.pilot import validate_causal_frame_states


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Combine R1-ready canonical source JSONL files without source-frame collisions."
    )
    parser.add_argument("source", type=Path, nargs="+", help="R1-ready canonical JSONL files.")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    frames = [frame for path in args.source for frame in read_frames_jsonl(path)]
    validate_causal_frame_states(frames)
    keys = [
        (
            frame.source_provider,
            frame.source_match_id or frame.sequence_id,
            frame.period,
            frame.frame_id,
            frame.sequence_id,
        )
        for frame in frames
    ]
    if len(keys) != len(set(keys)):
        raise SystemExit("R1 source files contain duplicate canonical source-frame rows")
    frames.sort(
        key=lambda frame: (
            frame.source_provider,
            frame.source_match_id or "",
            frame.sequence_id,
            frame.period,
            frame.timestamp_s,
            frame.frame_id,
        )
    )
    output = write_frames_jsonl(frames, args.output)
    print(
        json.dumps(
            {
                "output": str(output),
                "frames": len(frames),
                "source_sequences": len({frame.sequence_id for frame in frames}),
                "providers": sorted({frame.source_provider for frame in frames}),
                "matches": sorted({frame.source_match_id for frame in frames if frame.source_match_id}),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
