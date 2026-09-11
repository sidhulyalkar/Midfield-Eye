# R1 Execution Checklist

Operational runbook for the first real action-menu pilot. Pair with `docs/R1_REAL_ACTION_MENU_PILOT.md`.

## Claim rule (non-negotiable)

Software-validation runs (`--synthetic-software-validation` or `scripts/run_r1_software_validation.py`) **never** produce an empirical claim. Only a completed real pilot with reliability + sequence-held-out ladder may publish B2-vs-B1 (or any) superiority, null, or negative results.

## A. Software validation (any time)

```bash
pip install -e ".[dev,showcase]"
python scripts/run_r1_software_validation.py --output-dir artifacts/r1-sw
# or: make r1-sw-validate
```

Expected: pilot package, status JSON, `CLAIM_BOUNDARY.json` with `empirical_claim_allowed: false`.

## B. Real Tier A (Metrica) path

### 1. Source preparation

```bash
python scripts/prepare_metrica_r1_source.py \
  --home data/raw/metrica/Game1_TrackingHome.csv \
  --away data/raw/metrica/Game1_TrackingAway.csv \
  --events data/raw/metrica/Game1_Events.csv \
  --match-id metrica-game-1 \
  --output artifacts/r1/source_game1.jsonl
```

Repeat per match; combine:

```bash
python scripts/combine_r1_sources.py \
  artifacts/r1/source_game1.jsonl \
  artifacts/r1/source_game2.jsonl \
  --output artifacts/r1/metrica_receipts.jsonl
```

### 2. Sample proposal (pending review)

```bash
python scripts/prepare_r1_pilot.py \
  artifacts/r1/metrica_receipts.jsonl \
  --output-dir artifacts/r1/pilot \
  --config configs/r1_real_pilot.yaml \
  --rater expert_a \
  --rater expert_b
```

Review `sample_plan.csv`. Reject/rebuild if unsuitable. **Do not** hand-pick after seeing model scores.

### 3. Accept sample (immutable freeze)

```bash
python scripts/accept_r1_sample.py artifacts/r1/pilot \
  --reviewed-by research_lead \
  --rationale "Ten non-overlapping windows cover frozen diversity strata without tracking failures."
```

### 4. Full double annotation (outcome-blind, score-blind)

```bash
pip install -e '.[annotation]'
streamlit run src/midfielders_eye/annotation_app.py -- \
  --frames artifacts/r1/pilot/pilot_label_frames.jsonl \
  --context-frames artifacts/r1/pilot/pilot_causal_context_frames.jsonl \
  --assignment artifacts/r1/pilot/assignment_expert-a.csv \
  --annotator-id expert_a --lock-annotator-id \
  --annotations artifacts/r1/pilot/annotations/expert_a.csv
# repeat for expert_b
```

### 5. Finalize (fail-closed)

```bash
python scripts/finalize_r1_pilot.py artifacts/r1/pilot \
  --annotation artifacts/r1/pilot/annotations/expert_a.csv \
  --annotation artifacts/r1/pilot/annotations/expert_b.csv \
  --reviewed-by research_lead \
  --benchmark-config configs/r1_benchmark.yaml
```

If reliability fails → stop (`reliability_not_established`).  
If adjudication needed → complete queue and rerun with `--adjudication`.

### 6. Provider quality sign-off

Copy `configs/provider_quality_review_v1.yaml`, fill accept/reject with rationale, then:

```bash
python scripts/finalize_r1_pilot.py artifacts/r1/pilot \
  --annotation ... \
  --provider-review-config artifacts/r1/pilot/provider_quality_config.yaml \
  --benchmark-config configs/r1_benchmark.yaml
```

### 7. Benchmark + showcase

Sequence-held-out B0→B3 only. Preserve null and negative contrasts.

```bash
python scripts/build_r1_showcase.py \
  --r1-dir artifacts/r1/pilot \
  --output artifacts/showcase/pilot/index.json
midfielders-eye showcase-build
```

Frontend `/pilot` must show exactly the evidence that exists.

## C. Publishing ladder results

Allowed only after step 7 succeeds:

- Report NDCG@3, Recall@3, pairwise, top-3 stability, sequence-bootstrap CIs
- Report every prespecified contrast (including null/negative)
- State sample size, reliability α, provider, and hold-out design
- Do **not** filter to favorable sequences

## D. Public subset option

If full 10-sequence capacity is blocked, a smaller public subset is acceptable **only if**:

- Composition ratios are declared in advance
- Full double-rating and reliability gates still apply
- Results are labeled as a subset pilot, not the main Paper 1 sample
- Software-validation artifacts are never mixed into the empirical report
