# v1.3 Difference Support Algebra

## Purpose

v1.3 begins with a pure evidence-support model before any signed-difference rendering.

The core scientific rule is:

> A signed numerical difference exists only when the same canonical cell is retained in both conditions.

A missing or pruned voxel is not a numerical zero.

## Canonical comparison cell

Comparison identity is independent of frame ID and condition ID:

```text
(layerIndex, gridXIndex, gridYIndex)
```

The stable comparison key is:

```text
layerIndex:gridXIndex:gridYIndex
```

Condition-specific voxel IDs are preserved separately so the inspector can trace a comparison back to both original forensic records.

## Support states

The retained union is partitioned into exactly three rendered support states:

| Support | Condition A | Condition B | Numerical delta |
| --- | --- | --- | --- |
| `intersection` | retained | retained | `B.value - A.value` |
| `left_only` | retained | not retained | `null` |
| `right_only` | not retained | retained | `null` |

Cells retained in neither condition are counted in the summary as `neither` but omitted from the sparse comparison cell array.

The sign convention is frozen as:

```text
delta = conditionB.value - conditionA.value
```

Positive therefore means the active field is stronger in B than A.

## Required condition contract

`buildVolumeDifference()` does not accept an anonymous sparse array. Each side must provide:

- a non-empty condition ID;
- `retentionScope = full_retained_scene`;
- the full retained `VolumeScene`;
- horizon duration in seconds;
- pitch length and width in metres;
- the retention threshold used to build the scene.

The explicit metadata is necessary because sparse retention alone cannot prove that two disjoint scenes share the same temporal or spatial basis.

## Compatibility gate

Before support classification, both conditions must agree on:

- field channel;
- pitch length and width;
- horizon duration;
- X/Y grid dimensions;
- number of integer temporal layers;
- retention threshold;
- voxel budget;
- temporal render scale.

Each retained voxel must additionally satisfy:

- non-empty stable ID;
- matching channel;
- integer in-range layer/X/Y indices;
- finite value on the current `0..1` field scale;
- value not below the declared retention threshold;
- finite pitch/time/world coordinates;
- positive cell dimensions;
- pitch coordinates inside the declared pitch;
- forecast seconds equal to the timestamp implied by its integer layer;
- unique canonical comparison key.

The retained voxel count must match `stats.renderedVoxels`, and the field GPU buffer must contain exactly one `INSTANCE_STRIDE` record per retained voxel. This preserves the v1.2 forensic/GPU identity contract through comparison.

## Intersection gate

Even after a canonical key matches, a numerical difference is calculated only if the A/B cells agree, within tight numerical tolerance, on:

- pitch X/Y;
- forecast timestamp;
- cell X/Y/Z dimensions;
- rendered world X/Y/Z position.

A geometry mismatch fails closed rather than producing a misleading delta.

## Determinism

Comparison cells are ordered by:

1. `layerIndex`;
2. `gridXIndex`;
3. `gridYIndex`.

No sort depends on field magnitude, browser projection, object insertion order, or condition-specific voxel ID.

## Why one-sided support stays categorical

A `left_only` or `right_only` cell may arise because the underlying field changed, because the threshold removed one side, or because a fixed sparse budget retained a different set of cells. The current retained scenes do not contain enough evidence to distinguish those mechanisms safely.

Therefore one-sided presence is useful evidence, but it is **not** a numerical signed effect. v1.3.0-b must render it with a categorical visual grammar that is distinct from positive/negative intersection deltas and does not rely on color alone.

## Test contract

`volumeDifference.test.ts` defines adversarial cases for:

- valid `B - A` intersection deltas;
- exact left/right object-reference preservation;
- explicit `null` one-sided deltas;
- deterministic ordering;
- duplicate canonical cells;
- malformed layer timestamps;
- mismatched horizon, pitch, threshold, channel, grid, layer count, budget, and temporal render scale;
- mismatched intersection geometry;
- retained-count/GPU-buffer misalignment;
- malformed indices, below-threshold values, and out-of-pitch geometry.

## Validation status

GitHub Actions quota is currently exhausted, so the normal repository-wide matrix has not run for v1.3.0-a.

The pure comparison module itself has received standalone execution verification in the sandbox using a faithful local copy of the branch implementation and a minimal `affordanceVolume` type/runtime stub:

- TypeScript compilation passed with `--strict`, `--noUncheckedIndexedAccess`, and `--exactOptionalPropertyTypes`;
- the deterministic harness produced one valid intersection delta of `+0.35` for `B - A`;
- `left_only` and `right_only` both preserved `delta = null`;
- original left/right voxel object identity was preserved;
- the summary returned `intersection=1`, `leftOnly=1`, `rightOnly=1`, `neither=9` for a 12-cell canonical lattice;
- the harness correctly rejected threshold mismatch, malformed layer time, duplicate canonical cells, and GPU/forensic buffer misalignment.

This is meaningful execution evidence for the new pure scientific core, but it is **not** a substitute claim that repository formatting, lint, Vitest, production build, Playwright, or Python checks passed.

When execution capacity is available again, the remaining promotion gate is:

```text
format → repository strict TypeScript → lint → Vitest
```

before v1.3.0-a is considered fully verified in the normal project environment.
