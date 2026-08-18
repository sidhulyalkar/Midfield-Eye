# Temporal Affordance Volume 3D

## Status

- **v1.0:** sparse temporal affordance lattice, WebGPU-first renderer, WebGL2 fallback.
- **v1.1:** Voxel Inspector, deterministic picking, per-cell forensic metadata, evidence-aware drill-down.
- **v1.2 planned:** Time Slice Surgery. See [`V1_2_TIME_SLICE_SURGERY_PLAN.md`](./V1_2_TIME_SLICE_SURGERY_PLAN.md).

## Purpose

The **Temporal Affordance Volume** is the 3D research instrument for The Midfielder's Eye. It makes the central research object visible: not only the action eventually selected, but the changing field of actions, pressure, space, accessibility, and uncertainty surrounding a decision.

The design is intentionally not a stadium diorama. The third dimension carries scientific meaning.

```text
render x  = pitch x in metres
render z  = pitch y in metres
render y  = causal forecast horizon
```

The bottom layer is the focal state. Higher layers move toward the configured short horizon, currently +1.5 s in the showcase. A ridge that rises or leans through the volume therefore represents a field changing through time, not a player or tactical feature becoming physically taller.

## Core semantic contract

### Pitch coordinates

Pitch position always remains in the canonical metric coordinate system. The volume does not silently flip attack direction, stretch one pitch axis independently, or reinterpret coordinates for visual convenience.

### Vertical coordinate = future time

The vertical axis is a rendering transform of forecast horizon only. It must never be described as physical player height.

The current implementation propagates the **focal state** using available velocity and deterministic geometry. It does not read later observed tracking frames to populate future layers.

A future voxel is therefore:

- a focal-state-derived forecast visualization;
- not an observed future state;
- not calibrated probability unless a later model explicitly provides calibration metadata;
- not an expert label;
- not evidence that the forecast was correct.

## Voxel channels

The renderer exposes eight switchable fields:

1. **Action menu composite**: fused future space, corridors, option creation, perceptual access, pressure, and uncertainty. It is explanatory, not a learned probability.
2. **Pressure fronts**: opponent influence propagated from focal position and velocity.
3. **Pressure shadows**: geometric space screened behind defenders relative to the carrier. This is not literal visual occlusion.
4. **Future space**: estimated openness under focal-state motion propagation.
5. **Passing corridors**: candidate-aligned tubes weighted by the frozen geometric option score.
6. **Option creation**: places whose openness improves relative to the focal slice. This does not establish causal responsibility.
7. **Perceptual access**: visibility polygons when present, otherwise an explicitly labeled carrier orientation proxy.
8. **State uncertainty**: uncertainty accumulated from tracking status, confidence, and covariance when available.

## Rendering architecture

The current implementation deliberately uses **sparse instanced voxels**, not a general-purpose 3D scene graph and not dense ray marching.

### Field generation

For every focal frame:

1. choose an adaptive X/Y grid;
2. evaluate the selected field channel across each horizon slice;
3. attach a forensic metadata record to every evaluated retained cell;
4. discard cells below the user-controlled signal threshold;
5. sort surviving cells deterministically by signal strength and stable grid identity;
6. enforce the configured voxel budget;
7. upload only retained instances to the GPU.

Low-value empty volume is removed before rendering work begins.

### Shared mesh and two passes

All voxels, pitch segments, players, and the ball reuse one cube primitive. Per-instance GPU data remains:

```text
position.xyz
scale.xyz
color.rgba
```

The instance stride remains 10 floats.

The renderer performs two conceptual draws:

1. opaque/depth-writing geometry for pitch, players, and ball;
2. translucent/non-depth-writing field voxels.

The v1.1 inspector does **not** add a GPU picking pass and does not require GPU readback.

### WebGPU first, WebGL2 fallback

The runtime attempts WebGPU first. If WebGPU is unavailable or initialization fails, it uses WebGL2 instancing.

The fallback is part of the renderer contract. The research instrument should remain inspectable without WebGPU.

## v1.1 · Voxel Inspector

v1.1 turns the volume from a dramatic tactical landscape into a forensic research instrument.

### Selection behavior

A click on the canvas performs deterministic CPU-side screen-space picking over the **retained voxel set**. Dragging continues to orbit the camera. A short movement threshold separates a click from a navigation gesture.

For keyboard and non-precision-pointer use, **Inspect strongest voxel** selects the strongest currently visible retained cell.

The selected cell is marked by a screen-space crosshair that is reprojected whenever the camera moves or the canvas resizes.

Selection is invalidated if a frame, channel, quality, threshold, or sparse-budget change removes that voxel from the current scene. The inspector cannot display a stale cell from a previous visual state.

### Forensic payload

Every retained voxel exposes:

- stable voxel ID;
- frame ID;
- channel;
- layer and X/Y grid indices;
- exact pitch X/Y in metres;
- forecast horizon in seconds;
- world-space render coordinates and cell dimensions;
- active channel value;
- all eight channel component values at that same X/Y/time cell;
- nearest defender and teammate IDs and forecast distances;
- up to four strongest local pass/carry corridor contributions;
- each contribution's local value and frozen geometric option score;
- visibility evidence mode;
- uncertainty evidence mode;
- source provider;
- explicit `futureObservedFramesUsed = false` provenance.

