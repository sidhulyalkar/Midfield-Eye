# Gemini AI Studio Frontend Build Specification v0.6

Implementation authority: `docs/GEMINI_FRONTEND_IMPLEMENTATION_BLUEPRINT.md` and
`frontend_contract/integration-contract.json`. If this older route-oriented specification is less
specific, follow those two files.

## Product mission

Build an interactive tactical atlas that makes four layers of midfield play visible:

1. the action menu;
2. the player's perceptual access to that menu;
3. the body state from which actions can be executed;
4. the way teammates and opponents adapt around the player.

The application should feel like a coaching room, a football research instrument, and a visual essay. It should not look like a fantasy-sports dashboard.

## Data sources

### Static bundle

Root: `public/showcase`

Entry points:

- `manifest.json`
- `players/index.json`
- `players/cohorts.json`
- `players/comparison_axes.json`
- `scenarios/index.json`

### API bundle

Root from `VITE_MIDFIELDERS_EYE_API_URL`.

Use the contract in `frontend_contract/openapi.json`.

### Validation

Define Zod schemas for:

- manifest;
- player profile;
- scenario index item;
- canonical frame;
- action option;
- gaze payload;
- body-mechanics payload;
- relational-control payload.

Reject malformed payloads with a useful developer error view. Never silently coerce an unknown evidence status.

## Information architecture

### Global shell

Desktop:

```text
left icon rail | top context bar | main canvas | optional inspector
```

Mobile:

```text
top app bar | main content | bottom navigation | slide-over inspector
```

Global controls:

- evidence legend;
- active data source;
- scenario/player search;
- reduced motion;
- screenshot mode;
- method links.

## Route details

### `/`

Headline: `See the option before it exists.`

Show:

- an 8 to 12 second loop from a featured scenario;
- action menu, gaze field, body vectors, and relationship links appearing in sequence;
- atlas count and cohort balance;
- four research pillars;
- featured studies;
- evidence disclaimer above the fold.

### `/atlas`

Load all 100 profiles.

Desktop layout:

```text
filter rail | virtualized player grid | comparison tray
```

Required features:

- fuzzy search;
- cohort toggle;
- multi-select lens filters;
- archetype filter;
- scenario-available filter;
- evidence filter;
- shareable URL filter state;
- two-to-four player comparison tray;
- keyboard selection;
- no ordinal rank.

Each card shows:

- name;
- role;
- archetype;
- one-sentence signature;
- four talent lenses;
- evidence badge;
- scenario count;
- SVG profile.

### `/players/:playerId`

Sections:

1. research hypothesis;
2. signature and talent lenses;
3. gaze questions;
4. body-mechanics questions;
5. adaptation and orchestration questions;
6. available scenarios;
7. media registry;
8. evidence-upgrade requirements;
9. falsification panel.

The emphasis polygon must be titled `Research emphasis`, never `Ratings`.

### `/players/:playerId/perception`

A player-centered educational page that combines:

- gaze bands;
- representative scanning patterns;
- body-access diagrams;
- teammate adaptation questions;
- exact evidence status;
- links to scenarios and future data requirements.

Do not fabricate measured player timelines when none exist.

### `/scenario/:scenarioId`

