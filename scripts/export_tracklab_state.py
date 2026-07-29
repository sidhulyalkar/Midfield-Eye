#!/usr/bin/env python3
"""Export a trusted local TrackLab pandas pickle to a portable tabular format."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_pickle", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    dataframe = pd.read_pickle(args.input_pickle)
    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame in the trusted pickle")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.suffix.lower() == ".csv":
        dataframe.to_csv(args.output, index=False)
    elif args.output.suffix.lower() in {".parquet", ".pq"}:
        dataframe.to_parquet(args.output, index=False)
    else:
        raise ValueError("Output must be .csv or .parquet")
    print(f"Wrote {len(dataframe)} rows to {args.output}")


if __name__ == "__main__":
    main()
