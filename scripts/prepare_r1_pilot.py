from __future__ import annotations

import argparse
import json
from pathlib import Path

from midfielders_eye.r1 import load_r1_config, prepare_real_pilot


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare the R1 real action-menu pilot: non-overlapping decision windows, "
            "5 Hz focal frames, frozen candidates, blinded exports, and double-rater assignments."
        )
    )
    parser.add_argument("frames", type=Path, help="Canonical continuous-tracking JSONL.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/r1"),
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/r1_real_pilot.yaml"),
    )
    parser.add_argument(
        "--rater",
        action="append",
        required=True,
        help="Stable expert annotator ID. Repeat for each rater; R1 requires at least two.",
    )
    parser.add_argument(
        "--reviewed-by",
        help=(
            "Researcher who reviewed and accepted the automatically proposed diversity sample. "
            "Omit to emit a pending-review package without an empirical readiness claim."
        ),
    )
    parser.add_argument(
        "--synthetic-software-validation",
        action="store_true",
        help="Allow synthetic providers only to exercise software. Never use for an empirical R1 claim.",
    )
    args = parser.parse_args()

    manifest = prepare_real_pilot(
        args.frames,
        args.output_dir,
        rater_ids=args.rater,
        reviewed_by=args.reviewed_by,
        config=load_r1_config(args.config),
        allow_synthetic_software_validation=args.synthetic_software_validation,
    )
    print(json.dumps(json.loads(manifest.read_text(encoding="utf-8")), indent=2))


if __name__ == "__main__":
    main()
