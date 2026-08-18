# Temporal Affordance Volume 3D

## Status

- **v1.0:** sparse temporal affordance lattice, WebGPU-first renderer, WebGL2 fallback.
- **v1.1:** Voxel Inspector, deterministic CPU picking, per-cell forensic metadata, evidence-aware drill-down.
- **v1.2:** Time Slice Surgery, integer Full/Slice/Band filtering, same-cell trajectories, linked top-down slice, reproducible URL state, and forensic JSON export.

Detailed v1.2 release record: [`V1_2_TIME_SLICE_SURGERY_RELEASE.md`](./V1_2_TIME_SLICE_SURGERY_RELEASE.md).

## Purpose

The **Temporal Affordance Volume** is the 3D research instrument for The Midfielder's Eye. It visualizes the changing field of actions, pressure, space, accessibility, and uncertainty surrounding a football decision.

The third dimension carries scientific meaning:

```text
render x  = pitch x in metres
render z  = pitch y in metres
render y  = causal forecast horizon
```

The bottom layer is the focal state. Higher integer layers move toward the configured short horizon, currently +1.5 s in the showcase. Future layers are deterministic focal-state forecasts. They are not later observed tracking frames.

## Scientific source of truth

`buildAffordanceVolume()` remains the only tactical field generator used by the instrument.

For each focal frame it:

1. chooses the configured X/Y grid and integer temporal layers;
2. evaluates the requested field channel;
3. attaches a forensic metadata record to each cell;
4. removes cells below the sparse signal threshold;
5. orders retained cells deterministically;
6. applies the voxel budget;
7. produces the retained `VolumeVoxel[]` and index-aligned GPU instance buffer.

v1.2 view modes select from this retained set. They do not recompute tactical values.

## Channels

The instrument exposes eight explanatory fields:

1. **Action menu composite**
2. **Pressure fronts**
3. **Pressure shadows**
4. **Future space**
5. **Passing corridors**
6. **Option creation**
7. **Perceptual access**
8. **State uncertainty**

These remain visualization scores and proxies under the evidence rules in the repository. Brightness is not calibrated probability unless explicit calibration metadata is introduced later.

## Rendering architecture

The current implementation uses sparse instanced voxels rather than a dense ray-marched field.

Per-instance data remains:

```text
position.xyz
scale.xyz
color.rgba
```

The stride remains 10 floats.

The renderer remains two-pass:

1. opaque/depth-writing pitch, players, ball, and v1.2 temporal guide rails;
2. translucent/non-depth-writing field voxels.

WebGPU is attempted first and WebGL2 remains the fallback. Both backends consume the same `VolumeScene`. Voxel picking and temporal filtering require no GPU readback.

## v1.1 · Voxel Inspector

Every retained voxel exposes a stable forensic record including:

- stable voxel ID;
- frame, channel, integer layer, and grid indices;
- pitch coordinates and forecast horizon;
- active value and all component field values;
- nearest teammate/defender forecast drivers;
- strongest local pass/carry corridor contributors;
- visibility evidence mode;
- uncertainty evidence mode;
- source provider;
- explicit `futureObservedFramesUsed = false` provenance.

Click selection uses deterministic CPU projection. Drag remains camera orbit. The non-precision fallback **Inspect strongest visible voxel** uses an explicit tie-break:

1. highest active field value;
2. lexicographically smallest stable voxel ID.

Direct click ties use normalized pointer distance, then active value, then stable ID.

Selection is invalidated whenever its stable voxel ID is absent from the current rendered scene.

## v1.2 · Time Slice Surgery

### Integer temporal identity

Filtering uses `layerIndex`, never floating-point horizon equality. Seconds are labels derived from the configured horizon.

The current seven-layer default exposes:

```text
0.00
+0.25
+0.50
+0.75
+1.00
+1.25
+1.50 s
```

### Exact visible-set definition

The semantic operation is equivalent to:

```text
visibleVoxels = fullRetainedVoxels.filter(
  voxel => selectedLayerSet.has(voxel.layerIndex)
)
```

Full returns the original scene. Slice and Band copy the exact aligned GPU instance records for the selected retained voxels.

