# v1.2 Release Checklist

Time Slice Surgery is intentionally released through three reviewable checkpoints rather than one monolithic change.

| Checkpoint | Scope | GitHub state |
| --- | --- | --- |
| v1.2.0-a | Integer temporal identity, exact retained-set filtering, explicit trajectory gaps, deterministic picking | PR #6 merged |
| v1.2.0-b | Full/Slice/Band 3D surgery, guide rails, selection lifecycle, same-cell trajectory UI | PR #7 merged |
| v1.2.0-c | Linked top-down slice, URL restoration, forensic JSON export, final contracts | PR #8 release candidate |

## Validation status

The repository normally gates releases on the complete matrix used for v1.1 and the earlier v1.2 checkpoints:

- Python 3.10 / 3.11 / 3.12
- Ruff
- full pytest
- `midfielders-eye demo`
- `midfielders-eye demo-v2`
- showcase generation
- Prettier
- strict TypeScript
- ESLint
- frontend unit tests
- production frontend build
- Playwright on mobile, desktop, Full HD, and 4K

For v1.2.0-c, GitHub Actions execution is intentionally skipped because the repository owner has exhausted the available Actions quota. This is an infrastructure exception, not a claim that the final c-layer matrix ran successfully.

The release therefore uses the following explicit substitute gate:

1. v1.2.0-a and v1.2.0-b were independently merged after the complete repository matrix passed.
2. PR #8 is constrained to page orchestration, linked 2D view, URL/export helpers, tests/styles, and release documentation. It does not modify `buildAffordanceVolume()`, the pure temporal filter model, or the WebGPU/WebGL2 renderer implementation.
3. The complete PR #8 patch is manually reviewed for scientific identity, stale-scene safety, URL semantics, serialization semantics, accessibility, and accidental renderer/model changes.
4. Linked views and the outer inspector are gated by an exact scene fingerprint so a previous frame/channel/LOD/threshold scene cannot be presented or exported while a new retained scene is publishing.
5. The linked SVG has one deterministic keyboard focus anchor rather than hundreds of retained-cell tab stops.
6. React Router search-parameter usage is checked against the installed `react-router` API contract.
7. The final PR must remain mergeable against `main` with the expected c-only file scope.

When Actions quota is available again, the complete matrix should be run on the merged v1.2 head as a post-merge verification. Until then, the release record must continue to state that this final matrix was not executed.

## Scientific release gate

The release must preserve all of these invariants:

1. Temporal selection uses integer layer identity.
2. Slice/Band are strict subsets of the retained scientific scene.
3. Filtered field values and stable voxel IDs are unchanged.
4. 3D and linked 2D consume the same retained voxel records.
5. Missing/pruned layers remain explicit absence, never zero or interpolation.
6. URL state restores integer layer identity rather than comparing horizon floats.
7. JSON export preserves stable ID, evidence status, filter state, and explicit gaps.
8. No future observed tracking frame enters the forecast volume.
9. The renderer remains two-pass with no GPU readback requirement.
10. A view or export may only consume a retained scene whose scenario/frame/channel/quality/threshold/horizon/budget fingerprint matches the current interface state.
