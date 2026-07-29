from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from midfielders_eye.frozen_benchmark import FrozenBenchmarkConfig, run_frozen_benchmark


def _load_config(path: Path) -> FrozenBenchmarkConfig:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if "protocols" in payload:
        payload["protocols"] = tuple(payload["protocols"])
    if "b3_features" in payload:
        payload["b3_features"] = tuple(payload["b3_features"])
    if "dynamic_eligible_providers" in payload:
        payload["dynamic_eligible_providers"] = tuple(
            payload["dynamic_eligible_providers"]
        )
    return FrozenBenchmarkConfig(**payload)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the frozen B0-B3 sequence/provider-held-out benchmark."
    )
    parser.add_argument("options", type=Path)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/benchmark_frozen_v1.yaml"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/benchmark/frozen_b0_b3"),
    )
    parser.add_argument("--pilot-freeze", type=Path)
    parser.add_argument("--provider-quality-review", type=Path)
    args = parser.parse_args()

    manifest = run_frozen_benchmark(
        args.options,
        args.output_dir,
        config=_load_config(args.config),
        pilot_freeze_path=args.pilot_freeze,
        config_source_path=args.config,
        provider_quality_review_path=args.provider_quality_review,
    )
    print(json.dumps({"manifest": str(manifest)}, indent=2))


if __name__ == "__main__":
    main()
