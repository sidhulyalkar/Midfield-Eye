# Code, data, and model boundary

## Main package

The Midfielder's Eye source code is MIT licensed.

## SoccerNet GSR

The external `sn-gamestate` repository is GPLv3. This repository does not vendor, modify, or import
its code into the main Python package. The `services/video_perception` directory contains only a
process wrapper and container recipe that fetch the upstream project at build time.

A process boundary is operationally useful, but it is not legal advice or a universal exemption from
license obligations. Review intended distribution and deployment with qualified counsel.

## Data

SoccerNet data is intended for research and has separate registration, copyright, and usage terms.
Do not commit videos, labels, or derived media unless redistribution is explicitly permitted.

Metrica, SkillCorner, StatsBomb, SoccerTrack, Sportec, EgoTraj, and commercial providers each retain
their own terms. The provider registry is descriptive, not a grant of rights.

## Model weights

Detector, re-identification, calibration, OCR, and tracking weights may have licenses independent of
their code repositories. Every perception run must record model names, source URLs outside the
artifact, versions, and weight hashes. Do not include weights in release archives by default.

## Safe release contents

A project release may include:

- source code written for Midfielder's Eye;
- tiny synthetic fixtures;
- schemas and adapter tests;
- manifests without private credentials;
- aggregated metrics and legally shareable visualizations;
- instructions for users to obtain external dependencies themselves.

It should not include external match video, restricted provider data, unreviewed model weights,
credentials, or copied GPL source inside the MIT package.
