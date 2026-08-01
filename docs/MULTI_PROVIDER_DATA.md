# Multi-provider integration strategy

Checked against official project documentation on 2026-07-28.

## Provider taxonomy

### 1. Continuous full tracking

Examples: Metrica, Sportec Open DFL, licensed optical feeds.

These sources can support:

- player and defender velocity;
- acceleration after smoothing;
- option emergence and extinction;
- counterfactual earlier positioning;
- temporal rank stability;
- event-tracking synchronization.

They are the strongest sources for the first causal and temporal claims.

### 2. Broadcast-derived partial tracking

Example: SkillCorner Open Data.

These sources add a crucial perceptual ingredient: the camera-visible polygon and a distinction between detected and extrapolated players. They support experiments such as:

- observed-only versus observed-plus-extrapolated action menus;
- option uncertainty outside the camera view;
- whether broadcast data systematically hides weak-side options;
- sensitivity to identity and smoothing errors.

Do not use them as unquestioned full-pitch ground truth.

### 3. Event-centered spatial snapshots

Example: StatsBomb 360.

These sources expose spatial context around selected events and a visible-area polygon. They can scale supervision for:

- option availability at action moments;
- visible versus hidden receiver analysis;
- event-type-conditioned option distributions;
- counterfactual static geometry.

They cannot support defender momentum, temporal emergence, or true option lifetimes unless fused with another tracking source.

### 4. Video game-state reconstruction

Examples: SoccerTrack v2 and SoccerNet GSR.

These datasets help answer a different question:

> Can the affordance system remain useful when the game state itself must first be reconstructed from video?

SoccerTrack v2 provides panoramic full-pitch GSR records and BAS events. The adapter uses BAS to identify the actor and event time, then places the ball at the actor for an explicitly marked event snapshot.

SoccerNet GSR provides player localization, role, team, and identity attributes from broadcast clips. It does not provide the possession and ball contract required by the affordance engine, so the adapter requires a sidecar.

### 5. Provider bridges

Kloppy standardizes many event and tracking formats. The project uses it as an optional bridge rather than replacing the canonical contract. Provider-native metadata should always be preserved.

DataBallPy can become a future synchronization backend, especially when event and tracking streams are misaligned. It is not currently a hard dependency.

## Source-specific integration details

### Metrica

Official source: `https://github.com/metrica-sports/sample-data`

Current support:

- normalized wide CSV;
- official raw three-row tracking headers;
- normalized or metric coordinates;
- optional player and ball velocity columns;
- explicit warnings and quality flags for nearest-player carrier inference;
- provider-frame-first, period-aware event synchronization with recorded error and tolerance.

Next upgrade:

- halftime attacking-direction inference;
- dead-ball filtering.

### SkillCorner

Official source: `https://github.com/SkillCorner/opendata`

The current open repository documents ten Australian A-League matches from 2024/25 with 10 Hz tracking, possession, visible-area projections, dynamic events, and phases of play.

Current support:

- match metadata and pitch dimensions;
- tracking JSONL;
- player group and lineup mapping;
- observed versus extrapolated tracking state;
- camera polygon;
- possession actor;
- causal velocity and body-direction approximation;
- optional dynamic-event CSV.
- fixed provider-coordinate validation with no half flipping;
- match-specific half-direction evidence validation with inconclusive/failed states.

Next upgrade:

- phase-of-play joins;
- smoothing profiles validated against the official tutorials;
- off-ball-run event normalization.

### StatsBomb 360

Official source: `https://github.com/hudl/open-data`

Current support:

- event JSON;
- 360 freeze-frame JSON;
- 120 × 80 to metric-pitch conversion;
- event actor identity;
- event-local identities for other players;
- visible-area polygon;
- explicit snapshot and no-velocity flags.
- event-local selected-receiver mapping from pass-end geometry;
- selected-option labeling that does not manufacture availability labels;
- provider-visible-area masking that retains outside-view physical candidates.

Next upgrade:

- lineup-assisted persistent identity where possible;
- competition-level manifest generation.

### Sportec Open DFL

Official Kloppy documentation lists seven open matches that can be loaded using `sportec.load_open_tracking_data` and `sportec.load_open_event_data`.

Current support:

- optional Kloppy loader;
- Kloppy DataFrame bridge;
- team metadata mapping;
- canonical frame creation.

Next upgrade:

- event integration;
- explicit DFL coordinate and attacking-direction validation;
- alive/dead ball segmentation;
- stable local cache and manifest hashes.

### SoccerTrack v2

Official source: `https://github.com/AtomScott/SoccerTrack-v2`

The official format documents 25 Hz, center-origin metric GSR records with persistent player attributes, plus BAS events aligned in milliseconds.

Current support:

- flat GSR record grouping;
- BAS event loading;
- event-to-frame conversion using `round(position_ms / 40)`;
- actor/team mapping;
- center-origin coordinate conversion;
- event-centered full-pitch snapshots.

Next upgrade:

- temporal GSR trajectories between BAS events;
- ball tracking or ball detector fusion;
- half-to-half player relinking;
- upstream GSR uncertainty propagation.

### SoccerNet GSR

Official source: `https://github.com/SoccerNet/sn-gamestate`

Current support:

- annotations or prediction JSON;
- pitch positions from `bbox_pitch`;
- role, jersey, team, track identity, and confidence;
- explicit possession sidecar requirement;
- partial-visibility flags.

Next upgrade:

- sidecar generation from a ball detector and action spotter;
- camera-polygon approximation;
- GS-HOTA-to-affordance error decomposition;
- comparison of ground-truth versus predicted game state.

## Commercial or owned feeds

The canonical contract is intentionally suitable for Tracab, ChyronHego, Hawk-Eye, Second Spectrum, Stats Perform, Wyscout, Signality, PFF, and other feeds available through direct integrations or Kloppy.

This repository does not download, redistribute, or bypass access controls for commercial data.
