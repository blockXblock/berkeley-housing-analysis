# In-browser 3D triage: Cesium vs MapLibre GL JS

**Date:** 2026-05-18 (evening)
**Status:** Triage complete; both architectural questions and implementation paths identified. No production deploy from this work.

## Goal

Investigate whether we can deliver an in-browser interactive view of Berkeley housing pipeline 3D buildings, equivalent to or better than the current "download `geometry.kml`, open in Google Earth Pro" workflow.

## Triage findings

### Cesium 1.110 — does NOT render our KML out of the box

Built a minimal Cesium demo at `experiments/cesium/index.html`. Fetches `https://berkeleybuild.com/geometry.kml`, attempts to render. Result: Cesium reports "Loaded 545 entities" but renders zero buildings visible at any zoom level or pitch angle. Berkeley imagery loads correctly; data does not.

Likely root cause: our labeled `geometry.kml` wraps each Placemark's `<Polygon>` in `<MultiGeometry><Point><Polygon></...></MultiGeometry>` for label anchoring (the technique that works in Google Earth Pro). Cesium's KML importer appears to prefer the `<Point>` and silently drop the `<Polygon>` when both are present in a MultiGeometry. Also confirmed: even loading the UN-labeled `Geometry-2026-05-17.kml` (plain `<Polygon>` per Placemark) shows the same "loaded but invisible" symptom — so Cesium 1.110 has additional rendering issues beyond just the MultiGeometry handling.

Additional Cesium 1.110 API changes from older docs:
- `Cesium.createWorldTerrain()` was removed; use `Cesium.createWorldTerrainAsync()` or omit terrainProvider entirely
- KML StyleMap `highlight` state warnings (Cesium only supports `normal`)

**Conclusion: Cesium isn't a drop-in path for our KML.** To use Cesium, we'd need to convert our data to Cesium's native CZML format. That's substantive engineering work (~1 day for a converter) and would only make sense if we later wanted a globe view that MapLibre's 2.5D approach couldn't provide.

### MapLibre GL JS — WORKS with a small unwrap step

Built `experiments/maplibre/index.html`. Uses:
- MapLibre GL JS 4.7.1 from unpkg CDN
- `@tmcw/togeojson` 5.8.1 for in-browser KML→GeoJSON conversion
- OpenFreeMap.org "positron" tile style (no token required, no signup, community-funded)

Initial result: 4 buildings rendered, 180 did not.

Diagnosis via browser dev tools: togeojson converts KML `<MultiGeometry>` to GeoJSON `GeometryCollection`. The MapLibre `fill-extrusion` layer's filter `['==', '$type', 'Polygon']` rejects GeometryCollection features. Result: only the 4 un-labeled Placemarks (plain `<Polygon>`, no MultiGeometry) passed the filter.

Fix: post-process the converted GeoJSON before adding the source. For each feature whose `geometry.type === 'GeometryCollection'`, find the `Polygon` child inside `geometry.geometries` and replace the feature's geometry with that polygon directly. Drops the Point (which we don't need in MapLibre — labels would be a separate symbol layer).

After fix: all 184 buildings render as orange extruded boxes. Height extraction from the polygon's third coordinate value works for all 184; no fallbacks needed.

**Conclusion: MapLibre GL JS is the right tool for in-browser 3D Berkeley buildings.** Free, well-documented, handles GeoJSON natively, renders extruded polygons reliably. The unwrap step is ~10 lines of JavaScript.

## Architectural insight: the KML is the wrong data path

While planning stage color-coding, surfaced this: the current data flow is

    berkeley_housing_analysis.db (canonical stage column)
        ↓ generate_kml.py serializes to <description> HTML
    docs/geometry.kml (status embedded as `Status:</b> X` text)
        ↓ fetch in browser, parse via regex
    MapLibre demo (status property reconstructed)

The regex-parsing step is fragile. The description HTML format is brittle (changes to `add_labels_to_kml.py` could silently break the regex), CDATA boundary inconsistencies require defensive regex patterns, and a typo in any of 11 string-equality comparisons silently drops color-coding for that stage.

