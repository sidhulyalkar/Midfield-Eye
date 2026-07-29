from __future__ import annotations

import hashlib
import json
import os
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

MediaMode = Literal["local_analysis", "youtube_embed", "external_link"]
RightsStatus = Literal[
    "owned",
    "licensed",
    "public_domain",
    "creative_commons",
    "embed_only",
    "unknown",
]


@dataclass(slots=True)
class MediaAsset:
    asset_id: str
    title: str
    player_ids: list[str]
    mode: MediaMode
    source_url: str | None = None
    local_path: str | None = None
    youtube_video_id: str | None = None
    rights_status: RightsStatus = "unknown"
    license_name: str | None = None
    rights_evidence: str | None = None
    start_s: float | None = None
    end_s: float | None = None
    embeddable: bool | None = None
    content_hash: str | None = None
    notes: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self, root: str | Path | None = None) -> None:
        if not self.asset_id.strip():
            raise ValueError("asset_id is required")
        if not self.player_ids:
            raise ValueError(f"{self.asset_id}: player_ids cannot be empty")
        if self.start_s is not None and self.start_s < 0:
            raise ValueError(f"{self.asset_id}: start_s cannot be negative")
        if self.end_s is not None and self.start_s is not None and self.end_s <= self.start_s:
            raise ValueError(f"{self.asset_id}: end_s must be after start_s")
        if self.mode == "local_analysis":
            if self.rights_status not in {"owned", "licensed", "public_domain", "creative_commons"}:
                raise ValueError(
                    f"{self.asset_id}: local analysis requires owned, licensed, public-domain, or Creative Commons rights"
                )
            if not self.local_path:
                raise ValueError(f"{self.asset_id}: local_analysis requires local_path")
            candidate = Path(root or ".") / self.local_path
            if not candidate.exists():
                raise ValueError(f"{self.asset_id}: local file does not exist: {candidate}")
        elif self.mode == "youtube_embed":
            if self.rights_status != "embed_only":
                raise ValueError(f"{self.asset_id}: YouTube assets must be embed_only")
            if not self.youtube_video_id:
                raise ValueError(f"{self.asset_id}: youtube_embed requires youtube_video_id")
            if self.embeddable is False:
                raise ValueError(f"{self.asset_id}: video is not embeddable")
            if self.local_path:
                raise ValueError(f"{self.asset_id}: YouTube embed entries cannot include a downloaded local_path")
        elif self.mode == "external_link" and not self.source_url:
            raise ValueError(f"{self.asset_id}: external_link requires source_url")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class MediaManifest:
    version: int
    assets: list[MediaAsset]
    policy: str = "analyze only rights-cleared local media; embed YouTube without downloading"

    def validate(self, root: str | Path | None = None) -> None:
        ids = [asset.asset_id for asset in self.assets]
        if len(ids) != len(set(ids)):
            raise ValueError("media asset IDs must be unique")
        for asset in self.assets:
            asset.validate(root)

    def to_dict(self) -> dict[str, Any]:
        return {"version": self.version, "policy": self.policy, "assets": [asset.to_dict() for asset in self.assets]}


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_media_manifest(path: str | Path, *, validate: bool = True) -> MediaManifest:
    manifest_path = Path(path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = MediaManifest(
        version=int(payload.get("version", 1)),
        policy=str(payload.get("policy", "")),
        assets=[MediaAsset(**row) for row in payload.get("assets", [])],
    )
    if validate:
        manifest.validate(manifest_path.parent)
    return manifest


def write_media_manifest(manifest: MediaManifest, path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")
    return output


def create_media_template(path: str | Path) -> Path:
    template = {
        "version": 1,
        "policy": "analyze only rights-cleared local media; embed YouTube without downloading",
        "assets": [],
        "examples": [
            {
                "asset_id": "replace-me-local",
                "title": "Rights-cleared tactical clip",
                "player_ids": ["michael-olise"],
                "mode": "local_analysis",
                "local_path": "media/replace-me.mp4",
                "rights_status": "owned",
                "license_name": "Owner supplied",
                "rights_evidence": "media/replace-me-rights.txt",
                "start_s": 0.0,
                "end_s": 12.0
            },
            {
                "asset_id": "replace-me-youtube",
                "title": "Official channel reference clip",
                "player_ids": ["pedri"],
                "mode": "youtube_embed",
                "youtube_video_id": "REPLACE_ME",
                "source_url": "https://www.youtube.com/watch?v=REPLACE_ME",
                "rights_status": "embed_only",
                "embeddable": True,
                "notes": "Reference playback only. Do not download or analyze pixels from this entry."
            }
        ]
    }
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(template, indent=2), encoding="utf-8")
    return output


def discover_youtube_videos(
    query: str,
    *,
    api_key: str | None = None,
    max_results: int = 10,
    creative_commons_only: bool = False,
    region_code: str = "US",
) -> list[MediaAsset]:
    """Discover embeddable YouTube references through the official Data API.

    This function retrieves metadata and IDs only. It never downloads audiovisual content.
    Returned assets are always marked ``embed_only`` even when a Creative Commons filter is used;
    rights for pixel-level model analysis must be established separately.
    """
    key = api_key or os.environ.get("YOUTUBE_API_KEY")
    if not key:
        raise RuntimeError("Set YOUTUBE_API_KEY or pass api_key explicitly")
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": str(max(1, min(max_results, 50))),
        "videoEmbeddable": "true",
        "videoSyndicated": "true",
        "videoDefinition": "high",
        "regionCode": region_code,
        "key": key,
    }
    if creative_commons_only:
        params["videoLicense"] = "creativeCommon"
    search_url = "https://www.googleapis.com/youtube/v3/search?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(search_url, timeout=30) as response:  # noqa: S310 - fixed API host
        search_payload = json.load(response)
    video_ids = [item["id"]["videoId"] for item in search_payload.get("items", []) if item.get("id", {}).get("videoId")]
    if not video_ids:
        return []
    details_params = {
        "part": "snippet,status,contentDetails",
        "id": ",".join(video_ids),
        "key": key,
    }
    details_url = "https://www.googleapis.com/youtube/v3/videos?" + urllib.parse.urlencode(details_params)
    with urllib.request.urlopen(details_url, timeout=30) as response:  # noqa: S310 - fixed API host
        details_payload = json.load(response)
    assets: list[MediaAsset] = []
    for item in details_payload.get("items", []):
        video_id = str(item["id"])
        snippet = item.get("snippet", {})
        status = item.get("status", {})
        if not status.get("embeddable", False):
            continue
        assets.append(
            MediaAsset(
                asset_id=f"youtube-{video_id}",
                title=str(snippet.get("title", video_id)),
                player_ids=[],
                mode="youtube_embed",
                source_url=f"https://www.youtube.com/watch?v={video_id}",
                youtube_video_id=video_id,
                rights_status="embed_only",
                license_name=str(status.get("license", "youtube")),
                embeddable=True,
                metadata={
                    "channel_id": snippet.get("channelId"),
                    "channel_title": snippet.get("channelTitle"),
                    "published_at": snippet.get("publishedAt"),
                    "duration": item.get("contentDetails", {}).get("duration"),
                    "query": query,
                },
            )
        )
    return assets
