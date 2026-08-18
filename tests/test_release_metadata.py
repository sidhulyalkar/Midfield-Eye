from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from midfielders_eye import __version__

ROOT = Path(__file__).parents[1]


def _project_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    project_section = text.split("[project]", 1)[1].split("[project.", 1)[0]
    match = re.search(r'^version\s*=\s*"([^"]+)"', project_section, re.MULTILINE)
    if match is None:
        raise AssertionError("pyproject.toml [project] version is missing")
    return match.group(1)


def test_release_version_is_consistent_across_public_metadata() -> None:
    citation = yaml.safe_load((ROOT / "CITATION.cff").read_text(encoding="utf-8"))
    integration = json.loads(
        (ROOT / "frontend_contract" / "integration-contract.json").read_text(
            encoding="utf-8"
        )
    )
    components = json.loads(
        (ROOT / "frontend_contract" / "component-contract.json").read_text(
            encoding="utf-8"
        )
    )
    openapi = json.loads(
        (ROOT / "frontend_contract" / "openapi.json").read_text(encoding="utf-8")
    )

    assert __version__ == "0.7.0"
    assert _project_version() == __version__
    assert citation["cff-version"] == "1.2.0"
    assert citation["version"] == __version__
    assert integration["version"] == __version__
    assert components["version"] == __version__
    assert openapi["info"]["version"] == __version__


def test_readme_and_release_notes_lead_with_v07() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    notes = (ROOT / "RELEASE_NOTES.md").read_text(encoding="utf-8")

    assert readme.startswith("# The Midfielder's Eye v0.7")
    assert "## v0.7.0 · The Action Menu Benchmark" in notes
