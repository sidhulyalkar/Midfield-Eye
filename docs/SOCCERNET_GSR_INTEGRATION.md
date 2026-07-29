# SoccerNet Game State Reconstruction integration

## Role in the system

SoccerNet GSR is the perception layer. It reconstructs visible sports-person state from a moving
single broadcast camera. Midfielder's Eye owns the later state-reconstruction and tactical layers.

```text
video perception             state reconstruction                 tactical cognition
------------------           --------------------                 ------------------
detection                     coordinate normalization            pressure
re-identification             uncertainty propagation             passing corridors
tracking                      causal smoothing                     future space
pitch projection              camera-cut handling                  action menu
team / role attributes        ball and possession fusion          counterfactuals
```

The integration is external by design. It avoids dependency turbulence, preserves a clean license
boundary, and makes tactical experiments reproducible from frozen tracker states.

## Supported input forms

`read_tracker_state` accepts:

- official SoccerNet `predictions` or `annotations` JSON;
- JSONL observation exports;
- CSV dataframe exports;
- Parquet dataframe exports with the optional `parquet` dependency;
- trusted local pandas pickle outputs.

The reader recognizes explicit aliases for frame ID, track ID, pitch position, role, team, jersey,
confidence, camera confidence, and image bounding box. Records with missing pitch coordinates or
identity are skipped with warnings.

## Intermediate perception schema

A tracker state is first converted into `TrackerStateBundle`:

```python
TrackerStateBundle(
    frames=list[PerceptionFrame],
    source_path=str,
    match_id=str,
    fps=float,
    warnings=list[str],
    metadata=dict,
)
```

`PerceptionFrame` contains no invented ball or possession:

```python
PerceptionFrame(
    frame_id=int,
    timestamp_s=float,
    observations=list[TrackerObservation],
    visible_pitch_polygon=list[list[float]] | None,
    camera_confidence=float | None,
)
```

## Tactical conversion contract

`SoccernetGSRAdapter.convert` requires an explicit sidecar containing:

- frame ID;
- ball x and y;
- possession team;
- ball carrier track ID;
- optional timestamp, velocity, period, ball confidence, possession confidence, and status.

A frame is skipped when the sidecar carrier is absent from the visible tracker state. This is safer
than silently assigning the nearest visible player. Future work may represent an off-screen carrier
as a distribution, but it must not pretend that player was observed.

## Confidence and covariance

Detection, tracking, and calibration confidence are combined conservatively. The current covariance
mapping is a transparent heuristic:

```text
localization variance
  = base detector uncertainty
  + observation-confidence penalty
  + camera-calibration penalty
```

It is not advertised as calibrated probability. It exists so uncertainty is represented and can be
replaced by empirical calibration on held-out GSR ground truth.

## Team identity

Raw `left` and `right` labels are mapped to canonical teams only through an explicit mapping. The
current default is `left → home`, `right → away` for compatibility with open fixtures. Real match
processing should provide period-aware team metadata and verify halftime direction changes.

Jersey recognition is optional for the initial tactical experiments. Anonymous persistent tracks are
sufficient for pressure and option geometry. Jersey OCR should be enabled only when player-level
identity is needed and its compute or failure modes are justified.

## Reproducibility

Every frozen state should have a run manifest and a fully resolved model manifest containing:

- SHA-256 and byte size of the tracker state;
- exact upstream commit;
- dataset version;
- model names and weight hashes;
- active Hydra overrides;
- runtime information;
- input-video hash when legally permissible.

Use:

```bash
midfielders-eye gsr-manifest tracker_state.pkl \
  --repository-path /path/to/sn-gamestate \
  --dataset-version 1.3
```

## Acceptance criteria for a real baseline run

- one validation clip completes;
- tracker state is saved and hashed;
- minimap visualization renders;
- upstream GSR evaluation executes;
- the exact code, data, and weight versions are recorded;
- the state converts into canonical frames;
- quality audit reports visibility and uncertainty;
- tactical extraction runs without importing upstream dependencies.

## Non-goals

This adapter does not:

- bundle or execute upstream models inside the main package;
- infer true player gaze;
- reconstruct off-screen players as certainty;
- infer possession from player detections alone;
- claim that a good GSR score guarantees tactically faithful passing lanes.
