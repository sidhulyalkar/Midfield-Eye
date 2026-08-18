from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .pilot import sha256_file


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")
    return path


def accept_r1_sample(
    r1_dir: str | Path,
    *,
    reviewed_by: str,
    rationale: str,
) -> Path:
    """Sign an already prepared R1 sample without regenerating candidates."""

    root = Path(r1_dir)
    manifest_path = root / "r1_manifest.json"
    sample_plan_path = root / "sample_plan.csv"
    freeze_path = root / "pilot_candidates_freeze.json"
    for path in (manifest_path, sample_plan_path, freeze_path):
        if not path.exists():
            raise FileNotFoundError(path)
    reviewer = reviewed_by.strip()
    reason = rationale.strip()
    if not reviewer:
        raise ValueError("R1 sample acceptance requires a reviewer")
    if not reason:
        raise ValueError("R1 sample acceptance requires a rationale")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("stage") == "sample_frozen":
        raise ValueError("R1 sample has already been accepted")
    if manifest.get("stage") != "needs_sequence_review":
        raise ValueError(
            f"R1 sample cannot be accepted from stage {manifest.get('stage')!r}"
        )
    sample_plan = pd.read_csv(sample_plan_path)
    if len(sample_plan) != int(manifest["config"]["target_sequences"]):
        raise ValueError("R1 sample plan no longer matches the frozen target size")
    if sample_plan["sequence_id"].duplicated().any():
        raise ValueError("R1 sample plan contains duplicate sequences")

    review_path = root / "sample_review.json"
    if review_path.exists():
        raise FileExistsError(f"Refusing to overwrite R1 sample review: {review_path}")
    review = {
        "schema_version": "r1-sample-review-v1",
        "decision": "accept",
        "reviewed_by": reviewer,
        "rationale": reason,
        "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
        "manifest_sha256_before_review": sha256_file(manifest_path),
        "sample_plan_sha256": sha256_file(sample_plan_path),
        "candidate_freeze_sha256": sha256_file(freeze_path),
        "selected_sequences": sample_plan["sequence_id"].astype(str).tolist(),
    }
    _write_json(review_path, review)

    sample_plan["reviewed_by"] = reviewer
    sample_plan["review_status"] = "accepted_for_pilot"
    sample_plan.to_csv(sample_plan_path, index=False)
    manifest["stage"] = "sample_frozen"
    manifest["reviewed_by"] = reviewer
    manifest["sample_review"] = {
        "path": str(review_path),
        "sha256": sha256_file(review_path),
        "decision": "accept",
    }
    _write_json(manifest_path, manifest)
    return review_path
