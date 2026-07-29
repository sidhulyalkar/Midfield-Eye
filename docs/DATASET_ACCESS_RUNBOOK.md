# Dataset Access Runbook

The project never bypasses a dataset gate. `empirical-download` works only for sources marked `open_repository` or `open_download`. Registration and license-request sources raise an access error and print the human steps.

## Ego-Exo4D

1. Accept the official license agreement.
2. Install the official Ego4D/Ego-Exo4D CLI and configure AWS credentials.
3. Download metadata first.
4. Filter `takes.json` for soccer activities and `has_trimmed_eye_gaze`.
5. Download only selected take UIDs and the parts needed for the experiment:
   - metadata;
   - take eye gaze;
   - take trajectory;
   - downscaled synchronized videos;
   - full-resolution video only for the final selected subset.
6. Keep the original directory outside Git.
7. Create a local source manifest containing release, take UIDs, file hashes, and license-acceptance date.

The official V2 documentation reports 5,035 takes and provides dedicated `take_eye_gaze`, trajectory, video, and metadata parts. Do not begin with the multi-terabyte default download.

## WorldPose

1. Apply using an institutional email.
2. Document non-commercial academic use.
3. Accept the non-transferable license and prohibition on redistribution.
4. Store the dataset outside the repository.
5. Export only derived, non-identifying metrics when permitted.
6. Use `load_worldpose_export` for approved JSON or NPZ exports.

## OpenCap and Pose2Sim prospective capture

1. Obtain informed consent and media/model-output permissions.
2. Define retention, deletion, and public-display rules.
3. Record standardized football movements from calibrated cameras.
4. Keep raw video private unless participants explicitly permit release.
5. Export `.mot`, `.trc`, 3D pose, calibration, and quality reports.
6. Hash all outputs and link them to a session manifest.

## Open football data

Metrica, StatsBomb, and SkillCorner should still be source-pinned. Record:

- repository URL;
- commit or blob SHA;
- exact file path;
- provider terms;
- retrieval date;
- local SHA-256;
- transformations performed.

## Forbidden patterns

- scraping a registration portal;
- copying restricted files into the Git repository;
- downloading YouTube video outside the platform's permitted mechanisms;
- stripping attribution or provider marks;
- presenting inferred gaze as eye tracking;
- publishing identifiable prospective subjects without consent.
