# Verified software bootstrap

These results validate the executable path only. The targets are pseudo-labels generated from an undisclosed nonlinear combination of interpretable features, so they are **not evidence of tactical validity or superiority on real football decisions**.

## v0.3 compatibility verification run

Configuration:

- 4 synthetic sequences;
- 5 frames per sequence;
- sequence-grouped cross-validation;
- seed 7;
- provider-aware schema and bootstrap intervals enabled.

| Model | NDCG@3 | Recall@3 | Pairwise accuracy |
|---|---:|---:|---:|
| naive proximity | 0.929 | 0.467 | 0.699 |
| static geometry | 0.924 | 0.442 | 0.886 |
| dynamic geometry | 0.975 | 0.500 | 0.891 |
| learned nonlinear | 0.979 | 0.500 | 0.946 |

The small verification run is intentionally fast enough for continuous integration. The default experiment configuration remains larger and should be rerun whenever the feature or label contract changes.

## Multi-provider software check

`midfielders-eye demo-v2` produces provider-shaped synthetic views for Metrica, SkillCorner, StatsBomb 360, and SoccerTrack v2, then writes:

- normalized provider frames;
- provider capability summaries;
- affordance options;
- quality reports;
- temporal option-stability metrics;
- pairwise feature-shift statistics.

This checks that modality-specific uncertainty reaches the downstream model. It does not claim that synthetic provider views reproduce each source distribution.

## Test status

The v0.3 release extends this suite with SoccerNet tracker-state ingestion, uncertainty propagation, causal state reconstruction, possession handling, degradation controls, and layered perception-to-tactics evaluation. The final verified test count is recorded in the release notes and generated verification manifest.

The next result that matters is a frozen evaluation on independently annotated real sequences, followed by leave-one-match and leave-one-provider-out transfer.
