# Pilot freeze, expert reliability, and frozen B0-B3 benchmark

## Current evidence status

The repository does **not** contain genuine expert action-menu annotations. The bundled synthetic
options have `bootstrap-pseudo-label` provenance and exist only to verify software. They cannot
establish inter-rater reliability, freeze an empirical pilot, or support football-performance
claims.

The pipeline below is implemented and fail-closed. Its first genuine run requires rights-cleared
pilot sequences and ratings from at least two identifiable experts.

## Outputs and boundaries

The workflow keeps four artifacts distinct:

1. canonical sequence frames and generated candidates;
2. immutable raw expert ratings;
3. an agreement report plus explicit adjudication decisions;
4. one consensus row per candidate for model evaluation.

Selected actions remain descriptive labels. They are never expanded into the set of available
actions. `uncertain` availability is retained as missing for Recall@3 rather than converted to
`no`.

## 1. Freeze candidate sequences

Generate candidate options from canonical, provider-audited frames:

```bash
midfielders-eye extract data/pilot/frames.jsonl \
  --output-path data/pilot/candidates.csv
```

Create a candidate-only freeze before annotation:

```bash
python scripts/freeze_pilot.py \
  --frames data/pilot/frames.jsonl \
  --candidates data/pilot/candidates.csv \
  --output artifacts/pilot/pilot_candidates_freeze.json
```

The command refuses to overwrite an existing manifest. It records whole-file and per-sequence
SHA-256 hashes, provider and match IDs, frame IDs, periods, timestamps, frame rates, state
semantics, quality flags, and candidate hashes. Use a new freeze path for a deliberate revision.
Freeze and verification also apply a fail-closed causal state audit. Any interpolated player state,
`offline_interpolation`, `uses_future_endpoint`, retrospective/label-derived marker, or equivalent
future-derived frame/player metadata is rejected. Such state belongs only in an explicitly
retrospective analysis, never this causal pilot or its candidate replay.

## 2. Collect expert labels

Follow `docs/ANNOTATION_GUIDE.md` and `configs/annotation_v2.yaml`. Every row needs:

- `sequence_id`, `frame_id`, and `option_id`;
- a non-empty `annotator_id`;
- `label_available`: `yes`, `no`, or `uncertain`;
- `label_value_ordinal`: integer 0-4;
- `label_visibility`: `yes`, `partial`, `no`, or `uncertain`;
- `label_confidence`: 0-1;
- `source_provider`;
- `provenance` beginning with `human-annotation`.

At least 25% of frames must overlap between raters. Synthetic providers, generated labels,
pseudo-labels, unknown candidate IDs, duplicate item/rater rows, provider mismatches, and invalid
scales are rejected from an expert freeze.

## 3. Report reliability and prepare adjudication

```bash
python scripts/report_inter_rater_reliability.py \
  data/pilot/annotations/expert_a.csv \
  data/pilot/annotations/expert_b.csv \
  --candidates data/pilot/candidates.csv \
  --output artifacts/pilot/reliability_report.json \
  --queue artifacts/pilot/adjudication_queue.csv
```

The primary statistics are:

- nominal Krippendorff alpha for availability;
- ordinal Krippendorff alpha for tactical value;
- pairwise Cohen kappa and quadratic-weighted Cohen kappa as diagnostics;
- 95% intervals bootstrapped by possession sequence.

The report also includes overlap by item and frame, rating-matrix missingness, uncertain-label
fraction, confidence coverage, per-action-kind agreement, and exact annotation hashes.

The default gate in `configs/pilot_reliability_v1.yaml` requires:

- two genuine raters;
- ten sequences;
- double annotation on at least 25% of frames;
- at least 20 overlapping options;
- availability alpha of at least 0.60.
- genuine ratings covering 100% of frozen candidates.

