# Historical roadmap and active stage mapping

Package versions and earlier showcase milestone labels were previously used for different workstreams.
The active, gated sequence is now defined in `INTEGRATED_DELIVERY_PLAN.md`. The R-stage labels below
preserve the technical intent without implying that a future research gate is already complete
because the package version is v0.6.

## Platform release v0.2: multi-provider foundation, complete

- canonical provider-aware schema;
- Metrica, SkillCorner, StatsBomb 360, SoccerTrack v2, SoccerNet GSR, and Kloppy bridges;
- provider catalog;
- quality reports;
- event alignment;
- provider shift analysis;
- leave-one-provider-out evaluation;
- temporal stability metrics;
- uncertainty-aware annotation UI.

## Platform release v0.3: perception-to-tactics bridge, complete

- isolated SoccerNet/TrackLab GPU service boundary;
- official JSON and frozen dataframe tracker-state ingestion;
- exact tracker-state SHA-256 and run manifests;
- uncertainty-aware player and ball contract;
- causal trajectory smoothing and derived kinematics;
- camera-cut detection and conservative track-stitch proposals;
- explicit possession sidecars and ball-based possession baseline;
- visible-state cropping and transparent hidden-player completion baseline;
- oracle-versus-degraded tactical robustness benchmark;
- position noise, missing-player, ID-switch, calibration, crop, delay, and ball-dropout controls;
- perception, kinematic, tactical-geometry, decision, and robustness metrics;
- Claude/Codex operating contract and scientific guardrails.

Exit criterion achieved at the software level: frozen perception states can flow through canonical
normalization, reconstruction, affordance extraction, and layered evaluation without importing the
upstream GSR stack. External model execution and real-data validation remain separate milestones.

## Research stage R1: real-data pilot, next

- pin one official SoccerNet GSR commit and model manifest;
- run one legally accessible validation clip through the isolated GPU service;
- save tracker state, minimap output, run manifest, and upstream metrics;
- raw Metrica and Sportec event synchronization;
- 10–20 frozen expert-annotated possession sequences;
- two annotators for at least 25% of frames;
- inter-rater reliability;
- full B0–B3 ablation table;
- coaching-facing failure gallery.

Exit criterion: label agreement, reproducible real GSR ingestion, and a trustworthy estimate of
dynamic versus static geometry.

## Research stage R2: oracle-versus-real perception benchmark

- align broadcast video with clean full-pitch tracking where licensing permits;
- compare oracle, synthetically degraded, and real reconstructed states;
- evaluate localization and association errors at tactical thresholds;
- stratify by camera coverage, uncertainty, phase, pressure, and corridor width;
- SkillCorner observed-only versus extrapolated comparison;
- provider feature-shift report;
- frozen experiment manifests and data hashes.

Exit criterion: determine whether failures arise from tactical reasoning, incomplete observation, or
the upstream vision system.

## Research stage R3: temporal affordance model

- stable option identity across frames;
- emergence, persistence, and extinction targets;
- temporal graph baseline;
- causal context windows;
- option-set forecasting at 0.5, 1.0, and 2.0 seconds;
- uncertainty-aware ranking and abstention;
- learned hidden-player posterior compared with formation-prior completion.

Exit criterion: improve future option prediction without degrading provider transfer.

## Research stage R4: video-to-affordance stack

- SoccerTrack v2 full trajectories and ball fusion;
- SoccerNet ground-truth versus predicted game state;
- orientation estimation from pose and temporal context;
- dedicated ball detection and temporal smoothing;
- camera calibration and tracking error propagation;
- affordance sensitivity to identity and localization errors;
- video encoder fusion only after state baselines.

Exit criterion: quantify the value and cost of reconstructing affordances directly from video.

## Research stage R5: player-view capture

- purpose-built head or chest camera protocol;
- synchronized wide-angle tracking;
- head pose and gaze calibration;
- scanning, blind-side option, and information-gain labels;
- EgoTraj-pretrained versus scratch comparison.

Exit criterion: directly test whether player-view information improves action-menu prediction.

## Product release candidate: showcase system

- reproducible benchmark paper;
- interactive possession replay;
- player-view and overhead affordance overlays;
- counterfactual movement explorer;
- coach-readable explanations;
- model cards and dataset cards;
- public demo on legally redistributable data.

## Frontend showcase milestone (historical v0.4 label)

### Complete

- Static frontend bundle with 25-player study catalog
- Four illustrative featured scenarios
- 4K tactical, temporal, style, and counterfactual exports
- Optional FastAPI showcase service
- Google AI Studio build and iteration specifications
- Rights-aware media registry and embed-only YouTube discovery

### Next empirical sequence

1. Acquire or license at least 24 balanced clips for each featured player.
2. Reconstruct game state and record perception quality for every clip.
3. Annotate physical availability, visible availability, value, risk, and selected action separately.
4. Establish inter-rater reliability before publishing player comparisons.
5. Match contexts across players and providers.
6. Replace illustrative scenario profiles with measured, confidence-bounded summaries.
7. Add failed and falsifying examples to every named-player study.
8. Expand from four featured studies to twelve, then to the full candidate library.

## Product evidence transition

1. Curate balanced rights-cleared clips for the eight featured scenarios.
2. Add pose-based head and torso orientation with calibrated uncertainty.
3. Validate scan-event proxies against wearable or broadcast-derived head-pose labels.
4. Add teammate-response and opponent-displacement matched controls.
5. Replace illustrative research emphasis with context-normalized measurements for the first five players.
6. Build a real frontend from the Gemini specification and run visual regression tests at mobile, 1080p, and 4K.
7. Add coach annotation for gaze relevance, receiving posture, and collective influence.
8. Publish negative results and provider-specific failure cases.
