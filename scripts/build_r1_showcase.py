from __future__ import annotations

import argparse
import json
from pathlib import Path

from midfielders_eye.r1_showcase import write_r1_showcase_status


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the evidence-aware R1 frontend payload without inventing missing results."
    )
    parser.add_argument(
        "--r1-dir",
        type=Path,
        help="Prepared R1 directory. Omit to emit the honest protocol-ready state.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/showcase/pilot/index.json"),
    )
    parser.add_argument(
        "--annotation",
        type=Path,
        action="append",
        default=[],
    )
    args = parser.parse_args()

    output = write_r1_showcase_status(
        args.output,
        r1_dir=args.r1_dir,
        annotation_paths=args.annotation or None,
    )
    print(json.dumps(json.loads(output.read_text(encoding="utf-8")), indent=2))


if __name__ == "__main__":
    main()
