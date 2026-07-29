# Gemini frontend implementation blueprint

This document is the implementation source of truth for the Midfielder's Eye web application. Use it
with `frontend_contract/integration-contract.json`, `frontend_contract/component-contract.json`,
`frontend_contract/design-tokens.json`, and `frontend_contract/openapi.json`.

## Outcome

Build a production-quality React and TypeScript application that lets a viewer:

1. see an action option emerge before the selected pass;
2. understand physical availability, perceptual visibility, tactical value, future creation, and
   selection as separate concepts;
3. inspect the source, evidence tier, missing signals, uncertainty, and claim boundary;
4. compare original and counterfactual movement;
5. move from a synthetic teaching scenario to a real-source empirical study without confusing their
   evidence status.

Do not create placeholder analytics, random data, invented metrics, invented player photography, or
generic dashboard filler.

## Required stack

- React with TypeScript strict mode and Vite.
- React Router with lazy route modules.
- TanStack Query for server/static resource caching.
- Zod validation at every external data boundary.
- A small dedicated playback store; Zustand is acceptable. Do not put frame-rate animation state in
  a page-wide React context.
- SVG for the pitch, players, labels, option corridors, and interaction targets.
- DPR-aware Canvas only for dense trails, pressure fields, or animated textures.
- Vitest and Testing Library for unit/component tests.
- Playwright for route, keyboard, static/API parity, and screenshot tests.
- ESLint, TypeScript no-emit checking, Prettier, and a committed lockfile.

Pin dependency versions in the generated repository. Do not load runtime code, fonts, or chart
libraries from a CDN.

## Suggested project structure

```text
src/
  app/
    AppShell.tsx
    router.tsx
    providers.tsx
  contracts/
    component-contract.json
    design-tokens.json
    integration-contract.json
    openapi.json
  data/
    schemas.ts
    types.ts
    ShowcaseDataSource.ts
    StaticShowcaseDataSource.ts
    ApiShowcaseDataSource.ts
    normalize.ts
    queryKeys.ts
  state/
    playbackStore.ts
    urlState.ts
    preferencesStore.ts
  visualization/
    coordinates.ts
    evidenceStyle.ts
    pitch/
      TacticalPitch.tsx
      PitchSurface.tsx
      layers/
    timeline/
      SynchronizedTimeline.tsx
  components/
    evidence/
    feedback/
    controls/
    layout/
  features/
    landing/
    atlas/
    players/
    scenarios/
    empirical/
    capture/
    comparison/
    method/
  routes/
  styles/
    tokens.css
    global.css
    print.css
  test/
    fixtures/
    a11y/
    screenshots/
```

Feature modules may import domain types and shared visualization components. They may not fetch
bundle paths directly.

## One normalized data boundary

Implement:

```ts
export interface ShowcaseDataSource {
  mode: "static" | "api";
  getHealth(): Promise<Health>;
  getManifest(): Promise<ShowcaseManifest>;
  listPlayers(filters?: PlayerFilters): Promise<PlayerStudy[]>;
  getPlayer(playerId: string): Promise<PlayerStudy>;
  listScenarios(): Promise<ScenarioSummary[]>;
  getScenario(scenarioId: string): Promise<Scenario>;
  getScenarioFrames(scenarioId: string): Promise<FrameState[]>;
  getScenarioOptions(scenarioId: string): Promise<ActionOption[]>;
  getScenarioTimeline(scenarioId: string): Promise<TimelinePoint[]>;
  getScenarioGaze(scenarioId: string): Promise<GazePayload>;
  getScenarioBody(scenarioId: string): Promise<BodyMechanicsPayload>;
  getScenarioRelations(scenarioId: string): Promise<RelationalControlPayload>;
  getEmpiricalManifest(): Promise<EmpiricalManifest>;
  listEmpiricalSources(): Promise<EmpiricalSource[]>;
  listEmpiricalExperiments(): Promise<EmpiricalExperiment[]>;
  getEmpiricalExperiment(experimentId: string): Promise<EmpiricalExperiment>;
  getEvidenceLedger(): Promise<EvidenceLedgerEntry[]>;
  getClaimContract(): Promise<ClaimContract>;
  getCitations(): Promise<CitationEntry[]>;
  getAlignmentContract(): Promise<AlignmentContract>;
  getDefaultCaptureProtocol(): Promise<CaptureProtocolEnvelope>;
  validateCaptureProtocol(protocol: CaptureProtocol): Promise<CaptureValidation>;
  assetUrl(relativePath: string): string;
}
```

