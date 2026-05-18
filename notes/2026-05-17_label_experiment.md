# Label experiment: MultiGeometry+Point survives GE Pro round-trip

**Date:** 2026-05-17 evening
**Status:** Proof of concept complete. Script edit not yet done.

## What we confirmed

Building labels via `<MultiGeometry><Point/><Polygon/></MultiGeometry>` 
work in Google Earth Pro and survive Save Place As round-tripping.

The mechanism:
- A `<Placemark>` containing a `<MultiGeometry>` 
- The MultiGeometry contains both a `<Point>` (label anchor at roof altitude) 
  and a `<Polygon>` (the extruded building footprint)
- The Placemark's `<name>` element becomes the visible label text
- The Point's `<coordinates>` (lon, lat, alt) determines where the label floats

GE Pro re-serializes the structure on save (whitespace, floating-point 
representation, element ordering) but preserves all semantics. Placemark 
counts, MultiGeometry counts, and Point counts all unchanged after round-trip.

## Test artifacts (scratch, in /tmp, lost on reboot)

- `/tmp/geometry-label-test-with-label.kml` — modified May 17 file with one 
  hand-added test Placemark at Civic Center Park (37.8689, -122.2716)
- `/tmp/geometry-label-test-after-roundtrip.kml` — file after GE Pro Save 
  Place As; structure preserved
- `/tmp/geometry-label-test-all-visible.kml` — same as -with-label but with 
  `<visibility>0</visibility>` replaced by `<visibility>1</visibility>` so 
  all 184 production polygons render

## Visual finding

The label test renders as the polygon plus a default pushpin icon plus the 
text. For production rollout the pushpin should be hidden — add an 
`<IconStyle>` with `<scale>0</scale>` and `<Icon><href></href></Icon>` to a 
custom Style referenced via `<styleUrl>` on each Placemark.

## Architecture findings discovered during this work

1. **Embedded tour leftover.** `Geometry-2026-05-17.kml` contains an embedded 
   `<gx:Tour>` called "Berkeley Housing Pipeline - Extended Dramatic Tour" 
   that's leftover from prior GE Pro work. Should be removed before the 
   geometry is deployed publicly. Separate cleanup task.

2. **Visibility flag system.** The file uses `<visibility>0</visibility>` at 
   three levels (Document, Folder, Placemark). Intentional — the embedded 
   tour toggles visibility per-building during playback. For label rendering 
   outside the tour, set all visibility to 1 or strip the Document- and 
   Folder-level flags.

3. **OUTPUT_PATH is stale.** `scripts/generate_kml.py`'s OUTPUT_PATH points 
   at `berkeley_skyline_v9_2026-05-03.kml`. Needs updating to write to the 
   current canonical Geometry directory: 
   `docs/kml_versions/Geometry/Geometry-YYYY-MM-DD.kml`.

4. **Vertex-cleanup work is real and quantifiable.** Monotonic decrease in 
   total vertex count from 1176 → 1115 → 1103 → 1062 across the dated 
   Geometry files, despite polygon count increasing from 177 → 184. Average 
   vertices per polygon dropped from 6.64 to 5.77. This work shouldn't be 
   lost in any cleanup, and feeds the case for treating the GE-cleaned KML 
   as authoritative geometry (Pattern A) rather than treating database 
   geometry as canonical (Pattern B).

## What to do next session

1. Edit `scripts/generate_kml.py` lines 271-286 to emit `<MultiGeometry>` 
   wrapping `<Point>` (centroid + roof altitude) and `<Polygon>` (existing 
   extrusion).

2. Update `<name>` to include units and stage: 
   `f"{address} · {units} units · {stage}"`.

3. Add a label-only `<Style>` (zero-scale icon, custom LabelStyle) referenced 
   from each Placemark to suppress the default pushpin.

4. Update OUTPUT_PATH to write to current canonical location.

5. Run the script, import the result to GE Pro, manually verify labels 
   render correctly.

6. Decide whether to keep round-tripping through GE Pro for vertex cleanup 
   (Pattern A) or migrate vertex cleanup back into the source database 
   (Pattern B).
