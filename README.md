# The Midfielder's Eye v0.6 ⚽👁️🔬

**An evidence-aware 100-player perception atlas and empirical laboratory for the changing action menu of midfield play.**

Version 0.6 includes the first real-source layer and a production React Evidence Studio. The
repository contains source-pinned Metrica tracking and a real StatsBomb 360 Pedri event, an
authoritative dataset registry, fail-closed pilot/reliability and B0-B3 protocols, provenance
manifests, evidence validation, 4K empirical visualizations, and an integrated frontend.

## What v0.6 adds

- 12-source empirical registry covering gaze, head pose, 3D pose, kinematics, kinetics, tracking, 360 snapshots, and video reconstruction;
- real Metrica synchronized tracking excerpt around frame 1226;
- real StatsBomb 360 event snapshot for Pedri in Spain versus Germany, 27 November 2022;
- Ego-Exo4D gaze CSV ingestion and license-aware access plan;
- WorldPose JSON/NPZ pose ingestion contract;
- OpenCap/OpenSim `.mot` ingestion;
- governed download command that refuses gated sources;
- per-file SHA-256 provenance manifests;
- evidence-tier and claim-boundary validation;
- four new empirical 4K views;
- FastAPI routes for sources, experiments, citations, claim rules, clock alignment, and capture-protocol validation;
- raw Metrica synchronization, SkillCorner direction validation, visible-area masks, and StatsBomb receiver labels;
- immutable pilot/reliability and sequence/provider-held-out B0-B3 tooling;
- a strict React/TypeScript Evidence Studio with synthetic and empirical slices, the 100-profile atlas, and specialist laboratories;
- Gemini specifications and machine-readable contracts for continued frontend implementation.

## What remains intentionally unclaimed

No restricted gaze or pose dataset is mirrored. No named elite player's gaze, force, or body weight is fabricated. The included Pedri study contains real event and 360 geometry but no eye tracking or biomechanics. The included Metrica study contains real continuous tracking but anonymous identities.

## Empirical quick start

```bash
pip install -e ".[dev,showcase]"
midfielders-eye empirical-sources
midfielders-eye empirical-plan ego_exo4d
midfielders-eye empirical-build
midfielders-eye capture-protocol --participant-id study-001
midfielders-eye showcase-serve
```

Open `/api/empirical`, `/api/empirical/sources`, and `/api/empirical/experiments` in the API documentation.

## Core model

```text
rights-cleared video / provider tracking / manual annotation
                         │
                         ▼
                  canonical game state
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
  gaze and view      body mechanics   relational control
        │                │                │
        └────────────────┼────────────────┘
                         ▼
              dynamic affordance field
                         │
              pass / carry / hold menu
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
   current value     future options   counterfactuals
```

## Quick start

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -e ".[dev,showcase]"
pytest
midfielders-eye showcase-build
midfielders-eye showcase-serve
```

Open the API at `http://127.0.0.1:8000/docs`.

For a frontend on another origin, set a comma-separated allowlist before serving:

```bash
MIDFIELDERS_EYE_CORS_ORIGINS=https://your-frontend.example midfielders-eye showcase-serve
```

`MIDFIELDERS_EYE_CORS_ORIGIN_REGEX` is also supported for controlled preview-domain patterns. Do not
use an unrestricted production regex.

## Run the frontend

Node.js 22.22 or newer is required. The generated static bundle stays outside Git and is copied
into the frontend automatically before development, builds, and browser tests.

