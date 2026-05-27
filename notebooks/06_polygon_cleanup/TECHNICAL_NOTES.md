# Parcel Polygon Import: Technical Notes

**Date:** 2026-04-25
**Companion to:** PROGRESS.md

This document captures implementation details that should survive the chat session.

---

## 1. berkeley_parcels.csv Structure

**Path:** `data/reference/berkeley_parcels.csv`
**Rows:** 29,024 (29,025 including header)
**Unique APNs:** 29,003

### Columns

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `SitusStree` | TEXT | Street number | `3208` |
| `the_geom` | TEXT | WKT MULTIPOLYGON | `MULTIPOLYGON (((-122.266... 37.852...)))` |
| `DATE_UPDAT` | TEXT | Last update date | `2004-05-10` |
| `APN` | TEXT | Hyphenated APN (variable segments) | `55-1837-7` or `53-1591-8-2` |
| `SitusStr_1` | TEXT | Street name | `SHATTUCK AVE` |
| `SitusUnit` | TEXT | Unit number | (often empty) |
| `SitusCity` | TEXT | City | `BERKELEY` |
| `SitusZip` | TEXT | ZIP code | `94704` |
| `UseCode` | TEXT | Land use code | `1100`, `3200`, etc. |
| `BuildingAr` | TEXT | Building area (formatted) | `2,395` |
| `LotSize` | TEXT | Lot size (formatted) | `1,995` |
| `SitusAddre` | TEXT | Full situs address | `3208 SHATTUCK AVE BERKELEY 94705` |
| `Longitude` | TEXT | Centroid longitude | `-122.26636568` |
| `Latitude` | TEXT | Centroid latitude | `37.85201812` |
| `PARCELID` | TEXT | **12-digit APN with space** | `055 183700700` |
| `EXT_MIN_X` | TEXT | Bounding box min X | `564,525.0572` |
| `EXT_MIN_Y` | TEXT | Bounding box min Y | `4,189,644.3367` |
| `EXT_MAX_X` | TEXT | Bounding box max X | `564,556.3459` |
| `EXT_MAX_Y` | TEXT | Bounding box max Y | `4,189,655.4693` |

### Critical Finding: Dual APN Columns

The `PARCELID` column uses the same format as the `projects.apn` column in the database:
- Projects table: `058 214901904`
- PARCELID column: `058 214901904`

The `APN` column uses hyphenated format with **variable segment counts**:
- 3 segments: `53-1604-6`
- 4 segments: `53-1591-8-2`

**Use `PARCELID` for matching, not `APN`.**

---

## 2. APN Format Normalization

### Projects Table Format
```
XXX YYYYYYYY (12 digits with space after first 3)
Example: 058 214901904
```

### Normalization Function (Python)

```python
import re

def normalize_12digit(apn):
    """
    Normalize project APN to 12-digit string for matching.
    Strips all whitespace, validates length and digit-only.
    """
    if not apn:
        return None
    raw = re.sub(r'\s+', '', apn)
    if len(raw) == 12 and raw.isdigit():
        return raw
    return None
```

### Matching Logic

```python
# Primary match: PARCELID (12-digit)
pid_norm = normalize_12digit(project_apn)
if pid_norm and pid_norm in parcels_by_pid:
    parcel = parcels_by_pid[pid_norm]

# Fallback: direct APN match (for hyphenated APNs in projects table)
elif project_apn in parcels_by_apn:
    parcel = parcels_by_apn[project_apn]
```

### Hyphenated APN Parsing (Alternative)

For APNs already in hyphenated format (3 projects in database):

```python
def parse_hyphenated_apn(apn):
    """
    Parse hyphenated APN like '55-1871-20' to 12-digit format.
    Format: book-page-parcel or book-page-parcel-subparcel
    """
    parts = apn.split('-')
    if len(parts) == 3:
        book, page, parcel = parts
        subparcel = '0'
    elif len(parts) == 4:
        book, page, parcel, subparcel = parts
    else:
        return None

    # Pad to standard widths: 3-4-3-2 = 12 digits
    return f"{int(book):03d}{int(page):04d}{int(parcel):03d}{int(subparcel):02d}"
```

---

## 3. UC Project Handling

### Rule
UC-owned land is **not in the county assessor parcel system**. These projects should:
- Remain `apn = NULL` in the database
- Use synthetic polygon fallback in KML generation
- Be excluded from APN enrichment attempts

### Detection

```python
# In projects table
WHERE is_uc_project = 1
```

### UC Projects (4 total)

| Address | Units | APN Status |
|---------|-------|------------|
| 2400 BOWDITCH St | 750 | NULL (correct) |
| 2556 HASTE St | 556 | NULL (correct) |
| 2200 BANCROFT Way | 550 | NULL (correct) |
| 1950 OXFORD St | 300 | NULL (correct) |

---

## 4. APN Enrichment SKIP Categories

When attempting to enrich the 20 projects without APN:

| Category | Count | Meaning | Action |
|----------|-------|---------|--------|
| `SKIP_UC` | 4 | `is_uc_project = 1` | Never enrich — UC land not in assessor |
| `SKIP_NO_MATCH` | 6 | Address not found in alameda_lookup | Need manual research |
| `SKIP_NO_COORDS` | 7 | Project has no lat/lon | Cannot verify match distance |
| `SKIP_NO_PARCEL` | 1 | APN found but no polygon in parcel file | Edge case |
| `SKIP_DISTANCE` | 0 | Match found but centroid > 50m from project | Bad match |
| `WRITE` | 2 | Verified match, ready to write | Proceed |

