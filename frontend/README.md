# The Midfielder's Eye frontend

Evidence-aware React interface for the action-menu research system. The application renders the same
normalized domain objects from a generated static bundle or the FastAPI service.

## Requirements

- Node.js 22.22 or newer
- a generated showcase bundle in `../artifacts/showcase`

From the repository root, generate the bundle when needed:

```bash
midfielders-eye showcase-build
```

The frontend copies that generated output to the ignored `public/showcase/` directory before
development, builds, and end-to-end tests. No generated showcase artifact is committed.

## Run

```bash
cd frontend
npm install
npm run dev
```

Static mode is the default. To use the API, provide a non-empty absolute URL:

```bash
VITE_MIDFIELDERS_EYE_API_URL=http://localhost:8000 npm run dev
```

A configured API failure is surfaced; the application never silently falls back to static data.

## Quality checks

```bash
npm run typecheck
npm run lint
npm test
npm run build
npm run test:e2e -- --project=desktop
```

Playwright defines 390×844, 1440×900, 1920×1080, and 3840×2160 projects. Its deterministic captures
are written to the ignored `test-results/visuals/` directory.

When GitHub Actions quota is unavailable, do not treat the absence of a workflow run as a green matrix.
Use the scoped standalone/manual validation record documented in the active release PR.

## Implemented routes

- `/` — action-menu explanation and deterministic illustrative hero
- `/scenario/:scenarioId` — synchronized pitch, action rail, timeline, evidence, and URL state
- `/volume` — Temporal Affordance Volume with Full/Slice/Band temporal surgery, linked exact slice, forensic inspection, and citable URL/export state
- `/volume/compare` — v1.3 evidence-aware A/B Difference Volume; numerical `B - A` exists only on retained intersection, while A-only/B-only support remains categorical
- `/volume/compare?...&pub=figure` — v1.3 publication presentation of the same deterministic comparison state; requires exact `tm=slice&layer=<integer>`
- `/empirical` and `/empirical/experiments/:experimentId` — provider geometry, rights, provenance,
  missing signals, and 4K visual fallback
- `/atlas` — exactly 100 balanced, non-ranked hypothesis profiles with URL filters and comparison tray
- `/players/:playerId` and `/players/:playerId/perception` — editorial study and evidence-upgrade views
- `/gaze-lab`, `/body-mechanics`, `/orchestration`, `/perception-lab` — specialist visual laboratories
- `/method` and `/data-and-rights` — scientific gates and rights boundaries

## v1.3 Difference Volume

The first comparison experiment is deliberately limited to state-derived `future_space` and
`option_creation`. Condition B is a synthetic teaching intervention that places one feasible moving
off-ball teammate farther along their existing focal-state velocity. It is not an observed future or a
causal estimate.

The support algebra is frozen:

```text
intersection → delta = B.value - A.value
left_only    → delta = null
right_only   → delta = null
not_retained ≠ 0
```

The 3D workbench, linked top-down slice, forensic inspector, JSON export, and publication plate all
preserve this boundary. Candidate options are currently omitted on both sides; Action Menu / Passing
Corridor counterfactual comparison remains blocked until candidate actions are regenerated under
Condition B.

See:

```text
../docs/V1_3_COMPARISON_WORKBENCH.md
../docs/V1_3_RC_PUBLICATION_PLAN.md
../docs/V1_3_RELEASE_CONTRACT.md
../docs/V1_3_PUBLICATION_EXPORT.md
```

## Deterministic publication export

With a built frontend served by `npm run preview -- --host 127.0.0.1`, export a fully specified exact
slice with:

```bash
npm run export:difference-figure -- \
  --url '/volume/compare?scenario=aitana-overload&fi=10&cmp=earlier-run&lead=0.75&dc=future_space&dq=low&dt=0.200&tm=slice&layer=2&pub=figure'
```

The command validates the canonical scientific URL before launching Chromium and writes a plate PNG,
print PDF, and JSON manifest carrying the figure ID and source URL.

## Evidence rules

Synthetic named-player scenarios are teaching laboratories, not measured player performance.
`showcase_emphasis` is always labeled research emphasis. Literal gaze requires calibrated eye-gaze
data; body and motion axes remain distinct; load and balance are proxies without sensors. StatsBomb
360 is an event snapshot, and Metrica sample identities remain anonymous.

The default Difference Volume showcase source is itself synthetic, and the publication route surfaces
that status explicitly. A publication-quality graphic does not upgrade synthetic evidence into empirical
evidence.
