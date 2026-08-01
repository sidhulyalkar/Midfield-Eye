# Provider foundations: synchronization, direction, visibility, and selection

This note records the evidence boundary for four provider-facing foundations. The miniature files
under `tests/fixtures/` are provider-shaped test records, not redistributed match data.

## Metrica raw tracking and synchronized events

Official source: <https://github.com/metrica-sports/sample-data>

The official sample contract uses normalized `0–1` coordinates, a top-left origin, a 105 × 68 m
reference pitch, 25 Hz tracking, and synchronized event/tracking files. Metrica tracking files use
three header rows: team, player identity, and coordinate axis.

`adapters.metrica.read_metrica_tracking_csv` accepts that raw format and the existing normalized
single-header format. Official raw home and away team files can be joined one-to-one by period,
frame, and timestamp with `away_tracking_path`. The parser names provider columns without flipping
either half. Native coordinate conventions, the header format, and carrier/possession sources are
retained in frame metadata.

`load_metrica_open` parses events and attaches synchronization evidence:

- provider `Start Frame` plus period is preferred when present;
- otherwise `fusion.align_events_to_frames` performs period-aware nearest-time matching;
- match method, error, and tolerance remain on every event;
- unmatched events produce an adapter warning.

Event synchronization is not possession ground truth. The legacy `possession_team` argument is
still explicit, and nearest-player carrier assignment is marked `inferred_ball_carrier`.

## SkillCorner fixed coordinates and half direction

Official source: <https://github.com/SkillCorner/opendata>

The open-data README defines metres, pitch-centre origin, x on the long axis, y on the short axis,
10 Hz tracking, visible-area projection, and `is_detected`. It does not define a half-specific
attacking-direction field. The adapter therefore:

- treats provider coordinates as a fixed pitch frame and never flips them;
- preserves detected players as `observed` and undetected records as `extrapolated`;
- accepts a match-specific direction ledger only as external evidence;
- validates opposite home/away signs and the half-time side switch;
- returns `inconclusive` when evidence is absent and `failed` when supplied evidence is invalid;
- marks affected frames `attacking_direction_unverified` rather than hiding uncertainty.

Coordinates outside declared pitch bounds are explicitly clipped with an adapter warning; the
native coordinate remains on the player record.

## Visible-area option mask

The affordance engine retains every candidate represented in the canonical frame. A provider
camera polygon must not redefine physical availability or the player's literal perception.

Each option now carries separate fields:

- `visible_area_mask`: target inside the provider polygon (`0` or `1`);
- `provider_visibility_known`: whether such a polygon exists;
- `perceptual_visibility_proxy`: the carrier-orientation field-of-view proxy;
- `physical_candidate_retained`: always `1` for emitted candidates;
- `visible_pitch_fraction`: polygon coverage for quality stratification.

An outside-area target remains in the menu. Its observation confidence is reduced, but
`label_available` and `label_visibility` remain unset until supported by annotation.

## StatsBomb 360 selected receiver

Official sources:

- <https://github.com/hudl/open-data>
- <https://github.com/statsbomb/statsbombpy>

StatsBomb exposes event UUID, event actor, pass recipient and end location, and 360 freeze-frame
actor/teammate/location/visible-area fields. The 360 payload does not expose persistent identities
for all freeze-frame teammates.

The adapter preserves the event recipient ID when present, then maps the selected receiver to an
event-local freeze-frame teammate only when pass-end proximity is within tolerance and
unambiguous. The mapping method and distance remain in `frame.metadata.selected_action`.
Unmapped or ambiguous receivers produce a warning and no manufactured selection label.

`label_statsbomb_selected_options` labels one supported generated pass option and the alternatives
as not selected. It does not label alternatives unavailable, invisible, or low value. Event-local
receiver IDs may not be joined across event snapshots.
