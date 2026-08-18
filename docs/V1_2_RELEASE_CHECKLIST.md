# v1.2 Release Checklist

Time Slice Surgery is intentionally released through three reviewable checkpoints rather than one monolithic change.

| Checkpoint | Scope | GitHub state |
| --- | --- | --- |
| v1.2.0-a | Integer temporal identity, exact retained-set filtering, explicit trajectory gaps, deterministic picking | PR #6 merged |
| v1.2.0-b | Full/Slice/Band 3D surgery, guide rails, selection lifecycle, same-cell trajectory UI | PR #7 merged |
| v1.2.0-c | Linked top-down slice, URL restoration, forensic JSON export, final contracts | PR #8 release candidate |

## Final v1.2 gate

PR #8 must pass the same complete repository matrix used for v1.1 and the earlier v1.2 checkpoints:

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

The final merge is blocked on this matrix. A green UI in one viewport is not sufficient.

## Scientific release gate

The release must additionally preserve all of these invariants:

1. Temporal selection uses integer layer identity.
2. Slice/Band are strict subsets of the retained scientific scene.
3. Filtered field values and stable voxel IDs are unchanged.
4. 3D and linked 2D consume the same retained voxel records.
5. Missing/pruned layers remain explicit absence, never zero or interpolation.
6. URL state restores integer layer identity rather than comparing horizon floats.
7. JSON export preserves stable ID, evidence status, filter state, and explicit gaps.
8. No future observed tracking frame enters the forecast volume.
9. The renderer remains two-pass with no GPU readback requirement.
