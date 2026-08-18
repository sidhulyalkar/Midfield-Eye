from __future__ import annotations

import argparse
import json
from pathlib import Path

from midfielders_eye.r1_metrica import prepare_metrica_receipt_source


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build an R1-ready Metrica source from synchronized home/away tracking and PASS events. "
            "Carrier state is event-supported rather than nearest-player inferred."
        )
    )
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--away", type=Path, required=True)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--match-id", required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/r1/metrica_receipt_source.jsonl"),
    )
    parser.add_argument("--pre-context-s", type=float, default=1.6)
    parser.add_argument("--post-receipt-s", type=float, default=1.6)
    parser.add_argument("--minimum-control-s", type=float, default=0.45)
    parser.add_argument("--max-ball-carrier-distance-m", type=float, default=3.5)
    args = parser.parse_args()

    report = prepare_metrica_receipt_source(
        args.home,
        args.away,
        args.events,
        args.output,
        match_id=args.match_id,
        pre_context_s=args.pre_context_s,
        post_receipt_s=args.post_receipt_s,
        minimum_control_s=args.minimum_control_s,
        max_ball_carrier_distance_m=args.max_ball_carrier_distance_m,
    )
    print(json.dumps({"output": str(args.output), **report.to_dict()}, indent=2))


if __name__ == "__main__":
    main()
