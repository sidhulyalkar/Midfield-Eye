# v1.3.0-rc Validation Record

## Release scope

`v1.3.0-rc` is a publication choreography layer downstream of the merged v1.3 scientific comparison model.

The branch must not modify:

- `buildAffordanceVolume()`;
- v1.3 support algebra;
- earlier-run intervention construction;
- difference render payload semantics;
- WebGPU/WebGL2 renderer backends.

The final branch comparison against v1.3.0-c contains publication pages/components/styles/tests/export/docs only.

## Actions quota exception

GitHub Actions is not used as a release gate because repository Actions quota is exhausted. No green CI claim is made for this RC.

## Substitute execution and audit evidence

The following checks were performed during RC development:

- standalone strict-TypeScript compilation of the pure publication helper;
- deterministic helper harness for stable figure ID, exact-Slice requirement, one-sided gallery selection, numerical summary, and exact-record provenance rejection;
- standalone strict-TypeScript compilation of the publication page boundary using DOM-aware React/router stubs;
- Node syntax validation of the Playwright export script;
- manual branch-scope audit confirming no scientific-core or renderer-backend changes;
- publication URL validator aligned between the browser page and export CLI, including duplicate/unknown query-key rejection;
- export route refuses non-Slice publication state and refuses fallback-normalized comparison parameters;
- source URL stability is checked after browser navigation before export;
- PNG captures only the publication plate; PDF uses publication print CSS;
- authored Vitest and Playwright contracts exist but are not claimed as executed by the normal repository runner.

## Scientific invariants reviewed

- `B - A` exists only on retained intersection.
- One-sided support remains categorical and never receives a synthetic zero.
- Publication summary statistics ignore one-sided cells numerically.
- Publication plate receives exact `VolumeDifferenceCell` object references from the source comparison.
- Grayscale semantics use structure in addition to color: `+/-/0` markers, opposing diagonal hatches, vertical A-only rails, horizontal B-only rails.
- Baseline source evidence status is visible.
- Condition B is labeled as a synthetic teaching intervention, not observed future truth or causal evidence.
- Candidate options included: false.
- Candidate options regenerated: false.
- Future observed frames used: false.

## Remaining normal-run verification

When Actions/local browser capacity is available again, run:

```text
npm run format:check
npm run typecheck
npm run lint
npm test
npm run build
npm run test:e2e
npm run export:difference-figure -- --url '<canonical publication URL>'
```

Until then, the RC is promoted only under the documented Actions-quota exception.