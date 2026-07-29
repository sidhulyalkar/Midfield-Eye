# Multi-provider benchmark protocol v0.2

## Core goal

Determine whether the action-menu representation captures football structure that survives changes in match, player, camera coverage, and data provider.

## Dataset tiers

### Tier A: full tracking discovery

- 10–20 manually annotated sequences from one full-tracking source;
- sequence-held-out cross-validation;
- establish label reliability and baseline ordering.

### Tier B: full tracking replication

- repeat on a second full-tracking provider;
- freeze features and hyperparameters from Tier A;
- report within-provider and cross-provider transfer.

### Tier C: partial observation

- SkillCorner observed-only;
- SkillCorner observed plus extrapolated;
- full-tracking frames artificially masked to comparable camera polygons;
- evaluate option recall and false option creation.

### Tier D: event snapshots

- StatsBomb 360 event frames;
- static and visibility-conditioned metrics only;
- no momentum, emergence, or lifetime claims.

### Tier E: video-to-state

- SoccerTrack v2 ground-truth GSR;
- SoccerNet ground-truth GSR with ball/possession sidecar;
- predicted GSR from released baselines;
- decompose state reconstruction error from affordance model error.

## Split hierarchy

Use the strongest available split:

1. provider held out;
2. competition held out;
3. match held out;
4. possession sequence held out;
5. player held out where identity is meaningful.

Never split adjacent frames randomly.

## Baselines

- B0: distance and forward progress;
- B1: static corridor geometry and receiver pressure;
- B2: dynamic geometry with velocity and future space;
- B2-V: B2 plus viewpoint and visibility;
- B3: learned nonlinear tabular ranker;
- B4: temporal graph model;
- B5: video or egocentric representation fused with B2.

B4 and B5 should not be implemented until B0–B3 and label reliability are frozen.

## Primary metrics

- NDCG@3 for tactical value;
- Recall@3 for availability;
- pairwise ranking accuracy;
- top-3 Jaccard stability across adjacent frames;
- provider-held-out NDCG;
- sequence bootstrap 95% intervals.

## Provider-specific metrics

### SkillCorner

- observed-only recall;
- extrapolated-player sensitivity;
- visible-polygon-conditioned recall;
- identity-confidence stratification.

### StatsBomb 360

- visible option recall;
- selected receiver rank;
- event-type-conditioned NDCG;
- static counterfactual value.

### SoccerTrack and SoccerNet

- affordance metric versus GSR localization error;
- affordance metric versus identity error;
- ground-truth-state versus reconstructed-state degradation;
- actor/ball sidecar sensitivity.

## Required ablations

1. remove velocity;
2. remove viewpoint;
3. remove visible-area masking;
4. remove extrapolated players;
5. remove future-space forecast;
6. remove option-creation features;
7. replace provider-held-out split with random rows as a leakage demonstration only.

## Decision gates

Advance from pilot to temporal graph modeling only when:

- availability agreement is at least 0.6;
- dynamic geometry beats static geometry on held-out sequences or has a clear failure explanation;
- the result is not driven by one sequence;
- provider quality reports show usable carrier and player coverage.

Advance to egocentric representation transfer only when:

- a soccer player-view dataset or purpose-built capture is available;
- gaze/head features have a defined target beyond generic trajectory prediction;
- the transfer benchmark contains a geometry-only control.