At app startup:

1. If `VITE_MIDFIELDERS_EYE_API_URL` is a non-empty absolute URL, create
   `ApiShowcaseDataSource`.
2. Otherwise create `StaticShowcaseDataSource` rooted at
   `import.meta.env.BASE_URL + "showcase/"`.
3. Validate the manifest before mounting data-dependent routes.
4. Display the active mode and bundle/API version in a diagnostics popover.
5. Reject incompatible major versions. Warn, but continue, on a newer minor version when all required
   fields validate.

Do not silently fall back from a configured but failing API to stale static data. Offer an explicit
user action if both modes are intentionally packaged.

## Resource mapping

| Resource | Static mode | API mode |
|---|---|---|
| Health | synthesized after manifest validation | `GET /api/health` |
| Manifest | `manifest.json` | `GET /api/showcase/manifest` |
| Atlas | `players/index.json` | `GET /api/atlas` |
| Player | `players/{id}/profile.json` | `GET /api/players/{id}` |
| Profile SVG | `players/{id}/profile.svg` | `GET /api/players/{id}/profile-card` |
| Scenarios | `scenarios/index.json` | `GET /api/scenarios` |
| Scenario | `scenarios/{id}/scenario.json` | `GET /api/scenarios/{id}` |
| Frames | parse `scenarios/{id}/frames.jsonl` | `GET /api/scenarios/{id}/frames` |
| Options | `scenarios/{id}/options.json` | `GET /api/scenarios/{id}/options` |
| Timeline | `scenarios/{id}/timeline.json` | `GET /api/scenarios/{id}/timeline` |
| Gaze | `scenarios/{id}/gaze.json` | `GET /api/scenarios/{id}/gaze` |
| Body | `scenarios/{id}/body_mechanics.json` | `GET /api/scenarios/{id}/body-mechanics` |
| Relations | `scenarios/{id}/relational_control.json` | `GET /api/scenarios/{id}/relational-control` |
| Empirical | `empirical/manifest.json` | `GET /api/empirical` |
| Sources | `empirical/sources.json` | `GET /api/empirical/sources` |
| Experiments | `empirical/experiments.json` | `GET /api/empirical/experiments` |
| Evidence ledger | `empirical/player_evidence_ledger.json` | `GET /api/empirical/player-ledger` |
| Claim contract | `empirical/claim_contract.json` | `GET /api/empirical/claim-contract` |
| Citations | `empirical/citation_index.json` | `GET /api/empirical/citations` |
| Alignment | `empirical/alignment_contract.json` | `GET /api/empirical/alignment-contract` |
| Default capture protocol | `empirical/capture_protocol.json` | `GET /api/capture-protocol/default` |
| Validate capture protocol | local structural checks, marked offline | `POST /api/capture-protocol/validate` |

Static JSONL parsing must:

- split on newlines;
- ignore blank lines;
- parse each line independently;
- report the failing line number;
- validate every frame;
- never use `eval` or permissive coercion.

## Domain and validation rules

Build explicit Zod schemas from the real payloads copied into `public/showcase`. At minimum:

- `PlayerStudy.evidence_status` is `hypothesis_only | measured | mixed`.
- `FrameState.possession_team` and `PlayerState.team` are `home | away`.
- tracking status is `observed | extrapolated | inferred | interpolated | unknown`.
- action kind is `pass | carry | hold`.
- nullable values remain nullable. Do not turn `null` into `0`, an empty string, or a confident
  default.
- unknown top-level evidence states are errors.
- unknown additive metadata fields are preserved or ignored safely for minor-version compatibility.

Treat `geometric_score` and `learned_score` as model scores. Never append a percent sign. Rank within
a frame unless the contract explicitly supplies cross-context calibration.

The `showcase_emphasis` object is a research-emphasis profile. It is never an ability score, player
rating, percentile, or rank.

## Coordinate transform

Canonical input:

