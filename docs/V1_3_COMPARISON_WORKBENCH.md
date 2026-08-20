# v1.3 Comparison Workbench

## Purpose

v1.3.0-c turns the pure evidence-support algebra and render grammar from v1.3.0-a/b into a reproducible comparison instrument.

The first visible comparison is intentionally narrow:

> **How does the state-derived future-space field change if one off-ball teammate is already farther along the run they are making now?**

This is a synthetic teaching intervention, not observed future truth and not a causal estimate.

## Condition construction

Condition A is the current focal frame.

Condition B is produced deterministically:

1. restrict candidates to possession-team players other than the current ball carrier;
2. require finite focal-state velocity and at least `0.25 m/s` speed;
3. calculate each candidate arrival as current position plus `velocity × leadSeconds`;
4. clip each candidate arrival to the declared pitch;
5. discard candidates whose clipped arrival produces no meaningful positional displacement;
6. choose the fastest remaining feasible teammate;
7. break equal-speed ties by stable player ID;
8. move only that teammate's current X/Y position to the clipped arrival;
9. preserve the player's velocity and every other player state;
10. if no feasible moving teammate exists, fail closed rather than inventing a direction.

Supported lead presets are `0.50`, `0.75`, and `1.00 s`.

The feasibility check matters at pitch boundaries. A faster runner already pinned to a touchline and moving outward must not block a slower teammate whose earlier-arrival intervention is still geometrically valid.

## Why the first comparison excludes Action Menu / Passing Corridors

The current frontend scenario bundle contains candidate `ActionOption` records generated for the baseline focal state. Moving a teammate changes the state from which candidate scores should be generated.

Reusing baseline candidate scores in condition B would create a visually appealing but scientifically stale comparison.

Therefore v1.3.0-c supports only:

- `future_space`
- `option_creation`

Both A and B call `buildAffordanceVolume()` with an empty candidate-option list. This ensures the compared field is derived from matched player-state geometry rather than stale baseline pass scores.

Action-menu comparison is deferred until counterfactual candidate regeneration is implemented end-to-end.

## Reproducible URL contract

A comparison URL identifies the full sparse experiment:

- `scenario=<scenario id>`
- `fi=<focal frame index>`
- `cmp=earlier-run`
- `lead=0.50|0.75|1.00`
- `dc=future_space|option_creation`
- `dq=low|medium|high`
- `dt=<retention threshold>`
- v1.2 temporal view: `tm=full|slice|band` plus integer `layer` or `from/to`

`auto` LOD is forbidden in the comparison workbench. A citable URL must not change its scientific grid because it was opened on a different display.

Threshold is serialized and snapped to the supported `0.025` retention grid. Malformed comparison state fails closed to deterministic defaults.

## Temporal surgery reuse

v1.3 does not invent a second slicing model.

The full `VolumeDifference` is built once. The visible comparison cell array is then filtered by the same integer-layer set logic introduced in v1.2.

Filtered views preserve exact `VolumeDifferenceCell` object identity and never recompute A, B, or the signed delta.

## 3D rendering

The comparison renderer reuses the existing `AdaptiveVoxelRenderer` and therefore preserves WebGPU/WebGL2 parity, the 10-float instance stride, and the two-pass rendering architecture.

The existing renderer's public `update()` signature currently names `VolumeScene`, although both backends consume only `solids` and `field` arrays. Rather than rewrite the large proven renderer while GitHub Actions capacity is unavailable, v1.3.0-c isolates this structural mismatch in one function:

`updateDifferenceRenderer(renderer, { solids, field })`

No fake voxel list, stats object, or comparison metadata is manufactured. The adapter is covered by a focused unit-test contract and should be removed if/when the renderer API is later narrowed to an explicit array-only scene type.

The 3D actor/pitch solids remain the Condition A focal-state context. The Condition B player displacement is shown explicitly in the intervention mini-pitch and forensic metadata. v1.3.0-c does not render a second ghost actor state inside the 3D field, avoiding an ambiguous dual-player encoding before that grammar is designed explicitly.

## 3D / 2D synchronization

The 3D canvas and linked top-down Slice view consume the same `VolumeDifferenceRenderCell` records.

Both use the same support grammar:

- filled cell: retained intersection with numerical `B - A`;
- vertical parallel rails: A-only support, numerical difference undefined;
- horizontal parallel rails: B-only support, numerical difference undefined.

Color communicates signed direction only where a numerical intersection exists. Shape communicates whether a number exists at all.

The linked SVG exposes one keyboard focus anchor rather than one tab stop per retained cell.

## CPU picking

Comparison picking remains CPU-side:

1. project the comparison-cell center with the existing orbit view-projection matrix;
2. reject cells outside the click radius;
3. choose smallest screen distance;
4. then closest projected depth;
5. then integer `(layerIndex, gridXIndex, gridYIndex)` identity.

No GPU ID pass or readback is introduced.

## Selection identity and stale-state safety

A selected comparison cell is tagged with a fingerprint containing:

- scenario;
- focal frame;
- field channel;
- earlier-run lead;
- deterministic quality;
- threshold;
- horizon duration/layer count;
- voxel budget.

A selection from browser history or a previous A/B experiment is ignored unless its fingerprint matches the current comparison. Temporal Full/Slice/Band changes may preserve selection only when the same canonical key remains visible.

## Forensic export

The JSON comparison artifact uses schema `1.3.0` and records:

- scenario and focal frame;
- field channel and integer temporal filter;
- support state;
- whether numerical comparison is valid;
- `B - A` only when valid;
- full condition A/B forensic sides;
- intervention ID, player, lead, speed, displacement, and before/after coordinates;
- explicit synthetic-teaching-intervention status;
- explicit one-sided-not-zero and no-interpolation boundaries;
- `futureObservedFramesUsed = false`;
- active-channel boundary: state-derived Future Space / Option Creation only;
- `candidateOptionsIncluded = false`;
- `candidateOptionsRegenerated = false`.

The last two fields are intentionally separate. This release neither feeds candidate options into the compared volumes nor regenerates a counterfactual option table.

## Navigation boundary

`/volume` and `/volume/compare` are separate instruments. Navigation uses exact matching for `/volume` so the single-condition and difference-volume tabs cannot both appear active on the comparison route.

## Validation status

GitHub Actions quota is exhausted, so the normal repository matrix is not being used as the v1.3.0-c release gate and no document or PR should imply a green matrix.

Available substitute evidence:

- standalone strict TypeScript compilation passed for the c-layer non-React modules;
- standalone execution verified deterministic earlier-run player selection, 1.5 m displacement for a 0.75 s lead in the original harness case, and fail-closed URL defaults;
- the harness exposed and led to a fix for `exactOptionalPropertyTypes` handling of absent `position_covariance`;
- a second strict TypeScript + execution harness verified that a faster boundary-blocked runner is skipped in favor of a slower feasible runner;
- standalone JSX compilation passed for `LinkedDifferenceSlice` after element-local keyboard event typing;
- standalone JSX compilation passed for `DifferenceVolume3D` with DOM-aware pointer-capture stubs;
- manual page audit caught and fixed an incorrect `addTemporalGuideRails` import;
- final PR audit caught and fixed the missing `candidateOptionsIncluded=false` export boundary and the nested `/volume` navigation-active collision;
- Playwright and Vitest coverage are authored but are not claimed as executed under the normal repository runner.

The v1.3.0-c promotion decision is therefore based on the scoped PR diff, direct standalone execution of the new pure logic, strict-TypeScript/JSX checks on the new seams, and documented fail-closed scientific boundaries rather than GitHub Actions status.
