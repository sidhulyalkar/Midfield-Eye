# v0.3 implementation inventory

## Implemented now

- frozen tracker-state reader for official JSON and dataframe exports;
- camera-state and visible-polygon ingestion;
- explicit possession-sidecar contract;
- confidence fusion and 2D position covariance;
- canonical schema aliases and nested export;
- JSONL and optional Parquet frame serialization;
- immutable perception manifests;
- isolated external GSR service scaffold;
- causal Kalman reconstruction;
- acceleration, movement heading, and turning-rate derivation;
- explicit motion-proxy body orientation with provenance and confidence;
- marked offline gap interpolation;
- camera-cut detection;
- conservative track-stitch proposals;
- possession estimation from an actual ball track;
- pass-transition detection;
- synthetic camera crops;
- formation-prior state completion baseline;
- controlled perception degradation;
- perception, identity, fragmentation, calibration, camera-coverage, kinematic, tactical, and decision metrics;
- CLI commands and unit tests.

## Scaffolds requiring real external data

- execute a pinned SoccerNet GSR baseline clip;
- export a real TrackLab state from the pinned version;
- verify the exact upstream Hydra keys for skipping jersey OCR and saving state;
- run the official GS-HOTA evaluator;
- calibrate covariance against GSR ground truth;
- fuse a dedicated ball detector and tracker;
- align real broadcast video with a full-tracking oracle;
- train a learned hidden-player completion model.

## Why these remain external

The release archive intentionally contains no external video, model weights, or upstream code. The
heavy baseline cannot be truthfully declared executed without the dataset, GPU environment, pinned
weights, and upstream repository. The included service makes that next execution reproducible rather
than pretending a dry scaffold is an empirical result.
