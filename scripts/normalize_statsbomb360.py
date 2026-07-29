from __future__ import annotations

import argparse

from midfielders_eye.adapters.statsbomb import load_statsbomb_360
from midfielders_eye.io import write_frames_jsonl
from midfielders_eye.quality import assess_frames


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("events")
    parser.add_argument("three_sixty")
    parser.add_argument("output")
    parser.add_argument("--match-id")
    parser.add_argument("--home-team")
    args = parser.parse_args()
    result = load_statsbomb_360(
        args.events,
        args.three_sixty,
        match_id=args.match_id,
        home_team_name=args.home_team,
    )
    write_frames_jsonl(result.frames, args.output)
    print(result.summary())
    print(assess_frames(result.frames, "statsbomb360").to_dict())


if __name__ == "__main__":
    main()