There is no interpolation and no zero-filling.

### 3D guide geometry

Slice adds four thin solid rails around the pitch footprint at the exact selected temporal height. Band adds rails at both temporal boundaries.

The rails mark the analytical cut without implying a continuously evaluated surface between sparse retained cells. They remain inside the existing solid renderer pass.

### Same-cell trajectory

For an inspected voxel, v1.2 extracts `(frameId, channel, gridXIndex, gridYIndex)` and searches the full retained set across integer layers.

The trajectory is ordered by `layerIndex`. If a layer was pruned, the entry is explicitly:

```text
status = not_retained
voxelId = null
value = null
```

A missing retained cell is not a synthetic zero.

### Linked top-down slice

Exact Slice mode exposes a synchronized SVG view that consumes the exact filtered `visibleScene.voxels` array used by the 3D instrument.

Every 2D cell carries the same stable voxel ID and retained value. Clicking or keyboard-selecting a 2D cell calls the 3D instrument by that stable ID, synchronizing:

- linked 2D highlight;
- 3D selection crosshair;
- Voxel Inspector forensic record.

There is no separately computed 2D heatmap.

### Reproducible URL state

Temporal view state is encoded by integer indices:

```text
tm=full
tm=slice&layer=<integer>
tm=band&from=<integer>&to=<integer>
```

Malformed floats, reversed bands, missing indices, and out-of-range indices fail closed to Full. Other query parameters, including `scenario`, are preserved.

### JSON forensic export

An inspected voxel can be exported as JSON. The artifact includes:

- schema version `1.2.0`;
- complete `VolumeVoxel` record;
- active temporal filter;
- same-cell trajectory;
- explicit null gaps;
- `futureObservedFramesUsed: false`;
- `calibratedProbability: false`;
- `missingLayerSemantics: not_retained_not_zero`.

This makes a visual inspection state reproducible outside the browser and suitable for research figures, debugging records, and supplementary artifacts.

## Performance budgets

Default pre-pruning grids remain:

| Quality | Pitch grid | Temporal layers | Raw cells |
| --- | ---: | ---: | ---: |
| Low | 20 × 13 | 7 | 1,820 |
| Medium | 28 × 18 | 7 | 3,528 |
| High | 38 × 25 | 7 | 6,650 |

Sparse field budgets remain approximately 1,200 / 2,800 / 4,200 voxels for low / normal / high.

Slice and Band never upload more field instances than Full because they operate only by subset selection over the retained field buffer.

Other safeguards remain:

- canvas DPR cap of 2;
- adaptive LOD;
- weak-cell pruning before upload;
- power-of-two WebGPU buffer growth;
- live backend/grid/voxel/draw-call diagnostics;
- no extra GPU picking or slicing pass.

## Evidence and claim boundary

The instrument may communicate deterministic focal-state geometry, short-horizon forecasts, explicitly labeled perceptual proxies, explicit uncertainty modes, candidate corridor geometry, and exact per-cell component values.

It must not imply:

- synthetic scenarios are measured match evidence;
- forecast layers are observed future truth;
- orientation proxies are observed gaze;
- option creation establishes causal responsibility;
- a bright cell is calibrated probability;
- a pruned or clipped voxel equals numerical zero;
- R1 model superiority before the real expert benchmark establishes it.

## Validation contract

v1.2 remains gated by the same repository matrix as the research system:

- Python 3.10 / 3.11 / 3.12;
- Ruff;
- full pytest;
- both CLI demos;
- showcase generation;
- Prettier;
- strict TypeScript;
- ESLint;
- frontend unit tests;
- production frontend build;
- Playwright on mobile, desktop, Full HD, and 4K.

The v1.2 tests additionally cover integer filtering, exact object/GPU-instance preservation, deterministic picking, temporal guide geometry, explicit trajectory gaps, linked 2D/3D identity, URL restoration, and JSON download.

## Next direction

v1.3 should introduce **evidence-aware signed difference volumes**. Numerical difference is valid only where both conditions retain the same spatial/layer cell. One-sided support must remain an explicit evidence state rather than being converted to a difference against zero.