The overlap-frame denominator is every frame in the frozen candidate table, including frames with
no submitted rating. Candidate coverage defaults to 100%; a deliberate lower threshold must be
recorded explicitly with `--min-candidate-coverage`. Failure produces
`status: not_established`; it never silently relaxes a threshold.

## 4. Adjudicate without overwriting raters

Fill a separate CSV with the queue keys and:

```text
adjudicator_id
adjudicated_available
adjudicated_value_ordinal
adjudication_rationale
```

Then create one evaluation label per candidate:

```bash
python scripts/report_inter_rater_reliability.py \
  data/pilot/annotations/expert_a.csv \
  data/pilot/annotations/expert_b.csv \
  --candidates data/pilot/candidates.csv \
  --decisions data/pilot/annotations/adjudication_decisions.csv \
  --consensus-output artifacts/pilot/consensus_labels.csv
```

Every candidate admitted to consensus requires at least two genuine raters; the default 100%
coverage gate therefore requires this for the complete frozen set. Unanimous ratings become
`human-consensus-v1`. Disagreements require a non-null adjudicator, an integer 0-4 decision, and a
rationale, then become
`human-adjudication-v1`. The consensus row embeds the raw ratings as JSON; source rating files
remain immutable.

## 5. Freeze the expert pilot

First create the explicit feature-timing declaration:

```bash
python scripts/build_causal_feature_contract.py \
  --candidates data/pilot/candidates.csv \
  --benchmark-config configs/benchmark_frozen_v1.yaml \
  --reviewed-by research-lead-id \
  --output artifacts/pilot/causal_feature_contract.json
```

This command records a reviewed timing contract plus hashes for `affordance.py`, `geometry.py`,
`schema.py`, candidate serialization, and the polygon/state helper used by the generator. It does
not infer or empirically prove causality. The freeze rejects retrospective, selected-action,
outcome, and label-derived dependencies.

Only after agreement and adjudication, create the established freeze:

```bash
python scripts/freeze_pilot.py \
  --frames data/pilot/frames.jsonl \
  --candidates data/pilot/candidates.csv \
  --annotations data/pilot/annotations/expert_a.csv data/pilot/annotations/expert_b.csv \
  --reliability-report artifacts/pilot/reliability_report.json \
  --adjudication-decisions data/pilot/annotations/adjudication_decisions.csv \
  --consensus-labels artifacts/pilot/consensus_labels.csv \
  --causal-feature-contract artifacts/pilot/causal_feature_contract.json \
  --benchmark-config configs/benchmark_frozen_v1.yaml \
  --output artifacts/pilot/pilot_expert_freeze.json
```

The final freeze recomputes the complete reliability report, regenerates consensus from the frozen
candidates plus normalized ratings and adjudications, validates the timing contract, and compares
all hashes. It also reruns `AffordanceEngine` over the frozen canonical frames and requires exact
option-key coverage, identity equality, and tight numeric equality for targets,
`geometric_score`, and every B2/B3 causal feature. Extra, missing, or changed values fail the
freeze. It is written only with status
`expert_annotations_frozen_reliability_established`; otherwise the operation fails. Candidate-only
freezes remain available before annotation. A changed or missing original input invalidates the
freeze.

## 6. Freeze provider quality approval

Copy `configs/provider_quality_review_v1.yaml` and add exactly one decision plus rationale for
every provider in the pilot. The repository authority is
`configs/provider_quality_policy_v1.yaml`: a run may raise a `min_*` threshold or lower a `max_*`
threshold, but cannot weaken its approved floors or ceilings.

```yaml
providers:
  metrica:
    decision: accept
    rationale: Full-tracking metrics pass every frozen threshold.
  sportec_open:
    decision: accept
    rationale: Replication metrics pass every frozen threshold.
```

Then build the pre-evaluation artifact:

```bash
python scripts/build_provider_quality_review.py \
  --pilot-freeze artifacts/pilot/pilot_expert_freeze.json \
  --benchmark-config configs/benchmark_frozen_v1.yaml \
  --review-config data/pilot/provider_quality_decisions.yaml \
  --reviewer research-quality-lead-id \
  --output artifacts/pilot/provider_quality_review.json
```

