# Empirical Data Strategy

Version 0.6 separates six evidence classes that the interface, models, and written claims must never collapse:

1. **Direct measurement**: calibrated eye tracking, instrumented motion capture, IMU, or kinetics.
2. **Provider tracking**: player, ball, event, and visible-area coordinates supplied by a football data provider.
3. **Video reconstruction**: pose, tracking, identity, and calibration estimated from pixels.
4. **Inferred proxy**: movement heading, torso proxy, synthetic view cone, or model-derived body-load estimate.
5. **Synthetic**: controlled software demonstrations.
6. **Editorial hypothesis**: a scouting or research question.

## Best source stack

| Source | Strongest signal | Access | Immediate role |
|---|---|---|---|
| Ego-Exo4D V2 | 3D eye gaze, synchronized egocentric/exocentric video, head trajectory, IMU | License agreement and official CLI | Direct gaze pretraining and soccer-specific transfer experiments |
| WorldPose | Soccer-specific global 3D body pose and calibrated broadcast footage | Institutional registration, non-commercial academic license | Body-pose validation in real match geometry |
| OpenCap | Consented smartphone-derived 3D motion and model-derived forces | Prospective capture | Controlled receiving, scanning, braking, passing, and turning experiments |
| Pose2Sim | Multi-camera markerless 3D kinematics and OpenSim outputs | Open software; participant media requires consent | Reproducible field biomechanics laboratory |
| SportsPose | Dynamic sports 3D pose with marker-based validation | Academic request | Stress-testing sports pose estimators |
| AthletePose3D | High-speed, high-acceleration athletic pose | Research license | Athletic-motion pretraining and kinematic validation |
| Metrica Sample Data | Synchronized full tracking and events | Open sample | Oracle-state tactical geometry and temporal tests |
| StatsBomb Open Data 360 | Named-player events, visible-area polygons, event freeze frames | Open analysis with attribution terms | Named-player event-centered affordance snapshots |
| SkillCorner Open Data | Broadcast-derived tracking with observed/extrapolated state | Open repository | Partial-observation and provider-shift experiments |
| SoccerNet GSR | Broadcast video to identity-aware pitch state | Registered research data; GPL service | Real video perception and reconstruction benchmark |

## What has been incorporated now

The repository includes two compact, source-pinned empirical bundles:

- `data/empirical/open/metrica_game1_pass_1226`: 15 real synchronized tracking frames around a pass from anonymous Player10 to Player8.
- `data/empirical/open/statsbomb_3857263_pedri`: Pedri's real event and matching StatsBomb 360 snapshot from Spain versus Germany on 27 November 2022.

They support parser, provenance, visualization, and evidence-boundary tests. They do not claim literal gaze or biomechanics.

## Why the full gaze and pose datasets are not mirrored

Ego-Exo4D, WorldPose, SportsPose, AthletePose3D, SoccerNet, and SoccerTrack have license, registration, or redistribution restrictions. The repository contains:

- the exact access plan;
- official source URL and citation;
- governed downloader instructions;
- adapters for expected outputs;
- validation and claim gates;
- no copied restricted files.

Run:

```bash
midfielders-eye empirical-sources
midfielders-eye empirical-plan ego_exo4d
midfielders-eye empirical-plan worldpose
```

## Scientific sequence

1. Validate the tactical engine on Metrica full tracking.
2. Validate named-player event geometry on StatsBomb 360.
3. Train gaze-motion representations on Ego-Exo4D soccer takes, holding out participants and takes.
4. Test whether gaze pretraining improves option visibility prediction on a new consented football gaze study.
5. Validate pose estimation against WorldPose, SportsPose, and AthletePose3D.
6. Run a controlled OpenCap/Pose2Sim midfield-reception protocol.
7. Apply the validated perception stack to rights-cleared match video.
8. Publish named-player conclusions only when the source, context, and uncertainty support them.

## Official sources

- Ego-Exo4D: https://docs.ego-exo4d-data.org/
- WorldPose: https://worldpose.ait.ethz.ch/
- OpenCap: https://www.opencap.ai/
- Pose2Sim: https://github.com/perfanalytics/pose2sim
- SportsPose: https://orbit.dtu.dk/en/datasets/the-sportspose-dataset/
- AthletePose3D: https://github.com/calvinyeungck/AthletePose3D
- Metrica: https://github.com/metrica-sports/sample-data
- StatsBomb Open Data: https://github.com/hudl/open-data
- SkillCorner Open Data: https://github.com/SkillCorner/opendata
- SoccerNet GSR: https://github.com/SoccerNet/sn-gamestate
