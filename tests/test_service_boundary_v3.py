from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_gsr_service_is_dry_run_first_and_records_manifest(tmp_path: Path) -> None:
    repo = tmp_path / "sn-gamestate"
    repo.mkdir()
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"test-video")
    output = tmp_path / "run"
    script = Path(__file__).parents[1] / "services" / "video_perception" / "run_gsr.py"

    subprocess.run(
        [
            sys.executable,
            str(script),
            "--repo",
            str(repo),
            "--video",
            str(video),
            "--output-dir",
            str(output),
            "--dataset-version",
            "1.3",
            "--override",
            "example.key=value",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    manifest = json.loads((output / "perception_run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["executed"] is False
    assert manifest["command"][:4] == ["uv", "run", "tracklab", "-cn"]
    assert manifest["dataset_version"] == "1.3"
    assert manifest["overrides"] == ["example.key=value"]
    assert len(manifest["video_sha256"]) == 64


def test_gsr_service_does_not_import_upstream_packages() -> None:
    source = (
        Path(__file__).parents[1] / "services" / "video_perception" / "run_gsr.py"
    ).read_text(encoding="utf-8")
    assert "import tracklab" not in source
    assert "import sn_gamestate" not in source


def test_gsr_service_records_resolved_model_manifest(tmp_path: Path) -> None:
    repo = tmp_path / "sn-gamestate"
    repo.mkdir()
    output = tmp_path / "run"
    model_manifest = tmp_path / "models.json"
    model_manifest.write_text(
        json.dumps(
            {
                "sn_gamestate_commit": "a" * 40,
                "tracklab_version": "1.3.24",
                "dataset_version": "1.3",
                "models": {"detector": {"name": "example", "weights_sha256": "b" * 64}},
            }
        ),
        encoding="utf-8",
    )
    script = Path(__file__).parents[1] / "services" / "video_perception" / "run_gsr.py"
    subprocess.run(
        [
            sys.executable,
            str(script),
            "--repo",
            str(repo),
            "--output-dir",
            str(output),
            "--model-manifest",
            str(model_manifest),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    manifest = json.loads((output / "perception_run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["model_manifest"]["tracklab_version"] == "1.3.24"
    assert len(manifest["model_manifest_sha256"]) == 64
