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
3. choose the fastest eligible teammate;
4. break equal-speed ties by stable player ID;
5. advance only that teammate's current X/Y position by `velocity × leadSeconds`;
6. clip the arrival to the declared pitch;
7. preserve the player's velocity and every other player state;
8. if no eligible moving teammate exists, fail closed rather than inventing a direction.

Supported lead presets are `0.50`, `0.75`, and `1.00 s`.

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
- candidate options are not regenerated or compared in this release.

## Validation status

GitHub Actions quota remains exhausted. The normal repository matrix has not run for v1.3.0-c and no document or PR should claim otherwise.

Available substitute evidence so far:

- standalone strict TypeScript compilation passed for the c-layer non-React modules;
- standalone execution verified deterministic earlier-run player selection, 1.5 m displacement for a 0.75 s lead in the harness case, and fail-closed URL defaults;
- the harness exposed and led to a fix for `exactOptionalPropertyTypes` handling of absent `position_covariance`;
- standalone JSX compilation passed for `LinkedDifferenceSlice` after element-local keyboard event typing;
- standalone JSX compilation passed for `DifferenceVolume3D` with DOM-aware pointer-capture stubs;
- manual page audit caught and fixed an incorrect `addTemporalGuideRails` import before merge;
- Playwright and Vitest coverage are authored but are not claimed as executed.

Before merge under the quota exception, the branch still requires a final changed-file audit and PR review of the page/route/styles boundary.
