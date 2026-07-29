from __future__ import annotations

import argparse

from midfielders_eye.adapters.kloppy_bridge import load_sportec_open
from midfielders_eye.io import write_frames_jsonl


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("match_id")
    parser.add_argument("output")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--sample-rate", type=float)
    args = parser.parse_args()
    result = load_sportec_open(args.match_id, limit=args.limit, sample_rate=args.sample_rate)
    write_frames_jsonl(result.frames, args.output)
    print(result.summary())


if __name__ == "__main__":
    main()
