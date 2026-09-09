#!/usr/bin/env python3
"""End-to-end R1 *software* validation path.

This exercises sample discovery, candidate freeze, blinded exports, status
reporting, and optionally the action-menu benchmark ladder on synthetic
continuous tracking. It must never be published as an empirical R1 result.

Usage:
  python scripts/run_r1_software_validation.py
  python scripts/run_r1_software_validation.py --output-dir artifacts/r1-sw --skip-benchmark
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the full R1 software-validation pipeline on synthetic tracking. "
            "Never treat the output as an empirical action-menu claim."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/r1-sw"),
        help="Root directory for software-validation artifacts",
    )
    parser.add_argument(
        "--sequences",
        type=int,
        default=12,
        help="Synthetic sequences to generate (default 12 for reliable window discovery)",
    )
    parser.add_argument(
        "--frames-per-sequence",
        type=int,
        default=16,
        help="Frames per synthetic sequence",
    )
    parser.add_argument("--seed", type=int, default=31)
    parser.add_argument(
        "--skip-benchmark",
        action="store_true",
        help="Stop after pilot freeze + status (skip ladder run)",
    )
    args = parser.parse_args()

    from dataclasses import replace

    from midfielders_eye.affordance import AffordanceEngine
    from midfielders_eye.io import write_frames_jsonl, write_options_csv
    from midfielders_eye.r1 import (
        R1PilotConfig,
        build_r1_status,
        load_r1_config,
        prepare_real_pilot,
    )
    from midfielders_eye.r1_showcase import write_r1_showcase_status
    from midfielders_eye.synthetic import generate_dataset

    root = args.output_dir
    root.mkdir(parents=True, exist_ok=True)
    frames_path = root / "synthetic_frames.jsonl"
    pilot_dir = root / "pilot"

    print("[1/5] Generating synthetic continuous tracking (software validation only)...")
    frames = generate_dataset(
        sequences=args.sequences,
        frames=args.frames_per_sequence,
        seed=args.seed,
    )
    tagged = [
        replace(
            frame,
            source_provider="synthetic-software-validation",
            source_match_id=frame.source_match_id or f"sw-{frame.sequence_id}",
        )
        for frame in frames
    ]
    write_frames_jsonl(tagged, frames_path)
    print(f"  Wrote {len(tagged)} frames → {frames_path}")

    print("[2/5] Preparing R1 pilot package (allow_synthetic_software_validation=True)...")
    config_path = Path("configs/r1_real_pilot.yaml")
    config = load_r1_config(config_path if config_path.exists() else None)

    if args.sequences < config.target_sequences:
        scaled = max(2, min(args.sequences, 6))
        composition = {
            "central_pressure": max(1, scaled // 3),
            "transition": max(1, scaled // 4),
            "settled_possession": max(1, scaled // 4),
            "wide_overload": 0,
            "negative_control": 1 if scaled >= 4 else 0,
        }
        while sum(composition.values()) < scaled:
            composition["central_pressure"] += 1
        while sum(composition.values()) > scaled:
            for key in ("wide_overload", "settled_possession", "transition"):
                if composition[key] > 0:
                    composition[key] -= 1
                    break
        config = R1PilotConfig(
            target_sequences=scaled,
            label_hz=config.label_hz,
            pre_context_s=config.pre_context_s,
            label_duration_s=config.label_duration_s,
            minimum_control_s=min(config.minimum_control_s, 0.3),
            minimum_window_separation_s=config.minimum_window_separation_s,
            minimum_label_frames=max(2, config.minimum_label_frames - 1),
            seed=args.seed,
            require_continuous_tracking=True,
            require_full_double_rating=True,
            target_composition=composition,
        )
        config.validate()

    try:
        manifest_path = prepare_real_pilot(
            frames_path,
            pilot_dir,
            rater_ids=["sw_rater_a", "sw_rater_b"],
            reviewed_by=None,
            config=config,
            allow_synthetic_software_validation=True,
        )
    except Exception as exc:
        print(f"ERROR during prepare_real_pilot: {exc}", file=sys.stderr)
        print(
            "Hint: increase --sequences (default 12) or --frames-per-sequence.",
            file=sys.stderr,
        )
        return 1

    print(f"  Pilot package → {pilot_dir}")
    print(f"  Manifest → {manifest_path}")

    print("[3/5] Building R1 status payload (no invented metrics)...")
    status = build_r1_status(pilot_dir)
    status_path = root / "r1_status.json"
    status_path.write_text(json.dumps(status, indent=2, allow_nan=False), encoding="utf-8")
    print(f"  Stage: {status.get('stage', status.get('claim_state', 'unknown'))}")
    print(f"  Wrote {status_path}")

    showcase_out = root / "pilot_showcase.json"
    write_r1_showcase_status(showcase_out, r1_dir=pilot_dir)
    print(f"  Showcase status → {showcase_out}")

    _write_boundary(root)

    if args.skip_benchmark:
        print("[4/5] Skipping benchmark (--skip-benchmark)")
        print("[5/5] Software validation package ready (no empirical claim).")
        _print_summary(root, pilot_dir, status_path)
        return 0

    print("[4/5] Generating candidates and running software-validation ladder...")
    candidates_csv = pilot_dir / "pilot_candidates.csv"
    if not candidates_csv.exists():
        engine = AffordanceEngine()
        options = [option for frame in tagged for option in engine.generate(frame)]
        candidates_csv = root / "candidates.csv"
        write_options_csv(options, candidates_csv)

    benchmark_dir = root / "action-menu-benchmark"
    benchmark_dir.mkdir(parents=True, exist_ok=True)

    runner = Path("scripts/run_action_menu_benchmark.py")
    if runner.exists():
        import subprocess

        cmd = [
            sys.executable,
            str(runner),
            str(candidates_csv),
            str(benchmark_dir),
            "--synthetic-software-validation",
        ]
        config_bench = Path("configs/r1_benchmark.yaml")
        if config_bench.exists():
            cmd.extend(["--config", str(config_bench)])
        print(f"  Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=False)
        if result.returncode != 0:
            print(
                "  Warning: action-menu benchmark returned non-zero; "
                "status package still written without empirical claim.",
                file=sys.stderr,
            )
    else:
        print("  scripts/run_action_menu_benchmark.py not found; skipping ladder run.")

    print("[5/5] Software validation complete.")
    _print_summary(root, pilot_dir, status_path)
    return 0


def _write_boundary(root: Path) -> None:
    boundary = {
        "schema": "midfielders-eye-claim-boundary-v1",
        "empirical_claim_allowed": False,
        "reason": (
            "This package was produced with allow_synthetic_software_validation=True. "
            "It validates code paths, contracts, and status reporting only. "
            "It is not an R1 empirical result."
        ),
        "required_for_empirical_r1": [
            "real continuous-tracking source (e.g. Metrica receipt windows)",
            "reviewed non-overlapping sample freeze",
            "full double annotation by genuine experts",
            "reliability gate (availability α ≥ 0.60)",
            "signed provider-quality review",
            "sequence-held-out B0–B3 ladder with bootstrap intervals",
        ],
    }
    path = root / "CLAIM_BOUNDARY.json"
    path.write_text(json.dumps(boundary, indent=2), encoding="utf-8")
    print(f"  Claim boundary → {path}")


def _print_summary(root: Path, pilot_dir: Path, status_path: Path) -> None:
    print(
        json.dumps(
            {
                "claim": "software_validation_only",
                "empirical_claim_allowed": False,
                "output_dir": str(root),
                "pilot_dir": str(pilot_dir),
                "status": str(status_path),
                "claim_boundary": str(root / "CLAIM_BOUNDARY.json"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
