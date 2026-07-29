# Midfield Body-Mechanics Capture Protocol

## Goal

Measure how receiving posture, braking, turning, and weight transfer preserve or collapse the future action menu.

## Capture tiers

### Tier 1: OpenCap

Use two or more synchronized smartphones for the highest-accuracy OpenCap workflow. Export OpenSim motion and model-derived dynamics. OpenCap is appropriate for non-commercial research or educational studies under its terms.

### Tier 2: Pose2Sim

Use calibrated phones, webcams, or action cameras. Retain camera calibration, reprojection error, 2D keypoint confidence, triangulated 3D points, and OpenSim outputs.

### Tier 3: reference pose datasets

Use WorldPose for soccer-specific broadcast pose, SportsPose for dynamic-pose validation, and AthletePose3D for high-acceleration robustness. These are validation and pretraining resources, not named-player force measurements.

## Standardized tasks

- receive and play both directions;
- receive under passive and active rear pressure;
- brake from a curved approach;
- open hips before first contact;
- disguise and reverse pass;
- carry across the pressure line;
- shoot or slip pass from the same preparation;
- reposition off the ball and receive again.

## Required outputs

- pelvis, thorax, head, hip, knee, ankle, and foot orientation;
- center-of-mass estimate;
- angular velocity and acceleration;
- braking and lateral acceleration;
- support-foot placement;
- first-touch direction;
- time to stabilize;
- action-direction envelope;
- uncertainty and reprojection error.

## Claim language

OpenCap kinetics and monocular/multiview pose remain model-derived unless validated against direct force or marker systems in the same study. Use “estimated joint moment,” “kinematic load proxy,” or “model-derived ground reaction force,” never an unqualified force measurement.

## Machine-checkable protocol

Generate the v0.6 prospective study contract with:

```bash
midfielders-eye capture-protocol --participant-id study-001
```

The JSON contract records sensors, sampling rates, clock domains, calibration requirements, task blocks, consent scope, synchronization anchors, retention, direct versus derived measurements, preregistered metrics, and prohibited claims. The API exposes the same protocol at `/api/capture-protocol/default` and validates edited protocols at `/api/capture-protocol/validate`.
