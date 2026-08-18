from __future__ import annotations

import argparse
import json
from pathlib import Path

from midfielders_eye.r1 import build_r1_status


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Report R1 sample, annotation, reliability, and benchmark readiness."
    )
    parser.add_argument(
        "r1_dir",
        type=Path,
        nargs="?",
        default=Path("artifacts/r1"),
    )
    parser.add_argument(
        "--annotation",
        type=Path,
        action="append",
        default=[],
        help="Expert annotation CSV. Repeat as needed; otherwise r1_dir/annotations/*.csv is used.",
    )
    parser.add_argument("--bootstrap-iterations", type=int, default=250)
    parser.add_argument("--seed", type=int, default=17)
    args = parser.parse_args()

    payload = build_r1_status(
        args.r1_dir,
        annotation_paths=args.annotation or None,
        bootstrap_iterations=args.bootstrap_iterations,
        seed=args.seed,
    )
    print(json.dumps(payload, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
