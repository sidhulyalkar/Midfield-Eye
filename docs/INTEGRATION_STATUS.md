# Integration status matrix

| Integration | Parser | Coordinates | Possession | Events | Visibility | Kinematics | Uncertainty | Tests | Scientific status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Metrica normalized CSV | yes | yes | inferred/argument | pending raw sync | no | optional native | basic | yes | ready for real pilot after raw synchronization |
| SkillCorner Open JSONL | yes | yes | native | dynamic CSV | polygon | causal inferred | observed/extrapolated | yes | ready for visibility studies after coordinate audit |
| StatsBomb 360 | yes | yes | event actor | native events | polygon | unavailable | snapshot flags | yes | ready for snapshot studies |
| Sportec via Kloppy | optional | bridge assumes metric | nearest/native team | loader pending fusion | no | native bridge pending | provider dependent | bridge test | replication path ready |
| SoccerTrack v2 | yes | yes | BAS actor | BAS | panoramic | snapshot only | provider confidence | yes | event-snapshot path ready |
| SoccerNet official JSON | yes | yes | mandatory sidecar | sidecar/future spotting | optional polygon | reconstructed | covariance + confidence | yes | ready for frozen-state experiments |
| SoccerNet TrackLab CSV/JSONL/Parquet | yes | yes | mandatory sidecar | sidecar | camera sidecar | causal reconstruction | full v0.3 contract | yes | primary external perception boundary |
| SoccerNet trusted pickle | yes | yes | mandatory sidecar | sidecar | camera sidecar | causal reconstruction | full v0.3 contract | yes | local conversion only; portable formats preferred |
| EgoTraj | existing | trajectory-specific | not applicable | not applicable | egocentric | native | native/source dependent | existing | auxiliary pretraining only |

## SoccerNet boundary status

Implemented:

- dry-run-first external process wrapper;
- isolated Docker and Compose scaffold;
- exact run and model manifest templates;
- tracker-state readers and schema aliases;
- confidence fusion and covariance construction;
- explicit team mapping and pitch normalization;
- visibility/camera-state preservation;
- possession-template generation and required sidecar ingestion;
- causal reconstruction and degradation benchmarking.

Not executed in this release:

- downloading restricted data or model weights;
- running the external GPU perception pipeline;
- validating Hydra overrides against a specific pinned upstream commit;
- reproducing official upstream benchmark scores;
- comparing a real reconstructed clip against synchronized oracle tracking.

## Meaning of status

“Ready” means the software path is implemented and tested on provider-shaped fixtures. It does not
mean the external dataset has been downloaded, model weights have been licensed, the GPU pipeline has
been executed, or scientific validity has been established on real matches.

## Frontend integration status

| Layer | Status | Meaning |
|---|---|---|
| Static showcase bundle | implemented | 100 profiles, eight synthetic scenarios, two empirical studies, and 4K assets can be generated |
| FastAPI resources | implemented | scenario frames, options, timelines, cognition payloads, empirical evidence, and capture validation are served |
| Normalized data-source contract | specified | static/API mappings, null policy, joins, URL state, and evidence grammar are frozen for implementation |
| Component and visual tokens | specified | pitch order, component states, evidence styles, responsive targets, and motion rules are machine-readable |
| React application | not implemented | Gemini should build it from `GEMINI_FRONTEND_IMPLEMENTATION_BLUEPRINT.md` |
| Deployed public product | not implemented | requires frontend build, visual regression, accessibility audit, and deployment configuration |
