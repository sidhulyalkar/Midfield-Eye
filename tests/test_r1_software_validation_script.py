from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_r1_software_validation_writes_non_empirical_claim_boundary(tmp_path: Path) -> None:
    output = tmp_path / "r1-sw"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_r1_software_validation.py",
            "--output-dir",
            str(output),
            "--sequences",
            "12",
            "--frames-per-sequence",
            "16",
            "--seed",
            "31",
            "--skip-benchmark",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr

    boundary_path = output / "CLAIM_BOUNDARY.json"
    assert boundary_path.exists()
    boundary = json.loads(boundary_path.read_text(encoding="utf-8"))
    assert boundary["empirical_claim_allowed"] is False
    assert boundary["schema"] == "midfielders-eye-claim-boundary-v1"

    status_path = output / "r1_status.json"
    assert status_path.exists()
    status = json.loads(status_path.read_text(encoding="utf-8"))
    assert status.get("benchmark", {}).get("complete") is not True