```bash
midfielders-eye showcase-build
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. Static mode is the default. To use the FastAPI source instead:

```bash
VITE_MIDFIELDERS_EYE_API_URL=http://127.0.0.1:8000 npm run dev
```

The configured API never silently falls back to static data. Run the complete frontend gate with:

```bash
npm run format:check
npm run typecheck
npm run lint
npm test
npm run build
npm run test:e2e
```

See `frontend/README.md` for routes, evidence rules, and deterministic mobile through 4K captures.

## Frontend handoff to Gemini AI Studio

The application is implemented under `frontend/`. The following contracts remain the authoritative
handoff for Gemini when extending or restyling it.

Read and paste:

```text
docs/GEMINI_MASTER_PROMPT.md
```

Gemini must then inspect:

```text
docs/INTEGRATED_DELIVERY_PLAN.md
docs/GEMINI_FRONTEND_IMPLEMENTATION_BLUEPRINT.md
docs/GEMINI_AI_STUDIO_BUILD_SPEC.md
docs/100_PLAYER_ATLAS.md
docs/GAZE_AND_BODY_MECHANICS.md
docs/RELATIONAL_CONTROL.md
docs/MEDIA_INGESTION_AND_RIGHTS.md
frontend_contract/integration-contract.json
frontend_contract/README.md
frontend_contract/openapi.json
frontend_contract/component-contract.json
frontend_contract/design-tokens.json
artifacts/showcase/manifest.json
artifacts/showcase/players/index.json
artifacts/showcase/scenarios/index.json
```

To copy the complete static bundle into a generated frontend repository:

```bash
python scripts/prepare_gemini_handoff.py ../generated-frontend --rebuild
```

The handoff command is required after a clean clone because generated `artifacts/` are intentionally
not tracked.

## Frontend routes

The implemented application includes:

```text
/                         narrative landing page
/atlas                    filterable 100-player atlas
/players/:playerId        player research profile
/players/:playerId/perception
/empirical                source-pinned evidence studio
/empirical/experiments/:experimentId
/gaze-lab                 gaze source, scans, fields of view
/body-mechanics           receiving posture and execution envelope
/orchestration            teammate/opponent relational control
/scenario/:scenarioId     flagship tactical laboratory
/perception-lab            oracle versus degraded state
/method                    model and evidence explanation
/data-and-rights           provenance and media policy
```

## Included featured studies

- Michael Olise: pause, defender commitment, weak-side access
- Rodri: pre-reception scanning, open-body exits, rest-defense control
- Pedri: blind-side arrival, third-player timing, scan-to-action connection
- Aitana Bonmatí: overload, escape, late arrival, collective response
- Vitinha: support-angle creation and circulation-to-penetration
- Jamal Musiala: contact balance, pressure attraction, release after collapse
- Alexia Putellas: vacating and reoccupying central creation lanes
- Yui Hasegawa: micro-positioning and repeated support-angle renewal

All included named-player scenarios are illustrative synthetic reconstructions, not measured player performances.

## Data outputs

A full build creates:

```text
artifacts/showcase/
├── manifest.json
├── players.json
├── players/
│   ├── index.json
│   ├── cohorts.json
│   ├── comparison_axes.json
│   └── <100 player IDs>/
│       ├── profile.json
│       └── profile.svg
└── scenarios/
    ├── index.json
    └── <scenario ID>/
        ├── frames.jsonl
        ├── options.json
        ├── timeline.json
        ├── gaze.json
        ├── body_mechanics.json
        ├── relational_control.json
        └── visuals/
            ├── tactical-lens-4k.png
            ├── action-menu-timeline-4k.png
            ├── scenario-style-profile-4k.png
            ├── counterfactual-uplift-4k.png
            ├── gaze-lab-4k.png
            ├── body-mechanics-4k.png
            └── relational-control-4k.png
```

## Media policy

The repository has two lanes:

1. rights-cleared local media for frame extraction and model analysis;
2. YouTube embed-only references discovered through the official API.

The code does not download YouTube footage. An embed-only reference is never eligible for pixel analysis. See `docs/MEDIA_INGESTION_AND_RIGHTS.md`.

## Research goal

The strongest scientific target is not "predict which pass a player chose." It is:

> Estimate the action menu a player could perceive, the body states from which those actions were executable, and the way their movement changed the future options of teammates and opponents.

## License

MIT for this repository. External data, footage, model weights, and upstream perception systems retain their own licenses and access conditions.


## Empirical bundle outputs

```text
artifacts/showcase/empirical/
├── manifest.json
├── sources.json
├── experiments.json
├── player_evidence_ledger.json
├── claim_contract.json
├── capture_protocol.json
├── alignment_contract.json
├── citation_index.json
├── MANIFEST.json
└── visuals/
    ├── statsbomb-pedri-360-4k.png
    ├── metrica-tracking-pass-4k.png
    ├── empirical-source-landscape-4k.png
    └── evidence-ladder-4k.png
```

The two real-source examples are compact excerpts for reproducible software and visualization tests. Full datasets remain with their official providers.
