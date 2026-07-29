# Integrated research, product, and delivery plan

Status: reviewed against the v0.6 codebase on 2026-07-28.

## Executive decision

The project should be developed as one evidence-aware system with three deliberately separate
products:

1. a research pipeline that estimates physical availability, perceptual visibility, tactical value,
   future option creation, selection, and uncertainty without collapsing them;
2. an analyst API and reproducible static bundle that expose the same canonical contract;
3. a visual application that teaches the action-menu idea, then lets coaches and researchers inspect
   evidence, counterfactuals, and failure modes.

The frontend is not evidence by itself. The 100-player atlas is a hypothesis library, the eight
named-player scenarios are synthetic teaching laboratories, and the two empirical examples establish
source-aware behavior rather than player-performance conclusions.

The next scientific milestone is therefore not a temporal graph network or a larger showcase. It is
a frozen, expert-annotated real-data pilot with reliability, B0-B3 baselines, and sequence-held-out
evaluation. The next product milestone can proceed in parallel because it consumes already governed
contracts, but it must make evidence status impossible to miss.

## Codebase assessment

### What is already strong

- The canonical state distinguishes observed, extrapolated, inferred, interpolated, and missing
  information.
- Provider adapters are isolated from tactical logic and retain provider identity and uncertainty.
- The baseline ladder preserves naive, static, dynamic, viewpoint-aware, and learned-tabular
  comparisons.
- The repository already contains quality, transfer, degradation, counterfactual, and temporal
  evaluation utilities.
- External SoccerNet/TrackLab execution is correctly kept behind an immutable file and process
  boundary.
- The empirical registry treats access, licensing, consent, citations, and redistribution as
  first-class data.
- The 100-player catalog is balanced 50/50 across the two cohorts and explicitly avoids ordinal
  ranking.
- Static showcase output and a FastAPI service provide a credible frontend integration boundary.

### Gaps that limit scientific claims

- There is no frozen 10-20-sequence human-labeled pilot with published hashes.
- Inter-rater reliability is not yet the gate that controls modeling progression.
- Current demo scores are synthetic software checks, not empirical performance evidence.
- Raw Metrica event synchronization and SkillCorner half-direction validation remain incomplete.
- Visible-polygon candidate masking and StatsBomb selected-receiver labels are still priority work.
- Provider-held-out manifests and distribution-shift reports are implemented as machinery but not
  yet frozen as the main result.
- Temporal option identity, emergence, persistence, and extinction should wait until the pilot gates
  are satisfied.

### Gaps that limit product delivery

- No React frontend is checked in yet.
- The previous frontend documents described the desired pages well but did not define a single
  normalized data-source interface, URL state, component state machines, or exact responsive
  compositions.
- The checked-in OpenAPI contract enumerated routes without response models; the static bundle
  contains the concrete payload examples.
- API-mode scenario playback previously lacked a dedicated frames endpoint. It is now part of the
  contract at `/api/scenarios/{scenario_id}/frames`.
- Generated showcase artifacts are intentionally ignored by Git. A frontend handoff must run the
  preparation command rather than assuming `artifacts/` exists after a clone.
- The duplicated `docs/` and `gemini/` instructions had version drift. `docs/` is now the source of
  truth; `gemini/` is a short entrypoint only.

### Engineering debt to track explicitly

- CI should exercise the optional showcase/API dependencies so API tests cannot silently skip.
- Mypy currently exposes real typing gaps plus third-party stub gaps; make typing stricter by module,
  not with a repository-wide flag flip.
- API response models should migrate from `Any` to explicit Pydantic models after the frontend domain
  contract is accepted.
- Static/API parity requires contract tests for every resource, not just route existence.
- Long generated visuals and empirical bundles need deterministic build metadata and cross-platform
  provenance manifests.

## Product truth model

Every UI view and export must preserve this chain:

```text
source observation
  -> normalized state and uncertainty
  -> candidate action menu
  -> availability / visibility / value / creation estimates
  -> selected action as one observation
  -> explanation, counterfactual, and confidence
```

