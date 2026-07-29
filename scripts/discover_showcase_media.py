from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from midfielders_eye.showcase.media import MediaManifest, discover_youtube_videos, write_media_manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Discover embed-only player references through the official YouTube Data API."
    )
    parser.add_argument("--plan", type=Path, default=Path("data/showcase/media_discovery_plan.yaml"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/showcase/youtube_references.json"))
    parser.add_argument("--featured-only", action="store_true")
    parser.add_argument("--max-results-per-query", type=int, default=3)
    parser.add_argument("--creative-commons-only", action="store_true")
    parser.add_argument("--region-code", default="US")
    args = parser.parse_args()

    payload = yaml.safe_load(args.plan.read_text(encoding="utf-8"))
    assets = []
    seen = set()
    failures: list[dict[str, str]] = []
    for player in payload["players"]:
        if args.featured_only and not player.get("featured", False):
            continue
        for query in player["queries"]:
            try:
                results = discover_youtube_videos(
                    query,
                    max_results=args.max_results_per_query,
                    creative_commons_only=args.creative_commons_only,
                    region_code=args.region_code,
                )
            except Exception as exc:  # keep a resumable audit trail
                failures.append({"player_id": player["player_id"], "query": query, "error": str(exc)})
                continue
            for asset in results:
                if asset.youtube_video_id in seen:
                    continue
                seen.add(asset.youtube_video_id)
                asset.player_ids = [player["player_id"]]
                asset.metadata["discovery_query"] = query
                asset.metadata["analysis_allowed"] = False
                assets.append(asset)

    manifest = MediaManifest(version=1, assets=assets)
    write_media_manifest(manifest, args.output)
    audit = {
        "output": str(args.output),
        "assets": len(assets),
        "failures": failures,
        "policy": payload["policy"],
    }
    audit_path = args.output.with_suffix(".audit.json")
    audit_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
