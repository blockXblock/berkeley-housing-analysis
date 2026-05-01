# Berkeley Civic Data Infrastructure — Progress Document

**Last updated:** 2026-04-30
**Canonical location:** `~/berkeley-data/PROGRESS.md`
**Purpose:** Living document that survives across AI sessions and informs anyone returning to this work
- JG 7pm
---

## 1. TL;DR

This project tracks Berkeley's housing development pipeline and civic data infrastructure. The system currently spans 12 SQLite databases (~72MB total), with active work concentrated in `berkeley_housing_analysis.db` (174 housing projects) while `berkeley.db` (50MB) serves as the authoritative source for parcels, addresses, and zoning. An architectural decision has been made to consolidate toward a single master database (`berkeley.db`) over time. The immediate priority is APN format normalization to enable cross-database joins, followed by promoting hand-edited polygons from Google Earth and resolving remaining duplicate/missing address issues. The KML visualization pipeline is functional and generates `berkeley_skyline.kml` from the `project_geometries` table.

---

## 2. Architecture Decisions (Canonical)

These decisions are settled unless explicitly revisited:

| Decision                                                                                                            | Rationale                                                                                                                             |
| ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| **Master database:** `berkeley.db` will be the single source of truth for all Berkeley civic data                   | Already contains 65K addresses, 29K parcels, zoning districts. Foundational civic data that rarely changes.                           |
| **Working database during transition:** `berkeley_housing_analysis.db` continues as active housing pipeline tracker | 12+ scripts reference it; all current tooling targets it. Will be consolidated into `berkeley.db` when ready.                         |
| **Obsolete:** `berkeley_housing_v2.db` and others listed below                                                      | Migration never completed; empty tables; no scripts use them. To be archived then deleted. Was a level 3 normalization with 18 tables |
| **APN normalization required** for cross-DB joins                                                                   | Format mismatch is critical blocker. Canonical form TBD (likely 12-digit no separators).                                              |
| **Polygons stored as GeoJSON** in TEXT columns                                                                      | Not WKT, not SpatiaLite extension. Parsed by `shapely.shape()` on read.                                                               |
| **Per-field provenance** via `project_status_history` + `manual_overrides` pattern                                  | Chosen over fully attribute-level facts table. **Decision made; not yet implemented.**                                                |
| **Reference data versioning** via `is_current` / `superseded_by` pattern                                            | Applies to parcels, addresses, and operational data like project status.                                                              |
**Authoritative parcel data source:** Alameda County publishes parcel polygons at data.acgov.org. The City of Berkeley's parcel layer is a clipped copy of the County data, not an independent source. We use the County data directly. Polygons are approximate (±~1m, not legal surveys). When project visualization requires more accurate footprints than the parcel polygon provides (e.g., building footprint within a larger lot), we use `manual_polygon` rows in `project_geometries` as explicit overrides with provenance.

### Why Not berkeley_housing_v2.db?

Despite its cleaner normalized 3NF design with 18 vocabulary tables, `berkeley_housing_v2.db` was abandoned because:
- Migration never completed (people, assets, external_links tables are empty)
- No scripts use it (only the migration script references it)
- Adopting it would require rebuilding all tooling

The pragmatic choice is to improve `berkeley_housing_analysis.db` incrementally, then merge into `berkeley.db`.

---

## 3. Database Inventory (Current)

Full analysis: see `docs/database_architecture_review_2026-04-30.md`

### Active Databases (2)

| Database | Size | Last Modified | Role |
|----------|------|---------------|------|
| `databases/berkeley.db` | 50MB | Mar 19, 2026 | Master parcel/address/zoning store (29K parcels, 65K addresses, 13K licenses) |
| `databases/berkeley_housing_analysis.db` | 1.1MB | Apr 25, 2026 | Active housing pipeline (174 projects, 2,306 permit events, 1,423 documents) |

### Staging/Reference Databases (3)