The interface must never imply that:

- the selected action was the only available action;
- a model score is a probability unless it is calibrated as one;
- head, torso, or movement direction is literal gaze;
- a body-load proxy is a force measurement;
- a StatsBomb 360 snapshot contains temporal momentum;
- an anonymous Metrica identity is a named player;
- correlated player motion establishes leadership, communication, or intent.

## Target system architecture

```text
registered source + rights record + source manifest
                         |
                         v
provider adapters / isolated video-perception service
                         |
                         v
canonical causal state + events + uncertainty
                         |
          +--------------+--------------+
          |                             |
          v                             v
quality / alignment / reconstruction    annotation protocol
          |                             |
          +--------------+--------------+
                         |
                         v
B0 naive -> B1 static -> B2 dynamic -> B2-V viewpoint -> B3 tabular
                         |
                         v
sequence/provider-held-out evaluation + bootstrap + degradation
                         |
            +------------+------------+
            |                         |
            v                         v
static showcase bundle             FastAPI
            |                         |
            +------------+------------+
                         |
                         v
normalized TypeScript data source
                         |
                         v
pitch + action menu + timeline + evidence rail + coaching explanation
```

The normalized TypeScript data source is a product boundary. Components must not know whether a
payload came from `public/showcase` or the API.

## Delivery gates

### Gate 0: repository integrity

Outputs:

- full test suite and both demos pass on a clean install;
- lint passes in CI;
- Windows and Linux provenance manifests do not collide;
- the public repository contains no restricted files, secrets, model weights, or ignored generated
  artifacts;
- README and handoff commands work from a clone.

Exit criterion: a clean clone can install, test, build the showcase, prepare a frontend handoff, and
serve the API without undocumented steps.

### Gate 1: contracts and pilot labels

Research outputs:

- raw Metrica header and event synchronization;
- audited SkillCorner direction conventions by half;
- visible-polygon masking for candidate generation;
- StatsBomb 360 selected-receiver labels;
- ten to twenty frozen possession sequences with source and rights records;
- two raters on at least 25% of labeled frames;
- availability, visibility, value, creation, selection, and uncertainty stored separately;
- Krippendorff alpha or an appropriate categorical/ordinal agreement report with confidence
  intervals;
- frozen hashes for sequences, labels, config, and code.

Product outputs:

- canonical evidence badges and wording rules;
- a visible label-reliability view in `/method`;
- an annotation-quality state that distinguishes unreviewed, single-rated, adjudicated, and frozen.

Exit criterion: availability agreement is at least 0.6, or the annotation protocol is revised before
model expansion.

### Gate 2: honest geometry benchmark

Outputs:

- B0, B1, B2, B2-V, and B3 evaluated on identical sequence-held-out folds;
- NDCG@3, Recall@3, pairwise accuracy, top-3 stability, calibration where applicable, and
  sequence-bootstrap 95% intervals;
- ablations for velocity, viewpoint, visible area, extrapolated players, future space, and option
  creation;
- per-sequence results and negative results retained;
- a coaching-facing error gallery split into state, perception, value, and model failures.

Exit criterion: dynamic geometry improves on static geometry without one-sequence dependence, or a
clear negative result identifies the next measurement/label problem.

### Gate 3: transfer and observation uncertainty

Outputs:

- a second full-tracking provider;
- match-held-out and provider-held-out manifests;
- quality and distribution-shift report before cross-provider comparison;
- SkillCorner observed-only versus observed-plus-extrapolated analysis;
- StatsBomb snapshot-only analysis with no temporal claims;
- oracle, controlled degradation, and real reconstructed-state comparison;
- abstention or uncertainty intervals where state quality is insufficient.

Exit criterion: the model either transfers above B0/B1 or reports which provider/state differences
break the claim.

### Gate 4: temporal affordances

Only after Gates 1-3:

