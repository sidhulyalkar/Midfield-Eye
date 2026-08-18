# Action Menu Annotation Guide · v0.7

## What you are labeling

You are labeling the **menu of plausible actions at a moment**, not grading the player after seeing the outcome.

The publication protocol separates six objects:

1. physical availability;
2. perceptual accessibility;
3. tactical value;
4. option creation from earlier movement;
5. eventual selection;
6. annotation confidence.

The first four are expert judgments. Eventual selection is an observed outcome joined **after** the blinded expert ratings are stored.

The machine-readable contract is `configs/action_menu_annotation_v1.yaml`.

## Publication blinding

The default annotation application is both:

- **outcome-blind**: the selected action is hidden from the rater;
- **model-score-blind**: candidate rank, model score, score-weighted line width, pressure heatmap, and synthetic view cones are hidden.

The neutral pitch gives every candidate equal visual weight and labels candidates A01, A02, and so on.

Exploratory unblinded modes exist only for debugging. Ratings created with those modes must never enter the publication reliability report or frozen benchmark.

## Causal history

For creation labels, inspect only frames **before** the focal decision frame. The annotation interface can show up to three earlier frames in the same sequence.

Never use:

- future frames;
- the eventual selected action;
- post-action player motion;
- retrospective model explanations.

Birth and extinction labels generated after a sequence is complete are visualization outputs, not evidence that may be shown to a publication rater.

## Availability

- **yes**: a competent player could plausibly attempt the action now;
- **no**: the action is physically or temporally closed;
- **uncertain**: the footage, tracking, or tactical context is insufficient.

Availability does not mean the action is good.

## Perceptual accessibility

- **yes**: the available evidence plausibly supports that the relevant receiver or space was accessible to the carrier;
- **no**: the available evidence supports that the relevant information was not accessible;
- **uncertain**: the source cannot support a defensible player-view judgment.

Use **uncertain** aggressively when literal player-view information is unavailable.

Do not equate:

- broadcast visibility with player visibility;
- torso direction with head direction;
- head direction with calibrated gaze;
- movement heading with gaze.

There is deliberately no `partial` category in the v0.7 frozen contract. Ambiguous cases remain `uncertain` instead of creating a difficult-to-reproduce intermediate class.

## Tactical value, 0–4

- **0**: immediately harmful or produces a clearly losing state;
- **1**: weak option with little benefit or high avoidable risk;
- **2**: viable control option;
- **3**: strong option that improves the possession;
- **4**: exceptional option that creates a major advantage.

Judge the action assuming competent execution while accounting for realistic technical difficulty.

Do not force an unavailable action to value zero automatically. Availability and value are separate research targets, and impossible-but-theoretically-valuable actions may be useful disagreement cases during protocol development.

## Creation from earlier movement, 0–4

Creation asks a different question:

> How much did earlier movement improve this option relative to its recent baseline?

- **0**: earlier movement did not improve the option or clearly made it worse;
- **1**: small improvement;
- **2**: meaningful but ordinary improvement;
- **3**: strong creation effect;
- **4**: decisive movement substantially opened or upgraded the action.

Use only causal history visible before the focal frame. If the source window is too short, lower confidence rather than inventing a counterfactual.

## Failure reason

Choose the primary reason an unavailable or weak option fails:

- corridor;
- interception;
- body shape;
- receiver pressure;
- offside;
- player view;
- execution difficulty;
- other.

Use the tactical note for secondary reasons.

Failure reason is diagnostic metadata. It does not replace any of the primary labels.

## Selected action

**Do not mark the selected action during publication annotation.**

After blinded ratings are frozen, prepare a selection table with one row per decision frame:

```text
sequence_id,frame_id,selected_option_key,selection_provenance
sequence_001,17,pass:home_08,provider-event
```

`selected_option_key` may be blank when the observed action is not represented by any annotated candidate.

Join outcomes only after annotation with:

```bash
python scripts/join_action_menu_selection.py \
  data/annotations/action_menu.csv \
  data/annotations/selected_outcomes.csv \
  data/annotations/action_menu_with_selection.csv
```

The join refuses unblinded source ratings, duplicate frame outcomes, unknown selected candidates, and missing frame coverage by default.

## Confidence

Use lower confidence when:

- the camera does not show the full pitch;
- players are extrapolated;
- ball carrier identity is inferred;
- body or head orientation is unavailable;
- the action target is ambiguous;
- the causal-history window is too short;
- perceptual accessibility cannot be established from the source.

Confidence ranges from 0.0 to 1.0. The neutral default is 0.5 rather than a model-derived suggestion.

## Annotation procedure

1. Inspect the focal frame in neutral mode.
2. Inspect only the preceding causal-history frames when creation needs context.
3. Label availability independently for every candidate.
4. Label perceptual accessibility independently, using `uncertain` when evidence is inadequate.
5. Label tactical value on the 0–4 scale.
6. Label creation on the 0–4 scale using only earlier movement.
7. Record confidence and a concise note where reasoning is unusual.
8. Save the frame without seeing the selected outcome.
9. Join selected outcomes only after the blinded annotation file is frozen.
10. Revisit protocol-level disagreement before expanding the model class.

## Running the annotator

Install the optional annotation dependencies:

```bash
pip install -e ".[annotation]"
```

Launch Streamlit in the default publication-safe mode:

```bash
streamlit run src/midfielders_eye/annotation_app.py -- \
  --frames data/pilot/frames.jsonl \
  --annotations data/annotations/action_menu.csv
```

The two explicit exploratory escape hatches are:

```text
--unblinded-exploratory
--show-model-scores
```

Any file produced with either mode must be treated as exploratory and excluded from the publication freeze.

## Reliability sample

At least 25% of decision items should be labeled by two annotators. The pilot gate should report, as appropriate:

- Krippendorff's alpha or categorical agreement for availability;
- agreement for perceptual accessibility;
- weighted ordinal agreement for value;
- weighted ordinal agreement for creation;
- agreement by action type;
- disagreement categories;
- confidence-conditioned agreement;
- sequence-bootstrap uncertainty.

Availability agreement below the frozen 0.60 gate triggers protocol revision rather than model expansion.

## Provider-specific cautions

### Metrica

Tracking is continuous, but player identities are anonymous and literal gaze is unavailable. Perceptual-access labels should often remain uncertain unless additional defensible orientation evidence is supplied.

### SkillCorner

Distinguish detected from extrapolated players. Consider a second observed-only annotation pass for selected sequences. Do not mistake broadcast observation status for player perception.

### StatsBomb 360

Label only static/event-centered questions. Do not infer velocity, option lifetime, scanning history, or movement-created effects from one event snapshot.

### SoccerTrack v2

The ball is placed at the BAS actor in the current adapter. Treat pass-contact timing as approximate and preserve the reconstruction evidence tier.

### SoccerNet GSR

Inspect the possession sidecar and camera coverage. Do not assume missing players are absent from the tactical scene. Keep reconstructed state separate from provider-observed state in reporting.