| Database | Size | Last Modified | Role | Fate |
|----------|------|---------------|------|------|
| `databases/accela_reports.db` | 288KB | Mar 20, 2026 | Scraped Accela data staging | Keep as staging area |
| `databases/berkeley_housing_apr.db` | 84KB | Feb 22, 2026 | Frozen APR snapshot | Keep frozen (regulatory record) |
| `databases/berkeley_address_centric.db` | 14MB | Feb 27, 2026 | Materialized view for mapping | Investigate `news_coverage` (2,024 rows) before archiving |

### Dormant Databases (2)

| Database | Size | Last Modified | Role | Fate |
|----------|------|---------------|------|------|
| `databases/berkeley_energy_use.db` | 176KB | Jan 6, 2026 | BESO energy disclosure (520 buildings) | Merge into `berkeley.db` when utility domain expands |
| `databases/berkeley_housing_v2.db` | 1.4MB | Apr 22, 2026 | Abandoned normalized schema | Archive → delete after 90 days |

### Obsolete Databases (3) — Safe to Delete

| Database | Size | Last Modified | Why Obsolete |
|----------|------|---------------|--------------|
| `databases/berkeley_data.db` | 4.1MB | Nov 15, 2025 | Licenses duplicated in `berkeley.db` |
| `databases/berkeley_housing_map.db` | 56KB | Dec 22, 2025 | Superseded by `project_map` in analysis.db |
| `databases/housing_projects.db` | 60KB | Dec 14, 2025 | Original prototype; fully superseded |

### Backup Databases (2)

| Database | Size | Created | Purpose |
|----------|------|---------|---------|
| `databases/berkeley_housing_analysis_pre_parcel_import_2026-04-25.db` | 1.0MB | Apr 25 | Before 150 parcel polygons imported |
| `databases/berkeley_housing_analysis_pre_schema_alignment_2026-04-25.db` | 1.1MB | Apr 25 | Before schema alignment changes |

---

## 3a. Key Terms

| Term | Definition |
|------|------------|
| **Canonical KML** | The single authoritative KML file loaded into Earth Pro; regenerated from DB, not hand-edited |
| **My Places** | Google Earth Pro's local storage for user-created/edited placemarks; NOT version-controlled |
| **manual_polygon** | Hand-drawn polygon from Earth Pro, imported to DB and given authority over APN-derived shapes |
| **synthetic_footprint** | Auto-generated 40m square at project centroid; fallback when no parcel polygon available |
| **apn_parcel** | Polygon derived from county assessor parcel data via APN match |

---

## 4. Current Housing Pipeline Data State

**Source:** `berkeley_housing_analysis.db` as of 2026-04-25

### Project Counts

| Metric | Count |
|--------|-------|
| Total projects | 174 |
| With `apn_parcel` polygons | 149 |
| With `synthetic_footprint` | 12 |
| With `manual_polygon` | 2 |
| With no geometry (missing lat/lon) | 11 |
| Silently excluded from KML | 11 |

### Geometry Source Breakdown

```
apn_parcel:         149 projects (86%) — polygons from berkeley_parcels.csv via APN match
synthetic_footprint: 12 projects (7%)  — 40m square at lat/lon centroid
manual_polygon:       2 projects (1%)  — hand-drawn in Earth Pro, imported to DB
no_geometry:         11 projects (6%)  — no lat/lon, cannot generate any polygon
```

### Duplicate Address Status

| Address | Status | Resolution |
|---------|--------|------------|
| 2115 KITTREDGE St | ✅ Resolved | Duplicate rows merged |
| 2712 TELEGRAPH Ave | ✅ Resolved | Duplicate rows merged |
| 2740 SHASTA Rd | ⚠️ Pending | Two project rows exist; need to determine which is canonical and archive the other |

### Address Recovery Log

| Address | Issue | Resolution | Date |
|---------|-------|------------|------|
| 0 LE ROY Ave | SKIP_NO_MATCH (no APN) | Recovered APN `058 224402501` via Accela investigation | 2026-04-25 |

### Checkpoint Backups

Before major operations on 2026-04-25:
- `berkeley_housing_analysis_pre_parcel_import_2026-04-25.db` — before polygon import
- `berkeley_housing_analysis_pre_schema_alignment_2026-04-25.db` — before schema changes