- metres;
- origin at pitch top-left;
- x in `[0, pitch_length]`;
- y in `[0, pitch_width]`;
- no implicit half-time flip;
- explicit attacking direction metadata.

Use one pure transform:

```ts
type PitchTransform = {
  toScreen(point: { x: number; y: number }): { x: number; y: number };
  toPitch(point: { x: number; y: number }): { x: number; y: number };
  metresToPixels(distanceM: number): number;
};
```

The transform owns padding, aspect fit, and optional user-requested viewing rotation. Viewing
rotation must not mutate data or change labels. Do not stretch x and y independently. Clip only
visual primitives, never canonical coordinates.

## Synchronization model

One playback store controls every scenario view:

```ts
type PlaybackState = {
  scenarioId: string;
  frameIds: number[];
  currentFrameId: number;
  selectedOptionId: string | null;
  lockedOptionId: string | null;
  playing: boolean;
  playbackRate: 0.25 | 0.5 | 1 | 2;
  layers: LayerState;
  evidenceView: "observed" | "uncertainty-aware";
};
```

Rules:

1. Join frames, options, gaze, body, relations, and timeline by `frame_id`.
2. Use `timestamp_s` for display and drift diagnostics, not as a lossy join key when `frame_id`
   exists.
3. Selecting a timeline marker seeks first, then selects its option.
4. Locking an option keeps it selected only while that `option_id` exists; otherwise show its
   disappearance state.
5. Playback uses elapsed time and frame rate, not one `setInterval` tick per frame.
6. Pause playback when the tab is hidden. Resume only if the user had playback active.
7. Reduced motion replaces autoplay with a poster frame and explicit play.
8. Direct-gaze timelines must obey the alignment contract and retain dropout gaps.

URL state:

```text
?frame={frameId}
&option={optionId}
&rate={0.25|0.5|1|2}
&layers={comma-separated stable layer IDs}
&evidence={observed|uncertainty}
&compare={secondary ID when relevant}
&filters={route-specific compact encoding}
```

Back/forward navigation must restore state without starting playback automatically.

## Application shell

Desktop at 1440px and above:

```text
64px navigation rail | flexible content | 360px inspector when open
top context bar: breadcrumb / source / evidence / global search / diagnostics
```

Tablet:

```text
top app bar
content with inline controls
inspector as right sheet
```

Mobile:

```text
56px top bar
pitch and playback first
selected option summary second
timeline third
details in bottom sheet
four-item bottom navigation
```

Do not shrink the desktop dashboard into an unreadable mobile grid.

## Route composition and acceptance

### `/`

Data: manifest, one featured scenario, scenarios, empirical manifest.

Composition:

- evidence disclaimer above the fold;
- headline `See the option before it exists.`;
- deterministic 8-12 second pitch sequence;
- one explanatory sentence that changes with narrative beat;
- two clear paths: `Explore the action menu` and `Inspect the evidence`;
- concise research pillars and featured studies below.

Acceptance: a first-time viewer can state the project idea after the hero loop without opening a
tooltip.

### `/scenario/:scenarioId`

Data: scenario, frames, options, timeline, gaze, body, relations.

Desktop:

```text
title / source / evidence / playback
pitch (minmax(0, 1fr)) | action rail (320-380px)
full-width synchronized timeline
three detail cards: perception | body | collective response
counterfactual and coaching interpretation
```

Acceptance:

- every view changes on the same `currentFrameId`;
- selected option is visible on pitch, rail, and timeline;
- synthetic watermark is persistent for named-player synthetic scenarios;
- the UI never labels synthetic gaze as measured player gaze;
- missing layers are absent, not zero-filled.

### `/empirical/experiments/:experimentId`

Data: experiment, source, citation, provenance, referenced visual/data assets.

Composition:

- source and evidence tier before interpretation;
- geometry or provided 4K visual;
- persistent evidence rail;
- measured, inferred, and unavailable sections;
- citation and hash drawers;
- claim boundary near the conclusion.

Acceptance:

- StatsBomb is visibly a snapshot and offers no temporal playback claim;
- Metrica identities are visibly anonymous;
- unavailable gaze/biomechanics renders a missing-signal panel.

### `/atlas`

Data: all 100 profiles and comparison axes.

Acceptance:

