# v1.3 Difference Rendering and Forensics

## Scope

v1.3.0-b converts the pure support algebra from v1.3.0-a into the existing 10-float instanced-GPU format without converting comparison cells back into ordinary `VolumeVoxel` records.

The rendering payload and the scientific comparison record remain separate objects linked by exact reference.

## Visual grammar

The temporal coordinate is untouchable:

```text
worldY = forecast horizon
```

No comparison sign, magnitude, or support state may move a glyph up or down the temporal axis.

### Intersection

A cell retained in A and B renders as one filled inset cube at the original cell center.

- signed value: `B - A`
- positive, negative, and zero use different display colors
- opacity increases with absolute delta on the existing 0–1 field scale
- geometry remains a single filled cell

### A-only support

`left_only` has no numerical delta. It renders as **two parallel rails along the pitch-Y/world-Z footprint**.

The two-rail shape, not color alone, communicates categorical A-only support.

### B-only support

`right_only` also has no numerical delta. It renders as **two parallel rails along the pitch-X/world-X footprint**, orthogonal to A-only rails.

The orthogonal rail grammar remains distinguishable in grayscale and does not imply positive or negative numerical effect.

## Instance contract

Every GPU instance keeps the existing stride:

```text
position.xyz
scale.xyz
color.rgba
```

`INSTANCE_STRIDE = 10` remains unchanged.

Expected instance counts are deterministic:

```text
intersection → 1 instance
left_only    → 2 instances
right_only   → 2 instances
```

All instances for a comparison cell remain at the source voxel's exact `worldY` temporal height.

`VolumeDifferenceRenderCell` records the instance start/count alongside the exact source `VolumeDifferenceCell` reference.

## Forensic inspector contract

`inspectVolumeDifferenceCell()` resolves by canonical comparison key and exposes:

- support state;
- whether a numerical comparison is available;
- frozen `B - A` sign convention;
- signed/absolute delta only for intersections;
- condition A retained status, stable voxel ID, value, and exact source voxel record;
- condition B retained status, stable voxel ID, value, and exact source voxel record;
- explicit claim-boundary fields stating that one-sided presence is not zero, missing support is not interpolated, intensity is not calibrated probability, and future observed frames are not used.

No one-sided inspection record contains a synthetic zero.

## Deterministic fallback selection

`mostInformativeDifferenceCell()` is intentionally not called “strongest.”

1. If numerical intersections exist, choose largest absolute delta.
2. Break equal-magnitude ties by integer `(layerIndex, gridXIndex, gridYIndex)` order.
3. If no numerical intersection exists, choose the earliest categorical cell by the same integer identity.

Categorical support is therefore selectable without inventing a magnitude ranking.

## Validation status

GitHub Actions remains unavailable because repository quota is exhausted.

The new v1.3.0-b pure modules received standalone sandbox verification using faithful local copies plus minimal type stubs:

- strict TypeScript compilation passed with `noUncheckedIndexedAccess` and `exactOptionalPropertyTypes`;
- one intersection + one A-only + one B-only comparison produced exactly five GPU instances;
- A-only and B-only produced the expected orthogonal glyph identifiers;
- both one-sided render cells preserved `signedDelta = null`;
- forensic inspection of A-only support preserved the B side as not retained and `delta = null`;
- deterministic fallback selected the numerical intersection.

This is direct execution evidence for the new adapter/forensic logic. It is not a claim that repository Prettier, ESLint, Vitest, production build, Playwright, or Python checks ran.

## v1.3.0-c boundary

The next checkpoint owns application integration:

- explicit A/B condition construction;
- shared WebGPU/WebGL2 upload of the difference field payload;
- synchronized 3D and linked top-down comparison views;
- CPU-side comparison-cell picking;
- URL state for condition IDs and integer temporal filters;
- citable comparison JSON export;
- stale-comparison fingerprinting across condition/frame/channel/LOD/threshold transitions.
