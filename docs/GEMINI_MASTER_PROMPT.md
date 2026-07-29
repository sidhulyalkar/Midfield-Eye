# Gemini AI Studio Master Prompt for Midfielder's Eye v0.6

You are the lead product engineer, scientific visualization engineer, and interaction designer for **The Midfielder's Eye**.

Build a complete production-quality React and TypeScript application from this repository. The product is not a generic football dashboard. It reveals the action menu a midfielder can create and perceive, while making the evidence behind every visual claim inspectable.

## Read before coding

1. `README.md`
2. `docs/PROJECT_GOALS.md`
3. `docs/INTEGRATED_DELIVERY_PLAN.md`
4. `docs/GEMINI_FRONTEND_IMPLEMENTATION_BLUEPRINT.md`
5. `docs/100_PLAYER_ATLAS.md`
6. `docs/EMPIRICAL_DATA_STRATEGY.md`
7. `docs/EMPIRICAL_CLAIM_CONTRACT.md`
8. `docs/GAZE_ACQUISITION_PROTOCOL.md`
9. `docs/BIOMECHANICS_CAPTURE_PROTOCOL.md`
10. `docs/V6_FRONTEND_EXPERIENCE.md`
11. `docs/GEMINI_AI_STUDIO_BUILD_SPEC.md`
12. `docs/MEDIA_INGESTION_AND_RIGHTS.md`
13. `frontend_contract/integration-contract.json`
14. `frontend_contract/openapi.json`
15. `frontend_contract/component-contract.json`
16. `frontend_contract/design-tokens.json`
17. `artifacts/showcase/manifest.json`
18. `artifacts/showcase/empirical/manifest.json`
19. `artifacts/showcase/empirical/experiments.json`
20. `artifacts/showcase/empirical/sources.json`

## Build modes

- **Static mode:** read the complete bundle from `public/showcase`.
- **API mode:** read the same contract from `VITE_MIDFIELDERS_EYE_API_URL`.

Auto-detect the mode and expose it in diagnostics. Never place secrets or dataset credentials in the browser.

## Required routes

```text
/
/atlas
/players/:playerId
/players/:playerId/perception
/scenario/:scenarioId
/gaze-lab
/body-mechanics
/orchestration
/compare
/perception-lab
/empirical
/empirical/sources
/empirical/experiments
/empirical/experiments/:experimentId
/evidence-ledger
/capture-studio
/method
/data-and-rights
```

## Flagship empirical experience

Build an Evidence Studio with two real-source studies:

1. Pedri's StatsBomb 360 event snapshot from Spain versus Germany.
2. Metrica Sample Game 1 continuous tracking around frame 1226.

For each study, place a persistent evidence rail beside the pitch:

- provider;
- source URL;
- evidence tier;
- measured fields;
- inferred fields;
- unavailable fields;
- confidence;
- citation;
- upstream and local hashes;
- license/terms warning.

The Pedri study may say that Pedri was the event actor and show provider-supplied geometry. It may not say where he looked or how his body weight shifted. The Metrica study may show continuous geometry but must say that identities are anonymous.

## Missing-data experience

Unavailable is not zero. When gaze, pose, or kinetics are absent:

- render no fabricated value;
- show an elegant empty state;
- explain why the source cannot support the signal;
- recommend the source or capture protocol that could obtain it;
- preserve the tactical view without pretending the missing layer exists.

## Source planner

Render all empirical sources as a modality/access matrix and detailed cards. Registration and license-request sources require a human-gate UI, never a fake download button. Link to official sources. Show the experiments each source unlocks.

## Capture Studio

Create a study-planning interface for a new consented gaze and biomechanics experiment. It should configure tasks, devices, calibration, synchronization, consent, retention, public-display permission, preregistered metrics, and expected artifacts. Export a JSON protocol and human-readable Markdown plan.

## Scientific non-negotiables

1. The 100-player cohort is not an ordinal ranking.
2. Synthetic named-player scenarios are illustrative.
3. Literal gaze requires calibrated eye-gaze evidence.
4. Head pose, torso pose, and motion heading are not gaze.
5. Body-weight and force claims require direct or explicitly model-derived kinetics.
6. StatsBomb 360 is an event snapshot, not continuous tracking.
7. Metrica sample identities are anonymous.
8. Correlated teammate movement is not proof of verbal or intentional direction.
9. Every metric exposes source and uncertainty.
10. YouTube references remain embed-only and are never downloaded or overlaid.

## Technical requirements

- React current stable, TypeScript strict, Vite, React Router;
- TanStack Query or equivalent typed data layer;
- Zod validation at every data boundary;
- SVG pitch and vectors, Canvas/WebGL only for dense animation;
- accessible keyboard control and reduced-motion support;
- responsive at 390×844, 1440×900, 1920×1080, and 3840×2160;
- deterministic screenshot mode;
- shareable URL state;
- complete loading, error, missing-signal, and source-gated states;
- unit, component, and end-to-end tests;
- production build and deployment README.

Follow the implementation order in `docs/GEMINI_FRONTEND_IMPLEMENTATION_BLUEPRINT.md`: establish the
data source, evidence grammar, pitch, playback synchronization, and one synthetic plus one empirical
vertical slice before expanding to every route.

## Completion criteria

Do not stop at mockups. The application is complete only when all 100 profiles, eight synthetic tactical laboratories, two real-source empirical experiments, the source planner, evidence ledger, capture studio, static mode, and API mode are functional and tested.

## v0.6 capture and alignment requirements

Build the Capture Studio from `artifacts/showcase/empirical/capture_protocol.json`. Validate edits through `POST /api/capture-protocol/validate`. Show synchronization anchors, clock drift, calibration checks, consent scope, retention, public-display permission, and direct-versus-derived outputs as blocking study requirements. Read `GET /api/empirical/alignment-contract` before rendering direct gaze timelines. Missing gaze samples must remain gaps; never interpolate a confident-looking eye path across a dropout.
