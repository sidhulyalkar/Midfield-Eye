import json
from pathlib import Path

import pytest

from midfielders_eye.showcase.media import MediaAsset, MediaManifest, load_media_manifest, write_media_manifest


def test_local_analysis_requires_rights_and_existing_file(tmp_path: Path):
    clip = tmp_path / "clip.mp4"
    clip.write_bytes(b"fixture")
    asset = MediaAsset(
        asset_id="owned-clip",
        title="Owned clip",
        player_ids=["pedri"],
        mode="local_analysis",
        local_path="clip.mp4",
        rights_status="owned",
    )
    manifest = MediaManifest(version=1, assets=[asset])
    path = write_media_manifest(manifest, tmp_path / "manifest.json")
    loaded = load_media_manifest(path)
    assert loaded.assets[0].asset_id == "owned-clip"


def test_unknown_rights_are_rejected(tmp_path: Path):
    clip = tmp_path / "clip.mp4"
    clip.write_bytes(b"fixture")
    payload = {
        "version": 1,
        "assets": [
            {
                "asset_id": "bad",
                "title": "Unknown rights",
                "player_ids": ["rodri"],
                "mode": "local_analysis",
                "local_path": "clip.mp4",
                "rights_status": "unknown"
            }
        ]
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="local analysis requires"):
        load_media_manifest(path)


def test_youtube_is_embed_only_and_cannot_have_downloaded_path():
    asset = MediaAsset(
        asset_id="youtube-test",
        title="Reference",
        player_ids=["michael-olise"],
        mode="youtube_embed",
        youtube_video_id="abc123",
        rights_status="embed_only",
        embeddable=True,
    )
    asset.validate()
    asset.local_path = "download.mp4"
    with pytest.raises(ValueError, match="cannot include"):
        asset.validate()
