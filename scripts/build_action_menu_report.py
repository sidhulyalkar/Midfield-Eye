from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from midfielders_eye.action_menu import build_action_menu_tables


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build retrospective option lifecycle and action-menu timeline tables."
    )
    parser.add_argument("candidates", type=Path, help="Candidate-option CSV produced by the engine.")
    parser.add_argument("output_dir", type=Path, help="Directory for v0.7 action-menu outputs.")
    parser.add_argument("--score-column", default="geometric_score")
    parser.add_argument("--selection-column", default="label_selected")
    parser.add_argument("--top-k", type=int, default=3)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    candidates = pd.read_csv(args.candidates)
    lifecycles, timeline, summary = build_action_menu_tables(
        candidates,
        score_column=args.score_column,
        selection_column=args.selection_column,
        top_k=args.top_k,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    lifecycles.to_csv(args.output_dir / "option_lifecycles.csv", index=False)
    timeline.to_csv(args.output_dir / "action_menu_timeline.csv", index=False)
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"wrote {len(lifecycles)} lifecycles and {len(timeline)} timeline frames "
        f"to {args.output_dir}"
    )


if __name__ == "__main__":
    main()
