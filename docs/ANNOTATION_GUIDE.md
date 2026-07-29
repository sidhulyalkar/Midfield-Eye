# Annotation guide v0.2

## What you are labeling

You are labeling the **menu of plausible actions at a moment**, not grading the player after seeing the outcome.

Pause the clip at the focal frame, inspect the preceding context, then label each generated pass, carry, or hold option.

## Availability

- **yes**: a competent player could plausibly attempt the action now;
- **no**: the action is physically or temporally closed;
- **uncertain**: the footage, tracking, or tactical context is insufficient.

Availability does not mean the action is good.

## Tactical value, 0–4

- **0**: impossible, immediately harmful, or clearly loses the ball;
- **1**: weak option with little benefit or high avoidable risk;
- **2**: viable control option;
- **3**: strong option that improves the possession;
- **4**: exceptional option that creates a major advantage.

Judge the action assuming competent execution, while accounting for realistic technical difficulty.

## Visibility

- **yes**: the receiver or space is plausibly within the carrier's current information field;
- **partial**: the option may be detectable through peripheral vision, prior scanning, or teammate cues;
- **no**: the option is likely outside current view and unsupported by recent scanning evidence;
- **uncertain**: viewpoint cannot be inferred.

Do not equate broadcast visibility with player visibility.

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

## Selected action

Mark the action that occurred. This is descriptive and should not change your availability labels for alternatives.

## Confidence

Use lower confidence when:

- the camera does not show the full pitch;
- players are extrapolated;
- ball carrier identity is inferred;
- body or head orientation is unavailable;
- the action target is ambiguous;
- the sequence is too short to establish context.

## Annotation procedure

1. Watch the clip once without pausing.
2. Watch the preceding 2–4 seconds again.
3. Pause at the focal frame.
4. Label availability before value.
5. Label visibility independently.
6. Mark the selected action only after alternatives are labeled.
7. Add a short note for unusual tactical reasoning.
8. Revisit low-confidence labels after completing the sequence.

## Reliability sample

At least 25% of frames should be labeled by two annotators. Report:

- Cohen's kappa or Krippendorff's alpha for availability;
- weighted agreement for 0–4 value;
- agreement by action type;
- disagreement categories;
- confidence-conditioned agreement.

## Provider-specific cautions

### SkillCorner

Distinguish detected from extrapolated players. Consider a second observed-only annotation pass for selected sequences.

### StatsBomb 360

Label only static/event-centered questions. Do not infer velocity or scanning history from one frame.

### SoccerTrack v2

The ball is placed at the BAS actor in the current adapter. Treat pass-contact timing as approximate.

### SoccerNet GSR

Inspect the possession sidecar and camera coverage. Do not assume missing players are absent from the tactical scene.