The cleaner architecture is a **database-to-GeoJSON export**: a script that reads `projects` joined with `project_geometries` and emits a GeoJSON file where stage is a structured property, no parsing needed. Same principle as Pattern Z (KML cleanup → database) extended to a third output format (GeoJSON for browser consumption).

This is parked for a future session. The MapLibre demo on disk still uses the regex approach; should be migrated to the GeoJSON export path before being shipped publicly.

## Color legend (design intent for future implementation)

8 colors representing a permitting-progress gradient. Includes both "what we can color today" (our 184 tracked projects) and "what we'd need new data sources for" (background parcels and pre-application potential).

| Color | Hex | Stage | Data source |
|---|---|---|---|
| Light Grey | TBD | All existing parcels (background) | Berkeley 29K-parcel database — not currently in demo |
| Dark Grey | `#555555` | Pre-application potential (vacant lots, parking lots, middle-housing-enabled parcels) | NEW data source needed; cannot derive from existing data |
| Pink | `#ec4899` | Application Submitted | Existing `pipeline_stage` |
| Red | `#dc2626` | In process of City review (covers In Review, Decision Pending) | Existing `pipeline_stage` |
| Orange | `#ea580c` | Entitled (city-approved, no permit yet) | Existing `pipeline_stage` |
| Yellow | `#facc15` | Permit issued (building or demolition) | Existing `pipeline_stage` ("Permits Active") |
| Blue | `#2563eb` | Under Construction | Existing `pipeline_stage` |
| Green | `#16a34a` | Completed | Existing `pipeline_stage` |
| Black | `#1f2937` | Withdrawn or Stalled (terminated/paused) | Existing `pipeline_stage` |

**Distribution in current 184 projects:**
- Pre-Application: 2
- Application Submitted: 20
- In Review + In Review-Demolition + Decision Pending: 89
- Entitled: 30
- Permits Active: 5
- Under Construction: 11
- Completed: 17
- Withdrawn + Stalled: 2

**Honest read on the data:** ~half of tracked projects (89/184) are in "In Review / Decision Pending" — the legend's Red stage. The homepage video's existing legend (Orange/Yellow/Blue/Green) understates this. Worth reconciling the homepage video description, the methodology page, and any future visualization to one canonical legend.

## What we did NOT do (deferred)

1. **Implement color-coding in MapLibre demo** — code is drafted in the chat transcript but not applied to disk. Worth implementing in the database-to-GeoJSON refactor session rather than as a fragile-parsing extension.
2. **Click-to-show-info popup** — the data is in `f.properties.description` but no handler wired up
3. **Labels in MapLibre** — symbol layer with text rendering at building centroids, similar to what GE Pro does on pause
4. **Better basemap** — Positron is functional but visually uninteresting. Satellite or Voyager styles would be more engaging
5. **Mobile responsiveness** — desktop-focused
6. **Integration with berkeleybuild.com** — separate page vs iframe vs replacement of homepage video carousel

## Future workstreams identified by this triage

1. **Database-to-GeoJSON export script.** Parallel to `generate_kml.py`. Probably 50-80 lines. Output served at `https://berkeleybuild.com/geometry.geojson`.
2. **Stage freshness pipeline.** Periodic Accela/Clariti polling to update `pipeline_stage` in the database. Substantial multi-session workstream. Without this, any color-coded visualization shows possibly-stale stages.
3. **Pattern Z sync script.** Read cleaned KMLs back into the database (polygon vertices). Separate from #1 — that's for polygons; #1 is for new outputs.
4. **MapLibre demo evolution** into a real page on berkeleybuild.com once #1 and #2 are in place.

## Files on disk (uncommitted)

- `experiments/cesium/index.html` — Cesium 1.110 demo, working but renders zero buildings (kept as evidence of the triage finding)
- `experiments/maplibre/index.html` — MapLibre demo, renders 184 orange buildings, color-coding not yet implemented

## Bookmarks for resumption

- Color-coding the MapLibre demo with the legend above (after database-to-GeoJSON refactor lands)
- Reconciling the three color legends currently on the site (homepage top video, UC Berkeley Dormitories video, methodology page) to one canonical version
- Deciding the relationship between visualizations and stage freshness (don't ship color-coded views until stage data has a freshness mechanism)
