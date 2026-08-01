from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from midfielders_eye.pilot import (
    build_adjudication_queue,
    build_consensus_labels,
    load_annotations,
    sha256_file,
)
from midfielders_eye.reliability import ReliabilityGate, reliability_report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate expert ratings, report agreement, and prepare adjudication."
    )
    parser.add_argument("annotations", type=Path, nargs="+")
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--decisions", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/pilot/reliability_report.json"),
    )
    parser.add_argument(
        "--queue",
        type=Path,
        default=Path("artifacts/pilot/adjudication_queue.csv"),
    )
    parser.add_argument(
        "--consensus-output",
        type=Path,
        default=Path("artifacts/pilot/consensus_labels.csv"),
    )
    parser.add_argument("--bootstrap-iterations", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--min-raters", type=int, default=2)
    parser.add_argument("--min-sequences", type=int, default=10)
    parser.add_argument("--min-overlap-frame-fraction", type=float, default=0.25)
    parser.add_argument("--min-overlap-items", type=int, default=20)
    parser.add_argument("--min-availability-alpha", type=float, default=0.60)
    parser.add_argument("--min-candidate-coverage", type=float, default=1.0)
    args = parser.parse_args()

    candidates = pd.read_csv(args.candidates)
    imported = load_annotations(
        args.annotations,
        candidates=candidates,
        require_genuine_human=False,
    )
    gate = ReliabilityGate(
        min_genuine_raters=args.min_raters,
        min_sequences=args.min_sequences,
        min_overlap_frame_fraction=args.min_overlap_frame_fraction,
        min_overlap_items=args.min_overlap_items,
        min_availability_alpha=args.min_availability_alpha,
        min_candidate_coverage=args.min_candidate_coverage,
    )
    report = reliability_report(
        imported.dataframe,
        candidates=candidates,
        gate=gate,
        bootstrap_iterations=args.bootstrap_iterations,
        seed=args.seed,
    )
    report["annotation_import"] = imported.report.to_dict()
    report["annotation_inputs"] = [
        {"path": str(path), "sha256": sha256_file(path)} for path in args.annotations
    ]
    report["candidate_input"] = {
        "path": str(args.candidates),
        "sha256": sha256_file(args.candidates),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")

    queue = build_adjudication_queue(
        imported.dataframe[imported.dataframe["is_genuine_human"]]
    )
    args.queue.parent.mkdir(parents=True, exist_ok=True)
    queue.to_csv(args.queue, index=False)
    consensus_path = None
    if args.decisions or queue.empty:
        decisions = pd.read_csv(args.decisions) if args.decisions else pd.DataFrame()
        consensus = build_consensus_labels(
            imported.dataframe,
            candidates,
            decisions,
            min_candidate_coverage=args.min_candidate_coverage,
        )
        args.consensus_output.parent.mkdir(parents=True, exist_ok=True)
        consensus.to_csv(args.consensus_output, index=False)
        consensus_path = str(args.consensus_output)
    print(
        json.dumps(
            {
                "status": report["status"],
                "report": str(args.output),
                "adjudication_queue": str(args.queue),
                "consensus_labels": consensus_path,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
