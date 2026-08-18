from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

from .r1 import build_r1_status, protocol_ready_showcase_payload


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _set_step(payload: dict[str, Any], step_id: str, complete: bool, detail: str | None = None) -> None:
    for step in payload["evidence_ladder"]:
        if step["id"] == step_id:
            step["complete"] = bool(complete)
            if detail is not None:
                step["detail"] = detail
            return


def build_r1_showcase_status(
    r1_dir: str | Path | None = None,
    *,
    annotation_paths: Sequence[str | Path] | None = None,
) -> dict[str, Any]:
    if r1_dir is None:
        return protocol_ready_showcase_payload()
    root = Path(r1_dir)
    payload = build_r1_status(root, annotation_paths=annotation_paths)
    finalization_path = root / "r1_finalization_status.json"
    if not finalization_path.exists():
        return payload

    finalization = _load_json(finalization_path)
    allowed_stages = {
        "reliability_not_established",
        "needs_adjudication",
        "expert_pilot_frozen_needs_provider_review",
        "benchmark_ready",
        "benchmark_complete",
    }
    stage = str(finalization.get("stage", payload["stage"]))
    if stage in allowed_stages:
        payload["stage"] = stage
    payload["claim_state"] = finalization.get("claim_state", payload["claim_state"])

    reliability_path = root / "reliability_report.json"
    reliability = _load_json(reliability_path) if reliability_path.exists() else None
    if reliability is not None:
        payload["reliability"] = reliability
        import_report = reliability.get("annotation_import", {})
        payload["annotation"]["progress"] = {
            "files": len(reliability.get("annotation_inputs", [])),
            "candidate_coverage": import_report.get("candidate_coverage", 0.0),
            "annotators": import_report.get("annotators", 0),
            "rows": import_report.get("rows", 0),
            "genuine_human_rows": import_report.get("genuine_human_rows", 0),
        }
        _set_step(
            payload,
            "annotation",
            import_report.get("candidate_coverage") == 1.0
            and int(import_report.get("annotators", 0)) >= 2,
            "Full candidate coverage from at least two genuine expert raters."
            if import_report.get("candidate_coverage") == 1.0
            else "Expert annotation is incomplete.",
        )
        _set_step(
            payload,
            "reliability",
            bool(reliability.get("established")),
            "Frozen reliability gate established."
            if reliability.get("established")
            else "Reliability gate did not establish the annotation target.",
        )

    _set_step(payload, "sample", True, "Human-reviewed, non-overlapping R1 sample frozen.")
    benchmark_complete = stage == "benchmark_complete"
    _set_step(
        payload,
        "benchmark",
        benchmark_complete,
        "Frozen sequence-held-out B0/B1/B2/B2-V/B3 benchmark complete."
        if benchmark_complete
        else "Benchmark remains locked behind the earlier evidence gates.",
    )
    if benchmark_complete:
        metrics_path = root / "benchmark" / "metrics.csv"
        if metrics_path.exists():
            from .r1 import _read_metrics_summary

            payload["benchmark"] = {
                "complete": True,
                "metrics": _read_metrics_summary(metrics_path),
            }
    else:
        payload["benchmark"] = {"complete": False, "metrics": {}}
    return payload


def write_r1_showcase_status(
    output_path: str | Path,
    *,
    r1_dir: str | Path | None = None,
    annotation_paths: Sequence[str | Path] | None = None,
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            build_r1_showcase_status(r1_dir, annotation_paths=annotation_paths),
            indent=2,
            allow_nan=False,
        ),
        encoding="utf-8",
    )
    return output
