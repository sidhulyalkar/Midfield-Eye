# The Action Menu Benchmark · v0.7

## Research question

The v0.7 benchmark asks a narrower question than the full Midfielder's Eye research program:

> Can we estimate the changing set of physically available, perceptually accessible, tactically valuable, and movement-created actions without treating the action eventually selected as the full decision target?

The selected action is one observed outcome. It is never a substitute label for the menu that preceded it.

## Paper 1 scope

The first publishable unit is deliberately limited to:

1. a frozen expert annotation ontology;
2. sequence-held-out B0/B1/B2/B2-V/B3 comparisons;
3. uncertainty and reliability reporting;
4. one provider-transfer or partial-observation study after the pilot gate;
5. an evidence-aware visualization of option persistence and reordering.

Temporal graph models, video encoders, direct gaze fusion, and biomechanics fusion remain later research stages.

## Annotation object

Annotators rate one candidate action at one decision frame. The frozen contract is in `configs/action_menu_annotation_v1.yaml`.

The targets are kept separate:

| Target | Meaning |
|---|---|
| `available` | Could the action reasonably be completed? |
| `visible` | Was enough relevant information plausibly available to consider it? |
| `value_ordinal` | If competently executed, how useful is the resulting state? |
| `creation_ordinal` | How much did earlier movement improve this option? |
| `selected` | Was it eventually chosen? This is joined after blinded ratings. |
| `confidence` | How certain is the rater about the label? |

Availability and visibility use `yes`, `no`, and `uncertain`. Value and creation use a 0-4 ordinal scale. `uncertain` is preserved rather than coerced to a binary label.

## Outcome blinding

Whenever operationally possible, availability, visibility, value, and creation are rated without revealing the selected action. Selection is joined from the event stream only after those ratings are stored.

This reduces hindsight contamination and makes it possible for a selected action to be rated unavailable or low-value when the evidence genuinely supports that conclusion.

## Sampling

The possession sequence is the statistical unit. Adjacent frames must never be randomly separated across train and validation folds.

### Pilot

- 10-20 independent possession sequences;
- approximately three decision frames per sequence;
- at least 25% of decision items double-rated;
- reliability reported before expanding the model class.

### Main benchmark target

The preferred Paper 1 target is at least 150 independent possession windows, subject to data rights and annotation capacity. This is a planning target rather than a claim of achieved sample size.

## Stable option identity

Current engine option IDs contain the frame number because they are event-local records. v0.7 adds a separate stable identity for longitudinal analysis:

- pass: `pass:<receiver_id>`;
- carry: `carry:<configured_angle_bucket>`;
- hold: `hold`.

Stable identity does not change the candidate generator. It only allows the same conceptual action to be followed across frames.

## Retrospective lifecycle tables

Run:

```bash
python scripts/build_action_menu_report.py candidates.csv artifacts/action-menu
```

Outputs:

```text
artifacts/action-menu/
├── option_lifecycles.csv
├── action_menu_timeline.csv
└── summary.json
```

`option_lifecycles.csv` records first observed frame, last observed frame, frames seen, score summaries, and any selected frames.

`action_menu_timeline.csv` records menu breadth, the top option, top-k identities, option births, option extinctions, and adjacent-frame top-k Jaccard stability.

Birth and extinction are explicitly **retrospective visualization labels**. They must not be fed into a causal model as focal-frame features.

## Canonical model ladder

v0.7 makes the B2/B2-V distinction executable rather than documentary:

- **B0** naive distance / progression;
- **B1** static geometry;
- **B2** dynamic geometry with interception timing, future space, option creation, uncertainty-adjusted clearance, and state confidence;
- **B2-V** the exact B2 score plus body orientation and a perceptual-visibility proxy;
- **B3** learned nonlinear tabular ranker trained only inside each held-out fold.

The B2 score deliberately excludes body orientation and perceptual visibility. B2-V adds only those terms, so the B2-V minus B2 contrast has a literal interpretation. A proxy is never renamed as literal gaze.

The existing frozen benchmark remains the fail-closed validation foundation for pilot hashes, candidate lineage, provider-quality approval, sequence/provider splits, leakage checks, and B3 fold training. The v0.7 action-menu runner then recomputes the public five-model ladder from those exact same held-out predictions.

Run the canonical software-validation path with:

```bash
python scripts/run_action_menu_benchmark.py \
  candidates.csv \
  artifacts/action-menu-benchmark \
  --config benchmark.yaml \
  --synthetic-software-validation
```

For empirical evaluation, omit `--synthetic-software-validation` and provide the frozen pilot and provider-quality review:

```bash
python scripts/run_action_menu_benchmark.py \
  consensus.csv \
  artifacts/action-menu-benchmark \
  --config benchmark.yaml \
  --pilot-freeze pilot_freeze.json \
  --provider-quality-review provider_quality_review.json
```

The canonical v0.7 outputs are:

```text
artifacts/action-menu-benchmark/
├── action_menu_benchmark_manifest.json
├── action_menu_metrics.csv
├── action_menu_bootstrap_intervals.json
├── action_menu_contrasts.json
└── foundation/
    ├── benchmark_manifest.json
    ├── predictions.csv
    ├── metrics.csv
    ├── folds.json
    └── ...
```

The `foundation/` directory is retained rather than hidden. It makes the exact validated predictions, folds, quality reports, and legacy benchmark evidence auditable.

B4 temporal graph and B5 representation fusion remain blocked until the real pilot satisfies the reliability and transfer gates.

## Primary analyses

The canonical v0.7 benchmark reports:

- NDCG@3;
- Recall@3 with uncertain availability frames retained as null rather than silently binarized;
- pairwise ranking accuracy;
- adjacent-frame top-3 Jaccard stability using stable action identities;
- sequence-bootstrap 95% confidence intervals;
- match-held-out and provider-held-out performance when available;
- prespecified B2-B1, B2-V-B2, B3-B2-V, and B3-B1 contrasts;
- every negative, null, and non-estimable prespecified contrast rather than filtering to favorable results.

Additional feature ablations remain prespecified for velocity, visible-area masking, extrapolated players, future-space forecasting, and option creation.

## Visual instrument

v0.7 adds the **Action Menu Ribbon** to scenario playback. Each row is a stable candidate identity and each column is a synchronized frame. The interface makes three distinctions explicit:

1. candidate absent versus candidate low-scoring;
2. current model score versus observed selected action;
3. retrospective lifecycle visualization versus causal model input.

Clicking a ribbon cell seeks the synchronized pitch to that frame and candidate, creating the first version of the Decision Microscope.

## Publication gate

A publishable empirical result is not considered complete until:

- the annotation protocol is frozen;
- reliability is reported;
- code, configuration, data, and label hashes are frozen;
- baselines use identical sequence-held-out folds;
- negative results remain in the report;
- no result is driven by one possession sequence;
- provider quality and distribution shift are reported before transfer claims;
- the frontend labels synthetic, proxy, reconstructed, provider-observed, and directly measured evidence distinctly.

## Current claim boundary

v0.7 ships the benchmark contract, corrected five-model ladder, lifecycle analytics, tests, and visual instrument. It does **not** claim that the target real-data pilot or 150-sequence benchmark has already been completed. Those results must be produced from independently annotated real football sequences before tactical superiority claims are made.
