# Session close — 2026-05-21

## Headline

Polygon import workstream closed. v2's project_geometries went from
179 centroids-only to 184 current geometries (159 apn_parcel + 9
building_footprint + 11 synthetic_polygon + 5 surviving centroids),
plus 9 structures rows for the 4 multi-part projects (Ashby BART,
2200 Bancroft, 2400 Bowditch, 2556 Haste). Schema-fixed:
idx_one_current_geometry now includes COALESCE(structure_id, 0).

Pre-import backup at databases/berkeley_housing_v2_pre_kml_import_2026-05-21.db
(SHA256 97d978b60534ab82629cd18104906fc11a5eb8b1846662c0a383fb243a6bfce6).

4 commits pushed to origin/main today (ff63fb9, e82a18e, c8708fc, 83a6ec5).

## Stage 1 status

The largest single Stage 1 gap (v2 missing polygons that lived in v1
and the canonical KML) is closed. Remaining Stage 1 items, untouched
today:
- Reconcile the three database paths (data/, databases/, modules/'s
  berkeley_housing_map.db default)
- Identify deprecated scripts, move to scripts/archive/
- Document which exporter is canonical (v1's vs v2's, modules/'s
  report_generator never used)

## Accela verification (today's stated goal — not completed)

Inventoried the gap instead. Findings:
- 90 in-scope B-permits in v2 have no source_url
- 0 of those have recoverable capIDs from existing scrape files
- 3 verified master capIDs from prior session captured in
  notes/hand_copied_capids_2026-05-21.md
- URL discovery design sketch updated with master-and-suffix model
  (notes/2026-05-22_url_discovery_design_sketch.md)

The orchestrator built 2026-05-20 (build_scrape_queue.py +
scrape_inspections.py) is unblocked for any permits that already
have URLs, but most in-scope B-permits don't. URL discovery is the
prerequisite workstream.

## What I'd do next session

1. Decide whether to build URL discovery now (~2-3hr Type 2) or
   defer for some smaller Stage 1 cleanup first.
2. If URL discovery: the sketch is ready; the 3 verified triplets
   in hand_copied_capids_2026-05-21.md can serve as POC inputs.
3. If Stage 1 cleanup: inventory the v1 scripts and decide which
   are deprecated vs active (rule 4 task per yesterday's diagnosis).

## Loose ends

- Dharma University: housing project, exists in KML, not yet in v2.
  Needs create-project + import-its-polygon workstream.
- 2740 Shasta Rd (project 86): 2 duplicate-looking KML placemarks
  excluded from today's import. Needs investigation.
- 5 v2 projects with no KML polygon: which 5? Small Type 1 follow-up.
- CC environmental: auto-update was silently failing for weeks (caused
  by /opt/homebrew permissions). Fixed today via `sudo chown -R`.
  v2.0.76 had an interrupt-on-every-input bug that v2.1.147 doesn't.
  Worth re-running `claude doctor` in a week to confirm auto-update
  stays healthy.

## Files written today, by location

databases/:
- berkeley_housing_v2.db (canonical, modified — polygon import)
- berkeley_housing_v2_pre_kml_import_2026-05-21.db (backup)

notes/:
- kml_import_results_2026-05-21.md / .csv
- hand_copied_capids_2026-05-21.md / .csv
- b_permit_url_inventory_2026-05-21.md / .csv

notes/ (updated):
- 2026-05-22_url_discovery_design_sketch.md (master-and-suffix update)
