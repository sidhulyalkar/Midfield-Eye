# Gemini AI Studio Iteration Prompts

Use these only after the master build works.

## Pass 0: Contract and vertical-slice audit

Before broad route work, verify the `ShowcaseDataSource`, Zod boundaries, static/API normalization,
single playback store, evidence grammar, and one complete synthetic plus empirical vertical slice
against `docs/GEMINI_FRONTEND_IMPLEMENTATION_BLUEPRINT.md`. Remove direct bundle fetching from
components and make missing signals explicit.

## Pass 1: Tactical fidelity audit

Review the frontend against `src/midfielders_eye/schema.py`, `src/midfielders_eye/affordance.py`, and `docs/DATA_CONTRACT.md`. Remove invented fields and make every displayed metric traceable to an API or bundle field. Add tooltips with exact feature definitions. Verify that scores are called model scores, not probabilities.

## Pass 2: High-resolution visual polish

Optimize the tactical pitch for 3840×2160 screenshots. Ensure SVG strokes, labels, uncertainty halos, passing corridors, and pressure textures remain crisp. Add an export mode that hides navigation and produces a clean 16:9 analysis card without changing the underlying data.

## Pass 3: Timeline intelligence

Upgrade the timeline to mark option emergence, extinction, top-option switches, and confidence drops. Clicking a marker must move the pitch to the exact frame and select the relevant option. Preserve frame and option in the URL.

## Pass 4: Counterfactual coaching mode

Add a drag-to-reposition interaction for a supporting player. Use cached counterfactual data when available and label client-only approximations clearly. Show original position, alternative position, option-menu uplift, and a short coaching interpretation.

## Pass 5: Perception reliability

Create a compelling oracle-versus-degraded comparison using degradation results under `artifacts/verified_v3_degradation` or newly generated v0.4 outputs. Show how missing players, calibration drift, and position noise change tactical conclusions. Never hide uncertainty.

## Pass 6: Media integration

Implement the rights-aware media registry from `docs/MEDIA_INGESTION_AND_RIGHTS.md`. Add HTML5 playback only for local rights-cleared assets. Add standard YouTube iframe embeds only for `embed_only` assets. Keep tactical overlays in a separate panel.

## Pass 7: Portfolio narrative

Rewrite only page-level presentation copy, not scientific claims. Make the landing page explain the project in under 20 seconds, then invite deeper exploration. Preserve the distinction among perception, reconstructed state, and tactical cognition.

## Pass 8: Production hardening

Run tests, type checks, accessibility checks, and the production build. Remove console errors, unused dependencies, broken routes, layout shifts, and hard-coded absolute paths. Confirm static bundle fallback and API mode both work.
