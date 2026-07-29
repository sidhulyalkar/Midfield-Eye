# Agent development contract

This file governs Claude, Codex, and other coding agents working on The Midfielder's Eye.

## Mission

Build a scientifically defensible model of the **action menu a football player can perceive and create**, not merely a classifier of the action eventually selected.

The core targets remain separate:

- physical availability;
- perceptual visibility;
- tactical value;
- future option creation;
- selected action;
- label and state uncertainty.

Do not collapse these targets for convenience.

## Required startup sequence

Before modifying code:

```bash
pytest
midfielders-eye demo --sequences 4 --frames-per-sequence 5
midfielders-eye demo-v2 --sequences 2 --frames-per-sequence 6
```

Then read:

1. `docs/PROJECT_GOALS.md`
2. `docs/DATA_CONTRACT.md`
3. `docs/BENCHMARK_PROTOCOL_V2.md`
4. `docs/MULTI_PROVIDER_DATA.md`
5. `docs/EXPERIMENT_PROTOCOL.md`

## Hard scientific constraints

1. Never place frames from one possession sequence in both train and test.
2. Never use a future frame to construct a causal feature unless the feature is explicitly labeled retrospective.
3. Never treat the selected action as the complete set of available actions.
4. Never invent ball state or possession without marking the inference and its source.
5. Never treat StatsBomb 360 as continuous tracking.
6. Never treat SkillCorner extrapolated positions as equivalent to detected positions.
7. Never treat event-local player IDs as persistent identities.
8. Never silently flip, stretch, or clip coordinates.
9. Never compare providers without a quality and distribution-shift report.
10. Never add a learned model without retaining a simpler baseline and ablation.

## Adapter implementation checklist

Every new provider adapter must:

- declare a `ProviderSpec` in `adapters/catalog.py`;
- document source access and license constraints;
- define native coordinate origin, units, axis direction, pitch dimensions, and frame rate;
- preserve provider-native IDs;
- distinguish observed, extrapolated, and inferred states;
- populate source provider and match IDs;
- attach visibility polygons where available;
- emit warnings rather than silently dropping important records;
- include a miniature provider-shaped fixture;
- include parser, coordinate, possession, and quality tests;
- avoid downloading or redistributing restricted data.

## Modeling sequence

Work in this order unless a documented issue justifies changing it:

### Stage 1: contracts and labels

- improve adapters;
- improve quality audits;
- improve annotation reliability;
- freeze the pilot sequences and labels.

### Stage 2: honest baselines

- B0 naive;
- B1 static geometry;
- B2 dynamic geometry;
- B2-V viewpoint-aware geometry;
- B3 learned tabular ranker.

### Stage 3: transfer and uncertainty

- match-held-out evaluation;
- provider-held-out evaluation;
- sequence bootstrap intervals;
- partial-visibility and extrapolation ablations;
- calibration.

### Stage 4: temporal representation

Only after Stages 1–3:

- temporal option identities;
- graph scene encoder;
- causal temporal context;
- emergence and extinction targets;
- option-set forecasting.

### Stage 5: video and egocentric transfer

Only after a geometry baseline exists:

- video-to-state uncertainty propagation;
- player-view gaze/head representation;
- purpose-built capture protocol;
- representation fusion and transfer tests.

## Preferred next issues

1. Add raw Metrica header parsing and synchronized events.
2. Validate SkillCorner half-specific coordinate directions against official examples.
3. Add visible-polygon masking to candidate generation.
4. Implement selected-receiver labels for StatsBomb 360.
5. Add temporal GSR trajectories and ball fusion for SoccerTrack v2.
6. Add SoccerNet ground-truth versus predicted-state degradation experiments.
7. Add inter-rater reliability reports.
8. Add provider-held-out experiment manifests with frozen hashes.
9. Implement a small temporal graph ranker after the pilot labels exist.

## Pull request checklist

- [ ] all tests pass;
- [ ] both demos run;
- [ ] no frame or provider leakage;
- [ ] no unmarked future information;
- [ ] schema changes documented;
- [ ] coordinate conventions tested;
- [ ] provider uncertainty preserved;
- [ ] new metric has a unit test;
- [ ] new feature has units and timing semantics;
- [ ] synthetic and human labels remain distinguishable;
- [ ] negative results are retained;
- [ ] README commands remain valid;
- [ ] no external data is committed without clear permission.

## v0.5 implementation contract

Before changing the atlas or frontend contract, read:

- `docs/100_PLAYER_ATLAS.md`
- `docs/GAZE_AND_BODY_MECHANICS.md`
- `docs/RELATIONAL_CONTROL.md`
- `docs/GEMINI_AI_STUDIO_BUILD_SPEC.md`

Mandatory checks:

1. preserve exactly 100 unique player IDs;
2. preserve 50/50 cohort balance unless a versioned migration changes the research design;
3. preserve non-ranking language;
4. preserve source and confidence labels for gaze;
5. preserve proxy language for body mechanics;
6. preserve relational-control guardrails;
7. run the entire test suite;
8. rebuild the showcase bundle after schema changes;
9. verify all profile SVGs parse and all included PNGs meet expected dimensions;
10. update OpenAPI, component contract, Gemini prompt, README, and release notes together.

## v0.6 empirical evidence guardrails

- Treat `src/midfielders_eye/empirical/source_registry.yaml` as the access and claim authority.
- Never bypass registration, license, consent, or redistribution gates.
- Open-source downloads must retain upstream paths, versions, hashes, and attribution.
- Direct gaze language requires calibrated eye-gaze data. Head, pose, and motion proxies remain proxies.
- Body-weight, force, and kinetics language must state whether the value is directly measured or model-derived.
- StatsBomb 360 is event-centered and cannot supply continuous velocity.
- Metrica sample identities are anonymous and cannot support named-player claims.
- Missing signals remain missing. Never replace them with synthetic values in empirical views.
- Any new named-player empirical profile requires a source record, rights record, and evidence ledger entry.
- Gated dataset files must stay outside Git and outside release archives.
- Add tests for evidence-tier validation, provenance hashes, source access, and frontend claim boundaries with every empirical adapter.

