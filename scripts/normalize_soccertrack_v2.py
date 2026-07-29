from __future__ import annotations

import argparse

from midfielders_eye.adapters.soccertrack import load_soccertrack_v2
from midfielders_eye.io import write_frames_jsonl


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("gsr")
    parser.add_argument("bas")
    parser.add_argument("output")
    parser.add_argument("--match-id")
    parser.add_argument("--half", type=int, default=1)
    args = parser.parse_args()
    result = load_soccertrack_v2(
        args.gsr,
        args.bas,
        match_id=args.match_id,
        half=args.half,
    )
    write_frames_jsonl(result.frames, args.output)
    print(result.summary())


if __name__ == "__main__":
    main()
