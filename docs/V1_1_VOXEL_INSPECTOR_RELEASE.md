# Temporal Affordance Volume v1.1 · Voxel Inspector

## Release objective

v1.1 turns the Temporal Affordance Volume from a high-level 3D explanation into a forensic research instrument.

The central release question is:

> If a voxel is bright, can the interface explain exactly what that cell represents, what contributed to it, and what evidence boundary applies?

The answer in v1.1 is yes. Every retained voxel is paired with an auditable metadata record aligned to the exact GPU instance rendered on screen.

## Shipped capabilities

### Direct voxel inspection

- click a retained voxel to inspect it;
- drag remains camera orbit through a movement threshold, so navigation and inspection are distinct gestures;
- a projected crosshair follows the selected cell while the camera moves or the canvas resizes;
- changing frame, channel, quality, threshold, or sparse budget clears the selection if that voxel no longer exists in the current rendered scene.

### Accessible forensic control path

The 3D canvas is not the only way to select a voxel.

The Voxel Inspector panel exposes **Inspect strongest visible voxel**, which queries the same retained voxel set without requiring a precise pointer target. The panel also exposes **Clear inspected voxel**.

This path is intentionally in normal document flow rather than overlaid on the GPU canvas. It remains reachable on narrow mobile layouts, keyboard navigation, and assistive technology without competing with sticky application chrome or camera gestures.

### Per-voxel forensic record

A retained cell exposes:

- stable voxel ID;
- frame ID;
- active channel;
- layer and grid indices;
- exact pitch X/Y in metres;
- forecast horizon in seconds;
- active visualization value;
- all eight component-field values;
- nearest defender ID and forecast distance;
- nearest teammate ID and forecast distance;
- up to four strongest local pass/carry corridor contributions;
- each contribution's local corridor term and frozen geometric score;
- visibility evidence mode;
- uncertainty evidence mode;
- source provider;
- explicit declaration that later observed tracking frames were not used.

### Evidence-aware semantics

Visibility is explicitly categorized as:

- provider visibility polygon;
- carrier orientation proxy;
- unavailable.

Uncertainty is explicitly categorized according to the focal-state fields that exist:

- covariance + confidence + tracking status;
- covariance + tracking status;
- confidence + tracking status;
- tracking status only.

The interface never silently turns an orientation proxy into observed gaze or a visual field value into calibrated probability.

## Rendering architecture

v1.1 deliberately does not alter the two-pass GPU rendering contract.

Voxel picking is deterministic CPU projection over the already-retained sparse voxel set:

```text
retained scientific voxels
      ↓
current orbit view-projection matrix
      ↓
screen-space projected centers / hit radii
      ↓
stable voxel ID
      ↓
forensic metadata panel
```

Consequences:

- no GPU ID buffer;
- no third render pass;
- no GPU readback;
- identical tactical values on WebGPU and WebGL2;
- deterministic projection/picking can be unit tested directly;
- the inspector remains a query over the scientific scene rather than a second rendering truth.

## Test coverage added

### Unit tests

- retained forensic records remain aligned 1:1 with GPU field instances;
- local candidate contributions survive sparse retention;
- provider visibility polygons remain distinct from orientation proxies;
- a projected voxel center round-trips through picking to the same stable voxel ID;
- empty screen space does not invent a selection.

The frontend suite contains 22 passing unit tests on the v1.1 release candidate before browser installation/E2E.

### Browser coverage

The `/volume` Playwright contract verifies:

- scientific channel controls and claim-boundary copy;
- Voxel Inspector v1.1 is present;
- the panel-native accessible action can select a visible voxel;
- the crosshair appears;
- forecast horizon, component field, local driver and evidence details are exposed;
- brightness is explicitly described as not calibrated probability;
- changing the active field channel invalidates the prior selection;
- the same panel-native action can inspect the new channel.

The shared browser configuration exercises mobile, desktop, full-HD and 4K profiles.

## Bugs caught during release hardening

The browser suite found two mobile interaction failures while the first implementation used a canvas-adjacent floating fallback button. Sticky application chrome and canvas hit regions could intercept that control after Playwright scrolled it into view.

The release did **not** weaken the test with forced clicks. Instead, the interaction architecture changed:

1. canvas overlays now contain only render-local information and selection markers;
2. fallback inspector commands are exposed through an explicit component handle;
3. the forensic panel owns the stable touch/keyboard selection action in normal document flow.

This makes the fix useful beyond the test itself and gives v1.2 a safer place to add temporal surgery controls.

## Claim boundary

v1.1 does not change the scientific evidence status of the 3D fields.

A selected voxel remains:

- a deterministic focal-state-derived forecast visualization;
- not a later observed future state;
- not a calibrated probability unless future calibration metadata explicitly supports that claim;
- not an expert label;
- not proof that option creation is causally attributable to one player;
- not observed gaze when visibility is based on orientation proxy geometry.

The R1 real expert benchmark remains the authority for empirical model claims.

## GitHub tracking

- v1.1 implementation: PR #5
- v1.2 planning: issue #4
- detailed v1.2 design: `docs/V1_2_TIME_SLICE_SURGERY_PLAN.md`

## v1.2 handoff

v1.1 establishes stable voxel identity and a trustworthy inspector. v1.2 should build directly on those primitives rather than redesign them.

The next release, **Time Slice Surgery**, will isolate exact forecast horizons and temporal bands, add a linked top-down view using the same voxel IDs/values, and extend the inspector with neighboring retained time-layer comparisons without interpolation.
