# Showcase plan

## Portfolio story

The strongest story is not “I built another expected-pass model.” It is:

> I built a provider-aware representation of the opportunities a midfielder can perceive and create, then designed experiments to determine which conclusions survive changes in tracking system, camera coverage, and reconstructed game state.

## Demo sequence

### Scene 1: the action menu

Show a central midfielder receiving under pressure. Overlay:

- ranked passes;
- carry corridors;
- pressure field;
- visible area;
- options opening over the next second.

### Scene 2: information limits

Toggle:

- full tracking;
- broadcast-observed players only;
- observed plus extrapolated players;
- event snapshot.

The viewer should immediately see how the inferred action menu changes with the information source.

### Scene 3: counterfactual movement

Move an off-ball teammate or the carrier's earlier position. Show:

- option-set value before and after;
- defenders displaced;
- new passing corridors;
- uncertainty around the counterfactual.

### Scene 4: scientific benchmark

Present:

- B0–B3 results;
- sequence bootstrap intervals;
- provider-held-out transfer;
- visibility and extrapolation ablations;
- one negative result or failure case.

### Scene 5: player-view future

Show the roadmap from overhead state to player-view gaze and head pose. Keep this clearly labeled as the next experiment, not a completed claim.

## Suggested visual assets

1. full-pitch affordance field;
2. partial-camera versus completed-state comparison;
3. option emergence timeline;
4. provider shift heatmap;
5. counterfactual positioning map;
6. error decomposition: state error versus tactical-ranking error.

## Paper-style report

Suggested title:

**The Midfielder's Eye: Provider-Aware Dynamic Affordance Fields for Football Decision Analysis**

Sections:

1. motivation and distinction from action prediction;
2. canonical state and provider taxonomy;
3. geometric affordance model;
4. annotation protocol;
5. cross-provider experiments;
6. partial observability;
7. video-to-state error propagation;
8. limitations and player-view roadmap.

## Product concept

An analyst interface should allow the user to:

- select a possession;
- scrub time;
- toggle data assumptions;
- inspect ranked actions;
- view visibility and uncertainty;
- modify a player's earlier position;
- export a coaching clip and explanation.

## v0.4 interactive application

The primary portfolio artifact is now an interactive scenario lab with four synchronized views:

1. player viewpoint and action menu;
2. coaching interpretation;
3. model evidence and uncertainty;
4. oracle-versus-perceived-state reliability.

Use the generated assets under `artifacts/showcase/` for static previews and the JSON/API contract for interactive rendering. The Google AI Studio implementation specification lives in `GEMINI_AI_STUDIO_BUILD_SPEC.md`.
