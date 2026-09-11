# Showcase, demos, and visibility

This document implements the short-term visibility roadmap: reduce friction after a clean clone, make the Decision Microscope easy to experience, and keep claim boundaries honest.

## Why artifacts are not in Git

Generated `artifacts/showcase/` (and related outputs) are large, regenerable, and intentionally untracked. A clean clone therefore needs one build step before the full interactive studio has data:

```bash
pip install -e ".[dev,showcase]"
midfielders-eye showcase-build          # or: make showcase
midfielders-eye showcase-serve          # or: make showcase-serve
```

This is deliberate: the repository stays lean, CI remains deterministic, and every demo is reproducible from code + configs.

## One-click / low-friction paths

### Local

```bash
make install
make showcase
make frontend-dev     # builds showcase then starts Vite on :5173
```

### GitHub Codespaces / VS Code Remote

A `.devcontainer/devcontainer.json` is provided. Opening the repository in Codespaces should:

1. Install Python + Node dependencies via `postCreateCommand`
2. Forward ports 8000 (API) and 5173 (frontend)

Then run:

```bash
make showcase
make frontend-dev
# or in a second terminal:
make showcase-serve
```

### Hosted static demo (planned)

Target options (pick one once a polished pre-built bundle exists):

- GitHub Pages serving a static export of the frontend + a frozen showcase bundle
- Cloudflare Pages / similar with the same static assets

Until a hosted demo is live, the Codespaces path and local `make frontend-dev` are the recommended ways to experience the Decision Microscope.

## GIF / short video capture checklist

Record 10–20 second clips (or GIFs) of:

1. **Action Menu Ribbon + seek**  
   Scrub a possession; click ribbon cells; watch the pitch and candidate highlight jump in sync.

2. **Option lifecycle**  
   Show birth → persistence → selection (or extinction) for one stable candidate identity.

3. **B1 vs B2 contrast**  
   Side-by-side or sequential ranking on the same sequence so a viewer sees dynamic geometry change the ordering.

Store under `docs/assets/` (or `docs/assets/demo/`) and link from the README hero section. Prefer muted autoplay-friendly formats or short GIFs so the README itself communicates the capability without requiring a local run.

### Suggested tooling

- Browser recording (Chrome/Edge) or OBS for screen + optional voiceover
- `ffmpeg` for trimming and GIF conversion if needed
- Keep clips short; the scientific story should be readable in under 20 seconds

## R1 status surface

The `/pilot` route is designed to show *exactly* the evidence that exists:

- Protocol-ready / sample / annotation / reliability / benchmark stages
- Empty result panel until the frozen sequence-held-out run completes
- No synthetic metrics filling real-evidence slots

When R1 advances, rebuild the showcase (or the R1 payload via `scripts/build_r1_showcase.py`) so the research cockpit updates automatically. Do not invent numbers in the frontend.

## Claim boundary (repeat)

v0.7 ships the benchmark *contract*, software, and visual instrument. Empirical superiority claims require the completed R1 (or later) pilot with reliability and sequence-held-out results. Named-player scenarios remain illustrative synthetic reconstructions unless explicitly backed by measured evidence.
