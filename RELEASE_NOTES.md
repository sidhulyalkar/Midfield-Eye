# Release Notes

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
