# SoccerNet GSR perception service

This directory keeps SoccerNet/TrackLab outside the main Python environment and outside the
Midfielder's Eye license boundary. It is a process wrapper, not a vendored fork.

## Contract

1. Pin an upstream commit and model-weight manifest.
2. Run the external perception pipeline once.
3. Save its immutable tracker state and a run manifest.
4. Convert the tracker state with `midfielders-eye gsr-ingest`.
5. Perform temporal reconstruction and tactical experiments in the main package.

The wrapper defaults to a dry run. A resolved model manifest is mandatory with `--execute`. Add `--execute` only after verifying the Hydra overrides against
the pinned upstream commit. Upstream module names and installation details can change.

```bash
python services/video_perception/run_gsr.py \
  --repo /opt/sn-gamestate \
  --output-dir /output/run-001 \
  --dataset-version 1.3 \
  --model-manifest /output/MODEL_MANIFEST.resolved.json \
  --override state.save=true
```

The main repository never assumes that a five-metre GSR localization tolerance is tactically safe.
Every exported state must be tested against downstream affordance sensitivity.

The official baseline command for the pinned upstream release is `uv run tracklab -cn soccernet`. Custom-video keys must be verified against that commit rather than guessed by this wrapper.
