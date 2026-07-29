# Dataset and provider strategy

The project deliberately distinguishes data modalities rather than pretending that every provider exposes a complete game state.

## Integration tiers

| Tier | Integrations | What they contribute | Principal limitation |
|---|---|---|---|
| Full synchronized tracking | Metrica, SkillCorner, Sportec Open through Kloppy | Continuous player and ball geometry, temporal pressure, future-space estimation | Body orientation and gaze are usually absent; broadcast tracking may extrapolate players |
| Event-centered visible-area data | StatsBomb 360 | Event semantics, freeze frames, visible-area polygons, partial-observability experiments | Sparse snapshots rather than continuous trajectories |
| Video-to-game-state data | SoccerTrack v2, SoccerNet GSR | Detection, calibration, identity, role, team, jersey, and reconstructed state from video | Possession and tactical semantics may require sidecars or inference |
| Egocentric auxiliary data | EgoTraj | Head-motion, gaze-motion, future trajectory, and partial-observability pretraining | Not football and cannot establish soccer validity |
| Purpose-built capture | Future 5v5 or 7v7 study | Player-view RGB, gaze, full-pitch tracking, option recall, and tactical labels | Requires consent, hardware synchronization, and a new collection protocol |

## Supported integrations

### Metrica Sports sample data

Use as the cleanest full-state geometric baseline. The adapter handles normalized coordinates, synchronized home/away tracking, ball position, period-aware clocks, and optional event enrichment.

Official repository: `https://github.com/metrica-sports/sample-data`

### SkillCorner open data

Use for broadcast-derived tracking and realistic provider uncertainty. The adapter preserves observed versus extrapolated player status, camera visibility polygons, dynamic events, possession metadata, and causal kinematics.

Official repository: `https://github.com/SkillCorner/opendata`

### StatsBomb open data and 360

Use for action semantics and partial-observability experiments. Each 360 freeze frame becomes an event-centered `FrameState`; the visible-area polygon is retained and missing off-camera players are never interpreted as absent from the match.

Official repository: `https://github.com/statsbomb/open-data`

### Sportec Open Data through Kloppy

Use for a standardized full-tracking path and a bridge to additional providers supported by Kloppy. The optional adapter converts a Kloppy dataframe into the canonical schema while retaining match and provider provenance.

Kloppy documentation: `https://kloppy.pysport.org/`

### SoccerTrack v2

Use for panoramic video-to-state reconstruction and ball-action spotting. The adapter consumes normalized game-state records and optional ball-action labels. It explicitly flags actor-derived ball states and identity limitations.

Official repository: `https://github.com/AtomScott/SoccerTrack-v2`

### SoccerNet Game State Reconstruction

Use for broadcast detection, localization, role, team, and jersey-number experiments. A possession sidecar is required for affordance extraction because detection alone does not identify the decision maker.

Official repository: `https://github.com/SoccerNet/sn-gamestate`

### EgoTraj

Use only as an auxiliary representation sandbox for gaze-conditioned future motion, head and gaze coordination, and uncertainty under partial observability. Transfer must be evaluated against football-specific baselines and ablations.

Paper: `https://arxiv.org/abs/2605.19004`

## Canonical ingestion sequence

1. Preserve the raw provider files unchanged.
2. Convert coordinates and clocks into the canonical contract.
3. Retain confidence, visibility, extrapolation, and identity uncertainty.
4. Infer velocities causally, never with future frames in an online experiment.
5. attach events through tolerance-bounded alignment;
6. run `midfielders-eye quality`;
7. inspect a rendered sample before feature extraction;
8. write normalized JSONL and a machine-readable quality report.

## Purpose-built soccer capture

The decisive study would synchronize player-worn RGB or glasses, eye gaze, head pose, full-pitch optical or LPS tracking, ball tracking, coaching audio, and post-clip player recall. A 5v5 or 7v7 design is preferable for the first collection because it produces more decisions per minute and simplifies occlusion and synchronization.

## Data ethics

Obtain informed consent for wearable video and gaze, preserve provider license and attribution terms, blur non-consenting people when required, avoid opaque youth-player rankings, and distinguish coaching support from selection or employment decisions.
