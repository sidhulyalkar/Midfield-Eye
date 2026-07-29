# Version 0.2 evolution

## Why the first build needed to evolve

The first build proved that the affordance engine, counterfactual positioning analysis, annotation loop, and grouped evaluation could run end to end. It was intentionally centered on one clean tracking format.

That was not enough to test the actual research claim. Football data sources differ along dimensions that directly affect what an affordance model can know:

- full-pitch versus camera-limited player coverage;
- continuous trajectories versus event snapshots;
- observed versus extrapolated positions;
- persistent versus event-local player identities;
- measured versus inferred possession and ball state;
- metric versus normalized coordinates;
- tracking timestamps versus manually recorded event timestamps;
- raw optical tracking versus reconstructed game state from video.

A system that silently normalizes these differences away will produce polished but scientifically confused results.

## v0.2 design principle

Every adapter maps into one canonical contract while preserving what is missing, inferred, uncertain, or camera-limited.

```text
canonicalization ≠ pretending all sources are equivalent
```

## New research questions enabled

1. Does the geometric action menu replicate across full-tracking providers?
2. How much option recall is lost when only broadcast-visible players are observed?
3. Do extrapolated off-camera positions improve tactical ranking or introduce false options?
4. Can event-centered 360 data supervise option value without contaminating velocity claims?
5. How much affordance accuracy is lost upstream through game-state reconstruction errors?
6. Which features shift most between providers?
7. Does a learned ranker transfer to a provider it never saw during training?
8. Are action menus temporally stable, or does the model flicker between options?

## Deliverables now implemented

- six soccer adapter paths plus an auxiliary egocentric adapter;
- provider capability and limitation registry;
- provider quality reports;
- explicit tracking status and confidence fields;
- event alignment and event-centered sequence extraction;
- provider shift diagnostics;
- leave-one-provider-out evaluation;
- sequence bootstrap intervals;
- temporal rank stability;
- uncertainty-aware annotation UI;
- provider modality simulation demo;
- expanded CI and test coverage.

## What v0.2 still does not claim

- It does not yet contain a validated expert-labeled dataset.
- It does not prove that body orientation can be accurately inferred from tracking velocity.
- It does not treat StatsBomb 360 as tracking.
- It does not treat broadcast extrapolation as ground truth.
- It does not infer possession from SoccerNet player detections without a sidecar.
- It does not include a production graph neural network.
- It does not claim EgoTraj transfers to soccer until that transfer is tested.

## Definition of v0.2 success

The release succeeds when a researcher can ingest at least two fundamentally different soccer sources, produce a transparent quality report, extract comparable affordance features, annotate action menus, and run match-held-out or provider-held-out evaluation without changing model code.
