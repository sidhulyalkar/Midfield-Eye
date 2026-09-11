# Coach and player simplified views

Longer-term product layer on top of the same evidence stack. These views **must not** invent certainty the underlying pilot does not support.

## Implemented stubs (frontend)

Routes (illustrative scenario data only):

- `/coach/:scenarioId` → `CoachViewPage`
- `/player/:scenarioId` → `PlayerViewPage`

Both:

- load the same scenario bundle as the Decision Microscope
- show explicit **synthetic / illustrative** evidence badges
- link back to `/scenario/:scenarioId` and `/pilot`
- never display invented benchmark metrics or player grades

## Design principles

1. Same canonical state and action-menu evidence as the research cockpit
2. Language shifts from metrics to instructions and feedback
3. Evidence provenance remains visible (measured / reconstructed / proxy / synthetic)
4. Uncertainty is shown as confidence language, not hidden scores
5. No ordinal “player rating” from a single possession

## Coach view

**Primary job:** answer “what should we rehearse from this possession?”

- Session cues drawn from scenario narrative beats (teaching language only until R1)
- Evidence boundary card
- Links to full Decision Microscope and player view

## Player view

**Primary job:** individualized decision-menu feedback without overwhelm.

- One teachable moment
- Practice cue framed as a better question, not a grade
- Explicit non-claim of internal perception without direct evidence

## Next implementation steps (after R1 evidence)

1. Gate practice cues on measured/reconstructed evidence types
2. Surface top-k stable option identities from the Action Menu Ribbon
3. Optional counterfactual uplift strip when causal features exist
4. Keep `/pilot` and `/method` as the scientific source of truth

## Non-goals

- Replacing coaches with a scalar score
- Public ranking of named players from synthetic scenarios
- Hiding missing R1 results behind polished coaching language
