# Midfielder's Eye R1 · Real Action Menu Pilot

R1 is the first point where The Midfielder's Eye is allowed to make a real empirical statement about the action menu.

The release does **not** start from a more complex model. It starts by making the label, sampling, provenance, and evaluation loop difficult to fool.

## The R1 question

> Does dynamic geometry rank expert-labeled options better than static geometry on independent possession sequences?

The primary Tier A contrast is **B2 dynamic geometry vs B1 static geometry** under sequence-held-out evaluation. B2-V and B3 remain useful secondary contrasts. R1 is not provider-held-out: independent-provider replication is R2.

R1 may end with a positive result, a null result, a negative result, or a reliability failure. All four outcomes are scientifically useful and must remain visible.

## What R1 freezes

R1 freezes ten non-overlapping decision windows with this prespecified diversity mix:

| Sampling stratum | Count | Purpose |
|---|---:|---|
| central midfield receipts under pressure | 3 | stress option availability under immediate pressure |
| transition | 2 | test rapidly changing space and defender momentum |
| settled possession | 2 | test ranking in denser, slower organization |
| wide / half-space overload | 2 | test asymmetric support and corridor geometry |
| negative control | 1 | retain a low-opportunity case instead of selecting only dramatic moments |

These names are **sampling heuristics, not tactical labels**. They never enter a model target or feature.

Focal frames are sampled at 5 Hz. Each window carries earlier causal context for the creation label, but the frozen candidate table contains only focal frames.

## Why Metrica is R1 Tier A

Metrica is the cleanest first integration in the repository because the open samples can provide synchronized full-pitch home/away tracking plus events on a known pitch coordinate system.

R1 does not accept the generic nearest-player carrier inference as publication-grade possession evidence. `prepare_metrica_r1_source.py` instead uses synchronized PASS events:

- the recorded passer defines the pre-pass causal context,
- the recorded recipient becomes the carrier only at or after the recorded pass end frame,
- the team on the event defines possession,
- post-receipt frames are kept only while the recipient remains within the frozen ball-carrier distance gate,
- the selected pass is used to select a receipt window, not to label the complete action menu.

The event outcome is never inserted into candidate features.

## 1. Build R1-ready Metrica sources

For each Metrica match:

```bash
python scripts/prepare_metrica_r1_source.py \
  --home data/raw/metrica/Game1_TrackingHome.csv \
  --away data/raw/metrica/Game1_TrackingAway.csv \
  --events data/raw/metrica/Game1_Events.csv \
  --match-id metrica-game-1 \
  --output artifacts/r1/source_game1.jsonl
```

Repeat for additional matches, then combine them without duplicate source frames:

```bash
python scripts/combine_r1_sources.py \
  artifacts/r1/source_game1.jsonl \
  artifacts/r1/source_game2.jsonl \
  --output artifacts/r1/metrica_receipts.jsonl
```

Inspect each source report. A high rejection count for ball distance, missing recipient tracking, or short control is evidence about source quality and should not be relaxed merely to obtain ten windows.

## 2. Prepare the ten-sequence pilot

Generate a deterministic proposal plus frozen candidates and expert assignment packs:

```bash
python scripts/prepare_r1_pilot.py \
  artifacts/r1/metrica_receipts.jsonl \
  --output-dir artifacts/r1/pilot \
  --config configs/r1_real_pilot.yaml \
  --rater expert_a \
  --rater expert_b
```

This produces:

```text
artifacts/r1/pilot/
├── r1_manifest.json
├── sequence_inventory.csv
├── sample_plan.csv
├── pilot_label_frames.jsonl
├── pilot_causal_context_frames.jsonl
├── pilot_candidates.csv
├── pilot_candidates_blinded.csv
├── pilot_candidates_freeze.json
├── rater_assignments.csv
├── assignment_expert-a.csv
├── assignment_expert-b.csv
└── selection_outcomes_template.csv
```

The first run is intentionally `needs_sequence_review`. Review `sample_plan.csv` and the corresponding windows. Reject and rebuild with a new explicit input/config if the proposal is unsuitable. Do not hand-pick a replacement after looking at model scores.

If the sample is acceptable, sign it without regenerating candidates:

```bash
python scripts/accept_r1_sample.py artifacts/r1/pilot \
  --reviewed-by research_lead \
  --rationale "Ten non-overlapping windows cover the frozen diversity strata without obvious tracking failures."
```

This writes an auditable `sample_review.json` bound to the pre-review manifest, sample plan, and candidate freeze hashes.

## 3. Run full double annotation

Install the annotation extra:

```bash
pip install -e '.[annotation]'
```

Run one annotation process per expert. Example for expert A:

