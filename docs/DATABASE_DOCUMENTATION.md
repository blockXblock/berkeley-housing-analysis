# Berkeley Housing Analysis - Database Documentation

**Generated:** 2026-04-21
**Last Data Update:** 2026-04-15

---

## Overview

This project maintains multiple SQLite databases tracking Berkeley's housing pipeline, from planning applications through construction completion. Data is sourced from the City of Berkeley's Accela permit system, field surveys, and public records.

---

## Primary Databases

### 1. berkeley_housing_analysis.db (Main Analysis Database)

**Location:** `databases/berkeley_housing_analysis.db`
**Size:** 1.0 MB
**Last Modified:** 2026-04-15

The primary database for housing pipeline analysis, containing verified project data with permit timelines.

#### Tables

| Table | Rows | Description |
|-------|------|-------------|
| projects | 174 | Master project list with all fields |
| permit_events | 166 | Processing status events with dates |
| project_permits | 62 | Individual permits linked to projects |
| permit_fees | 12 | Fee payment records |
| project_velocity | view | Days at each pipeline stage |

#### Key Fields in `projects`

- **Identification:** id, address_display, apn, slug
- **Unit Counts:** units, vli_units, li_units, mod_units, above_mod_units
- **Timeline:** filed, complete, entitled, bp_date, co_date
- **Status:** status, pipeline_stage, construction_stage
- **Dimensions:** height_stories, height_feet, latitude, longitude
- **Associations:** developer, architect
- **Flags:** density_bonus, sb35_flag, sb330_flag, ab2011_flag, is_uc_project

#### Data Freshness

- Latest `updated_at`: 2026-04-01
- Latest `co_date`: 2026-01-27 (3030 Telegraph Ave)
- Projects by pipeline_stage:
  - Under Construction: 22
  - Completed: 30
  - Entitled: 32
  - In Review: 85

---

### 2. berkeley.db (Parcel & Business Data)

**Location:** `databases/berkeley.db`
**Size:** 50 MB
**Last Modified:** 2026-02-03

Comprehensive parcel data with business licenses, rent control, and corridor analysis.

#### Tables

| Table | Rows | Description |
|-------|------|-------------|
| parcels | 29,108 | All Berkeley parcels with geometry |
| licenses | 13,339 | Business license registry |
| rent_control | ~24,000 | Rent stabilization units |
| corridor_ownership | varies | Parcel ownership on key corridors |
| corridor_far | varies | Floor area ratio calculations |
| licenses_fts | FTS5 | Full-text search on licenses |
| corridor_master | view | Joined view of all corridor data |

#### Key Fields in `parcels`

- APN, SitusAddre (address)
- UseCode, BuildingAr (sqft), LotSize
- Latitude, Longitude, the_geom
- corridor (assigned corridor name)

---

### 3. berkeley_housing_map.db (Datasette Deployment)

**Location:** `databases/berkeley_housing_map.db` (also in `datasette-deploy/`)
**Size:** 56 KB
**Last Modified:** 2026-03-10

Lightweight database deployed to Datasette for public access.

**Live URL:** https://berkeley-housing.fly.dev

#### Tables

| Table | Rows | Description |
|-------|------|-------------|
| projects | 115 | Filtered project list for map |
| map_view | view | Formatted view with size categories |

---

## Build Scripts

### migrate_to_database.py (Primary)

**Purpose:** Creates and populates `berkeley_housing_analysis.db`

**Data Sources:**
- `data/processed/housing_projects_FINAL.csv` (164 projects)
- `data/processed/project_fees.json`
- Developer/architect associations (hardcoded)

**Actions:**
1. Creates/updates projects table schema
2. Imports projects from FINAL.csv
3. Assigns developer and architect associations
4. Links permit_events by address matching
5. Imports fee data
6. Creates performance indexes

**Usage:**
```bash
python scripts/migrate_to_database.py
```

---

### accela_workflow.py

**Purpose:** Collects permit data from Berkeley's Accela system

**Features:**
- Generates search URLs for all projects
- Parses Processing Status text
- Saves permit events to database

**Usage:**
```bash
python scripts/accela_workflow.py generate           # Generate URLs
python scripts/accela_workflow.py parse FILE         # Parse status text
python scripts/accela_workflow.py save_batch --db PATH --dir DIRECTORY
```

---

### generate_apr.py

