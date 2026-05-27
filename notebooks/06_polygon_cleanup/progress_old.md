# Parcel Polygon Import: Progress Report

**Date:** 2026-04-25
**Status:** Paused — awaiting v2 schema migration

---

## Summary

We completed reconnaissance and validation for importing parcel polygons from Alameda County assessor data into the housing pipeline database. The matching logic is validated and ready, but the target table (`project_geometries`) does not exist in the current v1 database schema.

---

## Data Sources Identified

| File | Size | Contents | Coverage |
|------|------|----------|----------|
| `data/reference/berkeley_parcels.csv` | 14 MB | 29,024 parcels with MULTIPOLYGON WKT geometries | Full Berkeley |
| `data/reference/alameda_lookup_complete.csv` | 59 MB | 563,193 addresses with APNs | Full Alameda County |
| `data/reference/corridor_parcels.geojson` | 157 KB | 332 parcels with owner names | Corridor subset only |

### Key Discovery: Dual APN Columns

`berkeley_parcels.csv` contains two APN representations:

| Column | Format | Example |
|--------|--------|---------|
| `APN` | Hyphenated, variable segments | `55-1837-7` or `53-1591-8-2` |
| `PARCELID` | 12-digit with space | `055 183700700` |

The `PARCELID` column matches the format used in the `projects` table, enabling direct joins.

---

## APN Coverage in Projects Table

| Metric | Count |
|--------|-------|
| Total projects | 174 |
| Projects with APN | 154 (88.5%) |
| Projects without APN | 20 (11.5%) |

### Projects Without APN (20)

| Category | Count | Notes |
|----------|-------|-------|
| UC projects | 4 | Intentionally APN-null (UC land not in assessor system) |
| Missing lat/lon | 7 | Cannot verify matches |
| Address not in lookup | 6 | Need manual research |
| Other | 3 | Various issues |

UC projects without APN:
- 2400 BOWDITCH St (750 units)
- 2556 HASTE St (556 units) — People's Park
- 2200 BANCROFT Way (550 units)
- 1950 OXFORD St (300 units)

---

## Parcel Matching Results

### Match Rate

| Method | Matched | Rate |
|--------|---------|------|
| PARCELID (12-digit) | 148 | 96.1% |
| APN column (hyphenated) | +2 | — |
| **Total** | **150** | **97.4%** |

### Unmatched Projects (4)

| APN | Address | Issue |
|-----|---------|-------|
| `60-2447-36` | 1850 BERRYMAN St | Not in parcel file |
| `057 210000702` | 1914 FIFTH St | Not in parcel file |
| `055 183600800` | 2614 TELEGRAPH Ave | Not in parcel file |
| `056 196301503` | 2221 FIFTH St | Not in parcel file |

---

## Spot-Check Validation

Three privately-owned projects were verified:

| Project | Distance | Area | Vertices | Status |
|---------|----------|------|----------|--------|
| 1740 SAN PABLO Ave | 10.7 m | 1,311 sqm | 8 | ✓ Pass |
| 1367 UNIVERSITY Ave | 0.1 m | 489 sqm | 4 | ✓ Pass |
| 2449 DWIGHT Way | 5.4 m | 1,006 sqm | 5 | ✓ Pass |

**Validation criteria:**
- Distance between project lat/lon and parcel centroid < 30m
- Parcel area in plausible range (200–5,000 sqm for typical lots)

All checks passed.

---

## APN Enrichment (Deferred)

A dry-run identified 2 projects that could be enriched with APNs via address matching:

| Address | Looked-up APN | Distance | Status |
|---------|---------------|----------|--------|
| 1614 Sixth St | `057 211700401` | 16.5 m | Ready to write |
| 2128 Oxford St | `057 203100101` | 0.0 m | Ready to write |

**Decision:** Deferred to workflow notebook. The 2-project enrichment will be handled separately.

---

## Database State

### Current Schema (v1)

The `project_geometries` table **does not exist**. Current tables:

```
apr_rhna_progress    data_collection_log  project_map
apr_streamlining     permit_events        project_permits
apr_unit_categories  permit_fees          projects
building_permits     project_documents    sfyimby_projects
```

### Backup Created

```
berkeley_housing_analysis_pre_parcel_import_2026-04-25.db
Size: 1,048,576 bytes
```

---

## Proposed Schema for project_geometries

```sql
CREATE TABLE project_geometries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    geometry_type TEXT NOT NULL,  -- 'apn_parcel', 'centroid_point', etc.
    geojson TEXT NOT NULL,
    height_meters REAL,
    base_elevation_meters REAL,
    source_document_id INTEGER,
    version_label TEXT,
    edited_by TEXT,
    edit_notes TEXT,
    is_current INTEGER NOT NULL DEFAULT 1,
    superseded_by INTEGER REFERENCES project_geometries(id),
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_project_geometries_project_id ON project_geometries(project_id);
CREATE INDEX idx_project_geometries_current ON project_geometries(project_id, is_current);
```

---

## Import Plan (When Ready)

### Step 1: Create Table
Execute the schema above.

### Step 2: Import Parcel Polygons
For each of the 150 matched projects:

1. Read WKT MULTIPOLYGON from `berkeley_parcels.csv`
2. Convert to GeoJSON using shapely or manual parsing
3. Insert into `project_geometries`:
   - `geometry_type = 'apn_parcel'`
   - `height_meters` from projects table
   - `version_label = 'parcel_import_2026-04-25'`
   - `edited_by = 'parcel_import_script'`
   - `is_current = 1`

### Step 3: Update generate_kml.py
Modify to read from `project_geometries` table when `geometry_type = 'apn_parcel'` exists, falling back to synthetic polygons for unmatched projects.

---

## Files Referenced

| File | Purpose |
|------|---------|
| `scripts/generate_kml.py` | Current KML generator (uses synthetic polygons) |
| `data/reference/berkeley_parcels.csv` | Parcel polygons with APNs |
| `data/reference/alameda_lookup_complete.csv` | Address-to-APN lookup |
| `databases/berkeley_housing_analysis.db` | Production database (v1) |
| `databases/berkeley_housing_analysis_pre_parcel_import_2026-04-25.db` | Pre-import backup |

---

## Next Steps

1. **Decide on schema approach:**
   - Option A: Create `project_geometries` table in v1 database now
   - Option B: Wait for full v2 migration

2. **After table exists:**
   - Run polygon import script (150 projects)
   - Update `generate_kml.py` to use real polygons

3. **Deferred tasks:**
   - APN enrichment for 2 ready projects
   - Manual research for 6 address-not-found projects
   - Coordinate lookup for 7 projects missing lat/lon

---

*Last updated: 2026-04-25*
