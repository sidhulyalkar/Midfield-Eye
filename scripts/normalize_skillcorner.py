from __future__ import annotations

import argparse

from midfielders_eye.adapters.skillcorner import load_skillcorner_open
from midfielders_eye.io import write_frames_jsonl
from midfielders_eye.quality import assess_frames


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("tracking")
    parser.add_argument("output")
    parser.add_argument("--match")
    parser.add_argument("--events")
    parser.add_argument("--match-id")
    args = parser.parse_args()
    result = load_skillcorner_open(
        args.tracking,
        match_path=args.match,
        dynamic_events_path=args.events,
        match_id=args.match_id,
    )
    write_frames_jsonl(result.frames, args.output)
    print(result.summary())
    print(assess_frames(result.frames, "skillcorner").to_dict())


if __name__ == "__main__":
    main()
