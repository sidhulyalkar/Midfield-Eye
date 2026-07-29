# Gaze Acquisition and Validation Protocol

## Goal

Estimate when a player acquired tactically relevant information, while distinguishing literal gaze from head direction, torso direction, and movement direction.

## Phase A: Ego-Exo4D transfer pretraining

Use only soccer takes with valid eye gaze, trajectory, and synchronized ego/exo views.

Inputs:

- personalized eye gaze when available;
- general gaze otherwise, with a source flag;
- Aria RGB and calibration;
- exocentric synchronized video;
- head trajectory and IMU;
- task and take metadata.

Targets:

- 3D gaze ray;
- 2D gaze projection in ego and exo views;
- scan-event onset and offset;
- gaze/head/torso dissociation;
- future attended region;
- uncertainty from calibration and missing depth.

Splits must be participant-held-out and take-held-out. Soccer takes from the same capture must not leak across train and evaluation.

## Phase B: consented football gaze study

Recommended minimum pilot:

- 12 to 20 players;
- multiple midfield roles and skill levels;
- instrumented small-sided and pattern-play tasks;
- synchronized eye-tracking glasses, wide tactical cameras, ball tracking, and manual event annotations;
- repeated forms of the same tactical problem.

Tasks:

1. receive on the half-turn under rear pressure;
2. switch play after attracting a presser;
3. third-player combination;
4. blind-side support run;
5. transition scan before ball recovery;
6. delayed pass versus immediate release.

## Core gaze metrics

- scan rate before reception;
- first acquisition time for the eventually selected target;
- first acquisition time for the model-best unselected option;
- visible-option recall;
- dwell on pressure, receiver, ball, and future space;
- head-gaze dissociation;
- scan-to-action latency;
- gaze entropy and repeated checking;
- calibration quality and missing-data fraction.

## Validation

- dual human review of scan-event boundaries;
- calibration drift checks before and after each block;
- sensitivity to gaze depth assumptions;
- agreement between eye gaze and exocentric projection;
- test-retest reliability by player and task;
- report direct gaze separately from pose-inferred and motion-proxy estimates.

## Clock alignment implementation

v0.6 includes `midfielders_eye.empirical.alignment` for reproducible sensor-to-match clock fitting, nearest-frame gaze alignment with explicit missing intervals, and a transparent threshold scan-event baseline. Every aligned sample preserves the original sensor timestamp, mapped canonical timestamp, frame timestamp, timing residual, source, and confidence. The baseline is not described as a physiological saccade detector until validated against human annotations.

Use at least three synchronization anchors per block in practice, even though two are the mathematical minimum for offset and drift. Keep the original clocks immutable and store the fitted clock parameters in the evidence manifest.