- stable option identity across frames;
- emergence, persistence, extinction, and top-option-switch targets;
- causal windows only;
- a simple temporal baseline before a temporal graph;
- 0.5, 1.0, and 2.0 second option-set forecasts;
- explicit retrospective labels for any analysis using a future endpoint.

Exit criterion: temporal modeling improves future-menu prediction and does not weaken provider
transfer or calibration.

### Gate 5: video and direct perception

Only after the geometry benchmark is stable:

- SoccerTrack v2 trajectories and ball fusion;
- SoccerNet ground-truth versus predicted-state degradation;
- pose/head estimation with source-specific uncertainty;
- direct gaze only from calibrated eye-gaze data;
- consented player-view capture with synchronized wide tracking;
- geometry-only control for every representation-fusion experiment.

Exit criterion: the additional modality improves a named target and its gain survives participant,
sequence, and provider controls.

## Frontend delivery sequence

### Product alpha: the action-menu instrument

Implement first:

- global shell and evidence legend;
- static/API `ShowcaseDataSource`;
- `/`, `/scenario/:scenarioId`, `/empirical`, `/method`, and `/data-and-rights`;
- synchronized pitch, action-menu rail, and timeline;
- persistent synthetic or empirical evidence treatment;
- deterministic screenshot mode;
- keyboard, reduced-motion, mobile, 1080p, and 4K behavior.

Why first: one excellent scenario plus one empirical study proves the visual and integration
architecture before the team creates a broad card catalog.

### Product beta: atlas and comparison

Then implement:

- `/atlas`, `/players/:playerId`, `/players/:playerId/perception`, and `/compare`;
- the complete 100-profile catalog with no ordinal ranks;
- context and evidence filters;
- blocked numeric comparisons when evidence is incompatible;
- shareable URL state.

### Product beta 2: specialist laboratories

Then implement:

- `/gaze-lab`, `/body-mechanics`, `/orchestration`, and `/perception-lab`;
- explicit measured/proxy/synthetic/unavailable visual grammar;
- oracle-versus-degraded tactical differences;
- counterfactual drag interaction backed by cached server data or clearly labeled local
  approximation.

### Product release candidate: evidence operations

Finally implement:

- `/empirical/sources`, `/empirical/experiments`, experiment detail, `/evidence-ledger`, and
  `/capture-studio`;
- source access gates and provenance drawers;
- protocol validation and JSON/Markdown export;
- complete error, missing-signal, source-gated, and unsupported-comparison states;
- production deployment, observability, accessibility, and visual-regression checks.

## Visual product direction

The product should feel like a quiet analysis room with an illuminated pitch, not a fantasy-sports
dashboard.

### Visual hierarchy

1. The pitch and the currently selected option are the brightest elements.
2. Other options remain visible but subordinate.
3. Perception, body, relation, and uncertainty layers use distinct line styles as well as color.
4. Evidence status is persistent but compact; deeper provenance opens in a drawer.
5. Detailed metrics appear on demand so the first view remains legible.

### Signature visual moment

The landing loop begins with a plain pitch. A teammate moves, a corridor emerges, the action-menu
leader changes, and the interface rewinds to show which earlier movement created the option. The
sequence is 8-12 seconds, deterministic, captions the evidence status, and stops animating under
reduced motion.

### Evidence grammar

| Evidence state | Geometry | Label behavior |
|---|---|---|
| Direct measurement | solid | `Measured` plus source |
| Provider observation | solid with provider mark | `Provider observed` |
| Video reconstruction | solid/dashed boundary | `Reconstructed` plus confidence |
| Inferred proxy | dashed | `Proxy`, never the direct-signal noun |
| Synthetic | dotted plus watermark | `Illustrative synthetic` |
| Unavailable | no geometry | explanatory missing-signal panel |

### Quality bar

- Pitch vectors remain crisp at 3840x2160.
- Playback targets 60 FPS at 1080p without rerendering the page tree every frame.
- Color never carries evidence or team meaning alone.
- No unlicensed player photography is required for visual quality.
- The mobile experience prioritizes pitch, playback, and the selected option; inspectors become
  sheets.