The artifact is bound to the pilot, canonical frames, candidates, benchmark configuration, and
repository-owned quality policy. It records per-provider frame quality, candidate coverage and
missingness, provider-catalog capabilities, every threshold result, the reviewer, explicit
accept/reject decision, and rationale. Its audited feature list must exactly equal the pilot's
validated causal-feature contract; omissions and extras fail verification. An explicit acceptance
cannot override a failed threshold or ineligible provider capability. The artifact is immutable
and its metrics are recomputed during verification.

## 7. Run frozen B0-B3 evaluation

The consensus file must retain all candidate feature columns. Run:

```bash
python scripts/run_frozen_benchmark.py \
  artifacts/pilot/consensus_labels.csv \
  --config configs/benchmark_frozen_v1.yaml \
  --pilot-freeze artifacts/pilot/pilot_expert_freeze.json \
  --provider-quality-review artifacts/pilot/provider_quality_review.json \
  --output-dir artifacts/benchmark/frozen_b0_b3_v1
```

Before the empirical run, populate `dynamic_eligible_providers` in a copied frozen configuration
with the exact IDs of at least two continuous-tracking providers that passed quality review.
The runner cross-checks every allowlisted provider against `adapters/catalog.py`, records the
catalog capability evidence, and refuses unknown or non-tracking coverage. StatsBomb 360 and every
event-centered snapshot source are categorically rejected even if named in the allowlist; evaluate
them separately with static and visibility-conditioned metrics.

The runner freezes and evaluates:

- B0: pass distance only and carry forward progress only;
- B1: static corridor clearance, receiver pressure/space, progress, xT, and distance;
- B2: the upstream dynamic geometric score;
- B3: a small nonlinear tabular ranker using the explicit feature allowlist.

B1 excludes velocity, future space, body/viewpoint, and option creation. B3 preprocessing and model
fitting occur inside each training fold. No selected-action label or annotation metadata is a
feature.

Every model uses the same sequence-held-out folds and the same leave-one-provider-out folds.
Sequence IDs are checked for train/test overlap. Each output directory includes:

```text
benchmark_manifest.json
FILE_MANIFEST.json
folds.json
predictions.csv
metrics.csv
bootstrap_intervals.json
provider_quality.csv
provider_shift.csv
prespecified_contrasts.json
```

The manifest hashes the input, configuration, folds, features, timing semantics, and outputs.
Intervals resample sequences, not rows. Provider evaluation always emits quality and
distribution-shift reports. All prespecified contrasts are retained, including negative and null
results.

An empirical run must receive the exact established pilot freeze and benchmark configuration. The
runner verifies every original freeze input, binds the benchmark input to the frozen regenerated
consensus hash, binds the configuration and candidate hashes, and revalidates the causal feature
contract and candidate-generator source dependencies. It reports that causal timing is
contract-validated—not inferred.

The separately frozen provider quality review is verified before any split or learned-model fit.
Every observed dynamic provider must have passed its thresholds and carry an explicit acceptance
decision. The later `provider_quality.csv` and `provider_shift.csv` outputs are evaluation reports;
they do not replace this pre-evaluation approval gate.

If any option in a frame has `uncertain` availability, Recall@3 is null for that entire frame.
Uncertain options are never removed to create an optimistically easier ranking set.

`allow_synthetic_software_validation` is `false` in the production configuration. Tests may set it
to `true`; resulting manifests are permanently labeled
`synthetic_software_validation_only`.

## Advancement gate

Do not start temporal graph or video models until:

1. the expert reliability report is `established`;
2. the pilot and consensus labels are frozen and hash-valid;
3. B2 improves over B1 on held-out sequences, or a documented failure analysis explains why not;
4. the result is not driven by one sequence;
5. provider quality and shift reports support the comparison.