---

## 5. KML and Visualization State

### Current Files

| File | Purpose | Status |
|------|---------|--------|
| `docs/berkeley_skyline.kml` | Canonical KML for Earth Pro | ✅ Active, generated from `project_geometries` |
| `scripts/generate_kml.py` | KML generator script | Rewritten 2026-04-25 to read from `project_geometries` table |
| `docs/kml_versions/` | Archive of 14 prior KML files | Historical reference only |

### Generator Details

```bash
# Regenerate KML from current project_geometries
python scripts/generate_kml.py
# Output: docs/berkeley_skyline.kml
```

The script:
- Reads from `project_geometries` table in `berkeley_housing_analysis.db`
- Outputs polygons with status-based styling (color by pipeline stage)
- Silently excludes 9 projects without coordinates
- Uses KML coordinate order: `lon,lat,alt` (opposite of GeoJSON)

### Google Earth Pro State

| Item | Status | Action Needed |
|------|--------|---------------|
| 5 hand-edited polygons in My Places | Not yet in DB | Promote to `manual_polygon` rows (deferred) |
| Duplicate stacked polygons | Accumulate over time | Periodic cleanup of My Places required |
| Network link to `berkeley_skyline.kml` | May be stale | Refresh after KML regeneration |

---

## 6. Open Work (Priority Order)

### High Priority

1. **Promote 5 hand-edited My Places polygons** to `manual_polygon` rows in `project_geometries`
   - These are user corrections that should be canonical
   - Requires: export from Earth Pro, parse KML, insert to DB

2. **Investigate scrape .txt files for DB integration**
   - Many .txt files were created during scraping that capture per-project information Claude found
   - May contain richer narrative content (owner intent, controversy, design notes, neighbor objections) than what's in structured DB columns
   - Tasks:
     - Inventory all .txt files under `~/berkeley-data/`: locations, count, total size, date range, naming convention
     - Sample 3-5 representative files to assess content quality
     - Determine whether project IDs or APNs are recoverable from filenames or content
     - Decide treatment: (A) preserve as-is with `project_text_captures` index table linking to file paths, (B) extract structured fields and archive originals, (C) full-text search via SQLite FTS5 indexed corpus
   - **Done when:** decision documented and either implementation completed or explicit deferral with rationale

3. **Join news articles to projects**
   - The `news_coverage` table in `berkeley_address_centric.db` contains 2,024 article rows that should be joinable to housing projects
   - Schema: `news_id`, `project_id` (TEXT), `project_name`, `url`, `source`, `date_added`
   - Tasks:
     - Design `project_news_links` join table with `match_type` and `confidence` columns to support multiple match semantics (address-mentioned, developer-mentioned, general-coverage, inferred)
     - Implement initial address-regex matching pass (high-precision low-recall)
     - Migrate `news_coverage` from `berkeley_address_centric.db` into the housing pipeline DB
   - **Done when:** join table populated for the high-confidence matches; remaining articles flagged for later manual or AI-assisted matching

4. **Build polygon refinement workflow for featured tour projects**
   - **Goal:** Achieve accurate building footprints for 10-20 projects that will be featured in flyover tours, while keeping parcel-polygon or synthetic fallback for the remaining ~150 projects.
   - Tasks:
     - Inventory project PDFs to determine what kinds of geometric information are extractable (in progress, see `docs/pdf_corpus_analysis_2026-04-30.md` when complete)
     - Decide tour selection (5-10 tours covering neighborhoods, project types, and status categories)
     - Identify the specific 10-20 projects that need accurate footprints based on tour selection
     - Hand-trace building footprints in Google Earth Pro for featured projects, using parcel polygon as ground reference
     - Round-trip hand-traced polygons into `project_geometries` as `manual_polygon` rows with provenance notes
     - Regenerate `berkeley_skyline.kml` with improved geometries
   - **Done when:** 10-20 featured projects have `geometry_type_id=8` (`manual_polygon`) rows with `is_current=1` in `project_geometries`, and the regenerated KML visually matches actual building footprints when reviewed in Earth Pro.