- Every tactical visual has a textual summary suitable for screen readers and exports.

The exact frontend architecture and acceptance criteria are in
`docs/GEMINI_FRONTEND_IMPLEMENTATION_BLUEPRINT.md`.

## Engineering workstreams

| Workstream | Immediate deliverable | Quality gate |
|---|---|---|
| Data contracts | schema versioning and exact adapter warnings | fixture, coordinate, possession, quality tests |
| Labels | frozen pilot and reliability report | no modeling gate without agreement |
| Baselines | B0-B3 manifest-driven benchmark | same folds, ablations, sequence bootstrap |
| Transfer | provider-held-out report | quality and shift report precedes comparison |
| Perception | oracle/degraded/reconstructed benchmark | missing ball or possession remains blocking |
| API | typed responses and static/API parity | contract tests and CORS configuration |
| Frontend | action-menu alpha | mobile/4K/keyboard/reduced-motion/evidence tests |
| Evidence operations | source planner and capture studio | licenses, consent, hashes, missingness enforced |
| Release | reproducible public demo | clean clone, no gated data, deterministic build |

## Priority backlog

### P0: next

1. Freeze the frontend contract and implement the product alpha.
2. Add raw Metrica headers and synchronized events.
3. Validate SkillCorner half-specific coordinate directions.
4. Add visible-polygon masking to candidate generation.
5. Add StatsBomb 360 selected-receiver labels.
6. Design and run the pilot annotation reliability study.
7. Add static/API parity tests and explicit API response models.
8. Add contract fixtures to the Gemini handoff and a frontend CI workflow.

### P1: after pilot labels

1. Freeze B0-B3 experiment manifests and hashes.
2. Add provider-held-out and match-held-out reports.
3. Add the full degradation matrix and tactical-threshold plots.
4. Build atlas, comparison, and specialist frontend routes.
5. Add analyst/coach failure galleries and negative-result cards.
6. Add partial-visibility and extrapolation ablations.

### P2: after transfer gates

1. Add temporal option identities and a simple causal sequence baseline.
2. Add temporal GSR trajectories and ball fusion for SoccerTrack v2.
3. Add SoccerNet ground-truth versus predicted-state degradation.
4. Add purpose-built gaze and biomechanics capture.
5. Add the temporal graph only after the simple baseline and labels are frozen.

## Repository and release policy

- `docs/` is authoritative. `gemini/` may point to it but must not become a divergent copy.
- `artifacts/` stays ignored. Rebuild it with `midfielders-eye showcase-build`.
- A Gemini handoff is produced with:

  ```bash
  python scripts/prepare_gemini_handoff.py ../generated-frontend --rebuild
  ```

- The generated frontend should live in its own repository or a deliberate `frontend/` workspace;
  do not mix generated dependencies into the Python package by accident.
- Commit code, tiny licensed fixtures, schemas, manifests, and docs. Do not commit restricted data,
  credentials, model weights, videos, or generated release artifacts.
- Use conventional, reviewable commits separated by contract, backend, frontend, and research
  changes.

## Definition of done

### A scientific result is done when

- labels and state provenance are frozen;
- frames are grouped by sequence;
- no unmarked future information is used;
- the selected action is not treated as the full action set;
- baselines and ablations use identical folds;
- uncertainty intervals and negative results are retained;
- provider quality and shift are reported;
- the exact code, config, data, and label hashes are published.

### A frontend feature is done when

- static and API modes render the same domain data;
- loading, error, empty, unavailable, source-gated, and unsupported states are designed;
- evidence and proxy wording passes automated tests;
- URL state restores the same scenario, frame, option, and layers;
- keyboard and reduced-motion behavior works;
- mobile, 1440x900, 1920x1080, and 3840x2160 screenshots pass;
- the production build has no console errors or broken paths;
- no visual or sentence claims more than its evidence source supports.

