# Temporal Affordance Volume 3D

## Purpose

The **Temporal Affordance Volume** is the 3D research instrument for The Midfielder's Eye. It is designed to make the central research object visible: not only the action eventually selected, but the changing field of actions, pressure, space, accessibility, and uncertainty surrounding a decision.

The design is intentionally not a stadium diorama. The third dimension carries scientific meaning.

```text
render x  = pitch x in metres
render z  = pitch y in metres
render y  = causal forecast horizon
```

The bottom layer is the focal state. Higher layers move toward the configured short horizon, currently +1.5 s in the showcase. A ridge that rises or leans through the volume therefore represents a field changing through time, not a player or tactical feature becoming physically taller.

## Core semantic contract

### X/Y pitch coordinates

Pitch position always remains in the canonical metric coordinate system. The volume does not stretch one pitch axis independently, silently flip attack direction, or reinterpret coordinates for visual convenience.

### Vertical coordinate = future time

The vertical axis is a rendering transform of forecast horizon only. It must never be described as physical player height.

The current implementation propagates the **focal state** using available velocity and deterministic geometry. It does not read later observed tracking frames to populate future layers.

This distinction is non-negotiable:

- a future voxel is a focal-state-derived forecast visualization;
- it is not an observed future state;
- it is not calibrated probability unless a later model explicitly provides calibration metadata;
- it is not an expert label;
- it is not evidence that the forecast was correct.

## Voxel channels

The renderer exposes eight switchable fields.

### 1. Action menu composite

A fused visualization of future space, passing corridors, option creation, perceptual access, pressure, and uncertainty.

This is an explanatory visualization score, not a learned probability and not the R1 benchmark target.

### 2. Pressure fronts

Opponent influence is propagated from focal position and velocity. The channel makes defensive pressure visible as a moving front through the temporal volume.

### 3. Pressure shadows

The channel estimates space screened behind defenders relative to the ball carrier. It is a geometric pressure-shadow proxy. It is not literal visual occlusion.

### 4. Future space

The channel estimates how open each pitch location becomes under focal-state motion propagation, using defender distance, support, and pressure.

### 5. Passing corridors

Current pass/carry candidates produce corridor tubes from the carrier toward their target. Corridor intensity is weighted by the frozen geometric option score.

### 6. Option creation

The channel highlights places whose openness improves relative to the focal slice. This visualizes emerging geometry. It does not establish that a particular player movement causally created the option.

### 7. Perceptual access

If a provider visibility polygon exists, the renderer can use it directly. Otherwise it falls back to a clearly labeled body/head/gaze-direction proxy around the carrier.

A proxy must never be described as observed gaze.

### 8. State uncertainty

The channel combines available tracking status, confidence, and position covariance into an uncertainty field. Missing uncertainty evidence remains missing rather than being silently treated as certainty.

## Rendering architecture

The current R1 implementation deliberately uses **sparse instanced voxels**, not a general-purpose 3D scene graph and not dense ray marching.

### Field generation

For every focal frame:

1. choose an adaptive X/Y grid;
2. evaluate the selected channel across each horizon slice;
3. discard cells below the user-controlled signal threshold;
4. sort surviving cells by signal strength;
5. enforce the configured voxel budget;
6. upload only the retained instances to the GPU.

This means low-value empty volume is removed before rendering work begins.

### Shared mesh

All voxels, pitch segments, players, and the ball reuse one cube primitive. Per-instance data contains:

```text
position.xyz
scale.xyz
color.rgba
```

The instance stride is 10 float values.

### Two GPU passes

The renderer performs two conceptual draws:

1. opaque/depth-writing geometry for pitch, players, and ball;
2. translucent/non-depth-writing field voxels.

Voxel count can therefore grow without draw-call count growing linearly with it.

### WebGPU first, WebGL2 fallback

The runtime attempts WebGPU first. If WebGPU is unavailable or initialization fails, it uses WebGL2 instancing.

The fallback is part of the renderer contract, not an optional compatibility patch. The research instrument should remain inspectable on browsers without WebGPU.

## Why sparse instancing is the R1 optimum

No renderer is universally optimal. The correct architecture depends on the scientific workload.

For R1, the important properties are:

- only a few thousand meaningful cells are needed;
- every visible cell should retain interpretable X/Y/time/channel semantics;
- thresholding and top-K pruning should be explicit;
- the browser fallback should remain straightforward;
- screenshots and demos should map cleanly back to deterministic calculations;
- renderer complexity should not outrun the evidence quality.

For that workload, sparse instancing is intentionally preferred over dense texture ray marching. A ray marcher becomes more attractive only when the scientific workload requires genuinely dense volumes, many uncertainty samples, or substantially longer temporal horizons.

## Current performance budgets

The current showcase uses the following pitch grids before pruning:

| Quality | Pitch grid | Default temporal slices | Raw cells before pruning |
| --- | ---: | ---: | ---: |
| Low | 20 × 13 | 7 | 1,820 |
| Medium | 28 × 18 | 7 | 3,528 |
| High | 38 × 25 | 7 | 6,650 |

The UI applies additional sparse budgets:

