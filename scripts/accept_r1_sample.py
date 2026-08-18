from __future__ import annotations

import argparse
import json
from pathlib import Path

from midfielders_eye.r1_review import accept_r1_sample


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sign the prepared R1 sample without regenerating its candidate freeze."
    )
    parser.add_argument(
        "r1_dir",
        type=Path,
        nargs="?",
        default=Path("artifacts/r1"),
    )
    parser.add_argument("--reviewed-by", required=True)
    parser.add_argument("--rationale", required=True)
    args = parser.parse_args()

    review_path = accept_r1_sample(
        args.r1_dir,
        reviewed_by=args.reviewed_by,
        rationale=args.rationale,
    )
    print(json.dumps(json.loads(review_path.read_text(encoding="utf-8")), indent=2))


if __name__ == "__main__":
    main()