The GPU instance buffer and the forensic record remain index-aligned after pruning.

### Evidence modes

Visibility is labeled as one of:

- `visibility_polygon`;
- `orientation_proxy`;
- `unknown`.

Uncertainty is labeled according to the available focal-state fields:

- covariance + confidence + tracking status;
- covariance + tracking status;
- confidence + tracking status;
- tracking status only.

The inspector does not silently promote an orientation proxy to observed gaze or a tracking-status heuristic to measured covariance.

### Why CPU picking is intentional

At the current maximum of only a few thousand retained cells, CPU projection is the more auditable engineering choice:

- no additional render pass;
- no encoded ID buffer;
- no GPU readback synchronization;
- identical behavior across WebGPU and WebGL2;
- deterministic unit tests can project a voxel and round-trip the click back to the same ID;
- selection remains a UI query over the scientific scene rather than a second rendering truth.

If a later dense ray-marched tier contains hundreds of thousands or millions of samples, the picking architecture can be revisited without changing the v1.1 voxel identity contract.

## Current performance budgets

The current showcase uses the following pitch grids before pruning:

| Quality | Pitch grid | Temporal slices | Raw cells before pruning |
| --- | ---: | ---: | ---: |
| Low | 20 × 13 | 7 | 1,820 |
| Medium | 28 × 18 | 7 | 3,528 |
| High | 38 × 25 | 7 | 6,650 |

Sparse UI budgets remain approximately:

- low: 1,200 field voxels;
- normal/auto: 2,800 field voxels;
- high: 4,200 field voxels.

Other safeguards:

- canvas device-pixel ratio capped at 2;
- auto LOD on narrow/high-DPR screens;
- weak cells removed before GPU upload;
- power-of-two WebGPU buffer growth;
- live backend/grid/voxel/draw-call diagnostics;
- inspector picking requires no extra GPU draw call.

These are implementation budgets, not universal frame-rate claims.

## Showcase choreography

The recommended v1.1 demonstration is:

1. **Action menu composite**: establish that height means when, not where.
2. **Pressure → pressure shadow**: show where the defense is arriving and what geometry it screens.
3. **Future space → option creation**: distinguish room that exists from room becoming available.
4. **Voxel Inspector**: click a bright cell and expose the exact coordinates, horizon, component values, contributors, nearby players, and evidence status underneath the glow.
5. **Passing corridor → perceptual access**: show that a route may be physically available without being equally accessible from the player's information state.
6. **Decision Microscope**: return to the synchronized 2D action-menu view for exact frame/candidate interpretation.

The signature v1.1 reveal is simple:

> **Every glow can now defend itself.**

## Evidence and claim boundary

The 3D instrument may communicate:

- deterministic focal-frame geometry;
- focal-state-derived short-horizon forecasts;
- visibility polygons when present;
- explicitly labeled orientation proxies;
- explicit uncertainty evidence modes;
- candidate corridors from the frozen action-menu generator;
- exact per-voxel component values and local contributors.

It must not imply:

- that a synthetic scenario is measured match evidence;
- that a focal-state forecast is later observed truth;
- that a visibility proxy is observed gaze;
- that option creation establishes causal responsibility;
- that a bright voxel is calibrated probability;
- that B2 beats B1 before the real expert benchmark establishes that result.

R1 benchmark metrics and reliability state remain controlled by the existing fail-closed pilot artifacts.

## v1.2 · Time Slice Surgery

v1.2 is deliberately planned as a temporal analysis release rather than a renderer rewrite.

It will add:

- Full / exact Slice / temporal Band modes;
- named horizon presets including now, +0.25 s, +0.5 s, +1.0 s, and +1.5 s;
- a linked top-down slice using the **same voxel IDs and values** as the 3D volume;
- selection synchronization with the v1.1 inspector;
- previous/next retained-cell comparison for the same pitch location;
- explicit distinction between a pruned/missing voxel and a true zero if a later representation supports evaluated zeros.

The full architecture, test plan, performance constraints, and delivery sequence are frozen in [`V1_2_TIME_SLICE_SURGERY_PLAN.md`](./V1_2_TIME_SLICE_SURGERY_PLAN.md).

## Later dense tier

Only after the scientific workload earns the complexity should the project add a dense WebGPU backend using compute shaders and 3D storage textures.

Candidate architecture:

```text
focal state
   ↓
WebGPU compute field evaluation
   ↓
3D texture / sparse bricks
   ↓
empty-space skipping + transfer function
   ↓
ray-marched volume
   ↓
instanced players/candidates/annotations overlay
```

The sparse backend should remain available for exact cell inspection, debugging, publication figures, and reproducible comparison even after a dense renderer exists.

## Validation contract

v1.1 is expected to remain gated by:

- strict TypeScript compilation;
- ESLint;
- Prettier;
- existing voxel field invariants;
- forensic metadata alignment tests;
- deterministic projection and picking tests;
- candidate-contribution tests;
- visibility evidence-mode tests;
- production frontend build;
- Playwright coverage of selection, invalidation, and evidence copy;
- the full Python/R1 suite on Python 3.10, 3.11, and 3.12;
- existing demo and demo-v2 smoke tests.

The visualization remains part of the same repository quality gates as the research system rather than a separate demo.
