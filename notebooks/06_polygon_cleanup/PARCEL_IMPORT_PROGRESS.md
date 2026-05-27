# Parcel Polygon Import: Progress

**Date:** 2026-04-25

---

## 1. TL;DR

165 of 174 projects now have geometry rows in `project_geometries`:
- **151 apn_parcel** — real parcel polygons from Alameda County assessor data
- **2 manual_polygon** — hardcoded polygons for People's Park (2556 HASTE) and 2400 BOWDITCH
- **12 synthetic_footprint** — rotated squares for projects with lat/lon but no parcel match

The remaining 9 projects have no lat/lon coordinates and are already excluded from KML generation. Next step: update `generate_kml.py` to read from `project_geometries` instead of synthesizing squares.

---

## 2. Database State

**Canonical database:** `berkeley_housing_analysis.db` (v1)
**Obsolete database:** `berkeley_housing_v2.db` — do not modify or read from; contains stale 165-row centroid data from an earlier design preview.

### project_geometries

- Exists in v1 with v2's schema design
- Versioning: `is_current`, `superseded_by` columns
- Partial unique index: `idx_one_current_geometry` ensures at most one `is_current=1` row per (project_id, geometry_type_id)
- **165 rows** with `is_current=1`:
  - 151 `apn_parcel` (geometry_type_id=1)
  - 2 `manual_polygon` (geometry_type_id=8)
  - 12 `synthetic_footprint` (geometry_type_id=9)

### vocabulary_geometry_types

| ID | Code | Label |
|----|------|-------|
| 1 | apn_parcel | APN Parcel |
| 2 | apn_parcel_merged | APN Parcel (Merged) |
| 3 | apn_parcel_subdivided | APN Parcel (Subdivided) |
| 4 | building_footprint | Building Footprint |
| 5 | building_3d | Building 3D Extrusion |
| 6 | site_plan | Site Plan |
| 7 | centroid_point | Centroid Point |
| 8 | manual_polygon | Manual Polygon |
| 9 | synthetic_footprint | Synthetic Footprint |

### Coverage

- 165 of 174 projects have a current geometry row
- 9 projects have no geometry row (all lack lat/lon coordinates, already excluded from KML)

---

## 3. What Was Imported and How

**Source:** `data/reference/berkeley_parcels.csv`
- 29,024 parcels with MULTIPOLYGON WKT in `the_geom` column
- Two APN columns: `PARCELID` (12-digit), `APN` (hyphenated)

**Match key:** `PARCELID` matched against `projects.apn`

**Match results:**
- 148 projects matched via 12-digit PARCELID
- 2 projects matched via hyphenated APN column (already in hyphenated format in projects table)
- 1 project (0 LE ROY Ave) recovered via Accela investigation → APN `058 224402501`
- 4 valid APNs not found in parcel file

**Unmatched APNs (4):**

| APN | Address |
|-----|---------|
| `60-2447-36` | 1850 BERRYMAN St |
| `057 210000702` | 1914 FIFTH St |
| `055 183600800` | 2614 TELEGRAPH Ave |
| `056 196301503` | 2221 FIFTH St |

**Import metadata:**
- `version_label`: `parcel_import_2026-04-25`
- `edited_by`: `parcel_import_script`
- GeoJSON converted via `shapely.geometry.mapping()`

---

## 4. The 9 Projects Without Geometry

All 9 projects without geometry rows lack lat/lon coordinates. They are already excluded from KML generation.

| Address | Issue |
|---------|-------|
| 1698 UNIVERSITY Ave | No lat/lon |
| 1773 OXFORD St | No lat/lon |
| 2000 DWIGHT Way | No lat/lon |
| 2435 SAN PABLO Ave | No lat/lon |
| 2440 SHATTUCK Ave | No lat/lon |
| 2650 TELEGRAPH Ave | No lat/lon |
| 3000 SAN PABLO Ave | No lat/lon |
| 3020 SAN PABLO Ave | No lat/lon |
| 3031 ADELINE St | No lat/lon |

**Resolution:** Backfill lat/lon from geocoding or Accela lookup, then add geometry rows.

