# Coach and player simplified views

Longer-term product layer on top of the same evidence stack. These views **must not** invent certainty the underlying pilot does not support.

## Design principles

1. Same canonical state and action-menu evidence as the research cockpit
2. Language shifts from metrics to instructions and feedback
3. Evidence provenance remains visible (measured / reconstructed / proxy / synthetic)
4. Uncertainty is shown as confidence language, not hidden scores
5. No ordinal “player rating” from a single possession

## Coach view (sketch)

**Primary job:** answer “what should we rehearse from this possession?”

Layout:

```text
┌─────────────────────────────────────────────────────────┐
│ Possession timeline (scrub) + pitch                     │
├──────────────────────┬──────────────────────────────────┤
│ Emerging option      │ Coaching card                    │
│ (Ribbon highlight)   │ • Hold shape one touch longer    │
│                      │ • Weak-side runner arrives late  │
│                      │ • Earlier support angle +2m      │
├──────────────────────┴──────────────────────────────────┤
│ Counterfactual: “If support moved earlier…” uplift strip│
└─────────────────────────────────────────────────────────┘
```

Coach card fields (from existing contracts):

- Option that improved / degraded
- Body / scan cue when evidence exists
- Off-ball movement that created value
- Confidence + evidence type badge

## Player view (sketch)

**Primary job:** individualized decision-menu feedback without overwhelm.

```text
┌──────────────────────────────────────────┐
│ “Your menu” — top 3 options over time    │
│ Simple icons: pass lane / carry / hold   │
├──────────────────────────────────────────┤
│ One selected teachable moment            │
│ “This lane closed as the defender stepped│
│  inside — the far option opened.”        │
├──────────────────────────────────────────┤
│ Practice cue (max one)                   │
└──────────────────────────────────────────┘
```

Constraints:

- Prefer one teachable moment per session clip
- Never claim internal perception without gaze/body evidence
- Link back to full Decision Microscope for analysts

## Implementation path (when R1 evidence exists)

1. Reuse `ActionMenuRibbon`, `TacticalPitch`, and evidence components
2. Add route stubs: `/coach/:scenarioId`, `/player/:scenarioId`
3. Drive copy from structured fields already in options / timeline JSON
4. Gate “practice cue” generation behind evidence-type checks
5. Keep `/pilot` and `/method` as the scientific source of truth

## Non-goals

- Replacing coaches with a scalar score
- Public ranking of named players from synthetic scenarios
- Hiding missing R1 results behind polished coaching language