5. **Create flyover tours for berkeleybuild.com**
   - **Goal:** 5-10 narrative tours embedded on the public site, supporting both pre-rendered video (for performance) and interactive exploration (for engagement).
   - Tasks:
     - Inventory existing tour KMLs in `docs/kml_versions/` to identify which can be reused or adapted
     - Define tour selection: 5-10 tours covering neighborhood, project type, status, and story/theme dimensions
     - For each tour: write or adapt a tour KML defining camera moves
     - Record each tour in Earth Pro using screen capture, optionally with voiceover
     - Encode and embed videos on berkeleybuild.com
     - Provide downloadable KMLs for advanced users
     - (Optional, lower priority) Add interactive Cesium or MapLibre embed for in-browser exploration
   - **Done when:** 5-10 tour videos are embedded on berkeleybuild.com with associated KMLs available for download.

6. **Cross-directory file consolidation**
   - **Goal:** Move useful files from `~/berkeley_data`, `~/berkeley-data-staging`, `~/berkeley-housing-research`, and `~/berkeley-permit-pipeline` into the canonical `~/berkeley-data` location, archive obsolete copies, and document the consolidated state.
   - Tasks (deferred from session 2026-04-30):
     - Review CC's survey report at `docs/cross_directory_survey_2026-04-30.md`
     - Decide per-file moves vs. archives vs. deletions
     - Execute moves with explicit per-file decisions
     - Two specific decisions documented as needing resolution: (a) keep Quartz site for public docs or extract content, (b) continue Obsidian for project notes or consolidate to markdown
   - **Done when:** only one canonical copy of each useful file exists in `~/berkeley-data`, obsolete copies are archived externally or deleted, and the four legacy directories contain only what's intentionally kept there or are empty.

7. **Investigate 2740 SHASTA duplicate**
   - Two project rows exist for this address
   - Need to determine which is canonical and archive the other

8. **APN normalization** across `berkeley.db` and `berkeley_housing_analysis.db`
   - Current formats incompatible:
     - `berkeley_housing_analysis.db`: `058 214901904` (space-separated)
     - `berkeley.db` parcels: `16-1428-2-2` (hyphenated)
     - `berkeley.db` addresses_arcgis: `055182901100` (no separator)
   - Blocks cross-database joins
   - Estimated effort: 2-4 hours

### Medium Priority

9. **Consolidate active databases** per architectural decision
   - Merge `berkeley_housing_analysis.db` tables into `berkeley.db`
   - Estimated effort: 8-12 hours (per CC estimate)
   - Deferred until APN normalization complete

10. **Investigate 5 remaining SKIP_NO_MATCH addresses**
   - Similar to 0 LE ROY recovery workflow
   - Requires Accela lookup by permit number

11. **Backfill lat/lon for 11 projects** without coordinates
   - Currently silently excluded from KML
   - May require manual geocoding or Accela address lookup

### Lower Priority

12. **Build post-Accela ingestion notebook** (`08_post_accela_pipeline.ipynb`)
   - Standardize workflow for processing scraped Accela data
   - Defer until workflow stabilizes

13. **Investigate berkeley_address_centric.db before archiving**
    - Contains 2,024 `news_coverage` rows — largely addressed by item 3 above
    - Other tables may still have value

14. **Plan BESO energy data integration**
    - `berkeley_energy_use.db` has 520 building records
    - Directly relevant to future utility-domain expansion
    - Merge into `berkeley.db` when ready

---

## 7. Conventions Worth Remembering

### APN Formats

| Source | Format | Example |
|--------|--------|---------|
| `projects` table | 12-digit space-separated | `058 214901904` |
| `berkeley_parcels.csv` | Hyphenated | `58-2149-19-4` |
| `berkeley.db` parcels | Hyphenated | `16-1428-2-2` |
| `berkeley.db` addresses_arcgis.apn_norm | No separator | `055182901100` |

**Normalization rule:** Strip all non-digits to get canonical 12-digit form. Both `058 214901904` and `58-2149-19-4` normalize to `058214901904`.

