# Data Sources and Citations

The canonical machine-readable registry is `src/midfielders_eye/empirical/source_registry.yaml`.

## Direct gaze

**Ego-Exo4D V2** is the priority source because it includes soccer among its skilled activities, synchronized first- and third-person video, Aria head trajectory and IMU, and 3D/2D eye-gaze products. Access requires the official license agreement and CLI. The repository adapter reads the official gaze CSV representation without copying the dataset.

**EgoTraj** supplies synchronized RGB, 6-DoF head pose, and per-frame 3D gaze for 75 real-world navigation sequences. It is useful for general gaze-motion pretraining but is not a football evaluation set.

## Soccer pose and athletic kinematics

**WorldPose** supplies more than 80 2022 World Cup sequences and approximately 2.5 million global 3D player poses. Its license is non-commercial academic, non-transferable, and prohibits redistribution.

**SportsPose** contains more than 176,000 dynamic 3D sports poses from 24 participants across five activities, with 34.5 mm mean error against a commercial marker-based system.

**AthletePose3D** targets high-speed, high-acceleration sports motion and includes roughly 1.3 million frames and 165,000 postures. Use the corrected current release noted by the maintainers.

## Prospective biomechanics

**OpenCap** provides smartphone-video-derived 3D human motion and model-derived forces. Its hosted service is free for non-commercial research and education under its terms.

**Pose2Sim** is an open, multi-camera workflow for markerless 3D kinematics and OpenSim analysis. Participant video remains governed by consent even when the software is open.

## Football state

**Metrica Sample Data** supplies anonymized synchronized tracking and events on a 105 × 68 m pitch.

**StatsBomb Open Data** supplies named events and selected 360 freeze frames. Public analysis must acknowledge StatsBomb according to the repository terms.

**SkillCorner Open Data** supports broadcast-derived observed and extrapolated state.

**SoccerNet GSR** and **SoccerTrack v2** support video-to-game-state research but require their official access and usage terms.

See `data/empirical/CITATIONS.bib` for citation templates.
