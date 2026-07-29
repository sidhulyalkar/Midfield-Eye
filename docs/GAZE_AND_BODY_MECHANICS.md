# Gaze and Body Mechanics

## Why they matter

The same pitch location can expose radically different action menus depending on where the player is looking, how the torso is oriented, which foot is loaded, and whether the body can still brake or turn.

Version 0.5 separates these quantities instead of collapsing them into one "vision" score.

## Gaze source hierarchy

Every frame has one of these sources:

1. `observed`: calibrated eye tracking or an equivalent direct measurement;
2. `pose_inferred`: head or face pose used as a gaze proxy;
3. `motion_proxy`: body or movement heading used as a coarse proxy;
4. `synthetic`: an illustrative generated scenario;
5. `unknown`.

The frontend must show source and confidence beside every gaze view.

## View bands

The renderer exports three nested geometric fields:

- foveal band: narrow attention emphasis;
- actionable band: primary field used for option visibility;
- peripheral band: broad awareness context.

These are communication and modeling bands, not a universal physiological model of human vision.

## Gaze metrics

- scan count and scan rate;
- head-body dissociation;
- gaze-head dissociation;
- top-option angular error;
- visible-option recall;
- blind-side option count;
- first acquisition time for the top option;
- visible dwell duration.

A scan event is inferred from head-angle velocity. It is only a literal eye-movement claim when the source is `observed`.

## Body-mechanics metrics

- body and movement heading separation;
- forward acceleration;
- lateral-load proxy;
- braking-load proxy;
- turning-load proxy;
- balance-reserve proxy;
- open-body score;
- option angular spread;
- multi-action readiness;
- weight-transfer vector.

These values describe kinematic or pose-derived execution conditions. They do not measure ground-reaction force, center of pressure, support-foot load, or joint torque unless appropriate sensors are attached.

## Future upgrades

- multi-view 2D/3D pose;
- foot-contact and plant-foot classification;
- monocular head-pose uncertainty;
- synchronized wearable gaze;
- inertial measurement units;
- shoe or insole pressure;
- pose-to-action calibration by player and action type;
- direct validation against eye-tracking and biomechanics data.
