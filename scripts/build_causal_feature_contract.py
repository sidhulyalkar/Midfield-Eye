from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

from midfielders_eye.pilot import (
    candidate_generator_source_records,
    sha256_file,
    validate_causal_feature_contract,
)
from midfielders_eye.affordance import AffordanceEngine

FORECAST_FEATURES = {
    "interception_margin_s",
    "future_space",
    "option_creation",
}
CAUSAL_HISTORY_FEATURES = {
    "target_motion_alignment",
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Create an explicit, reviewable timing declaration for frozen candidate features. "
            "This records a causal contract; it does not infer causality."
        )
    )
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument(
        "--benchmark-config",
        type=Path,
        default=Path("configs/benchmark_frozen_v1.yaml"),
    )
    parser.add_argument("--reviewed-by", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    candidates = pd.read_csv(args.candidates)
    config = yaml.safe_load(args.benchmark_config.read_text(encoding="utf-8")) or {}
    b3_features = list(config.get("b3_features", []))
    required_features = sorted(set(b3_features) | set(AffordanceEngine.feature_names))
    missing = sorted({"geometric_score", *required_features} - set(candidates.columns))
    if missing:
        raise SystemExit(f"Candidate table is missing contract features: {missing}")

    features = {}
    for feature in required_features:
        if feature in FORECAST_FEATURES:
            timing = "forecast_from_focal_state"
            justification = (
                "Computed as a forecast from the frozen focal state and causal kinematics; "
                "no later observed frame is read."
            )
        elif feature in CAUSAL_HISTORY_FEATURES:
            timing = "causal_history"
            justification = (
                "Uses focal state plus derivatives estimated only from timestamps at or before "
                "the focal frame."
            )
        else:
            timing = "focal_frame"
            justification = "Computed entirely from the frozen focal-frame state."
        features[feature] = {
            "timing": timing,
            "dependencies": [],
            "justification": justification,
        }
    features["geometric_score"] = {
        "timing": "derived_from_declared_causal_features",
        "dependencies": list(AffordanceEngine.feature_names),
        "justification": (
            "Frozen upstream score composed only from features declared in this contract."
        ),
    }
    payload = {
        "schema_version": "causal-feature-contract-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "reviewed_by": args.reviewed_by,
        "candidate_path": args.candidates.as_posix(),
        "candidate_sha256": sha256_file(args.candidates),
        "benchmark_config_path": args.benchmark_config.as_posix(),
        "benchmark_config_sha256": sha256_file(args.benchmark_config),
        "causality_scope": (
            "Contract validation only. This declaration does not empirically prove causality."
        ),
        "generator_sources": candidate_generator_source_records(),
        "features": features,
    }
    validate_causal_feature_contract(
        payload,
        candidate_sha256=payload["candidate_sha256"],
        required_features=b3_features,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    print(json.dumps({"contract": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
