"""Template for mapping an EgoTraj release into the repository's normalized CSV contract.

The exact upstream paths and field names should be confirmed against the downloaded release.
This script deliberately refuses to guess them. Edit `COLUMN_MAP` after inspecting one sequence.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

COLUMN_MAP = {
    # "upstream_timestamp": "timestamp_s",
    # "upstream_head_tx": "head_x",
    # Add the remaining fields described in docs/DATASETS.md.
}

REQUIRED = {
    "timestamp_s",
    "head_x",
    "head_y",
    "head_z",
    "quat_x",
    "quat_y",
    "quat_z",
    "quat_w",
    "gaze_origin_x",
    "gaze_origin_y",
    "gaze_origin_z",
    "gaze_dir_x",
    "gaze_dir_y",
    "gaze_dir_z",
}


def main(input_path: Path, output_path: Path) -> None:
    if not COLUMN_MAP:
        raise RuntimeError("Inspect the current EgoTraj release and fill COLUMN_MAP first")
    data = pd.read_csv(input_path).rename(columns=COLUMN_MAP)
    missing = sorted(REQUIRED - set(data.columns))
    if missing:
        raise ValueError(f"Missing normalized fields: {missing}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(output_path, index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    main(args.input, args.output)
