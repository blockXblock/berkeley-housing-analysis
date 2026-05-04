# Tour KMLs

Tour files animate camera paths over the skyline. Open alongside
`docs/berkeley_skyline.kml` so the extruded buildings render during flight.

## Naming convention

`tour-{corridor}-{direction}-{variant}.kml`

- **corridor** — lowercase, hyphenated. Examples: `shattuck`, `bancroft`,
  `university`, `adeline`, `telegraph`, `san-pablo`. Multi-corridor tours
  join with `+` (e.g., `adeline+shattuck`) or use a route name
  (e.g., `downtown-loop`, `campanile-to-shattuck`).

- **direction** — `s2n`, `n2s`, `e2w`, `w2e`, `loop`, `pan`.

- **variant** (optional) — single word. Reserved vocabulary:
  - `slow`, `fast` — pace
  - `low`, `high` — altitude
  - `dawn`, `dusk` — Google Earth lighting
  - `narrate` — long pauses for voiceover
  - `draft` — preview, not for publication
  - `v2`, `v3` — iteration on same route/pace/altitude

Date is metadata in the tour's `<description>`, not the filename. Filenames
stay stable; new content replaces old at the same filename when revising.

## Theme tours (no corridor)

Some tours showcase a project category rather than a route:
- `tour-uc-projects-tour.kml`
- `tour-completed-tour.kml`
- `tour-stalled-tour.kml`

## Tours index

See `scripts/list_tours.py` for an auto-generated index (TODO).
