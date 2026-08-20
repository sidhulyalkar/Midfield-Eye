# v1.3.0-rc Publication Choreography

## Goal

Turn the evidence-aware difference workbench into a deterministic publication artifact without introducing a second scientific implementation.

The publication layer may **re-layout** already-computed comparison records. It may not rebuild, smooth, interpolate, rescore, or otherwise reinterpret the A/B volume.

## Source-of-truth rule

The interactive comparison route remains the scientific source of truth:

```text
/volume/compare
```

Publication mode is an alternate presentation of the same URL state and the same `VolumeDifferenceRenderCell` records.

No publication-only call to `buildAffordanceVolume()` is permitted.

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

- scenario
- focal frame index
- comparison intervention ID
- lead duration
- state-derived comparison channel
- deterministic LOD
- retention threshold
- exact integer temporal layer
- publication mode

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

- positive shared support: filled cell + `+` marker + forward diagonal hatch;
- negative shared support: filled cell + `−` marker + backward diagonal hatch;
- zero shared support: filled cell + `0` marker;
- A-only support: two vertical rails;
- B-only support: two horizontal rails.

A monochrome print must preserve all five states.

## Failure gallery

The gallery exists to explain why sparse one-sided support cannot be treated as a difference from zero.

Representative cells are chosen deterministically by integer `(layerIndex, gridXIndex, gridYIndex)` order.

The gallery must never rank A-only or B-only cells by a fabricated magnitude.

Each card states:

```text
No numerical delta. This condition retained evidence here while the other did not.
```

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

A Playwright-based export script may capture the publication plate at a fixed viewport and save PNG/PDF.

The script must:

- navigate to an explicit comparison URL;
- require `pub=figure` and exact Slice mode;
- use reduced motion;
- use a fixed viewport;
- capture only `[data-testid="difference-publication-plate"]` for PNG;
- use print CSS for PDF;
- never alter URL state after load;
- never trigger a publication-only recomputation.

## Validation under Actions quota exception

GitHub Actions is not the release gate while quota is unavailable.

RC verification should use:

- pure helper strict-TypeScript compilation;
- deterministic helper harnesses;
- manual full-PR audit;
- authored Vitest/Playwright contracts without claiming they ran under CI;
- explicit documentation of any unexecuted browser/export checks.
