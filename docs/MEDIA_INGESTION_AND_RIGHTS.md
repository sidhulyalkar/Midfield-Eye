# Media Ingestion, Discovery, and Rights

## Non-negotiable boundary

The repository does not scrape or download highlight videos from YouTube, social platforms, broadcasters, or club sites.

It supports two separate lanes.

## Lane A: rights-cleared local analysis

Allowed rights states:

- `owned`
- `licensed`
- `public_domain`
- `creative_commons`

Every local asset must include:

- Stable asset ID
- Local path
- Player IDs
- Rights status
- License name
- Rights evidence path or reference
- Start and end times
- File hash before production analysis

Use:

```bash
midfielders-eye media-template --output data/showcase/media_manifest.json
midfielders-eye media-validate data/showcase/media_manifest.json
```

The validator rejects local analysis assets marked `unknown` or `embed_only`.

## Lane B: YouTube embed-only references

The official YouTube Data API may be used to discover videos and retrieve metadata. The application must:

- Filter for embeddable and syndicated videos
- Use the standard YouTube iframe player
- Preserve title, channel, branding, controls, and ads
- Avoid overlays over the player
- Avoid downloads or separated audio/video
- Provide independent tactical value in an adjacent panel
- Revalidate metadata and availability as needed

Discovery command:

```bash
export YOUTUBE_API_KEY=...
midfielders-eye youtube-discover \
  "Michael Olise official highlights" \
  --player-id michael-olise \
  --output artifacts/olise_youtube_references.json
```

This stores metadata and video IDs only. It does not download footage.

Batch discovery for the full 25-player candidate library:

```bash
export YOUTUBE_API_KEY=...
python scripts/discover_showcase_media.py --featured-only
python scripts/discover_showcase_media.py --max-results-per-query 3
```

The versioned query plan is `data/showcase/media_discovery_plan.yaml`. Every discovered asset is marked `embed_only` and `analysis_allowed=false` until separate rights are documented.

Official policy references:

- https://developers.google.com/youtube/v3/getting-started
- https://developers.google.com/youtube/v3/docs/search/list
- https://developers.google.com/youtube/terms/developer-policies-guide
- https://developers.google.com/youtube/terms/required-minimum-functionality

YouTube policy changes in 2026 added further conditions around derived metrics and data storage for audited analytics use cases. Do not build player-performance scores from YouTube API metadata. Consult current terms and seek an API compliance audit before production analytics that depend on API data.

## Recommended acquisition strategy

1. Begin with Metrica, SkillCorner open data, StatsBomb 360, Sportec open data, SoccerTrack, and SoccerNet under their respective terms.
2. Add your own or explicitly licensed match clips.
3. Ask clubs, academies, analysts, or players for permission to use selected sequences.
4. Use public embeds as qualitative reference only.
5. Store a rights manifest beside every published analysis.

## Privacy and identity

Do not process youth footage without appropriate consent and governance. Do not infer sensitive personal attributes. Player identity should be used only for the football-analysis purpose described by the project.

## Frontend rule

A YouTube player and tactical overlay may be synchronized side by side, but the overlay must not be placed on top of the YouTube iframe. For rights-cleared local files, the application may display a separate calibrated overlay canvas while preserving the original video.
