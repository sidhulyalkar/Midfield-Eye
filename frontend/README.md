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

## Implemented routes

- `/` — action-menu explanation and deterministic illustrative hero
- `/scenario/:scenarioId` — synchronized pitch, action rail, timeline, evidence, and URL state
- `/empirical` and `/empirical/experiments/:experimentId` — provider geometry, rights, provenance,
  missing signals, and 4K visual fallback
- `/atlas` — exactly 100 balanced, non-ranked hypothesis profiles with URL filters and comparison tray
- `/players/:playerId` and `/players/:playerId/perception` — editorial study and evidence-upgrade views
- `/gaze-lab`, `/body-mechanics`, `/orchestration`, `/perception-lab` — specialist visual laboratories
- `/method` and `/data-and-rights` — scientific gates and rights boundaries

## Evidence rules

Synthetic named-player scenarios are teaching laboratories, not measured player performance.
`showcase_emphasis` is always labeled research emphasis. Literal gaze requires calibrated eye-gaze
data; body and motion axes remain distinct; load and balance are proxies without sensors. StatsBomb
360 is an event snapshot, and Metrica sample identities remain anonymous.
