# Empirical Claim Contract

Every frontend metric and exported sentence must expose:

```text
source_id
evidence_tier
modalities
measured_fields
inferred_fields
unavailable_fields
confidence
license_or_terms
citation
transformations
```

## Allowed examples

- “StatsBomb recorded Pedri as the actor of this pass and supplies an event-centered visible-area snapshot.”
- “The model estimates that the weak-side option was outside the current proxy view cone.”
- “OpenCap produced a model-derived knee-flexion trajectory for this consented capture.”
- “Metrica supplies synchronized player and ball coordinates for this anonymous sequence.”

## Disallowed examples

- “Pedri looked at the receiver,” when the source contains no eye gaze.
- “Rodri generated 1,200 N,” from video pose alone.
- “This player directed the teammate,” from temporal correlation alone.
- “The player ignored an open option,” when the option was outside observed visibility.
- “WorldPose proves elite-player biomechanics,” when it provides pose rather than direct kinetics.

## Frontend behavior

Unavailable signals are not zero. Render them as absent with a reason and a source recommendation. Proxy signals use dashed geometry and a proxy badge. Direct measurements use a solid measurement badge. Synthetic demonstrations have a persistent watermark.