**Purpose:** Generates HCD Annual Progress Report tables

**Tables Generated:**
- Table A: Projects with applications complete in reporting year
- Table A2: Projects permitted (entitled, BP, CO) in reporting year
- Table B: Developer/affordability summary

**Usage:**
```bash
python scripts/generate_apr.py --year 2025
```

---

### generate_kml.py

**Purpose:** Creates 3D KML visualization of housing pipeline

**Output:** `docs/berkeley_skyline.kml`

**Features:**
- Extruded polygons showing building heights
- Color-coded by pipeline stage
- Special handling for UC projects (gold)
- Parcel-accurate footprints for key projects

**Usage:**
```bash
python scripts/generate_kml.py
```

---

## Data Sharing

### 1. GitHub Pages (Public Website)

**URL:** https://berkeleybuild.com (or blockxblock.github.io/berkeley-housing-analysis)

**Deployment:**
```bash
git checkout dev
# make changes
git add . && git commit -m "message"
git checkout main && git merge dev
git push origin main
```

**Published Files:**
- `docs/index.html` - Main site
- `docs/explorer.html` - Data explorer
- `docs/berkeley_skyline.kml` - 3D visualization
- `docs/videos/campanile-adeline-shattuck.mp4` - Campanile-Adeline-Shattuck tour video
- `docs/videos/elmwood-bancroft-shattuck.mp4` - Elmwood-Bancroft-Shattuck tour video

---

### 2. Datasette (Interactive Database)

**URL:** https://berkeley-housing.fly.dev

**Deployment:**
```bash
cd datasette-deploy
flyctl deploy
```

**Features:**
- SQL query interface
- Interactive map with clustering
- CSV/JSON export
- Canned queries (stalled projects, timeline events, fees)

---

## Data Verification

### Field Survey (April 3, 2026)

Physical inspection verified construction status for key projects:
- 2317 CHANNING Way: Stalled (demolished_vacant)
- 2538 DURANT Ave: Under Construction (topped_out)
- 2442 HASTE St: Under Construction (demolition)
- 2587 TELEGRAPH Ave: Under Construction (topped_out)
- 2480 BANCROFT Way: Completed
- 3030 TELEGRAPH Ave: Finishing

### APR Cross-Reference (April 2026)

Comparison with City's 2025 APR identified discrepancies:
- 2029 UNIVERSITY Ave: City double-counted (+160 units error)
- 2425 DURANT Ave: City overstated (+52 units error)
- 2100 MILVIA St: City reported 0 units (should be 201)
- 2 CO projects missing from city report (107 units)

See: `data/apr/2025/city_apr_error_audit.md`

---

## File Locations

```
berkeley-data/
├── databases/
│   ├── berkeley_housing_analysis.db    # Main analysis (174 projects)
│   ├── berkeley.db                     # Parcels + licenses (29K parcels)
│   └── berkeley_housing_map.db         # Datasette deployment
├── data/
│   ├── processed/
│   │   ├── housing_projects_FINAL.csv  # Source data
│   │   └── project_fees.json           # Fee records
│   ├── apr/2025/
│   │   ├── table_a_comparison.md       # Our vs City Table A
│   │   └── city_apr_error_audit.md     # Error analysis
│   └── raw/
│       └── city_apr_2025_table_a2.csv  # City APR extract
├── scripts/
│   ├── migrate_to_database.py          # Main DB builder
│   ├── accela_workflow.py              # Accela data collection
│   ├── generate_apr.py                 # APR table generation
│   └── generate_kml.py                 # 3D KML generation
└── docs/
    ├── index.html                      # Public website
    ├── explorer.html                   # Data explorer
    └── berkeley_skyline.kml            # 3D visualization
```

---

## Maintenance

### Adding New Projects

1. Add to `data/processed/housing_projects_FINAL.csv`
2. Run `python scripts/migrate_to_database.py`
3. Run `python scripts/generate_kml.py`
4. Deploy updates

### Updating Permit Status

1. Use `accela_workflow.py generate` to create URLs
2. Copy Processing Status from Accela
3. Use `accela_workflow.py parse` to extract events
4. Use `accela_workflow.py save` to update database

### Refreshing Datasette

1. Copy updated `berkeley_housing_map.db` to `datasette-deploy/`
2. `cd datasette-deploy && flyctl deploy`

---

*Documentation generated 2026-04-21*
