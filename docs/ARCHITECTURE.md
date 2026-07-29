# Architecture

## System layers

```text
Layer 0: source data
  full tracking | partial tracking | event snapshots | video GSR | egocentric

Layer 1a: isolated perception service
  broadcast video → external SoccerNet/TrackLab run → frozen tracker state + manifest

Layer 1b: provider adapters
  parse → transform coordinates → preserve uncertainty → emit warnings

Layer 2: canonical state
  PlayerState + BallState + GameStateFrame/FrameState + EventState

Layer 3: state reconstruction
  camera cuts + causal smoothing + kinematics + possession + optional completion

Layer 4: data intelligence
  quality reports + event alignment + sequence construction + provider shift

Layer 5: affordance engine
  candidate generation + corridor timing + pressure + viewpoint + future space

Layer 6: counterfactuals
  alternate receiver, carrier, and off-ball positions

Layer 7: models
  naive → static → dynamic → learned tabular → future temporal graph

Layer 8: evaluation
  sequence held out + provider held out + oracle/degraded + bootstrap + temporal stability

Layer 9: delivery contracts
  CLI + annotation UI + static bundle + FastAPI + normalized frontend data source

Layer 10: interactive product
  synchronized pitch + action menu + evidence rail + counterfactuals + coaching explanation
```

## External SoccerNet boundary

The core package does not import `sn-gamestate`, TrackLab, MMDetection, MMOCR, or their GPU stack.
The perception service runs in its own environment and communicates through immutable files:

```text
video
  → tracker state
  → perception run manifest
  → optional visibility/camera state
  → explicit ball and possession sidecar
  → canonical JSONL or Parquet
```

This boundary keeps tactical experiments reproducible, avoids rerunning costly video perception, and
prevents a legacy computer-vision dependency graph from controlling the research environment. It also
makes upstream uncertainty observable rather than silently converting projected detections into exact
football coordinates.

## Provider boundary

Provider adapters are deliberately thin and deterministic. They should not contain tactical modeling.
Their responsibilities are:

- parse the source format;
- transform to canonical coordinates;
- preserve source provenance;
- expose uncertainty and missingness;
- validate invariants;
- emit canonical frames and events.

Tactical logic begins only after the canonical contract.

## Canonical scene representation

`FrameState`, publicly aliased as `GameStateFrame`, is a causal scene snapshot. It contains the state
available at that timestamp and no future context. `PlayerState` includes observation provenance,
tracking status, visibility, calibration confidence, trajectory confidence, and position covariance.
`BallState` records confidence, provenance, carrier, possession probability, and covariance.

`EventState` remains separate because events and tracking are commonly misaligned. Alignment is an
explicit operation with an error tolerance.

`ActionOption` is generated from a frame and becomes the unit of ranking, annotation, and evaluation.

## State reconstruction

The default trajectory reconstruction is causal:

1. sort frames within sequence;
2. identify camera discontinuities;
3. run a constant-velocity Kalman filter independently per track;
4. derive velocity, acceleration, movement heading, and turning rate;
5. preserve observed, extrapolated, inferred, and interpolated provenance;
6. apply possession only from an explicit sidecar or a real ball trajectory.

Offline short-gap interpolation is opt-in and marked `uses_future_endpoint`. Track stitching emits
proposals rather than silently merging identities. Hidden-player completion begins with a transparent
formation prior and uncertainty, not a fabricated observation.

## Affordance feature groups

### Geometry

- pass distance;
- corridor clearance;
- uncertainty-adjusted clearance;
- forward progress;
- expected-threat gain.

### Timing

- ball travel time;
- defender interception time;
- interception margin.

### Local control

- receiver pressure;
- future receiver space;
- target motion alignment.

### Perception

- carrier view alignment;
- body, head, or gaze orientation;
- camera-visible polygon;
- observed versus extrapolated status;
- state and calibration confidence.

### Creation

- change in option quality after an off-ball displacement;
- counterfactual positioning uplift;
- future option-set diversity.

## Three-track benchmark

### Track A: oracle state

Clean synchronized tracking feeds the tactical model directly.

### Track B: controlled perception degradation

The robustness engine independently injects position noise, missing players, identity switches,
calibration drift, synthetic broadcast crops, observation delay, and ball dropout.

### Track C: real reconstructed state

Frozen SoccerNet/TrackLab outputs are normalized, temporally reconstructed, fused with explicit ball
and possession state, and compared with oracle outputs whenever aligned tracking exists.

This decomposition separates tactical-model validity, robustness to observation errors, and upstream
computer-vision quality.

## Future temporal graph model

The next learned architecture should represent:

- player nodes with team, role, motion, orientation, confidence, and covariance;
- a ball node with possession uncertainty;
- pass-lane edges;
- pressure and marking edges;
- temporal edges for persistent identities;
- candidate-action query nodes;
- latent nodes for unobserved players when state completion is enabled.

The encoder must be causal. A compact temporal graph transformer or graph-SSM should be compared
against the current tabular model under the same frozen splits.

## Uncertainty propagation

Provider confidence is not hidden inside feature values. Models and evaluations receive:

- player confidence and position covariance;
- observed, extrapolated, inferred, or interpolated status;
- camera visibility;
- ball and possession confidence;
- GSR localization and calibration uncertainty;
- trajectory confidence;
- upstream run and model provenance.

Evaluation stratifies by uncertainty and can support abstention or prediction intervals rather than
forcing false precision.

## Frontend boundary

The frontend consumes either the static bundle or FastAPI through one normalized
`ShowcaseDataSource`. Components do not fetch provider files or bundle paths directly. Scenario
playback joins frames, options, gaze, body, relational, and timeline records by `frame_id`; it does
not use rounded timestamps when a frame identity exists.

The implementation contract is defined in:

- `docs/GEMINI_FRONTEND_IMPLEMENTATION_BLUEPRINT.md`;
- `frontend_contract/integration-contract.json`;
- `frontend_contract/component-contract.json`;
- `frontend_contract/design-tokens.json`;
- `frontend_contract/openapi.json`.