### SKIP_NO_MATCH Projects (need manual research)

- 0 LE ROY Ave
- 1048 Keith St
- 2435 SAN PABLO Ave
- 2820 San Pablo
- 2833 Seventh St
- 811 Cedar

### SKIP_NO_COORDS Projects (need coordinate lookup)

- 1698 UNIVERSITY Ave
- 1773 OXFORD St
- 2000 DWIGHT Way
- 2440 SHATTUCK Ave
- 2650 TELEGRAPH Ave
- 3020 SAN PABLO Ave
- 3031 ADELINE St

### WRITE Projects (ready for enrichment)

| Address | APN | Distance |
|---------|-----|----------|
| 1614 Sixth St | `057 211700401` | 16.5 m |
| 2128 Oxford St | `057 203100101` | 0.0 m |

---

## 5. Spot-Check Validation Protocol

### Criteria

1. **Distance check:** Project lat/lon vs. parcel centroid ≤ 50m (used 30m for spot-check)
2. **Area plausibility:** 200–5,000 sqm for typical residential lots
3. **Address sanity:** Parcel situs address should match project address

### Centroid Calculation

```python
def compute_centroid(coords):
    """Compute centroid of polygon coordinates."""
    if not coords:
        return None, None
    # Remove closing vertex if duplicates first
    if len(coords) > 1 and coords[0] == coords[-1]:
        coords = coords[:-1]
    lon = sum(c[0] for c in coords) / len(coords)
    lat = sum(c[1] for c in coords) / len(coords)
    return lon, lat
```

### Distance Calculation (Haversine)

```python
import math

def haversine_m(lat1, lon1, lat2, lon2):
    """Compute distance in meters between two points."""
    R = 6371000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))
```

### Validated Projects

| Project | APN | Parcel Address | Distance | Area |
|---------|-----|----------------|----------|------|
| 1740 SAN PABLO Ave | `058 212701403` | 1740 SAN PABLO AVE | 10.7 m | 1,311 sqm |
| 1367 UNIVERSITY Ave | `057 207300500` | 1367 UNIVERSITY AVE | 0.1 m | 489 sqm |
| 2449 DWIGHT Way | `055 188100400` | 2482 TELEGRAPH AVE* | 5.4 m | 1,006 sqm |

*Corner lot addressed to Telegraph side

---

## 6. project_geometries Schema Design

### Rationale

- **geometry_type as TEXT:** v1 database lacks vocabulary tables; use string literals
- **is_current + superseded_by:** Track geometry history without deleting old versions
- **height_meters:** Pre-computed for KML extrusion
- **version_label:** Tag imports for auditability

### Full Schema

```sql
CREATE TABLE project_geometries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    geometry_type TEXT NOT NULL,  -- 'apn_parcel', 'centroid_point', 'manual_polygon'
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

### geometry_type Values

| Value | Meaning |
|-------|---------|
| `apn_parcel` | Polygon from assessor parcel data |
| `centroid_point` | Point from geocoded address |
| `manual_polygon` | Hand-drawn or manually adjusted polygon |
| `synthetic_footprint` | Generated square/rectangle from centroid |

---

## 7. WKT to GeoJSON Conversion

### Using Shapely (preferred)

```python
from shapely import wkt
from shapely.geometry import mapping
import json

def wkt_to_geojson(wkt_str):
    geom = wkt.loads(wkt_str)
    return json.dumps(mapping(geom))
```

### Manual Fallback

```python
import re

def wkt_to_geojson_manual(wkt_str):
    """Manual WKT MULTIPOLYGON to GeoJSON conversion."""
    match = re.search(r'MULTIPOLYGON\s*\(\(\((.*)\)\)\)', wkt_str, re.DOTALL)
    if not match:
        return None

    coord_str = match.group(1)
    coords = []
    for pair in coord_str.split(','):
        parts = pair.strip().split()
        if len(parts) >= 2:
            coords.append([float(parts[0]), float(parts[1])])

    return {
        "type": "Polygon",
        "coordinates": [coords]
    }
```

---

## 8. Match Statistics Summary

| Metric | Value |
|--------|-------|
| Total projects | 174 |
| Projects with APN | 154 (88.5%) |
| APNs matched to parcels | 150 (97.4% of those with APN) |
| Unmatched APNs | 4 |
| UC projects (intentionally no APN) | 4 |
| Projects needing enrichment | 16 (excluding UC) |
| Projects ready for APN enrichment | 2 |

---

## 9. File Inventory

| File | Purpose |
|------|---------|
| `data/reference/berkeley_parcels.csv` | Parcel polygons (29K rows, 14 MB) |
| `data/reference/alameda_lookup_complete.csv` | Address→APN lookup (563K rows, 59 MB) |
| `data/reference/corridor_parcels.geojson` | Subset with owner names (332 parcels) |
| `scripts/generate_kml.py` | Current KML generator |
| `databases/berkeley_housing_analysis.db` | Production v1 database |
| `databases/berkeley_housing_analysis_pre_parcel_import_2026-04-25.db` | Backup |

---

*Last updated: 2026-04-25*
