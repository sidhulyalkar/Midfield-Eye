from __future__ import annotations

import argparse
import json
from pathlib import Path

from midfielders_eye.provider_quality_review import build_provider_quality_review


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Freeze provider quality metrics and explicit pre-evaluation acceptance decisions."
        )
    )
    parser.add_argument("--pilot-freeze", type=Path, required=True)
    parser.add_argument(
        "--benchmark-config",
        type=Path,
        default=Path("configs/benchmark_frozen_v1.yaml"),
    )
    parser.add_argument("--review-config", type=Path, required=True)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    artifact = build_provider_quality_review(
        pilot_freeze_path=args.pilot_freeze,
        benchmark_config_path=args.benchmark_config,
        review_config_path=args.review_config,
        reviewer=args.reviewer,
        output_path=args.output,
    )
    print(json.dumps({"provider_quality_review": str(artifact)}, indent=2))


if __name__ == "__main__":
    main()