Desktop composition:

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ title | player | evidence | source confidence | frame controls          │
├──────────────────────────────────────────┬──────────────────────────────┤
│ Tactical pitch                           │ Ranked action menu           │
│ gaze + pressure + movement + uncertainty │ option explanation          │
│                                          │ evidence and data quality    │
├──────────────────────────────────────────┴──────────────────────────────┤
│ synchronized timeline: options | scans | body load | relational signal  │
├───────────────────────────┬──────────────────────┬───────────────────────┤
│ Gaze detail               │ Body mechanics       │ Relational control    │
├───────────────────────────┴──────────────────────┴───────────────────────┤
│ Counterfactual movement | coaching interpretation | share/export        │
└─────────────────────────────────────────────────────────────────────────┘
```

Frame synchronization is mandatory. One global frame index controls every view.

Controls:

- play and pause;
- one-frame stepping;
- 0.25x, 0.5x, 1x, 2x;
- lock option;
- layer toggles;
- observed versus uncertainty-aware;
- gaze band toggles;
- body-vector toggles;
- relationship-link toggles;
- deterministic screenshot mode.

### `/gaze-lab`

Use one large pitch and one temporal strip.

Layers:

1. body direction;
2. head direction;
3. gaze direction;
4. foveal field;
5. actionable field;
6. peripheral field;
7. option targets;
8. scan trail;
9. blind-side options.

Explain the source hierarchy in a persistent panel.

### `/body-mechanics`

Use a receiving-posture workbench with:

- body and movement axes;
- weight-transfer vector;
- braking, lateral, and turning load bars;
- balance reserve;
- action-access fan;
- option angular spread;
- before-and-after counterfactual posture.

### `/orchestration`

Use a dynamic relationship graph aligned to pitch coordinates.

- subject node is emphasized;
- teammate links encode support and option access;
- opponent links encode pressure attraction;
- link thickness and opacity are explained;
- co-adaptation lag is displayed in time, not only frames;
- a timeline shows when the collective response peaks.

### `/compare`

Comparison modes:

- two player hypotheses;
- two scenarios;
- same scenario, two frames;
- oracle versus degraded state.

Required context filters:

- possession phase;
- pressure level;
- field zone;
- action type;
- provider;
- evidence status;
- cohort.

Block unsupported numeric comparison with an explanatory warning.

### `/perception-lab`

Modes:

- oracle;
- position noise;
- missing players;
- calibration drift;
- camera crop;
- ID switch;
- ball dropout;
- gaze-source downgrade;
- body-orientation downgrade.

Show how the tactical conclusion changes, not only the tracking error.

### `/method`

Explain the pipeline in football language, with expandable technical details.

Include:

> The selected action is one observation of the player's decision, not the full set of actions that was available.

### `/data-and-rights`

Explain:

- rights-cleared analysis lane;
- YouTube embed-only reference lane;
- provider tracking;
- reconstructed broadcast state;
- human annotation;
- synthetic illustration;
- source and license manifests.

## Core components

### `TacticalPitch`

Inputs:

- frame;
- options;
- selected option;
- layer state;
- coordinate transform;
- active evidence view.

Layer order:

1. pitch;
2. visible-pitch polygon;
3. pressure;
4. uncertainty;
5. players;
6. trails and movement vectors;
7. body/head/gaze vectors;
8. gaze bands;
9. relationship links;
10. option corridors;
11. ball;
12. interaction highlights.

### `GazeField`

- nested polygons;
- confidence-dependent opacity;
- source badge;
- option visibility classification;
- scan trail;
- top-option acquisition marker.

### `BodyMechanicsOverlay`

- body axis;
- movement axis;
- weight-transfer vector;
- action-access fan;
- proxy labels.

### `RelationalControlGraph`

- pitch-anchored nodes;
- support links;
- pressure links;
- hover explanation;
- temporal link history.

### `SynchronizedTimeline`

Tracks:

- best option value;
- menu breadth;
- visible options;
- scan events;
- head-body dissociation;
- balance reserve;
- turning load;
- directive influence;
- support reactivity;
- evidence-confidence changes.

## Rendering standard

- SVG for the pitch and static vectors;
- DPR-aware Canvas for trails and dense fields;
- 60 FPS target during playback at 1080p;
- do not rerender the full React tree on every animation frame;
- memoize transforms and paths;
- lazy-load 4K PNGs;
- virtualize the 100-card atlas;
- use responsive typography rather than fixed screenshot text;
- preserve pitch aspect ratio.

## Accessibility

- keyboard scrubbing;
- play/pause shortcut;
- visible focus rings;
- layer toggles with labels;
- text alternative for every tactical visual;
- pattern or line-style distinctions in addition to color;
- reduced-motion mode;
- color contrast meeting WCAG AA where practical.

## Tests

Add:

- route smoke tests;
- schema validation tests;
- 100-player loading test;
- filter tests;
- no-rank-text test;
- frame synchronization test;
- evidence badge test;
- gaze-source wording test;
- proxy wording test;
- static/API parity test;
- mobile interaction tests;
- production build test.

## v0.6 empirical implementation requirements

Add the routes and components defined in `docs/V6_FRONTEND_EXPERIENCE.md`. The implementation must load `artifacts/showcase/empirical/manifest.json`, `sources.json`, `experiments.json`, `player_evidence_ledger.json`, `claim_contract.json`, and `citation_index.json` in both static and API modes.

Required components:

- `EmpiricalEvidenceRail`
- `SourceAccessCard`
- `ProvenanceDrawer`
- `MissingSignalPanel`
- `CaptureStudio`

The two bundled real-source studies must be visually differentiated from synthetic scenario pages. Display the StatsBomb and Metrica source attribution, evidence tier, measured fields, inferred fields, unavailable fields, and citation before any tactical interpretation.

A registered or license-request dataset must never display a one-click download action. Instead, display the official URL, required human steps, and copyable CLI command after access has been granted.