### Geometry Formats

| Context | Format | Coordinate Order |
|---------|--------|------------------|
| `project_geometries.geojson` column | GeoJSON TEXT | `[lon, lat]` (standard) |
| KML output | KML coordinates | `lon,lat,alt` (same as GeoJSON) |
| Shapely parsing | `shapely.shape(json.loads(geojson))` | N/A |

### Special Cases

**UC Projects (4 known):**
- 2400 BOWDITCH St
- 2556 HASTE St
- 2200 BANCROFT Way
- 1950 OXFORD St

These intentionally have no APN (UC land is not in county parcel system). They fall back to `synthetic_footprint` or `manual_polygon` geometry sources.

---

## 8. Known Data Quality Issues

### Critical

| Issue | Severity | Status |
|-------|----------|--------|
| APN format mismatch blocks cross-DB joins | High | Open — normalization required |
| 2740 SHASTA has two project rows | Medium | Open — needs investigation |

### Moderate

| Issue | Severity | Status |
|-------|----------|--------|
| Project 25 permit mismatch | Medium | Open |
| — `permits` field says `PLN2025-0066` | | |
| — `permit_events` point to `ZP2026-0015` | | |
| — Data entry error in projects table | | |
| 9 projects without lat/lon excluded from KML | Medium | Open — need geocoding |
| 5 SKIP_NO_MATCH addresses pending | Medium | Open — need Accela lookup |

### Informational

| Issue | Notes |
|-------|-------|
| `berkeley_housing_v2.db` has 17 quarantined documents | Migration artifacts; will be deleted with DB |
| `berkeley_housing_v2.db` has 3 duplicate address quarantine rows | Migration artifacts; will be deleted with DB |
| `berkeley_address_centric.db` news_coverage (2,024 rows) | Should investigate before archiving |

---

## 9. Workflow Notes for AI Collaboration

### Tool Selection

| Task Type | Use |
|-----------|-----|
| Execution / filesystem work / database queries | Claude Code (CC) |
| Design conversations / multi-step planning / catching reasoning errors | Chat Claude |
| Quick lookups / explaining concepts | Either |

### State Management

**The two AIs do NOT share state.** This `PROGRESS.md` is the bridge.

| Rule | Why |
|------|-----|
| When state changes, update this doc in the same session | Prevents drift between reality and documentation |
| When starting a new chat session, paste relevant sections to the AI | AI cannot read files; needs context in conversation |
| Reference specific sections rather than asking AI to "remember" | AIs have no cross-session memory |

### Session Handoff Checklist

When ending a session that made changes:
1. Update relevant sections of `PROGRESS.md`
2. Commit changes to git (if appropriate)
3. Note any open threads in "Open Work" section
4. Record decisions in "Recent Decisions Log"

When starting a new session:
1. Read `PROGRESS.md` yourself first
2. Paste TL;DR + relevant sections to AI
3. Reference `docs/database_architecture_review_2026-04-30.md` for detailed analysis
4. Check "Open Work" for priorities

---

## 10. Recent Decisions Log

*Most recent first. Include date, decision, and brief rationale.*

### 2026-04-30

- **Featured projects polygon approach:** Decided to feature 10-20 projects with hand-traced building footprints; remaining ~150 projects keep parcel-polygon or synthetic fallback.

- **Parcel data authority confirmed:** Alameda County is the authoritative parcel data source; City of Berkeley parcel layer is a clipped derivative of County data.

- **PDF corpus analysis commissioned:** To inform polygon extraction approach; results will be in `docs/pdf_corpus_analysis_2026-04-30.md`.

- **Cross-directory survey completed:** Survey at `docs/cross_directory_survey_2026-04-30.md`; consolidation deferred to future session.

- **Architecture review committed:** "One master DB, many tables" model selected. `berkeley.db` will absorb `berkeley_housing_analysis.db` tables over time. Rationale: reduces complexity, enables cross-domain queries, matches how civic data actually relates.

- **MCP integration deferred:** Progress doc and session discipline are the priority. MCP can be revisited once workflows stabilize.

