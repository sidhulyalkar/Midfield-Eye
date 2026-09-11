# R1 Annotation Runbook

This runbook starts **after** the pilot is `sample_frozen`. It produces the only
inputs that can unlock reliability, provider quality review, and the B1-vs-B2
ladder.

## Preconditions

```bash
make r1-pilot-status
# stage must be sample_frozen

PYTHONPATH=src python scripts/smoke_r1_annotation_pack.py artifacts/r1/pilot
# ok: true

PYTHONPATH=src python scripts/assess_r1_pilot_quality.py artifacts/r1/pilot
# writes pre_annotation_quality.json — review before accepting provider quality later
```

## Protocol (non-negotiable)

- Outcome **blinded** (selected action hidden until labels freeze)
- Model scores **blinded**
- Full double rating of **every frozen candidate** (not a 25% sample)
- Provenance must start with `human-annotation`
- Do not rate from synthetic templates without filling labels
- Do not use `--unblinded-exploratory` or `--show-model-scores` for publication

## Launch (one process per expert)

```bash
pip install -e '.[annotation]'

streamlit run src/midfielders_eye/annotation_app.py -- \
  --frames artifacts/r1/pilot/pilot_label_frames.jsonl \
  --context-frames artifacts/r1/pilot/pilot_causal_context_frames.jsonl \
  --assignment artifacts/r1/pilot/assignment_expert-a.csv \
  --candidates artifacts/r1/pilot/pilot_candidates.csv \
  --annotator-id expert_a \
  --lock-annotator-id \
  --annotations artifacts/r1/pilot/annotations/expert_a.csv
```

Repeat with `assignment_expert-b.csv`, `expert_b`, and `expert_b.csv`.

Always pass `--candidates` so ratings attach to frozen option IDs (not live
AffordanceEngine regeneration). Sidebar shows save progress. Resume opens the first unsaved frame.
Keys: `j`/← prev · `k`/→ next · `n` next-unsaved · `s` save · `]` save+next.

Workload: **72 frames / rater**, **1 152 candidates** (~16/frame). Budget
**~6–10 hours per rater** at careful pace.

## Validate

```bash
make r1-validate-annotations \
  ANN_A=artifacts/r1/pilot/annotations/expert_a.csv \
  ANN_B=artifacts/r1/pilot/annotations/expert_b.csv
```

Must report `ok: true` with candidate coverage 1.0 for both files.

## Finalize (stops honestly at the weakest gate)

```bash
python scripts/finalize_r1_pilot.py artifacts/r1/pilot \
  --annotation artifacts/r1/pilot/annotations/expert_a.csv \
  --annotation artifacts/r1/pilot/annotations/expert_b.csv \
  --reviewed-by research_lead \
  --benchmark-config configs/r1_benchmark.yaml
```

Possible stages:

| Stage | Meaning |
|---|---|
| `reliability_not_established` | Agreement gate failed — still a valid R1 outcome |
| `needs_adjudication` | Fill `adjudication_decisions.csv`, re-run with `--adjudication` |
| `expert_pilot_frozen_needs_provider_review` | Labels frozen; sign provider quality next |

After reviewing `pre_annotation_quality.json` and finalize metrics, edit
`artifacts/r1/pilot/provider_quality_config.yaml` (`decision: accept|reject` +
rationale), then:

```bash
python scripts/finalize_r1_pilot.py artifacts/r1/pilot \
  --annotation artifacts/r1/pilot/annotations/expert_a.csv \
  --annotation artifacts/r1/pilot/annotations/expert_b.csv \
  --reviewed-by research_lead \
  --benchmark-config configs/r1_benchmark.yaml \
  --provider-review-config artifacts/r1/pilot/provider_quality_config.yaml
```

Only then can the B0–B3 ladder run. Retain null and negative contrasts.

## Claim boundary

Until reliability + provider review pass:

- `empirical_claim_allowed: false`
- Software-validation numbers must not appear in the published ladder table
