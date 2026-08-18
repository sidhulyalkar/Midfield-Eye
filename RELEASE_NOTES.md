# Release Notes

## R1 · Real Action Menu Pilot

### Real-pilot control plane

- Added a deterministic ten-sequence R1 sampler with the frozen 3/2/2/2/1 diversity mix, 5 Hz focal labels, causal context, and non-overlapping source-frame checks.
- Added a score-free blinded candidate export, full double-rating assignment packs, a post-rating selection template, and an auditable sample-review/sign-off step that never regenerates the candidate freeze.
- Added R1 status and finalization ledgers so incomplete, failed, adjudication-needed, and benchmark-complete states remain machine-readable rather than being summarized by hand.

### Metrica Tier A bridge

- Added event-supported receipt-window construction from synchronized Metrica home/away tracking and PASS events.
- The recorded passer defines causal pre-pass context and the recorded recipient becomes the carrier only at or after the pass end frame.
- Post-receipt frames must satisfy the frozen carrier-to-ball distance and control-duration gates; nearest-player carrier inference is removed from R1 publication windows.
- Added cross-match R1 source combining with duplicate source-frame and causal-state validation.

### Expert evidence workflow

- Upgraded the Streamlit annotator to accept randomized per-rater assignment packs and a separate causal-context file.
- Publication annotation remains outcome-blind and model-score-blind, with selected-action controls unavailable by default.
- R1 requires full double rating of every frozen candidate so the reliability design and 100% consensus-coverage requirement cannot conflict.
- Added one-command fail-closed finalization: reliability → adjudication → consensus → causal-feature contract → immutable expert freeze → human-signed provider quality → benchmark.

### R1 benchmark and showcase

- Added `configs/r1_benchmark.yaml`, which intentionally runs Tier A as sequence-held-out only. Provider-held-out replication is deferred to R2.
- Added the `/pilot` research cockpit: falsifiable question, five-rung evidence ladder, frozen pilot composition, blinding contract, empty-result state, benchmark table, and staged R1→R4 improvement path.
- The showcase payload is generated from real R1 artifact state. It never displays benchmark metrics before the corresponding evidence files exist.
- Added `docs/R1_REAL_ACTION_MENU_PILOT.md` as the executable runbook and research-expansion plan.

## v0.7.0 · The Action Menu Benchmark

### Research contract

- Added a frozen action-menu annotation ontology that keeps availability, visibility, value, creation, selection, and confidence separate.
- Added explicit outcome-blinding, sequence-level sampling, double-rating, reliability, and causal-use guardrails.
- Added stable option identities across frames without changing the existing frame-local affordance IDs.
- Added retrospective option lifecycle, birth/extinction, top-k stability, and selected-frame reporting.
- Added a command-line report builder for candidate CSVs and tests for lifecycle and annotation invariants.

### Decision Microscope

- Added the Action Menu Ribbon to scenario playback.
- Ribbon cells seek the synchronized frame and candidate while preserving the existing pitch, evidence, and URL-state controls.
- Added current-time rails, observed-selection markers, missing-candidate gaps, mobile layout, keyboard-compatible controls, and reduced-motion behavior.
- Kept lifecycle semantics explicitly retrospective so the visualization cannot be mistaken for a future-aware model feature.

### Release hygiene

- Bumped the Python package to 0.7.0.
- Corrected `CITATION.cff` to use the CFF 1.2.0 schema instead of the project version as the schema version.
- Added `docs/ACTION_MENU_BENCHMARK.md` and `configs/action_menu_annotation_v1.yaml` as the v0.7 research specification.
- No empirical superiority claim is added by this release. The real expert-annotated pilot remains the publication gate.

## v0.6.0 · Empirical Evidence Studio

### Real source-backed examples

- Added a 15-frame Metrica Sample Game 1 excerpt with synchronized pass event and upstream blob SHAs.
- Added Pedri's real StatsBomb event and matching 360 snapshot from Spain versus Germany, match 3857263.
- Added 4K empirical pitch views, source landscape, and evidence ladder.

### Data governance

- Added a 12-source registry with access mode, modality, official URL, license, redistribution rule, adapter, caveats, and acquisition plan.
- Added open-only download enforcement. Registered and license-request datasets cannot be silently downloaded.
- Added local SHA-256 manifests and verification.
- Added measured/inferred/unavailable field contracts and direct-claim validation.

### Gaze and biomechanics

- Added Ego-Exo4D gaze CSV ingestion.
- Added WorldPose JSON/NPZ export ingestion.
- Added OpenCap/OpenSim MOT ingestion.
- Added detailed gaze and body-mechanics capture protocols.
- Added sensor-clock drift fitting, explicit gaze-to-frame alignment, missingness preservation, and a transparent scan-event baseline.
- Added a machine-checkable consent, calibration, synchronization, retention, and task-block capture contract.

### Frontend

- Added empirical API routes and OpenAPI contract, including capture-protocol and alignment-contract endpoints.
- Added Gemini instructions for Evidence Studio, Source Planner, Evidence Ledger, and Capture Studio.
- Preserved all v0.5 atlas, scenario, perception, body, and relational-control features.
