from __future__ import annotations

import argparse
import json
from pathlib import Path

from midfielders_eye.r1_finalize import finalize_r1_pilot


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Finalize R1 from expert ratings. The command stops cleanly at failed reliability, "
            "unresolved adjudication, or missing provider review instead of weakening a gate."
        )
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
        required=True,
        help="Expert annotation CSV. Repeat for each rater.",
    )
    parser.add_argument("--reviewed-by", required=True)
    parser.add_argument(
        "--adjudication",
        type=Path,
        help="Completed adjudication CSV when the generated queue is non-empty.",
    )
    parser.add_argument(
        "--benchmark-config",
        type=Path,
        default=Path("configs/r1_benchmark.yaml"),
    )
    parser.add_argument(
        "--provider-review-config",
        type=Path,
        help=(
            "Human-signed provider quality config. Omit to freeze expert labels and stop before benchmarking."
        ),
    )
    parser.add_argument("--bootstrap-iterations", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument(
        "--no-benchmark",
        action="store_true",
        help="Stop after expert freeze and provider-quality review.",
    )
    args = parser.parse_args()

    status_path = finalize_r1_pilot(
        args.r1_dir,
        args.annotation,
        reviewed_by=args.reviewed_by,
        adjudication_path=args.adjudication,
        benchmark_config_path=args.benchmark_config,
        provider_review_config_path=args.provider_review_config,
        bootstrap_iterations=args.bootstrap_iterations,
        seed=args.seed,
        run_benchmark=not args.no_benchmark,
    )
    print(json.dumps(json.loads(status_path.read_text(encoding="utf-8")), indent=2))


if __name__ == "__main__":
    main()
