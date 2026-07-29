# v0.6 Frontend Experience: The Evidence Studio

The frontend gains a second narrative spine alongside the 100-player atlas.

## New routes

```text
/empirical                         evidence-studio landing page
/empirical/sources                 source landscape and access planner
/empirical/experiments             real-source experiment gallery
/empirical/experiments/:id         interactive evidence-backed study
/evidence-ledger                   measured, inferred, unavailable, and synthetic inventory
/capture-studio                    gaze and biomechanics study designer
```

## Evidence Studio landing page

Lead with four large 4K panels:

1. Pedri's real StatsBomb 360 event snapshot.
2. The real Metrica continuous tracking excerpt.
3. The multimodal source landscape.
4. The evidence ladder.

The visual grammar must make evidence visible before interpretation:

- source badge;
- evidence tier;
- access/license state;
- measured fields;
- inferred fields;
- unavailable fields;
- citation drawer;
- file-hash/provenance drawer.

## Source planner

Each source card shows:

- modalities;
- best use;
- access gate;
- expected download size when known;
- official URL;
- commands or human steps;
- adapter readiness;
- redistribution constraints;
- experiments unlocked by the source.

Never add a one-click download button for a registered or license-request source.

## Experiment page

Synchronize the source geometry, action menu, evidence ledger, and citation. When a signal is unavailable, show an empty-state explanation and the source required to obtain it. Do not fill the hole with a synthetic value.

## Capture Studio

Build a protocol composer for a new rights-cleared study:

- participant and consent status;
- task blocks;
- cameras and eye tracker;
- calibration checks;
- synchronization markers;
- data-retention and public-display permissions;
- expected outputs;
- pre-registered metrics;
- manifests and hashes.

The Capture Studio must load `/api/capture-protocol/default`, let the researcher edit a local copy, and validate it with `/api/capture-protocol/validate` before enabling export. Invalid consent, missing gaze/ball/player sensors, absent calibration, or insufficient synchronization anchors must appear as blocking errors rather than yellow decorative warnings.
