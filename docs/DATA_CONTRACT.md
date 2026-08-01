# Canonical data contract

## Coordinate frame

Every canonical frame uses:

- metres;
- origin at the top-left corner of the attacking diagram;
- x from 0 to pitch length;
- y from 0 to pitch width;
- explicit attacking direction for home and away;
- no hidden half-time flipping.

Provider-native coordinates remain recoverable through metadata or source IDs.

## PlayerState

Core identity and geometry:

- `player_id`, the canonical within-frame identity;
- `observation_id`, the immutable source observation identity when available;
- `track_id`, the source temporal track identity when available;
- `source_player_id`, a provider identity when available;
- `team` / `team_id`;
- `x`, `y` in metres.

Kinematics and orientation:

- `vx`, `vy`;
- `ax`, `ay`;
- body, head, and gaze angle;
- movement heading and turning rate;
- role and jersey number.

Uncertainty and provenance:

- tracking status: observed, extrapolated, inferred, interpolated, or unknown;
- visibility status;
- detection and tracking confidence;
- calibration confidence;
- trajectory confidence;
- 2 × 2 position covariance;
- image bounding box;
- provenance flags and provider-native metadata.

A zero velocity is not automatically evidence of no movement. Adapters add a `no_velocity` quality
flag when temporal information is absent. Inferred, extrapolated, and interpolated points remain
explicitly distinguishable from observations.

## BallState

The nested `BallState` view includes:

- x, y, vx, and vy;
- confidence and status;
- carrier identity;
- possession probability;
- 2 × 2 position covariance;
- source metadata.

Player-only GSR output is not sufficient for actionable affordance scoring. SoccerNet ingestion
therefore requires a ball and possession sidecar rather than silently inventing a carrier.

## GameStateFrame / FrameState

Required operational fields:

- sequence and frame IDs;
- timestamp and period;
- possession team;
- ball position and velocity;
- ball carrier ID;
- player states;
- pitch dimensions.

Provider and uncertainty fields:

- source provider and match ID;
- frame rate and camera ID;
- visible-pitch polygon;
- ball, possession, and calibration confidence;
- ball status;
- quality flags;
- state semantics and upstream provenance in metadata;
- schema version.

`FrameState` is retained for backward compatibility. `GameStateFrame` is its public v0.3 contract
alias, and `to_canonical_dict()` emits the nested representation.

## EventState

Events are stored separately from frames because event time and tracking time are often different
measurement systems.

Fields include:

- event ID and type;
- timestamp and period;
- team and actor;
- start and end locations;
- outcome;
- provider metadata.

Use `fusion.align_events_to_frames` rather than joining on rounded timestamps without inspection.

## ActionOption

The action option is the main prediction unit.

It stores:

- action kind and actor;
- target player or target point;
- interpretable features;
- uncertainty-adjusted geometry and state confidence;
- baseline and learned scores;
- provider provenance;
- availability, value, visibility, confidence, failure reason, and selected-action labels.

Provider camera coverage and player-view visibility remain separate option features.
`visible_area_mask` reports whether a target lies inside a supplied provider polygon;
`perceptual_visibility_proxy` reports the orientation-based player-view proxy. An option outside
the provider polygon remains a physical candidate, with `physical_candidate_retained = 1`; the
mask must not be converted into an availability label.

For StatsBomb 360, a selected receiver may be mapped to an event-local teammate using pass-end
geometry. This is a selected-action label only. It is neither a persistent player identity nor a
complete action-menu label.

## Persistence formats

- JSONL is the canonical portable representation.
- Optional Parquet stores the complete serialized payload losslessly in `payload_json` rows.
- Pickle is accepted only for trusted local TrackLab tracker states and should be converted promptly.
- Every frozen perception state can be accompanied by a SHA-256 manifest containing repository,
  dataset, model, input, and override provenance.

## Invariants

1. Ball carrier must appear in the player list.
2. Ball carrier team must equal possession team.
3. Coordinates must be in canonical pitch bounds before the affordance engine runs.
4. Duplicate canonical player IDs are invalid within a frame.
5. Inferred, interpolated, and extrapolated states may not be relabeled as observed.
6. Snapshot data may not be used for velocity claims.
7. Event-local IDs may not be treated as persistent identities.
8. Provider-specific information must survive normalization in metadata.
9. Non-causal interpolation must expose that it used a future endpoint.
10. Player-only GSR detections may not silently define ball state or possession.
11. Camera crops and hidden-player completion must preserve visible versus inferred provenance.
12. Calibration and localization uncertainty must not be discarded before tactical scoring.
13. Provider visible-area masks may change observation confidence, not physical candidate membership.
14. Event-supported receiver selection may not be propagated into availability or value labels.
