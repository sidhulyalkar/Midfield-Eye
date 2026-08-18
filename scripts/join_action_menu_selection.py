from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from midfielders_eye.selection_labels import (
    join_selected_outcomes,
    selection_join_summary,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Join observed selected actions onto outcome-blinded action-menu ratings."
        )
    )
    parser.add_argument("annotations", type=Path)
    parser.add_argument("selections", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--allow-missing-frames",
        action="store_true",
        help="Permit annotated frames without a selection record.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    annotations = pd.read_csv(args.annotations)
    selections = pd.read_csv(args.selections)
    joined = join_selected_outcomes(
        annotations,
        selections,
        require_complete_frames=not args.allow_missing_frames,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    joined.to_csv(args.output, index=False)
    summary = selection_join_summary(joined)
    summary_path = args.output.with_suffix(".summary.json")
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {len(joined)} rows to {args.output}")
    print(summary_path)


if __name__ == "__main__":
    main()
