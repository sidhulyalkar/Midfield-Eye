# Temporal Affordance Volume v1.2 · Time Slice Surgery

v1.2 turns the Temporal Affordance Volume from an inspectable 3D forecast into a temporally dissectable, reproducible research instrument.

The scientific object is still the retained voxel set produced by `buildAffordanceVolume()`. v1.2 does not introduce a second tactical model, a second 2D heatmap, temporal interpolation, or a new GPU truth. It adds controlled views over the same retained scientific records.

## Release sequence

v1.2 was deliberately developed as three independently testable checkpoints.

### v1.2.0-a · Pure temporal filter

- temporal identity is the non-negative integer `layerIndex`
- Full mode returns the original `VolumeScene`
- Slice and Band select retained voxels by integer layer membership only
- filtered scenes reuse the exact `VolumeVoxel` objects
- filtered GPU buffers copy the exact aligned instance records from the full retained scene
- same-cell trajectories key on `(frameId, channel, gridXIndex, gridYIndex)`
- pruned layers are explicit `not_retained` gaps with `null` value, never synthetic zero
- strongest-visible and click-picking ties are deterministic

### v1.2.0-b · 3D surgery

- Full, exact Slice, and inclusive Band modes
- every configured discrete horizon remains selectable
- current seven-layer default exposes `0.00`, `+0.25`, `+0.50`, `+0.75`, `+1.00`, `+1.25`, and `+1.50 s`
- exact Slice uses four solid guide rails at the selected temporal layer height
- Band uses guide rails at both temporal boundaries
- guide rails live in the existing solid pass, so the renderer remains two-pass
- WebGPU and WebGL2 consume the same filtered scene
- the v1.1 Voxel Inspector persists when its stable voxel ID remains visible and clears when the temporal cut removes it
- the same-cell trajectory shows retained values and explicit gaps across integer layers

Guide rails are intentional. A filled cutting plane would visually imply a continuously evaluated surface between sparse retained cells. Rails mark the analytical cut without inventing that continuity.

### v1.2.0-c · Linked slice and reproducibility

- exact Slice mode gains a linked top-down SVG view
- the linked view receives `visibleScene.voxels` directly
- each 2D cell exposes the exact stable voxel ID and retained value from the 3D scene
- there is no separately computed 2D tactical heatmap
- selecting a 2D cell calls the 3D instrument by the same stable voxel ID
- temporal view state is serialized in the URL using integer indices
- malformed, floating, reversed, or out-of-range URL state fails closed to Full
- unrelated query state such as `scenario` is preserved
- an inspected voxel can be exported as JSON with its complete forensic record, active temporal filter, evidence boundary, and same-cell trajectory

## URL contract

- `tm=full`
- `tm=slice&layer=<integer>`
- `tm=band&from=<integer>&to=<integer>`

The URL stores layer identity, not floating-point seconds. Seconds remain presentation labels derived from the configured horizon.

## JSON inspection artifact

The v1.2 export schema includes:

- schema version `1.2.0`
- complete retained `VolumeVoxel` forensic record
- stable voxel ID
- frame, channel, integer layer and grid indices
- pitch coordinates and forecast horizon
- all component field values
- local option contributors and nearby-player drivers
- visibility and uncertainty evidence mode
- source provider
- active Full/Slice/Band filter
- same-cell trajectory ordered by integer layer index
- explicit `not_retained` trajectory gaps with `voxelId: null` and `value: null`
- `futureObservedFramesUsed: false`
- `calibratedProbability: false`
- `missingLayerSemantics: not_retained_not_zero`

## Scientific invariants

The following are release-blocking invariants:

1. `buildAffordanceVolume()` is the scientific source of truth.
2. View mode may select a subset of retained voxels but may not recompute tactical values.
3. The 3D and linked 2D views share stable voxel IDs and values.
4. A pruned or clipped voxel is absence of retained evidence, not a numerical zero.
5. Same-cell trajectories do not interpolate missing layers.
6. Future forecast layers do not consume later observed tracking frames.
7. Brightness remains a visualization score, not a calibrated probability.
8. The renderer remains two-pass and requires no GPU readback for inspection or slicing.

## Test strategy

The release uses three levels of evidence:

- unit tests for integer filtering, object/GPU-instance preservation, trajectory gaps, deterministic picking, guide geometry, URL parsing, linked-view identity, and JSON serialization
- strict frontend checks for formatting, TypeScript, lint, unit tests, and production build
- Playwright for Full → Slice → Band interaction, selection persistence/invalidation, linked 2D/3D selection, URL reload restoration, and JSON download across the repository viewport matrix

A browser test during v1.2.0-b originally assumed the demo's strongest selected cell would necessarily contain a pruned layer. That assumption was intentionally removed: deterministic synthetic gap semantics belong in the unit model; browser coverage verifies the user-visible gap contract and the real interaction lifecycle. No scientific behavior was weakened.

## What v1.2 still does not claim

Time Slice Surgery does not turn a focal-state kinematic forecast into observed future truth. It does not make orientation proxies into eye tracking, make option-creation geometry causal, or make field intensity calibrated probability. R1 benchmark claims remain governed separately by real annotated evidence.

## Next release direction

v1.3 should add evidence-aware signed difference volumes. Difference must be defined over explicit support states:

- `intersection`: both conditions retain the same spatial/layer cell, so a signed numerical delta is valid
- `left_only`: retained only in condition A
- `right_only`: retained only in condition B
- `neither`: absent from the comparison visualization

One-sided presence must never be converted into a numeric difference against zero. This preserves the same evidence discipline introduced by v1.2 trajectories.