### Previously Resolved

- **0 LE ROY Ave:** Recovered APN `058 224402501` via Accela → now has apn_parcel geometry
- **UC Projects (4):** Now have manual_polygon (2556 HASTE, 2400 BOWDITCH) or synthetic_footprint (2200 BANCROFT, 1950 OXFORD)
- **Unmatched APNs (4):** 1850 BERRYMAN, 1914 FIFTH, 2614 TELEGRAPH, 2221 FIFTH → now have synthetic_footprint
- **Other SKIP_NO_MATCH (5):** 1048 Keith, 2820 San Pablo, 2833 Seventh, 811 Cedar → now have synthetic_footprint

---

## 5. Key Design Decisions

1. **Primary parcel source:** `berkeley_parcels.csv` (has polygons). Use `alameda_lookup_complete.csv` only as address→APN bridge for enrichment.

2. **UC projects stay APN-null.** UC land isn't in the assessor system. Don't attempt enrichment; use synthetic polygons.

3. **50m centroid-distance threshold** for verifying APN enrichment matches. If looked-up parcel centroid is >50m from project lat/lon, reject the match as likely wrong.

4. **Adopt v2 schema design in v1.** Versioning fields (`is_current`, `superseded_by`), partial unique index, full vocabulary.

5. **Preserve v1's geometry types.** Added `manual_polygon` (id=8) and `synthetic_footprint` (id=9) to v2's 7-entry vocabulary.

---

## 6. Backups

| File | State |
|------|-------|
| `berkeley_housing_analysis_pre_parcel_import_2026-04-25.db` | Before any project_geometries inserts |
| `berkeley_housing_analysis_pre_schema_alignment_2026-04-25.db` | After parcel import, before vocabulary migration |

Backups are file-level snapshots in `databases/`, not git-tracked.

---

## 7. Open Work (Priority Order)

1. ~~**Update `scripts/generate_kml.py`**~~ ✓ Done — reads from `project_geometries`, uses stored polygon coordinates

2. ~~**Populate synthetic_footprint rows**~~ ✓ Done — 14 rows inserted (2 manual_polygon, 12 synthetic_footprint)

3. ~~**Investigate 0 LE ROY Ave**~~ ✓ Done — APN `058 224402501` recovered via Accela

4. **Backfill lat/lon** for the 9 projects without coordinates (blocks geometry row creation).

5. **Build `08_post_accela_pipeline.ipynb`** workflow notebook for ongoing data maintenance (longer-term).

---

## 8. Conventions Worth Remembering

- **PARCELID format:** 12-digit space-separated, e.g., `057 211700401`
- **projects.apn format:** Same as PARCELID
- **Hyphenated APN format** (in `APN` column of parcel CSV): `16-1428-2-2` style. Equivalent to PARCELID with leading zeros stripped from each segment.
- **GeoJSON storage:** Stored as TEXT in `project_geometries.geojson`. Parse with `shapely.geometry.shape()` on read.
- **KML coordinate order:** lon,lat,alt (opposite of lat,lon convention in most tools).

---

## 9. Questions Still Open

1. ~~**People's Park polygon:**~~ Resolved — using `manual_polygon` with hardcoded coordinates from generate_kml.py

2. **Assemblage projects:** How to handle the 3 true assemblages where multiple project entries share one APN?
   - 1740 SAN PABLO Ave / 1701 SAN PABLO Ave
   - 2205 BLAKE St / 2201 BLAKE St

3. **Likely duplicate entries:** Should these be deduplicated in the projects table?
   - 2455 TELEGRAPH Ave (appears twice, same APN)
   - 2740 SHASTA Rd (appears twice, same APN)
   - 2099 M L KING JR Way / 2099 MLK Jr Way (same APN, spelling variant)
   - 2138 KITTREDGE St (appears twice, same APN)

4. **Schema constraints:** Should `project_geometries` add `ON DELETE CASCADE` and `CHECK (is_current IN (0,1))`? Deferred from migration because SQLite requires table rebuild.

---

*Last updated: 2026-04-25 (synthetic footprint insert complete)*
