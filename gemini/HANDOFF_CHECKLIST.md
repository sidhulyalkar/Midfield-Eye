# Gemini Handoff Checklist

Before opening Google AI Studio:

- [ ] Push the complete v0.6 repository to GitHub.
- [ ] Confirm `artifacts/showcase/manifest.json` exists.
- [ ] Confirm all eight scenario folders contain seven 4K visuals.
- [ ] Confirm `frontend_contract/integration-contract.json` is present.
- [ ] Confirm `/api/scenarios/{scenario_id}/frames` is in the OpenAPI contract.
- [ ] Keep `docs/GEMINI_MASTER_PROMPT.md` open for the first Build-mode prompt.
- [ ] Tell Gemini to treat `frontend_contract/openapi.json` as stable.
- [ ] Do not upload licensed video files to a public repository.
- [ ] Put API keys and private media URLs in server-side secrets only.
- [ ] Require a successful production build before accepting the frontend.
- [ ] Run each prompt in `docs/GEMINI_ITERATION_PROMPTS.md` separately.
- [ ] Audit every player claim for evidence status before publishing.
- [ ] Complete one synthetic and one empirical vertical slice before expanding every route.

After Gemini creates the frontend:

```bash
python scripts/prepare_gemini_handoff.py /path/to/generated-frontend
```

This copies the static bundle into `public/showcase` and the stable contracts into `src/contracts`.

- [ ] `/empirical` loads the source-backed studies.
- [ ] `/empirical/sources` shows access and license gates.
- [ ] Missing gaze and biomechanics are rendered as unavailable, not zero.
- [ ] `/evidence-ledger` covers all 100 player profiles.
- [ ] `/capture-studio` exports JSON and Markdown protocols.