- exactly 100 cards and the declared 50/50 cohort balance;
- no ordinal number attached to a player;
- filters and two-to-four-item comparison tray are URL-addressable;
- virtualization does not break keyboard order or screen-reader access;
- cards say `Research emphasis`, never `Ratings`.

### `/players/:playerId` and `/players/:playerId/perception`

Acceptance:

- editorial hypotheses are visually distinct from empirical evidence;
- every profile includes evidence-upgrade and falsification sections;
- no measured timeline is invented for a hypothesis-only player.

### `/compare`

Acceptance:

- supports hypothesis, scenario, frame, and oracle/degraded comparisons;
- blocks numeric comparison when provider, context, or evidence compatibility is insufficient;
- explains the block and offers compatible alternatives.

### `/gaze-lab`

Acceptance:

- body, head, gaze, foveal, actionable, peripheral, scan trail, and blind-side layers can be
  distinguished without color alone;
- a source ladder is persistent;
- a proxy can never be relabeled as eye tracking.

### `/body-mechanics`

Acceptance:

- body and movement axes are distinct;
- every load, balance, and weight-transfer proxy carries a proxy label;
- direct force language appears only when the evidence contract supports it.

### `/orchestration`

Acceptance:

- geometry communicates support, pressure, and response timing;
- the copy does not infer leadership, speech, or intent;
- lag is shown in seconds and frames.

### `/perception-lab`

Acceptance:

- oracle and degraded states share the same base frame;
- the view shows changes to action-menu conclusions, not only localization error;
- degradation type and magnitude are explicit.

### `/capture-studio`

Acceptance:

- loads the default protocol;
- edits a local draft without mutating server state;
- debounces validation but validates again on export;
- consent, required sensors, calibration, and synchronization failures block export;
- JSON and Markdown exports contain the same protocol version and ID;
- static-mode offline validation is labeled and never presented as server approval.

## Tactical pitch rendering

Render in this exact semantic order:

1. pitch surface and markings;
2. visible-pitch polygon;
3. pressure field;
4. uncertainty and missing-state regions;
5. players;
6. movement trails and velocity vectors;
7. body, head, and gaze vectors;
8. gaze bands;
9. relational links;
10. option corridors;
11. ball;
12. selection, hover, focus, and annotation highlights.

### Player marks

- possession team: cool light fill with dark edge;
- opposition: coral fill with dark edge;
- ball carrier: gold ring plus possession marker;
- extrapolated/inferred state: dashed ring;
- uncertainty: covariance ellipse or halo sized from the state, never a generic glow;
- focus: high-contrast outer ring that does not replace evidence styling.

### Option marks

- selected/top option: mint corridor, strongest contrast;
- other high-value option: blue;
- unavailable or blocked option: muted red/orange with the failure reason on inspection;
- corridor width reflects interaction target size, not tactical confidence;
- confidence changes opacity and/or hatch density;
- arrowheads remain legible at all supported viewports.

Do not show every label at once. Labels use collision-aware placement and progressive disclosure:
selected, hovered, focused, then top-N.

### Perception marks

- gaze direction: solid only for direct gaze, dashed for proxy, dotted for synthetic;
- body direction and head direction must use different glyphs;
- foveal/actionable/peripheral regions use nested opacity with boundaries visible in monochrome;
- unavailable gaze draws no cone.

## Visual system

Use `frontend_contract/design-tokens.json` as values and emit CSS custom properties.

Direction:

- near-black green background;
- deep pitch panels;
- restrained mint, sky, gold, coral, and violet accents;
- fine grid/noise texture at very low opacity;
- strong whitespace and large tactical canvas;
- avoid glassmorphism stacks, oversized metric cards, neon bloom, and decorative gauges.

Typography:

- one readable sans family for display and body;
- tabular numerals for time and metrics;
- mono only for IDs, hashes, sources, and coordinates;
- responsive type via `clamp`;
- sentence case for navigation and controls.

Motion:

- 120ms feedback, 220ms state transition, 480ms narrative transition;
- movement communicates causality and selection, not decoration;
- no perpetual ambient animation behind the pitch;
- reduced motion removes interpolation, autoplay, shimmer, and parallax.

## Evidence and feedback components

Every data-dependent page implements:

