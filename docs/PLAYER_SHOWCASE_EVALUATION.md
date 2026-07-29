# Player Showcase and Evaluation Protocol

## Purpose

Named-player studies are the narrative doorway into the project, not permission to cherry-pick famous successful actions. The evaluation should test whether the model captures repeatable tactical behavior under matched contexts.

The 25-player catalog in `data/showcase/player_catalog.yaml` is a **candidate library, not a ranking**. Its archetypes are hypotheses that require evidence.

## Featured first cohort

### Michael Olise

Study as a right-sided creator and attacking-midfield-adjacent player.

Primary questions:

- Does a pause increase weak-side access?
- How does left-footed body shape preserve inside and outside options?
- When does carrying half a step commit the defender without closing the passing lane?

### Rodri

Study as a single pivot and controller.

Primary questions:

- Does pre-reception orientation create multiple safe exits?
- When does a low-risk pass improve the two-action future menu?
- How does positioning preserve rest defense during circulation?

### Pedri

Study as an interior and pocket connector.

Primary questions:

- Does arriving late into the pocket produce stronger line-breaking options than waiting there?
- Which scans precede successful half-turns?
- How often does a third-player route become available because of prior movement?

### Aitana Bonmatí

Study as a dynamic half-space controller.

Primary questions:

- How do rotations generate overloads and late box entries?
- Which off-ball movements change defender assignments?
- How does she preserve local combinations while threatening forward space?

## Clip sampling

For each featured player, target at least 24 rights-cleared sequences before making a player-level claim:

| Context | Minimum sequences |
| --- | ---: |
| Receive under direct pressure | 4 |
| Receive with cover shadow | 4 |
| Weak-side switch opportunity | 3 |
| Third-player combination | 3 |
| Transition after regain | 3 |
| Final-third creation | 3 |
| Unsuccessful or neutral outcome | 4 |

A sequence should begin 2–4 seconds before the relevant reception or movement and continue 2–4 seconds after the decision. Include unsuccessful, ignored, and low-value actions. A highlight reel alone is not a representative sample.

## Data hierarchy

Preferred evidence, strongest first:

1. Licensed synchronized tracking plus event data
2. Rights-cleared video with calibrated game-state reconstruction
3. Public research datasets under their permitted terms
4. Human tactical annotation
5. Embed-only reference video for qualitative presentation

YouTube embed-only media is not an analysis source unless separate rights to obtain and process the underlying file are documented.

## Annotation layers

Each sequence receives separate labels for:

- Physical availability
- Player-visible availability
- Tactical value
- Technical difficulty
- Transition risk
- Selected action
- Outcome
- Annotator confidence
- Failure reason

The selected action must never be used as the only definition of availability.

## Core metrics

### Opportunity creation

- Menu breadth
- High-value option count
- Option emergence rate
- Option lifetime
- Counterfactual option uplift caused by earlier movement

### Perception and orientation

- Visible option count
- Scan-to-reception interval
- Body-orientation alignment
- Blind-side access
- Viewpoint-conditioned missed-option rate

### Manipulation

- Defender displacement before release
- Number of defenders whose reachability region changes materially
- Cover-shadow escape
- Weak-side corridor expansion
- Pressure attracted per retained option

### Control

- Future menu value after action
- Rest-defense preservation
- Turnover exposure
- Top-option stability
- State uncertainty

### Execution

- Chosen-action regret relative to the estimated menu
- Completion or retention outcome
- Line-breaking realization
- Next-action value

Execution and decision quality must be reported separately.

## Context normalization

Do not compare raw player scores unless contexts are matched or modeled.

Control for:

- Pitch zone
- Possession phase
- Pressure level
- Team shape
- Opponent shape
- Score state
- Match minute
- Player role
- Provider and reconstruction quality
- Visibility fraction

Use hierarchical models or within-context percentiles once sample size permits. Until then, show scenario-level evidence rather than universal ratings.

## Negative and falsification examples

Each player page must include:

- A sequence where the hypothesized behavior does not occur
- A sequence where another option appears stronger
- A confidence warning when hidden players could reverse the conclusion
- A statement describing what evidence would falsify the archetype interpretation

## Expansion to 25 players

Do not analyze all 25 simultaneously. Expand in waves:

1. Four featured archetypes
2. Eight additional contrasting players
3. Full candidate library after annotation reliability and provider robustness are acceptable

The catalog should remain editable and versioned. Add or remove players based on research coverage, not popularity alone.

## v0.5 additions

Player studies now require separate evaluation across:

- gaze and scan timing;
- body orientation and execution envelope;
- teammate and opponent adaptation;
- tempo direction;
- option enablement;
- off-ball contribution;
- physical execution context.

Do not collapse these into one "midfielder score." Compare within matched tactical contexts and report source confidence.
