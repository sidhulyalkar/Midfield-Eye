# R1 critical next plan

Honest status as of the `sample_frozen` handoff.

## What is actually done

| Layer | State |
|---|---|
| Protocol + claim boundary | Frozen and enforced in software |
| Metrica Tier A source | Game 1 + Game 2 receipt windows on disk |
| 10-sequence pilot | Accepted, hashed, stage `sample_frozen` |
| Annotation pack integrity | Smoke-tested (assignments, blinding, coverage) |
| Pre-annotation quality | Metrica thresholds pass on pilot label frames |
| Annotator | Assignment mode + **frozen candidate load** (not live regen) |
| Empirical claim | **Still forbidden** |

## The real bottleneck

| Item | Number |
|---|---:|
| Assigned focal frames / rater | 72 |
| Frozen candidates / rater | 1 152 (exactly 16 / frame) |
| Double-rated candidate judgments | 2 304 |
| Estimated effort @ 20–30 s / candidate | **~6–10 h per rater** |

This is feasible for two trained annotators over a few sessions. It is **not** a weekend of casual clicking if quality is taken seriously.

Kinds in the freeze: 720 pass, 360 carry, 72 hold. Hold is one per frame; pass dominates the cost.

## Scientific weaknesses to own (do not paper over)

1. **`no_velocity` on every label frame** — raw Metrica sample has no velocity columns. Transition stratum scoring used geometry density only. Dynamic geometry (B2) still uses positions; kinematics features that need velocity are weak or zero. Document in any paper methods section.
2. **Soft-clipped pitch coordinates** — official sample occasionally leaves the nominal pitch; clipped with quality flags.
3. **Single match in the frozen pilot** — Game 2 is prepared but not in the freeze. R1 is not provider-held-out; still, multi-match diversity is limited.
4. **Annotator UI previously regenerated options** — fixed to prefer `pilot_candidates.csv`. Always pass `--candidates` for publication sessions.

## Critical path (ordered)

### P0 — Must happen for any empirical sentence

1. **Recruit two experts** with football tactical literacy; lock IDs `expert_a` / `expert_b`.
2. **Calibration session** (30–45 min): 2–3 practice frames, align on availability vs value vs creation; confirm “uncertain” for visibility without player-view evidence.
3. **Production annotation** (see `R1_ANNOTATION_RUNBOOK.md`), always with `--candidates`.
4. **`make r1-validate-annotations`** until coverage = 1.0.
5. **`finalize_r1_pilot`** → reliability gate.
6. Adjudication if needed; **human** provider decision on `provider_quality_config.yaml`.
7. Benchmark ladder; **publish null/negative results**.

### P1 — Parallel, does not unlock claims

- PR #20 for `improve/showcase-and-visibility` so reviewers can audit freeze hashes and claim boundary.
- Static demo package + 2–3 GIFs of Ribbon / microscope (showcase value only).
- Optional second pilot on Game 2 **after** R1 methods are proven — do not expand N mid-annotation.

### P2 — After R1 result exists

- Deepen coach/player views with real consensus labels.
- Velocity reconstruction experiment (finite differences) for a **future** pilot — never rewrite the frozen R1 features post-hoc to chase a positive B2–B1.

## What not to do

- Do not invent labels or “pseudo-human” provenance.
- Do not shrink the frozen 1 152 after acceptance without a new sample review.
- Do not mix software-validation ladder numbers into the R1 table.
- Do not treat pre-annotation quality pass as provider acceptance.
- Do not unblind outcomes mid-rating for publication files.

## Decision for the project lead

| Path | When to choose |
|---|---|
| **A. Full R1 annotation now** | Experts available this week; goal is Paper 1 pilot table |
| **B. Methods PR only** | Experts delayed; still ship reproducibility story |
| **C. Feasibility pilot** | Only if experts cannot commit ~8h — then design a **new** smaller freeze (new sample review), do not silently subsample the current freeze |

Recommended default: **A if experts exist, else B**. Do not invent a C that pretends the current freeze was fully rated.
