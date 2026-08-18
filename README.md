# The Midfielder's Eye v0.7 ⚽👁️🔬

**An evidence-aware research system for studying the changing action menu of midfield play, not only the action eventually selected.**

Version 0.7 turns the project into a sharper publication-oriented benchmark while preserving the v0.6 empirical Evidence Studio. It adds a frozen action-menu annotation contract, stable cross-frame option identities, lifecycle analytics, a reproducible report builder, and the interactive **Action Menu Ribbon / Decision Microscope**.

The central research object is deliberately decomposed into five questions that must not collapse into one another:

```text
                    ┌ physical availability
                    ├ perceptual accessibility
state → ACTION MENU ├ tactical value
                    ├ option creation
                    └ eventual selection
```

The selected action is one observed outcome. It is not treated as the full action set.

## What v0.7 adds

### Action Menu Benchmark

- frozen `configs/action_menu_annotation_v1.yaml` contract;
- separate availability, visibility, value, creation, selection, and confidence labels;
- explicit outcome blinding for expert judgments before selection is joined from events;
- sequence-level sampling and no adjacent-frame random splits;
- 10–20-sequence pilot gate with at least 25% double-rating;
- a preferred main Paper 1 target of at least 150 independent possession windows, subject to data access and annotation capacity;
- stable option identities across frames for pass, carry, and hold candidates;
- retrospective birth, persistence, extinction, selected-frame, and top-k stability analytics;
- causal guardrails that forbid using future lifecycle information as focal-frame model features;
- a standalone action-menu report builder and unit tests for annotation/lifecycle invariants.

### Decision Microscope

The React Evidence Studio now includes an **Action Menu Ribbon** inside every scenario laboratory. Each row follows one stable candidate across synchronized frames. Clicking a ribbon cell seeks the pitch to that exact frame and candidate.

The visual instrument distinguishes:

- candidate absent from candidate low-scoring;
- model score from observed selected action;
- current frame from option history;
- retrospective lifecycle labels from causal model inputs;
- synthetic, proxy, reconstructed, provider-observed, and directly measured evidence.

### Release robustness

- one package version authority now drives the FastAPI version, API health payload, OpenAPI contract, and generated showcase manifest;
- checked-in integration and component contracts are versioned to v0.7 and explicitly require the new Decision Microscope semantics;
- `CITATION.cff` now uses the valid CFF 1.2.0 schema;
- backend, frontend, contract, build, and browser gates remain part of CI.

## What remains intentionally unclaimed

v0.7 ships the **benchmark contract and software**, not fabricated empirical superiority. The real expert-annotated pilot and main benchmark still need to be run before claiming that dynamic geometry, viewpoint conditioning, or any learned model better reflects real football decisions.

No restricted gaze or pose dataset is mirrored. No named elite player's gaze, force, or body weight is fabricated. The included Pedri study contains real event and 360 geometry but no eye tracking or biomechanics. The included Metrica study contains real continuous tracking but anonymous identities.

## Action-menu quick start

```bash
pip install -e ".[dev,showcase]"

# Existing synthetic/software verification
midfielders-eye demo
midfielders-eye demo-v2

# Build the Evidence Studio
midfielders-eye showcase-build
midfielders-eye showcase-serve
```

For a candidate CSV produced by the engine, build the v0.7 lifecycle report with:

```bash
python scripts/build_action_menu_report.py candidates.csv artifacts/action-menu
```

This writes:

```text
artifacts/action-menu/
├── option_lifecycles.csv
├── action_menu_timeline.csv
└── summary.json
```

See `docs/ACTION_MENU_BENCHMARK.md` for the frozen Paper 1 scope, annotation protocol, causal boundaries, and publication gates.

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

## Core system

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
                         │
                         ▼
              Action Menu Ribbon
              / Decision Microscope
```

## Benchmark ladder

The existing fail-closed benchmark remains the modeling authority:

```text
B0 naive
  ↓
B1 static geometry
  ↓
B2 dynamic geometry
  ↓
B2-V viewpoint / visibility conditioned
  ↓
B3 learned nonlinear tabular ranker
```

B4 temporal graphs and B5 representation fusion remain blocked until the expert-label reliability and transfer gates are satisfied.

Primary metrics include NDCG@3, Recall@3, pairwise ranking accuracy, adjacent-frame top-k stability, sequence-bootstrap confidence intervals, and provider/match-held-out evaluation where supported.

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

`MIDFIELDERS_EYE_CORS_ORIGIN_REGEX` is also supported for controlled preview-domain patterns. Do not use an unrestricted production regex.

## Run the frontend

Node.js 22.22 or newer is required. The generated static bundle stays outside Git and is copied into the frontend automatically before development, builds, and browser tests.

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

The application is implemented under `frontend/`. The following contracts remain the authoritative handoff for Gemini when extending or restyling it.

Read and paste:

```text
docs/GEMINI_MASTER_PROMPT.md
```

Gemini must then inspect:

```text
docs/ACTION_MENU_BENCHMARK.md
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

The handoff command is required after a clean clone because generated `artifacts/` are intentionally not tracked.

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
/scenario/:scenarioId     flagship Decision Microscope + tactical laboratory
/perception-lab           oracle versus degraded state
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

> Estimate the action menu a player could perceive, the body states from which those actions were executable, and the way movement changed the future options of teammates and opponents.

Paper 1 narrows that program to a testable first question: can the action menu itself be annotated reliably and modeled better than static geometry without collapsing selected action into available action?

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

## License

MIT for this repository. External data, footage, model weights, and upstream perception systems retain their own licenses and access conditions.
