# Frozen first experiment

This protocol is the first honest scientific test. Do not tune it after inspecting held-out results.

## Dataset

Select ten short sequences from open or owned video/tracking data.

Recommended composition:

| Sequence type | Count | Why |
|---|---:|---|
| central midfield receipt under pressure | 3 | canonical scanning and release problem |
| transition or counterattack | 2 | rapidly changing future space |
| settled possession against a block | 2 | corridor and off-ball manipulation |
| wide overload or half-space entry | 2 | body orientation and blind-side options |
| deliberate negative/control case | 1 | few genuinely useful options |

Each clip should contain 4–8 seconds before and after the focal decision. Sample decision frames at 5 Hz, but label only frames in which the ball carrier plausibly controls or is about to receive the ball.

## Unit of evaluation

The split unit is the **sequence**, never the frame. Frames from one sequence are temporally dependent and may not appear in both train and test.

## Labels

For every generated candidate action:

- `available`: yes / no / uncertain;
- `value`: 0–4 ordinal score;
- `visible`: yes / partial / no / uncertain;
- `selected`: whether the action occurred;
- `failure_reason`: corridor, interception, body shape, receiver pressure, offside, view, execution difficulty, or other;
- optional free-text tactical explanation.

The current CSV uses continuous `label_value` in `[0,1]`. The annotation app may be extended to store the original ordinal value and uncertainty separately.

## Baselines

### B0: naive proximity

Rank passes by distance only and carries by forward progress.

### B1: static geometry

Use distance, defender-to-lane clearance, receiver pressure, and xT gain. Ignore velocity, viewpoint, and future space.

### B2: dynamic geometry

The repository's `AffordanceEngine`: B1 plus defender momentum, interception timing, viewpoint, body orientation, and one-second future space.

### B3: learned tabular model

Fit nonlinear combinations of the interpretable features using sequence-grouped cross-validation.

### B4: visual representation

Only after the first ten-sequence benchmark: frozen video or egocentric encoder features fused with B2 features.

## Primary endpoints

- NDCG@3 for graded option value;
- Recall@3 for physically available options;
- pairwise ranking accuracy;
- top-1 selected-action coverage, reported as descriptive only;
- calibration for predicted availability when a classifier is added.

## Secondary endpoints

- visibility-conditioned NDCG;
- performance by pressure tercile;
- performance by action type;
- temporal rank stability;
- counterfactual option-set uplift;
- performance with and without gaze/viewpoint features.

## Statistical analysis

1. Evaluate each held-out sequence once using grouped folds.
2. Compute paired per-frame metric differences between models.
3. Bootstrap by sequence, not by individual option row.
4. Report point estimate and 95% interval.
5. Treat ten sequences as a pilot. Emphasize effect sizes and failure modes rather than p-values.

## Ablations

Run in this order:

1. remove visibility;
2. remove body orientation;
3. remove defender velocity;
4. remove future-space forecast;
5. remove option-creation feature;
6. replace sequence-grouped splits with random splits only as a leakage demonstration.

## Decision rules

Advance to video representation learning when one of these is true:

- dynamic geometry clearly outperforms static geometry and remaining errors appear perceptual;
- dynamic geometry does not improve, but annotations show viewpoint is important and poorly approximated;
- rater agreement is high enough to support a richer model.

Do not scale modeling when availability agreement is below 0.6 without revising the annotation protocol.
