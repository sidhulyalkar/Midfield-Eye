# Release Notes

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