```bash
streamlit run src/midfielders_eye/annotation_app.py -- \
  --frames artifacts/r1/pilot/pilot_label_frames.jsonl \
  --context-frames artifacts/r1/pilot/pilot_causal_context_frames.jsonl \
  --assignment artifacts/r1/pilot/assignment_expert-a.csv \
  --annotator-id expert_a \
  --lock-annotator-id \
  --annotations artifacts/r1/pilot/annotations/expert_a.csv
```

Expert B uses the corresponding assignment and output file.

R1 deliberately double-rates **every frozen candidate**, not only a 25% overlap subset. This keeps the 100% consensus coverage requirement and the reliability design consistent.

The publication annotation view is:

- outcome blind,
- model-score blind,
- randomized per rater,
- neutral candidate ordering,
- causal-history only,
- selected-action controls disabled.

## 4. Finalize expert evidence

Run:

```bash
python scripts/finalize_r1_pilot.py artifacts/r1/pilot \
  --annotation artifacts/r1/pilot/annotations/expert_a.csv \
  --annotation artifacts/r1/pilot/annotations/expert_b.csv \
  --reviewed-by research_lead \
  --benchmark-config configs/r1_benchmark.yaml
```

The command advances only as far as the evidence permits.

### Reliability failure

If the availability gate is not established, R1 stops at:

```text
reliability_not_established
```

The report remains an R1 result. Do not tune the alpha threshold or relabel only difficult frames after seeing the score.

### Disagreement requiring adjudication

If reliability passes but individual items disagree, R1 writes `adjudication_queue.csv` and stops at:

```text
needs_adjudication
```

Complete the adjudication file using the existing adjudication contract, then rerun with:

```bash
--adjudication artifacts/r1/pilot/adjudication_decisions.csv
```

Consensus is created only from unanimous expert ratings or explicit adjudication. Original expert rows remain unchanged.

### Expert freeze

After reliability and adjudication pass, R1 automatically writes:

```text
reliability_report.json
adjudication_queue.csv
consensus_labels.csv
causal_feature_contract.json
pilot_expert_freeze.json
```

At this point the expert pilot is immutable, but the model benchmark is still locked.

## 5. Human-sign provider quality

Copy `configs/provider_quality_review_v1.yaml`, fill exactly the providers present in the frozen pilot, and make an explicit accept/reject decision with rationale **after reviewing the generated quality metrics and source limitations**.

For the Metrica Tier A pilot, the corresponding benchmark allowlist is frozen in `configs/r1_benchmark.yaml`.

Then rerun finalization with:

```bash
python scripts/finalize_r1_pilot.py artifacts/r1/pilot \
  --annotation artifacts/r1/pilot/annotations/expert_a.csv \
  --annotation artifacts/r1/pilot/annotations/expert_b.csv \
  --reviewed-by research_lead \
  --benchmark-config configs/r1_benchmark.yaml \
  --provider-review-config artifacts/r1/pilot/provider_quality_config.yaml
```

Only an accepted provider review can unlock the benchmark.

## 6. R1 benchmark

R1 uses **sequence-held-out only** evaluation:

```text
B0 naive
  ↓
B1 static geometry
  ↓
B2 dynamic geometry
  ↓
B2-V dynamic + viewpoint/perceptual access
  ↓
B3 learned nonlinear ranker
```

The primary R1 question is B2 vs B1. The benchmark retains:

- NDCG@3,
- Recall@3 where availability is fully defined,
- pairwise ranking accuracy,
- top-3 adjacent-frame Jaccard stability,
- sequence bootstrap 95% intervals,
- every prespecified negative, null, and non-estimable contrast.

R1 does **not** claim cross-provider generalization.

## 7. The R1 showcase

Build the normal showcase. With no R1 directory, it renders the honest `protocol_ready` state automatically:

```bash
midfielders-eye showcase-build --output-dir artifacts/showcase
```

To render the live research state from R1 artifacts, invoke the Python bundle builder with `r1_dir` or build the R1 payload directly:

```bash
python scripts/build_r1_showcase.py \
  --r1-dir artifacts/r1/pilot \
  --output artifacts/showcase/pilot/index.json
```

The frontend route is:

```text
/pilot
```

### What the visitor should understand in twenty seconds

The R1 page is designed around five things, in this order:

1. **Question:** can dynamic geometry recover the expert action menu better than static geometry?
2. **Evidence ladder:** protocol → sample → double annotation → reliability → benchmark.
3. **Frozen sample:** 3/2/2/2/1, explicitly described as diversity sampling rather than truth.
4. **Blind expert view:** outcome, score, and future-state leakage are visibly locked out.
5. **Result:** absent until it exists. When the benchmark is complete, a model table appears in the same location where the empty-result panel used to be.

