from __future__ import annotations

import argparse
import json
from pathlib import Path

from midfielders_eye.pilot import freeze_pilot, verify_pilot_freeze


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Freeze canonical pilot sequences, candidates, and genuine expert labels."
    )
    parser.add_argument("--frames", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--annotations", type=Path, nargs="*", default=[])
    parser.add_argument(
        "--protocol",
        type=Path,
        default=Path("docs/ANNOTATION_GUIDE.md"),
    )
    parser.add_argument("--reliability-report", type=Path)
    parser.add_argument("--adjudication-decisions", type=Path)
    parser.add_argument("--consensus-labels", type=Path)
    parser.add_argument("--causal-feature-contract", type=Path)
    parser.add_argument("--benchmark-config", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/pilot/pilot_freeze.json"),
    )
    args = parser.parse_args()

    manifest = freeze_pilot(
        frames_path=args.frames,
        candidates_path=args.candidates,
        annotation_paths=args.annotations,
        protocol_path=args.protocol,
        reliability_report_path=args.reliability_report,
        adjudication_path=args.adjudication_decisions,
        consensus_path=args.consensus_labels,
        causal_feature_contract_path=args.causal_feature_contract,
        benchmark_config_path=args.benchmark_config,
        output_path=args.output,
    )
    failures = verify_pilot_freeze(manifest)
    if failures:
        raise SystemExit(json.dumps({"valid": False, "failures": failures}, indent=2))
    print(json.dumps({"valid": True, "manifest": str(manifest)}, indent=2))


if __name__ == "__main__":
    main()
