from __future__ import annotations

from pathlib import Path

import pytest

from midfielders_eye.empirical.showcase import build_empirical_showcase


ROOT = Path(__file__).parents[1]


def test_empirical_api_routes(tmp_path: Path) -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from midfielders_eye.showcase.api import create_app

    bundle = tmp_path / "showcase"
    build_empirical_showcase(bundle / "empirical", data_root=ROOT / "data" / "empirical", render_dpi=100)
    client = TestClient(create_app(bundle))
    assert client.get("/api/empirical").status_code == 200
    sources = client.get("/api/empirical/sources").json()
    assert len(sources["sources"]) == 12
    experiments = client.get("/api/empirical/experiments").json()
    assert len(experiments) == 2
    experiment = client.get(f"/api/empirical/experiments/{experiments[0]['id']}")
    assert experiment.status_code == 200
    assert client.get("/api/empirical/claim-contract").status_code == 200
    alignment = client.get("/api/empirical/alignment-contract")
    assert alignment.status_code == 200
    assert alignment.json()["minimum_anchor_count"] == 2
    capture = client.get("/api/capture-protocol/default")
    assert capture.status_code == 200
    assert capture.json()["valid"] is True
    validation = client.post("/api/capture-protocol/validate", json=capture.json()["protocol"])
    assert validation.status_code == 200
    assert validation.json()["valid"] is True
