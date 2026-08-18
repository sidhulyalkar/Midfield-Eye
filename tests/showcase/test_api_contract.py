import json
from pathlib import Path

from midfielders_eye import __version__
from midfielders_eye.showcase.openapi import write_frontend_contract

ROOT = Path(__file__).parents[2]


def test_openapi_contract_contains_core_routes(tmp_path: Path):
    path = write_frontend_contract(tmp_path / "openapi.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert "/api/showcase/manifest" in payload["paths"]
    assert "/api/analyze-frame" in payload["paths"]
    assert "/api/atlas" in payload["paths"]
    assert "/api/scenarios/{scenario_id}/frames" in payload["paths"]
    assert "/api/scenarios/{scenario_id}/gaze" in payload["paths"]
    assert payload["info"]["version"] == __version__


def test_checked_in_frontend_contracts_are_synchronized_and_evidence_aware(tmp_path: Path):
    generated = json.loads(write_frontend_contract(tmp_path / "openapi.json").read_text(encoding="utf-8"))
    checked_in = json.loads(
        (ROOT / "frontend_contract" / "openapi.json").read_text(encoding="utf-8")
    )
    assert checked_in == generated

    integration = json.loads(
        (ROOT / "frontend_contract" / "integration-contract.json").read_text(encoding="utf-8")
    )
    assert integration["version"] == __version__
    assert integration["resources"]["frames"]["api"] == "GET /api/scenarios/{scenario_id}/frames"
    assert integration["scoreSemantics"]["null"] == "missing_not_zero"
    assert integration["scoreSemantics"]["action_menu_birth_extinction"] == (
        "retrospective_visualization_label_not_causal_feature"
    )
    assert integration["qualityGates"]["staticApiDomainParity"] is True
    assert integration["qualityGates"]["stableOptionIdentityTests"] is True

    components = json.loads(
        (ROOT / "frontend_contract" / "component-contract.json").read_text(encoding="utf-8")
    )
    assert components["version"] == __version__
    assert "missing_signal" in components["global"]["requiredStates"]
    assert "SynchronizedTimeline" in components["components"]
    assert "ActionMenuRibbon" in components["components"]
    assert "DecisionMicroscope" in components["components"]

    tokens = json.loads(
        (ROOT / "frontend_contract" / "design-tokens.json").read_text(encoding="utf-8")
    )
    assert tokens["evidenceStyles"]["synthetic"]["watermark"] is True
    assert tokens["motion"]["autoplayWhenReducedMotion"] is False