- low: up to roughly 1,200 field voxels;
- normal/auto: up to roughly 2,800 field voxels;
- high: up to roughly 4,200 field voxels.

Other runtime safeguards:

- device-pixel ratio is capped at 2 for the 3D canvas;
- auto LOD reduces the pitch grid on narrow/high-DPR screens;
- weak cells are removed before GPU upload;
- buffer growth uses power-of-two capacity on the WebGPU path;
- the live UI reports backend, grid, rendered voxel count, and draw calls.

These are implementation budgets, not empirical claims about universal frame-rate performance on all hardware.

## Showcase choreography

The strongest demonstration is a controlled decomposition rather than a rapid tour of every control.

### Beat 1 · Action menu composite

Open on the full temporal lattice. Establish the visual grammar immediately:

> **Height means when, not where.**

The viewer should understand that they are looking into the next short interval of the decision.

### Beat 2 · Pressure → pressure shadow

Switch to pressure fronts and orbit slightly so their direction through time is visible. Then switch to pressure shadows.

The conceptual question becomes:

> Where is the defense arriving, and what space is it screening while it gets there?

### Beat 3 · Future space → option creation

Future space answers where room will exist. Option creation answers where room is **becoming** more available relative to now.

This is one of the most important distinctions in the project.

### Beat 4 · Passing corridor → perceptual access

Show a strong physical corridor, then switch to perceptual access.

The conceptual reveal is:

> A route can be physically available without being equally accessible from the player's information state.

When visibility is only a proxy, the UI must say so.

### Beat 5 · Return to the Decision Microscope

Finish by returning to the synchronized 2D Decision Microscope / Action Menu Ribbon. The 3D volume explains the field; the 2D instrument preserves exact frame/candidate inspection and evidence detail.

The pair is stronger than either view alone.

## Evidence and claim boundary

The 3D instrument must remain subordinate to the evidence contract.

It may visually communicate:

- deterministic focal-frame geometry;
- focal-state-derived short-horizon forecasts;
- provider-observed visibility when present;
- explicitly labeled proxies;
- explicit uncertainty fields;
- candidate corridors from the frozen action-menu generator.

It must not visually imply:

- that a synthetic scenario is measured match evidence;
- that a focal-state forecast is later observed truth;
- that a visibility proxy is observed gaze;
- that option creation establishes causal responsibility;
- that a bright voxel is a calibrated probability;
- that B2 beats B1 before the real expert benchmark establishes that result.

R1 benchmark metrics and reliability state remain controlled by the existing fail-closed pilot artifacts.

## Evolution path

### V1 · Sparse temporal affordance lattice

Implemented now:

- eight field channels;
- vertical future-time semantics;
- adaptive grid and sparse threshold/top-K pruning;
- WebGPU-first rendering;
- WebGL2 fallback;
- instanced two-pass GPU rendering;
- orbit/zoom/reset camera;
- frame scrubbing;
- live renderer diagnostics;
- unit and browser regression tests.

### V1.1 · Voxel Inspector

Add GPU or CPU picking so a click exposes the exact:

- pitch X/Y;
- forecast time;
- channel value;
- component values;
- source/proxy status;
- candidate IDs contributing to the cell;
- uncertainty metadata.

This is the highest-value next visualization improvement because it turns the dramatic volume into a precise analytical microscope.

### V1.2 · Time-slice surgery

Add movable horizontal clipping planes and an isolated-slice mode. Researchers should be able to compare `now`, `+0.25s`, `+0.5s`, `+1.0s`, and `+1.5s` without perspective occlusion.

### V1.3 · Difference volumes

Only when bound to legitimate benchmark/model artifacts, support signed difference volumes such as:

- B2 dynamic minus B1 static;
- full observation minus masked observation;
- expert consensus value minus model value;
- source A minus independent replication source B.

Difference voxels should preserve both source values and never display an unexplained residual.

### R2 · Real replication binding

Bind the same 3D grammar to the independent Tier B tracking replication. The visualization should not be redesigned to flatter a provider.

### R3 · Observation stress test

Use the volume to compare full-pitch and partial-observation conditions, explicitly separating unavailable regions from low model values.

### R4 · Dense GPU volume tier

Only after the workload earns the complexity, add a dense WebGPU path using compute shaders and 3D storage textures.

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

Useful techniques at that stage include:

- 3D storage textures;
- compute-shader field evaluation;
- sparse bricks or clipmaps;
- empty-space skipping;
- temporal interpolation in texture space;
- uncertainty ensembles;
- order-independent transparency where needed;
- dynamic resolution tied to measured frame time.

The dense renderer should be added as another backend, not by deleting the sparse auditable path. Sparse voxels remain valuable for debugging, publication figures, and exact cell inspection.

## Validation

The implementation is covered by:

- strict TypeScript compilation;
- ESLint;
- Prettier;
- voxel field unit tests;
- deterministic camera-matrix tests;
- production frontend build;
- Playwright coverage of `/volume`;
- the full Python/R1 suite on Python 3.10, 3.11, and 3.12;
- existing demo and demo-v2 smoke tests.

The visualization is therefore integrated into the same quality gates as the rest of the research system rather than maintained as a separate demo.
