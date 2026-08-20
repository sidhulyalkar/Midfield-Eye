## v1.3.0-rc · Publication Choreography

This RC turns the merged evidence-aware difference workbench into a deterministic paper/export artifact without introducing a second scientific implementation.

### What it adds

- `pub=figure` publication presentation on the existing `/volume/compare` scientific URL
- exact-Slice-only paper figure choreography
- stable figure IDs derived only from scientific state
- fixed publication plate with intervention geometry, exact difference slice, support accounting, failure gallery, and claim footer
- grayscale/CVD-safe structural grammar: `+/-/0`, opposing diagonal hatches, vertical A-only rails, horizontal B-only rails
- strict canonical publication URL gate in both page and CLI
- Playwright export script producing plate PNG, print PDF, and provenance manifest
- authored Vitest/Playwright contracts
- explicit v1.3 release/claim contract and validation record

### Scientific boundary

The RC is downstream-only. It does **not** modify `buildAffordanceVolume()`, the v1.3 support algebra, earlier-run intervention construction, difference render semantics, or WebGPU/WebGL2 backends.

The publication page reconstructs the same comparison encoded by the URL using the same `buildVolumeComparison()` path as the interactive workbench. There is no publication-specific field formula, smoothing, interpolation, or zero filling.

### Frozen evidence semantics

- `B - A` only on retained intersection
- `not_retained != 0`
- one-sided support is categorical, never numerical
- missing support is not interpolated
- publication summary statistics ignore one-sided cells numerically
- source evidence status is visible
- Condition B is a synthetic teaching intervention, not observed future truth or causal evidence
- candidate options included: false
- candidate options regenerated: false
- future observed frames used: false

### Reproducibility

Canonical publication URLs must contain exactly one of each:

`scenario`, `fi`, `cmp`, `lead`, `dc`, `dq`, `dt`, `tm`, `layer`, `pub`

with `cmp=earlier-run`, `pub=figure`, deterministic `dq`, supported lead/threshold values, and `tm=slice`.

The export CLI rejects duplicate/unknown/malformed query state before browser launch and verifies the loaded URL is byte-for-byte unchanged before capture.

### Validation status · Actions quota exception

GitHub Actions quota is exhausted. No green CI matrix is claimed.

Substitute evidence includes:
- standalone strict-TypeScript compilation of publication helper/page seams
- deterministic helper execution for figure identity, Slice gate, one-sided gallery selection, numerical summaries, and exact-record provenance
- Node syntax validation for exporter
- full branch-scope audit
- authored Vitest and Playwright contracts, not claimed as executed by the normal runner

See `docs/V1_3_RC_VALIDATION.md`, `docs/V1_3_RELEASE_CONTRACT.md`, and `docs/V1_3_PUBLICATION_EXPORT.md`.

Part of #9.