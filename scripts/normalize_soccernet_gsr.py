from __future__ import annotations

import argparse

from midfielders_eye.adapters.soccernet import load_soccernet_gsr
from midfielders_eye.io import write_frames_jsonl


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("labels")
    parser.add_argument("possession_sidecar")
    parser.add_argument("output")
    parser.add_argument("--match-id")
    args = parser.parse_args()
    result = load_soccernet_gsr(
        args.labels,
        args.possession_sidecar,
        match_id=args.match_id,
    )
    write_frames_jsonl(result.frames, args.output)
    print(result.summary())


if __name__ == "__main__":
    main()
