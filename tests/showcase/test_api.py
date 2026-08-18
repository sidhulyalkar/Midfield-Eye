from pathlib import Path

import pytest

from midfielders_eye import __version__
from midfielders_eye.showcase.export import build_showcase_bundle

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from midfielders_eye.showcase.api import create_app  # noqa: E402


def test_showcase_api_serves_static_bundle(tmp_path: Path):
    bundle = tmp_path / "showcase"
    build_showcase_bundle(bundle, scenario_ids=["rodri-pivot"], frame_count=8, render_dpi=60)
    client = TestClient(create_app(bundle))
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["bundle_version"] == __version__
    assert client.get("/api/showcase/manifest").json()["scenario_count"] == 1
    assert len(client.get("/api/players").json()["players"]) == 100
    assert client.get("/api/scenarios/rodri-pivot").status_code == 200

    assert client.get("/api/atlas").status_code == 200
    assert client.get("/api/archetypes").status_code == 200
    frames = client.get("/api/scenarios/rodri-pivot/frames")
    assert frames.status_code == 200
    assert len(frames.json()) == 8
    assert client.get("/api/scenarios/rodri-pivot/gaze").status_code == 200
    assert client.get("/api/scenarios/rodri-pivot/body-mechanics").status_code == 200
    assert client.get("/api/scenarios/rodri-pivot/relational-control").status_code == 200
    assert client.get("/api/players/rodri/profile-card").status_code == 200
