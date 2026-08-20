# v1.3.0-rc Publication Choreography

## Goal

Turn the evidence-aware difference workbench into a deterministic publication artifact without introducing a second scientific implementation.

The publication layer may re-layout comparison records. It may not smooth, interpolate, rescore, zero-fill, or introduce publication-specific field formulas.

## Source-of-truth rule

The comparison URL and the existing scientific builder stack remain the source of truth:

```text
/volume/compare
        ↓
parseVolumeComparisonUrl()
        ↓
buildVolumeComparison()
        ↓
VolumeDifference
        ↓
exact temporal filter
```

`pub=figure` selects a different presentation of that same deterministic state. The publication route reconstructs the comparison from the URL using the **same `buildVolumeComparison()` path as the interactive workbench**. It does not implement a publication-specific call path or formula for Future Space / Option Creation.

Within a publication render, the plate receives the exact `VolumeDifferenceCell` object references produced by that source `VolumeDifference`. `assertPublicationDifferenceMatches()` rejects copied or publication-only records.

## Publication URL

A publication plate is enabled with:

```text
pub=figure
```

The first paper figure requires an exact temporal slice:

```text
tm=slice&layer=<integer>
```

The full reproducible state therefore includes:

- scenario;
- focal frame index;
- `cmp=earlier-run`;
- lead duration;
- state-derived comparison channel;
- deterministic LOD;
- retention threshold;
- exact integer temporal layer;
- publication mode.

The export CLI rejects under-specified or noncanonical URLs rather than relying on application fallbacks.

## Figure identity

Every plate receives a stable readable figure ID derived only from the scientific URL state, never viewport dimensions or browser state.

Canonical form:

```text
ME-DIFF-<scenario>-f<frame>-<channel>-l<layer>-lead<centiseconds>-q<quality>-t<thousandths>
```

Example:

```text
ME-DIFF-aitana-overload-f10-future-space-l2-lead075-qlow-t0200
```

## Fixed composition

The first publication plate contains:

1. figure title + stable ID;
2. source/evidence status;
3. Panel A: earlier-run intervention mini-pitch;
4. Panel B: exact evidence-aware top-down difference slice;
5. Panel C: support counts and signed-delta summary;
6. grayscale-safe support legend;
7. failure gallery showing A-only and B-only examples with explicit `no numerical delta` language;
8. claim-boundary footer.

## Grayscale / color-vision-deficiency contract

Color is supplemental only.

Structural semantics are frozen as:

- positive shared support: `+` marker + forward diagonal hatch + solid outline;
- negative shared support: `−` marker + backward diagonal hatch + dashed outline;
- zero shared support: `0` marker + unhatched filled cell;
- A-only support: two vertical rails;
- B-only support: two horizontal rails.

A monochrome print must preserve all five states.

## Failure gallery

The gallery exists to explain why sparse one-sided support cannot be treated as a difference from zero.

Representative cells are chosen deterministically by integer `(layerIndex, gridXIndex, gridYIndex)` order.

The gallery never ranks A-only or B-only cells by a fabricated magnitude.

Each populated card states:

```text
No numerical delta. This condition retained evidence here while the other did not.
```

If a slice has no example for one support side, the plate says so instead of borrowing a cell from another time.

## Claim footer

Every publication plate visibly states:

- `B - A` is defined only on retained intersection;
- `not_retained ≠ 0`;
- missing support is not interpolated;
- baseline source evidence status;
- Condition B is a synthetic teaching intervention;
- candidate options are not included;
- candidate options are not regenerated;
- no future observed frame is used;
- current channels are state-derived Future Space / Option Creation only.

## Export path

`npm run export:difference-figure` uses Playwright to capture the publication plate at a fixed viewport and save PNG/PDF plus a manifest.

The script:

- requires `/volume/compare`;
- requires `pub=figure`;
- requires `cmp=earlier-run`;
- requires exact `tm=slice&layer=<integer>`;
- validates scenario, frame index, lead preset, channel, deterministic quality, and threshold grid;
- uses reduced motion;
- uses a fixed `1600 × 1200` viewport;
- captures only `[data-testid="difference-publication-plate"]` for PNG;
- uses print CSS for PDF;
- never alters URL state after load;
- records the exact source URL and figure ID in a JSON manifest.

The manifest claim boundary says:

```text
publicationSpecificScientificFormulaUsed = false
sameComparisonBuilderAsWorkbench = true
publicationRequiresExactSlice = true
notRetainedIsNumericalZero = false
```

## Validation under Actions quota exception

GitHub Actions is not the release gate while quota is unavailable.

RC verification uses:

- pure helper strict-TypeScript compilation;
- deterministic helper harnesses;
- standalone page/JSX strict-TypeScript checks;
- manual full-PR audit;
- authored Vitest/Playwright contracts without claiming they ran under CI;
- explicit documentation of any unexecuted browser/export checks.
