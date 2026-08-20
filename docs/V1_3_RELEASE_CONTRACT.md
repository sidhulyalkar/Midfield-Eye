# v1.3 Release Contract

## Release thesis

v1.3 makes sparse condition comparison scientifically explicit.

Its central rule is:

> **A numerical signed difference exists only on retained evidence intersection.**

For a canonical `(layerIndex, gridXIndex, gridYIndex)` cell:

```text
intersection → delta = conditionB.value - conditionA.value
left_only    → delta = null
right_only   → delta = null
neither      → omitted from sparse comparison cells
```

`not_retained` is not numerical zero.

## What v1.3 can claim

v1.3 can claim that it provides:

1. a deterministic support algebra for sparse A/B affordance volumes;
2. fail-closed compatibility checks for channel, pitch, grid, horizon, threshold, voxel budget, temporal scale, layer time, and geometry;
3. exact preservation of A/B retained voxel records for forensic inspection;
4. signed `B - A` only on retained intersection;
5. categorical A-only and B-only states with `delta=null`;
6. a non-color-only support grammar shared by 3D, linked 2D, and publication views;
7. a reproducible comparison URL with deterministic LOD and integer temporal surgery;
8. JSON export carrying support state, exact A/B records, intervention metadata, and claim boundaries;
9. a deterministic publication plate with stable figure identity, exact-Slice requirement, failure gallery, and PNG/PDF export path.

## Current comparison experiment

The first public A/B experiment is deliberately narrow.

### Condition A

The current focal frame from the selected showcase scenario.

The default showcase source is an **illustrative synthetic reconstruction**, not measured player performance. The source evidence status is surfaced in the comparison UI and publication/export artifacts.

### Condition B

A synthetic teaching intervention:

- possession-team non-carriers only;
- finite focal-state velocity;
- minimum speed `0.25 m/s`;
- candidate arrival = current position + `velocity × leadSeconds`;
- arrival clipped to the pitch;
- zero-displacement post-clipping candidates discarded;
- fastest feasible candidate selected;
- stable player-ID tie break;
- only X/Y position moved;
- velocity and all other player states preserved.

Lead presets are `0.50`, `0.75`, and `1.00 s`.

This intervention is not an observed future frame and is not causal evidence.

## Supported scientific channels

v1.3 counterfactual comparison supports only:

- `future_space`
- `option_creation`

Both conditions are built with `options=[]`.

Therefore the release explicitly records:

```text
candidateOptionsIncluded = false
candidateOptionsRegenerated = false
```

## What v1.3 does not claim

v1.3 does **not** claim:

- a counterfactual pass-completion probability;
- a counterfactual Action Menu ranking;
- a counterfactual Passing Corridor score based on regenerated candidates;
- causal effect of the teammate movement;
- observed future player trajectories;
- measured player gaze;
- measured biomechanics;
- calibrated probabilities from voxel intensity;
- equivalence between pruning absence and a true field value of zero;
- that one-sided support has a signed magnitude.

## Evidence rules

The following remain release-blocking invariants:

- no missing/pruned voxel is substituted with zero;
- no one-sided support is interpolated into an intersection;
- no future observed frame is used by the current volume forecast;
- a numerical delta requires compatible A/B canonical geometry;
- temporal view filtering reuses retained comparison records rather than rebuilding the scientific field;
- publication layout does not introduce a publication-specific scientific formula.

## Visual grammar

### Interactive 3D / 2D

- shared intersection: filled cell, signed color allowed;
- A-only: parallel rails in one orientation;
- B-only: orthogonal rails;
- one-sided support always has `delta=null`.

### Publication

- positive shared support: forward hatch + `+` + solid outline;
- negative shared support: backward hatch + `−` + dashed outline;
- zero shared support: `0` + unhatched cell;
- A-only: vertical rails;
- B-only: horizontal rails.

Color is supplemental.

## Publication identity

Publication mode uses the same `/volume/compare` scientific URL plus:

```text
pub=figure
```

It requires:

```text
tm=slice&layer=<integer>
```

Stable figure IDs are derived from scenario, focal frame index, channel, integer layer, lead, deterministic quality, and threshold.

A publication plate accepts only exact `VolumeDifferenceCell` references from its source `VolumeDifference`.

## Export contract

The deterministic exporter validates a canonical URL before launching Chromium.

Outputs:

- PNG of the exact publication plate;
- print-media PDF;
- JSON manifest containing figure ID, source URL, viewport, output paths, and publication claim boundary.

The export manifest states:

```text
publicationSpecificScientificFormulaUsed = false
sameComparisonBuilderAsWorkbench = true
publicationRequiresExactSlice = true
notRetainedIsNumericalZero = false
```

## Validation status

GitHub Actions is intentionally not used as the v1.3 release gate while quota is unavailable.

The release record must distinguish:

- direct standalone execution evidence;
- strict TypeScript / JSX checks;
- authored but unexecuted Vitest / Playwright coverage;
- manual PR audit.

No release note may imply a green repository-wide Actions matrix unless one actually ran successfully.

## Next scientific boundary

The next release may add counterfactual Action Menu / Passing Corridor comparison only after candidate actions are regenerated under Condition B with the same evidence-aware rigor.

Separately, the larger publication program still depends on the real annotated action-menu benchmark. The synthetic comparison instrument is a methodological and explanatory tool, not a substitute for frozen expert-labeled empirical results.
