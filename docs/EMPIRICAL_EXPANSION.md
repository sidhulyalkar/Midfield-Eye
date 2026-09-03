# Expanding real empirical examples

Discipline: every expanded example must keep **measured / inferred / proxy / reconstructed / synthetic** labels honest.

## Currently shipped open excerpts

| Bundle | What it is | What it is not |
|--------|------------|----------------|
| `data/empirical/open/metrica_game1_pass_1226` | Real Metrica tracking + synchronized pass event | Named identity, gaze, biomechanics |
| `data/empirical/open/statsbomb_3857263_pedri` | Real StatsBomb event + 360 snapshot | Continuous velocity / full dynamic persistence |

## Expansion rules

1. Prefer rights-cleared open or license-compliant sources from the registry (`midfielders-eye empirical-sources`).
2. Write `SOURCE.json` + `MANIFEST.json` with upstream SHAs and redistribution rules.
3. Never invent player gaze, force, or named biomechanics.
4. Event/snapshot sources support different claims than continuous tracking — label claim scope in the README of each bundle.
5. Rebuild empirical showcase after adding bundles:

```bash
midfielders-eye empirical-build
# or: make empirical-build
```

## Suggested next open expansions

- Additional Metrica receipt windows (still anonymous) for temporal option persistence demos
- Second StatsBomb 360 event cluster for event-centered menu snapshots
- SkillCorner open samples **only** for partial-observation stress tests (R3), not as full dynamic ground truth

## Claim mapping

| Evidence type | Allowed claims |
|---------------|----------------|
| Continuous full tracking | Dynamic geometry, option persistence, B2-style features |
| Event + 360 snapshot | Local geometry at event time, selected-action context |
| Partial tracking | Robustness / visibility masks |
| Synthetic | Interface, software validation, hypothesis illustration |

Mixing claim types in one figure without badges is a publication defect.
