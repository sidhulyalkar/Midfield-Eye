# Clean-state versus perceived-state benchmark

## Question

How do perception errors change tactical conclusions?

The benchmark separates tactical-model validity from computer-vision quality.

## Track A: oracle state

Use synchronized full tracking and explicit ball state. Generate the oracle action menu and freeze:

- player and ball states;
- provider and match hashes;
- affordance-engine version;
- option IDs, targets, features, and ranks;
- tactical labels where available.

## Track B: controlled degradation

Apply one failure at a time before testing compound conditions.

| Failure | Parameter | Primary diagnostic |
|---|---:|---|
| Localization noise | standard deviation in metres | pitch error, corridor recall |
| Missing players | fraction removed | pressure IoU, option recall |
| ID switches | within-team switch probability | temporal option identity |
| Calibration drift | x/y offset in metres | line geometry, lane decisions |
| Broadcast crop | visible rectangle | hidden-player sensitivity |
| Delay | frame count | momentum and interception timing |
| Ball dropout | frame probability | possession reliability |

Run:

```bash
midfielders-eye degradation-benchmark frames.jsonl
```

The default suite includes identity, isolated failures, and a compound condition. All randomness is
seeded and every frame records its degradation configuration.

## Track C: real video reconstruction

When aligned video and full tracking are legally available:

1. run the frozen GSR frontend;
2. synchronize reconstructed and oracle frames;
3. compute perception and kinematic error;
4. generate both action menus with identical tactical code;
5. compare tactical outputs;
6. stratify by camera coverage, pitch location, pressure, and lane width.

## Metrics

### Perception

- GSR/GS-HOTA from the upstream evaluator;
- player recall;
- pitch-coordinate error;
- team and role accuracy;
- identity assignment accuracy and switch count;
- track fragments per identity;
- calibration-offset error;
- visible-pitch fraction.

### Kinematics

- velocity and acceleration error;
- heading error;
- turning-rate error;
- track fragmentation;
- uncertainty calibration.

### Tactical geometry

- pressure-map IoU;
- passing-corridor precision and recall;
- corridor-decision and narrow-corridor flip rates;
- line-breaking classification agreement;
- receiver-space mean absolute error;
- interception-margin mean absolute error.

### Decision layer

- top-k option-set recall;
- matched-option rank Spearman;
- selected-option regret under the oracle score;
- temporal emergence and extinction error;
- calibration of availability and value.

## Statistical unit

Adjacent frames are not independent. Confidence intervals must resample possession sequences or
matches, not rows. Parameter tuning must never see the held-out sequence or provider.

## Required plots

- tactical metric versus pitch error;
- tactical metric versus visible-pitch fraction;
- tactical metric versus missing-player rate;
- lane-decision flip probability versus lane width;
- regret versus observation delay;
- uncertainty coverage and calibration.

## Interpretation

The benchmark should be able to produce a negative result. If a one-metre coordinate error destroys
passing-lane agreement, the conclusion is not that the benchmark failed. It means the intended
coaching claim requires stronger perception, probabilistic corridors, or a coarser tactical target.
