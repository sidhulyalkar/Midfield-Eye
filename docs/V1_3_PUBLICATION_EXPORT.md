# v1.3 Difference Figure Export

## Purpose

Export a paper-ready PNG/PDF from a fully specified evidence-aware comparison URL.

The exporter does not choose a frame, channel, temporal slice, threshold, or intervention for you. Those choices must already be encoded in the URL.

## 1. Build and serve the frontend

From `frontend/`:

```bash
npm run build
npm run preview -- --host 127.0.0.1
```

The default exporter expects the preview at:

```text
http://127.0.0.1:4173
```

To use another origin, set:

```bash
FIGURE_BASE_URL=http://127.0.0.1:PORT
```

## 2. Start from a canonical comparison URL

Example:

```text
/volume/compare?scenario=aitana-overload&fi=10&cmp=earlier-run&lead=0.75&dc=future_space&dq=low&dt=0.200&tm=slice&layer=2&pub=figure
```

Required publication state:

- route: `/volume/compare`
- `pub=figure`
- `cmp=earlier-run`
- `scenario=<non-empty scenario id>`
- `fi=<integer frame index>`
- `lead=0.50|0.75|1.00`
- `dc=future_space|option_creation`
- `dq=low|medium|high`
- `dt` within `[0.05, 0.65]` on the `0.025` retention grid
- `tm=slice`
- `layer=<integer>`

The exporter rejects malformed or fallback-dependent state.

## 3. Export

```bash
npm run export:difference-figure -- \
  --url '/volume/compare?scenario=aitana-overload&fi=10&cmp=earlier-run&lead=0.75&dc=future_space&dq=low&dt=0.200&tm=slice&layer=2&pub=figure'
```

Optional output directory:

```bash
npm run export:difference-figure -- \
  --url '<canonical publication URL>' \
  --output artifacts/paper-figures
```

## Outputs

For a figure ID such as:

```text
ME-DIFF-aitana-overload-f10-future-space-l2-lead075-qlow-t0200
```

the exporter writes:

```text
<figure-id>.png
<figure-id>.pdf
<figure-id>.json
```

### PNG

Captured directly from:

```text
[data-testid="difference-publication-plate"]
```

at a fixed `1600 × 1200` viewport with reduced motion.

### PDF

Rendered with print media and the publication print stylesheet.

### JSON manifest

Records:

- figure ID;
- exact source URL;
- fixed viewport;
- output paths;
- generation timestamp;
- publication claim boundary.

## Reproducibility guard

After navigation, the exporter checks:

```text
page.url() === requested canonical URL
```

If application code rewrites the scientific URL, export fails rather than silently producing a figure from changed state.

## Scientific boundary

The current showcase comparison is illustrative/synthetic.

The publication plate visibly carries the baseline source evidence status and states:

- Condition B is a synthetic teaching intervention;
- `B - A` exists only on retained intersection;
- `not_retained ≠ 0`;
- missing support is not interpolated;
- candidate options included: false;
- candidate options regenerated: false;
- future observed frames used: false;
- supported comparison channels are state-derived Future Space / Option Creation only.

A publication-quality visual does not convert synthetic evidence into empirical evidence.

## CI / Actions note

GitHub Actions is not the current release gate because quota is unavailable.

The export script and browser contracts are checked into the repository, but this document must not be read as a claim that the full repository Actions matrix executed successfully.
