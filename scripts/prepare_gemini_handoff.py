from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from midfielders_eye.showcase import build_showcase_bundle
from midfielders_eye.showcase.openapi import write_frontend_contract


REPO_ROOT = Path(__file__).resolve().parents[1]
HANDOFF_DOCS = (
    "GEMINI_MASTER_PROMPT.md",
    "INTEGRATED_DELIVERY_PLAN.md",
    "GEMINI_FRONTEND_IMPLEMENTATION_BLUEPRINT.md",
    "GEMINI_AI_STUDIO_BUILD_SPEC.md",
    "100_PLAYER_ATLAS.md",
    "GAZE_AND_BODY_MECHANICS.md",
    "RELATIONAL_CONTROL.md",
    "V6_FRONTEND_EXPERIENCE.md",
    "EMPIRICAL_DATA_STRATEGY.md",
    "EMPIRICAL_CLAIM_CONTRACT.md",
    "GAZE_ACQUISITION_PROTOCOL.md",
    "BIOMECHANICS_CAPTURE_PROTOCOL.md",
    "DATA_SOURCES_AND_CITATIONS.md",
    "MEDIA_INGESTION_AND_RIGHTS.md",
)
CONTRACT_FILES = (
    "design-tokens.json",
    "component-contract.json",
    "integration-contract.json",
    "openapi.json",
)


def _copy_handoff_docs(target: Path) -> list[str]:
    docs_target = target / "docs" / "midfielders-eye"
    docs_target.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for name in HANDOFF_DOCS:
        source = REPO_ROOT / "docs" / name
        if not source.exists():
            continue
        destination = docs_target / name
        shutil.copy2(source, destination)
        copied.append(str(destination.relative_to(target)))
    return copied


def prepare(target: Path, source: Path, rebuild: bool) -> dict[str, Any]:
    source = source if source.is_absolute() else REPO_ROOT / source
    target = target.resolve()
    if rebuild or not (source / "manifest.json").exists():
        build_showcase_bundle(source)

    public_showcase = target / "public" / "showcase"
    if public_showcase.exists():
        shutil.rmtree(public_showcase)
    public_showcase.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, public_showcase)

    contract_dir = target / "src" / "contracts"
    contract_dir.mkdir(parents=True, exist_ok=True)
    for name in CONTRACT_FILES:
        if name == "openapi.json":
            continue
        shutil.copy2(REPO_ROOT / "frontend_contract" / name, contract_dir / name)
    write_frontend_contract(contract_dir / "openapi.json")
    copied_docs = _copy_handoff_docs(target)

    manifest = json.loads((public_showcase / "manifest.json").read_text(encoding="utf-8"))
    result: dict[str, Any] = {
        "handoff_version": "0.6.0",
        "target": str(target),
        "showcase_files": sum(1 for path in public_showcase.rglob("*") if path.is_file()),
        "manifest": str((public_showcase / "manifest.json").relative_to(target)),
        "player_count": int(manifest.get("player_count", 0)),
        "scenario_count": int(manifest.get("scenario_count", 0)),
        "empirical_manifest": "public/showcase/empirical/manifest.json",
        "contracts": [
            str((contract_dir / name).relative_to(target))
            for name in CONTRACT_FILES
        ],
        "docs": copied_docs,
        "master_prompt": "docs/midfielders-eye/GEMINI_MASTER_PROMPT.md",
        "next_step": "Give Gemini repository access, then paste the copied master prompt verbatim.",
    }
    (target / "MIDFIELDERS_EYE_HANDOFF.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Copy the static Midfielder's Eye bundle into a generated frontend.")
    parser.add_argument("target", type=Path, help="Generated frontend repository root")
    parser.add_argument("--source", type=Path, default=Path("artifacts/showcase"))
    parser.add_argument("--rebuild", action="store_true")
    args = parser.parse_args()
    print(json.dumps(prepare(args.target, args.source, args.rebuild), indent=2))


if __name__ == "__main__":
    main()
