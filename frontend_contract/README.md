# Frontend contract

This directory is the machine-readable boundary between the Python research system and the web
application.

Read in this order:

1. `integration-contract.json` for mode selection, resource mappings, required fields, joins,
   coordinate rules, null policy, evidence grammar, URL state, and quality gates.
2. `component-contract.json` for component inputs, events, feedback states, constraints, and route
   assemblies.
3. `design-tokens.json` for the visual system, responsive layout, motion, and evidence styling.
4. `openapi.json` for API route names. The generated static payloads are the concrete contract
   fixtures until API responses migrate from `Any` to typed Pydantic models.

The human implementation specification is
`docs/GEMINI_FRONTEND_IMPLEMENTATION_BLUEPRINT.md`.

The reference implementation is under `frontend/`. It consumes this boundary through one
`ShowcaseDataSource` interface for generated static files and FastAPI responses. Contract changes
must keep both modes, their tests, and the generated payloads compatible.

Generate a complete handoff, including real payload fixtures, with:

```bash
python scripts/prepare_gemini_handoff.py ../generated-frontend --rebuild
```

Do not edit generated files under `artifacts/` as a substitute for changing their Python exporters.
