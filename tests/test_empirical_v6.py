from __future__ import annotations

import json
from pathlib import Path

import pytest

from midfielders_eye.empirical.adapters import (
    load_egoexo_gaze_csv,
    load_opencap_mot,
    load_statsbomb_empirical_bundle,
)
from midfielders_eye.empirical.downloads import AccessGateError, download_open_source, source_plan
from midfielders_eye.empirical.provenance import verify_file_manifest
from midfielders_eye.empirical.registry import load_source_registry
from midfielders_eye.empirical.schemas import EvidenceRecord, EvidenceTier, SignalModality
from midfielders_eye.empirical.showcase import build_empirical_showcase
from midfielders_eye.empirical.validation import ClaimBoundaryError, validate_claim


ROOT = Path(__file__).parents[1]
DATA = ROOT / "data" / "empirical"


def test_registry_declares_authoritative_modalities_and_access() -> None:
    registry = load_source_registry()
    assert len(registry.sources) == 12
    egoexo = registry.get("ego_exo4d")
    assert SignalModality.EYE_GAZE in egoexo.modalities
    assert not egoexo.can_auto_download
    assert registry.get("metrica_sample_data").can_auto_download


def test_gated_source_refuses_automatic_download(tmp_path: Path) -> None:
    with pytest.raises(AccessGateError):
        download_open_source("worldpose", tmp_path)
    plan = source_plan("worldpose")
    assert plan["automatic_download_permitted"] is False
    assert plan["required_human_steps"]


def test_source_pinned_manifests_verify() -> None:
    for path in (
        DATA / "open" / "metrica_game1_pass_1226" / "MANIFEST.json",
        DATA / "open" / "statsbomb_3857263_pedri" / "MANIFEST.json",
    ):
        assert verify_file_manifest(path) == []


def test_egoexo_gaze_adapter_preserves_direct_signal_source() -> None:
    samples = load_egoexo_gaze_csv(DATA / "templates" / "egoexo_gaze_template.csv")
    assert len(samples) == 2
    assert samples[0].timestamp_s == pytest.approx(1.0)
    assert samples[0].source == "ego_exo4d_personalized"
    assert samples[0].depth_m == pytest.approx(4.2)


def test_opencap_mot_adapter_reads_kinematics() -> None:
    frame = load_opencap_mot(DATA / "templates" / "opencap_kinematics_template.mot")
    assert list(frame.columns) == ["time", "pelvis_tilt", "pelvis_rotation", "knee_angle_r"]
    assert frame.iloc[-1]["knee_angle_r"] == pytest.approx(21.0)


def test_statsbomb_bundle_is_named_real_event_but_not_gaze() -> None:
    bundle = load_statsbomb_empirical_bundle(DATA / "open" / "statsbomb_3857263_pedri")
    event = bundle["event"]
    assert event["player"]["name"] == "Pedro González López"
    assert event["pass"]["recipient"]["name"] == "Aymeric Laporte"
    assert any(item["actor"] for item in bundle["three_sixty"]["freeze_frame"])
    source = json.loads((DATA / "open" / "statsbomb_3857263_pedri" / "SOURCE.json").read_text())
    assert "literal_gaze" in source["not_measured"]


def test_direct_claim_language_is_blocked_for_provider_tracking() -> None:
    record = EvidenceRecord(
        evidence_id="statsbomb-example",
        source_id="statsbomb_open_data",
        tier=EvidenceTier.PROVIDER_TRACKING,
        modalities=(SignalModality.EVENT_360,),
        subject_id="pedri",
        sequence_id="3857263",
        timestamp_start_s=70.618,
        timestamp_end_s=72.512,
        confidence=1.0,
        measured_fields=("event_location",),
        inferred_fields=("literal_gaze_direction",),
    )
    with pytest.raises(ClaimBoundaryError):
        validate_claim(record, {"literal_gaze_direction"})


def test_empirical_showcase_builds_real_source_artifacts(tmp_path: Path) -> None:
    manifest_path = build_empirical_showcase(tmp_path, data_root=DATA, render_dpi=100)
    manifest = json.loads(manifest_path.read_text())
    assert manifest["real_source_experiment_count"] == 2
    assert manifest["direct_gaze_downloaded"] is False
    assert (tmp_path / "FILE_MANIFEST.json").exists()
    assert verify_file_manifest(tmp_path / "FILE_MANIFEST.json") == []
    experiments = json.loads((tmp_path / "experiments.json").read_text())
    assert {item["source_id"] for item in experiments} == {"metrica_sample_data", "statsbomb_open_data"}
    from PIL import Image
    for relative in manifest["visuals"]:
        with Image.open(tmp_path / relative) as image:
            assert image.size == (1920, 1080)
