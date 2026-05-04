# Snapshot: 2026-05-03_post_handtraced

Created: 2026-05-03 evening

## Summary

Post hand-traced building footprints import. KML v9 generated.

## Changes from previous snapshot (2026-05-03_post_v8_kml)

- **4 new building_footprint geometries** imported from Google Earth Pro hand-traced KML files:
  - Project 170: 1950 Oxford St (UC student housing)
  - Project 119: 1974 Shattuck Ave (tower-only footprint)
  - Project 165: 2200 Bancroft Way (UC project)
  - Project 180: 2065 Kittredge St (entitled-but-not-built)

- **project_geometries table now has 5 building_footprint rows** (was 1)
  - 4 new rows with is_current=1
  - 4 old geometry rows marked is_current=0

- **KML v9 geometry breakdown:**
  - 159 apn_parcel (-2 from v8)
  - 12 synthetic (-2 from v8)
  - 5 building_footprint (+4 from v8)
  - 1 manual_polygon (unchanged)

## Files

- `projects.csv` — 179 projects
- `project_geometries.csv` — all geometry rows (current and superseded)
- `project_documents.csv` — document references
- `data_collection_log.csv` — data lineage
- `vocabulary_geometry_types.csv` — geometry type codes
- `schema.sql` — full database schema

## Hand-traced source files

Raw KML files archived at:
`data/raw/google_earth_audit/2026-05-03_handtraced/`

4 files:
- tour-edit-1950-oxford-2026-05-03.kml
- tour-edit-1974-SHATTUCK-2026-05-03 Ave.kml
- tour-edit-2065-Kittredge-2026-05-03.kml
- tour-edit-2200-bancroft-2026-05-03.kml
