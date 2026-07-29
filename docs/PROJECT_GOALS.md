# Project goals

## North-star question

At each moment, what actions are becoming physically possible, tactically valuable, dangerous, visible, or invisible to the player in possession?

## Primary scientific objective

Build and validate a representation of the **changing action menu** available to a football player. The model should explain not only why an action was chosen, but also:

- which alternatives existed;
- which alternatives were hidden from view;
- which alternatives were closing or opening;
- how earlier movement created or destroyed future options;
- how uncertainty in the observed game state changes those conclusions.

## Product objective

Produce a coaching-facing system that can replay a possession and answer:

1. What did the player appear to see?
2. What were the strongest available actions?
3. Which option was emerging or disappearing?
4. Which earlier movement would have improved the future menu?
5. How confident is the system given the camera and data source?

## Core representation

The project models five related but distinct quantities:

1. **Availability**: Can the action physically and temporally succeed?
2. **Visibility**: Is the information likely available to the player?
3. **Value**: How useful is the action if executed competently?
4. **Creation**: Does movement improve later options even without receiving the ball?
5. **Selection**: Which action actually occurred?

Selection is evidence, not complete supervision for the other four.

## First falsifiable hypothesis

A dynamic geometry model using pressure, defender momentum, body/view orientation, and near-future space will rank expert-labeled actions better than static distance-and-angle geometry under sequence-held-out evaluation.

## Stronger v0.2 hypothesis

The improvement will survive:

- a second full-tracking provider;
- match-held-out evaluation;
- provider-held-out evaluation;
- partial-observation and extrapolation ablations.

## Audiences

### Coaches and analysts

- possession review;
- scanning and body-shape feedback;
- off-ball movement value;
- counterfactual positioning;
- tactical pattern discovery.

### Players

- individualized decision-menu feedback;
- blind-side and scanning education;
- movement choices that create future options;
- role-specific development.

### Researchers

- embodied decision-making;
- partial observability;
- affordance learning;
- causal sequence modeling;
- transfer across sensors and providers.

### Broadcast and games

- explainable telestration;
- “options opening” overlays;
- player-view reconstructions;
- realistic agent perception and decision systems.

## Non-goals for the current release

- predicting player quality from a single action;
- replacing coaches with a scalar score;
- claiming access to a player's true internal perception;
- using selected action as the only ground truth;
- hiding uncertainty from partial camera coverage;
- training a large video model before the state-space baselines are understood.

## Success criteria

### Pilot success

- annotation protocol is usable;
- inter-rater availability agreement is at least 0.6;
- quality reports identify problematic sequences before training;
- baseline and ablation results have sequence-level uncertainty intervals.

### Research success

- dynamic features improve ranking or reveal a clear negative result;
- results replicate across at least two soccer data sources;
- provider-held-out performance exceeds naive and static baselines;
- errors can be categorized into state, perception, value, or model failures.

### Portfolio success

A reviewer can run the repository, inspect a possession, understand the scientific claim, audit the data assumptions, and see a credible route from open data to a coaching product.

## Frontend communication goal

A new viewer should understand the project within twenty seconds by watching one option emerge before a pass occurs. A coach should then be able to inspect the movement that created it, an analyst should be able to inspect the feature and uncertainty evidence, and a perception engineer should be able to see how reconstruction error changes the tactical conclusion.

Named-player studies are hypothesis-driven entry points. They become evidence only after rights-cleared, context-balanced sequences are reconstructed, annotated, and evaluated under the protocol in `PLAYER_SHOWCASE_EVALUATION.md`.

## v0.5 showcase goal

Build a 100-player perception atlas that turns elite midfield play into testable questions about scanning, body access, physical execution, teammate adaptation, opponent manipulation, and future option creation. The atlas is a hypothesis generator and frontend research interface, not a universal ranking system.