- **Per-field provenance pattern selected:** `project_status_history` + `manual_overrides` tables chosen over fully attribute-level facts table. Rationale: simpler to implement, sufficient for current audit needs. **Decision made; not yet implemented.**

- **Database inventory completed:** 12 databases catalogued. 3 marked obsolete (safe to delete), 2 marked dormant, 2 active, 3 staging/reference, 2 backups.

### 2026-04-25

- **Schema migration completed:** v1 → v2-style structure with versioning and 9-type geometry vocabulary.

- **150 parcel polygons imported:** Into `project_geometries` table from `berkeley_parcels.csv` via APN matching.

- **0 LE ROY APN recovered:** Was SKIP_NO_MATCH, recovered as `058 224402501` via Accela investigation.

- **generate_kml.py rewritten:** Now reads from `project_geometries` table instead of flat CSV.

- **NICAR tutorial button:** Merged dev → main and deployed to GitHub Pages.

---

## Appendix A: File Locations Quick Reference

```
~/berkeley-data/
├── PROGRESS.md                          # This file
├── databases/
│   ├── berkeley.db                      # Master (50MB)
│   ├── berkeley_housing_analysis.db     # Active housing (1.1MB)
│   ├── accela_reports.db                # Staging
│   ├── berkeley_housing_apr.db          # Frozen APR
│   ├── berkeley_address_centric.db      # To investigate
│   ├── berkeley_energy_use.db           # BESO data
│   ├── berkeley_housing_v2.db           # Obsolete
│   ├── berkeley_data.db                 # Obsolete
│   ├── berkeley_housing_map.db          # Obsolete
│   └── housing_projects.db              # Obsolete
├── docs/
│   ├── database_architecture_review_2026-04-30.md
│   ├── berkeley_skyline.kml             # Canonical KML
│   └── kml_versions/                    # 12 archived tours
├── scripts/
│   ├── generate_kml.py                  # KML generator
│   ├── accela_workflow.py               # Accela processing
│   └── [12+ other active scripts]
└── data/
    ├── processed/
    │   └── housing_projects_FINAL.csv   # Flat CSV export
    └── reference/
        └── berkeley_parcels.csv         # Parcel polygons source
```

---

## Appendix B: Key Table Schemas

### berkeley_housing_analysis.db.projects (57 columns)

Key columns for common operations:

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER | Primary key |
| `address_display` | TEXT | Canonical display address |
| `apn` | TEXT | Format: `058 214901904` |
| `units` | INTEGER | Total unit count |
| `status` | TEXT | Pipeline status |
| `latitude` | REAL | WGS84 |
| `longitude` | REAL | WGS84 |
| `permits` | TEXT | Comma-separated permit numbers |
| `is_uc_project` | INTEGER | 1 if UC Berkeley project |

### berkeley_housing_analysis.db.project_geometries

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER | Primary key |
| `project_id` | INTEGER | FK to projects |
| `geometry_type_id` | INTEGER | FK to vocabulary (1-9) |
| `geojson` | TEXT | GeoJSON polygon |
| `height_meters` | REAL | Building height |
| `base_elevation_meters` | REAL | Ground elevation |
| `source_document_id` | INTEGER | FK to source document |
| `version_label` | TEXT | Version identifier |
| `edited_by` | TEXT | Who edited |
| `edit_notes` | TEXT | Edit description |
| `is_current` | INTEGER | 1 if active version |
| `superseded_by` | INTEGER | FK to replacement geometry |
| `created_at` | TEXT | Timestamp |
| `updated_at` | TEXT | Timestamp |

### berkeley.db.parcels

| Column | Type | Notes |
|--------|------|-------|
| `APN` | TEXT | Format: `16-1428-2-2` |
| `SitusAddre` | TEXT | Full situs address |
| `the_geom` | TEXT | GeoJSON geometry |
| `Latitude` | TEXT | (stored as text, needs cast) |
| `Longitude` | TEXT | (stored as text, needs cast) |

---

*End of PROGRESS.md — Last reviewed 2026-04-30*
