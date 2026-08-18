# Temporal Affordance Volume v1.2 · Time Slice Surgery

## Objective

v1.2 should make the temporal axis analytically separable without weakening the central visual idea that **height means future time**.

v1.1 makes every retained voxel inspectable. v1.2 should answer the next research question:

> What exactly changes between now, +0.25 s, +0.5 s, +1.0 s, and +1.5 s when perspective and overlapping layers are removed from the comparison?

The release is therefore not a new renderer. It is a **temporal dissection layer** on top of the same sparse, auditable volume.

## User modes

### 1. Full volume

The current v1.1 presentation remains the default. All retained horizon layers are visible and the Voxel Inspector remains active.

### 2. Single slice

A user selects one exact forecast horizon. Only voxels assigned to that horizon slice remain visible.

Required presets:

- `0.00 s`
- `0.25 s`
- `0.50 s`
- `1.00 s`
- `1.50 s`

The implementation must also support arbitrary available layer times when the configured number of horizon steps changes.

### 3. Slice band

A lower and upper temporal clipping boundary define a visible band, for example `+0.25 s → +0.75 s`.

The band must be expressed in forecast seconds, not world-space rendering height.

### 4. Linked top-down slice

A second synchronized view shows the selected slice as a 2D pitch field. It must use the exact same retained voxel values as the 3D view, not recompute a visually similar heatmap through a separate formula.

Selecting a voxel in either view selects the same voxel in both.

## Architecture

### Preserve one scientific scene

`buildAffordanceVolume()` remains the source of truth for the retained sparse voxel set.

v1.2 should add a pure temporal visibility transform:

```text
VolumeScene.voxels
      ↓
SliceFilter(mode, lower_seconds, upper_seconds)
      ↓
visible voxel indices
      ↓
GPU instance buffer + linked 2D slice
```

The slice system should never evaluate football geometry itself.

### Stable voxel identity

v1.1 voxel IDs already encode:

```text
frame : channel : layer : grid_x : grid_y
```

v1.2 must preserve those IDs across full-volume and slice modes. Selection therefore survives a view-mode change when the selected voxel is still visible, and clears explicitly when it is clipped out.

### GPU strategy

For the current sparse workload, prefer CPU-side index filtering followed by a compact instance upload. This keeps behavior identical between WebGPU and WebGL2 and remains easy to test.

Do not add shader clipping solely for novelty. Shader clipping should be considered only if measured buffer churn becomes a bottleneck.

### Optional horizontal guide plane

A translucent horizontal guide plane may mark the selected forecast horizon, but it must be visually subordinate to the voxels and labeled in seconds.

The guide plane is a rendering aid. It is not a data surface.

## Interaction design

### Timeline surgery control

Add a dedicated control block with:

- mode: `Full`, `Slice`, `Band`;
- exact slice selector when in `Slice`;
- lower/upper range handles when in `Band`;
- `Link top-down view` toggle;
- concise text such as `+0.50 s from focal state`.

### Camera behavior

Switching to a single slice should offer, but not force, a top-down camera preset. Users must be able to move back to the oblique view without losing the slice selection.

### Voxel Inspector integration

The v1.1 inspector is mandatory in every v1.2 mode.

The inspector should add:

- whether the selected voxel is inside the active temporal filter;
- active slice/band bounds;
- previous/next layer values for the same pitch cell when those cells exist in the retained sparse set.

This creates a small local temporal derivative without inventing interpolation.

## Scientific guardrails

v1.2 must preserve all v1.1 boundaries:

- no future observed tracking frames may populate future slices;
- filtering cannot change voxel values;
- a missing voxel after sparse pruning is **not** equivalent to a true zero;
- a slice is a focal-state-derived forecast at a named horizon;
- provider visibility and orientation proxies remain visually and textually distinct;
- brightness remains a visualization score unless calibration metadata explicitly says otherwise;
- option creation remains an emerging-geometry signal, not causal attribution.

The linked 2D slice must display missing/pruned cells differently from evaluated zero-valued cells if the latter become part of a later dense representation.

## Performance targets

The v1.2 feature should not increase the normal full-volume GPU draw-call budget.

Targets for the current sparse architecture:

- full-volume mode: unchanged from v1.1;
- single-slice mode: fewer uploaded field instances than full-volume mode;
- band mode: upload only retained voxels within the active horizon band;
- no GPU readback for filtering or picking;
- filter changes should avoid rebuilding pitch/player solid instances;
- interaction should remain responsive at the existing high budget of roughly 4,200 retained field voxels.

A performance regression test should compare instance counts before and after slice filtering rather than claiming a universal FPS target across hardware.

## Test plan

### Unit tests

1. Full mode returns every retained voxel.
2. Exact slice mode returns only the requested layer/time.
3. Band mode is inclusive at both boundaries.
4. Filtering never mutates voxel values or IDs.
5. Selection persists when its voxel remains visible.
6. Selection clears when its voxel is clipped out.
7. Linked 2D cells reference the exact same voxel IDs.
8. Previous/next temporal neighbor lookup never interpolates a missing voxel.

### Browser tests

1. `/volume` opens in Full mode.
2. Switching to `+0.50 s` reduces or preserves the visible voxel count, never increases it.
3. The time-axis label and control agree on the selected horizon.
4. A selected v1.1 voxel remains inspectable in slice mode when visible.
5. The linked top-down slice can select a voxel and synchronize the 3D marker.
6. Returning to Full restores the original scene count.
7. Scientific boundary copy remains visible.

### Cross-backend contract

The same slice filter output must feed WebGPU and WebGL2. No backend-specific tactical values are allowed.

## Delivery sequence

### v1.2.0-a · Pure slice model

- implement `VolumeSliceFilter` types and pure filtering functions;
- unit-test IDs, boundaries, counts, and non-mutation;
- no UI yet.

### v1.2.0-b · 3D clipping controls

- Full/Slice/Band controls;
- selected-horizon guide plane;
- inspector integration;
- browser tests.

### v1.2.0-c · Linked top-down slice

- exact same voxel IDs and values;
- synchronized selection;
- top-down camera preset;
- accessibility pass.

### v1.2.0-rc · Performance and publication polish

- measure buffer upload sizes by mode;
- capture deterministic screenshots for key horizons;
- add figure-export choreography;
- freeze the updated frontend contract.

## Definition of done

v1.2 is complete when a researcher can freeze the volume at an exact forecast horizon, compare a temporal band, inspect any surviving voxel, and move between 3D and a linked top-down slice without changing the underlying tactical values or their provenance.

The release should make time easier to reason about, not merely add another slider.
