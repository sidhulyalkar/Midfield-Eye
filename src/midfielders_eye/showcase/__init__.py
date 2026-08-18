from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .catalog import PlayerCatalog, PlayerStudy, load_player_catalog
from .scenarios import SCENARIOS, ShowcaseScenario, build_scenario_frames, list_scenarios


def build_showcase_bundle(*args: Any, **kwargs: Any):
    """Build the showcase and attach the evidence-aware R1 research milestone.

    ``r1_dir`` is deliberately optional. Without it the bundle emits a
    protocol-ready pilot state with no empirical metrics. Supplying a prepared
    R1 directory upgrades the same frontend contract only when corresponding
    real artifacts exist.
    """

    from ..r1_showcase import write_r1_showcase_status
    from .export import build_showcase_bundle as _build

    r1_dir = kwargs.pop("r1_dir", None)
    manifest_path = _build(*args, **kwargs)
    root = Path(manifest_path).parent
    write_r1_showcase_status(root / "pilot" / "index.json", r1_dir=r1_dir)

    payload = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    payload["pilot_path"] = "pilot/index.json"
    payload["description"] = (
        "Frontend-ready perception atlas, source-pinned empirical evidence, "
        "the Action Menu Decision Microscope, and the R1 Real Action Menu Pilot."
    )
    payload.setdefault("evidence_contract", {})["r1_pilot"] = (
        "R1 metrics appear only when genuine expert reliability and benchmark "
        "artifacts exist; missing evidence remains explicitly incomplete."
    )
    payload.setdefault("frontend_contract", {})["research_milestone"] = (
        "R1 · Real Action Menu Pilot"
    )
    Path(manifest_path).write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )
    return manifest_path


__all__ = [
    "PlayerCatalog",
    "PlayerStudy",
    "SCENARIOS",
    "ShowcaseScenario",
    "build_scenario_frames",
    "build_showcase_bundle",
    "list_scenarios",
    "load_player_catalog",
]
