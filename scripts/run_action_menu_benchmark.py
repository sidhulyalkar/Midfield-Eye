from __future__ import annotations

import argparse
from dataclasses import fields, replace
from pathlib import Path

import yaml

from midfielders_eye.action_menu_benchmark import run_action_menu_benchmark
from midfielders_eye.frozen_benchmark import FrozenBenchmarkConfig


def _load_config(path: Path | None) -> FrozenBenchmarkConfig:
    if path is None:
        return FrozenBenchmarkConfig()
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    tuple_fields = {"protocols", "dynamic_eligible_providers", "b3_features"}
    allowed = {field.name for field in fields(FrozenBenchmarkConfig)}
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise ValueError(f"Unknown benchmark config fields: {unknown}")
    for key in tuple_fields:
        if key in payload:
            payload[key] = tuple(payload[key])
    return FrozenBenchmarkConfig(**payload)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the v0.7 B0/B1/B2/B2-V/B3 action-menu benchmark."
    )
    parser.add_argument("options", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--pilot-freeze", type=Path)
    parser.add_argument("--provider-quality-review", type=Path)
    parser.add_argument(
        "--synthetic-software-validation",
        action="store_true",
        help="Permit pseudo/synthetic labels only for software verification.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = _load_config(args.config)
    if args.synthetic_software_validation:
        config = replace(config, allow_synthetic_software_validation=True)
    manifest = run_action_menu_benchmark(
        args.options,
        args.output_dir,
        config=config,
        pilot_freeze_path=args.pilot_freeze,
        config_source_path=args.config,
        provider_quality_review_path=args.provider_quality_review,
    )
    print(manifest)


if __name__ == "__main__":
    main()