- skeleton loading with stable layout;
- recoverable error with resource name and retry;
- route-level not found;
- empty result after filters;
- missing signal;
- gated source;
- unsupported comparison;
- version mismatch;
- offline static validation;
- partial data with warnings.

`Unavailable` is never a warning-colored zero. It is a first-class state with a reason and a path to
better evidence.

## Accessibility

- WCAG 2.2 AA contrast for text and controls.
- Full keyboard scrubbing, stepping, play/pause, layer toggling, option selection, and drawer close.
- Visible focus on SVG interaction targets.
- Pitch has an accessible name plus a live textual summary that updates no more than once per user
  action; do not flood assistive technology during autoplay.
- Patterns, dashes, labels, and shapes duplicate color meaning.
- Touch targets are at least 44x44 CSS pixels.
- The bottom sheet traps focus only while modal and returns focus on close.
- Exports and print views preserve evidence labels.

Recommended shortcuts:

```text
Space       play/pause
Left/Right previous/next frame
Shift+Left/Right previous/next event marker
1-9         toggle documented layer shortcuts
Escape      close inspector or clear hover
?           keyboard help
```

Do not intercept shortcuts while focus is in a text field, select, textarea, or content-editable
element.

## Performance budgets

- 60 FPS playback target at 1920x1080 on a contemporary laptop.
- No page-wide React rerender for each animation frame.
- Route modules and 4K images are lazy.
- Atlas cards are virtualized after initial visible rows.
- Cache parsed frames and options by scenario/version.
- Avoid duplicating the full bundle in application state.
- Abort stale fetches on route changes.
- Initial landing route should not download all 100 SVGs or all scenario payloads.
- Keep layout shifts negligible by reserving pitch and media aspect ratios.

## Test matrix

### Contract

- all static resources validate;
- all API resources normalize to equivalent domain objects;
- JSONL reports its failing line;
- null remains missing;
- unknown evidence status fails;
- score wording never implies probability;
- exactly 100 balanced profiles and no rank field.

### Interaction

- frame, pitch, rail, and timeline synchronization;
- option lock and extinction behavior;
- keyboard controls;
- URL restore and browser back/forward;
- reduced motion;
- comparison compatibility block;
- capture export block and success.

### Scientific wording

Automated text assertions must reject:

- `player rating` or ordinal rank language for `showcase_emphasis`;
- literal gaze wording for synthetic, pose, or motion sources;
- direct force wording for proxy kinetics;
- continuous tracking claims for StatsBomb 360;
- named identity claims for Metrica sample players;
- leadership/intent claims derived only from relational geometry.

### Visual regression

Capture at:

- 390x844;
- 1440x900;
- 1920x1080;
- 3840x2160;
- reduced motion;
- high-contrast forced colors where supported;
- loading, error, missing, gated, and unsupported states.

Required golden routes:

- landing hero;
- one synthetic scenario;
- Pedri empirical snapshot;
- Metrica empirical sequence;
- atlas with filters;
- capture studio with blocking errors.

### Production

- typecheck;
- lint;
- unit/component tests;
- Playwright;
- production build;
- bundle-size report;
- broken-link and missing-asset check;
- zero console errors on required routes.

## Implementation passes

1. Scaffold, tokens, shell, router, error boundaries, and test harness.
2. Implement both data sources, Zod schemas, normalization, diagnostics, and contract tests.
3. Build the pitch, playback store, option rail, timeline, and one synthetic scenario.
4. Build one empirical experiment with the full evidence rail and missing-signal states.
5. Complete landing, method, and data/rights narrative.
6. Add atlas, profile, comparison, and URL state.
7. Add gaze, body, relational, and perception laboratories.
8. Add evidence studio, source planner, ledger, and capture studio.
9. Run accessibility, mobile, 4K, performance, static/API parity, and scientific-language audits.
10. Produce deployment docs and a deterministic portfolio recording.

Do not implement all routes as shallow card grids before the pitch, data source, evidence grammar, and
playback architecture work.

## Completion report required from Gemini

When finished, report:

- repository path and commit;
- exact run, test, and build commands;
- static and API configuration;
- completed routes;
- contract deviations, if any;
- known data limitations;
- accessibility and viewport results;
- performance and bundle results;
- screenshots or visual-regression artifact paths;
- any scientific wording that required clarification.