This is intentionally better than leading with a highlight reel. The distinctive product is not a colored pitch overlay. It is the ability to watch a tactical claim earn evidence rung by rung.

## Best visual demonstration after R1 data exists

The strongest public figure should combine three synchronized views for one held-out sequence:

```text
┌──────────────────────┬──────────────────────────────┐
│ Tactical pitch       │ Action Menu Ribbon           │
│ current geometry     │ option birth/persistence     │
│ pressure + movement  │ expert value + model ranks   │
├──────────────────────┴──────────────────────────────┤
│ B1 vs B2 rank delta over time + expert annotations │
└─────────────────────────────────────────────────────┘
```

The story should be a **rank reversal**, not a cherry-picked goal:

- B1 prefers an apparently open static pass.
- Defender momentum closes it.
- B2 demotes it before the action occurs.
- another option is becoming available because of movement elsewhere.
- the experts independently rate the changing menu.

If no clean rank-reversal case exists, do not manufacture one. Showcase the failure mode instead.

## What R1 should teach us before adding model complexity

The next representation change should be chosen from observed error categories, not enthusiasm for an architecture.

### If B2 does not beat B1

Investigate, in order:

1. **label reliability:** do experts agree on availability but not value?
2. **candidate recall:** is the expert option missing from the generated menu entirely?
3. **state quality:** are carrier/velocity/defender trajectories unstable?
4. **horizon:** are 0.5–1.0 s forecasts too short or too long for the decision?
5. **feature semantics:** are pressure shadows and interception margins measuring the football concept we think they measure?

Do not respond first by adding a GNN.

### If B2 beats B1 but B2-V does not beat B2

That is useful evidence that the current body/viewpoint proxy adds little. The next move is better observation evidence, not a larger viewpoint model.

### If B3 materially beats B2-V

Use feature ablation and error slices to identify which nonlinear interactions matter before moving to temporal graphs.

### If all models perform similarly

The likely bottleneck is the candidate/label representation or pilot diversity, not capacity.

## R2 · Independent full-tracking replication

Freeze the R1 method and add an independent continuous full-tracking provider, preferably Sportec Open if its approved quality review supports the same dynamic features.

R2 unlocks the provider-held-out protocol that R1 intentionally avoids.

Primary question:

> Does the R1 B2-vs-B1 effect survive a provider and competition shift without retuning the label or feature contract?

Do not change the R1 threshold after seeing R2.

## R3 · Partial-observation stress test

SkillCorner should be used to ask a different question:

> Which parts of the action menu survive when observation is incomplete?

This is where visibility masks, off-screen uncertainty, and candidate preservation become central. Full-pitch candidates should not silently disappear merely because the provider cannot observe them.

StatsBomb 360 remains useful for event-centered snapshots and selected-action context, but not for velocity or dynamic persistence claims.

## R4 · Earn temporal and egocentric models

Only after the R1/R2/R3 evidence identifies a concrete representation failure should the project promote:

- temporal graphs,
- sequence transformers,
- future occupancy fields,
- multi-agent counterfactual rollouts,
- video-derived body/head orientation,
- egocentric or gaze-informed perceptual access.

A temporal model is justified when the frozen dynamic hand-engineered representation fails in a repeatable temporal way.

## Longer-term differentiators

The research program can then evolve from ranking the present menu toward four harder questions:

### Option creation

Which earlier off-ball movement caused an option to become valuable?

This turns the model from an action evaluator into a positioning evaluator.

### Option suppression

Which defender removed the most valuable future options without touching the ball?

This creates a natural defensive counterpart to the midfielder representation.

### Information advantage

Which valuable options existed physically but were plausibly inaccessible from the carrier's perception?

This requires stronger observation evidence than body direction alone.

### Counterfactual menu quality

How would moving two metres earlier have changed the future menu, even if the player never received the ball?

This is the long-term bridge to coaching and player development, but it should be downstream of the real action-menu benchmark, not a substitute for it.

## R1 success criteria

R1 is considered operationally successful when:

- ten reviewed non-overlapping real tracking sequences are frozen,
- all candidates are double-rated by two genuine experts,
- availability reliability meets the prespecified alpha gate,
- disagreements are explicitly adjudicated,
- candidate regeneration and causal timing contracts verify,
- Metrica passes the signed provider-quality gate,
- sequence-held-out B0/B1/B2/B2-V/B3 runs reproducibly,
- bootstrap intervals and null results are preserved,
- `/pilot` shows exactly the evidence that exists and nothing stronger.

R1 is scientifically informative even if the primary B2-vs-B1 contrast is null or negative.
