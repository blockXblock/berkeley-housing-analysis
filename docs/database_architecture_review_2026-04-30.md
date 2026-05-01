# Berkeley Data Infrastructure: Architectural Review

**Generated:** 2026-04-29
**Purpose:** Read-only investigation to inform design decisions for data consolidation

---

## Executive Summary

The Berkeley data infrastructure contains **12 SQLite databases** totaling ~72MB. Active development centers on `berkeley_housing_analysis.db`, while `berkeley.db` serves as the authoritative source for parcel/address data. The system shows signs of organic growth with several abandoned schemas and duplicate data stores.

---

## Database Inventory

### 1. berkeley.db (50MB) — MASTER PARCEL/ADDRESS STORE

**Last Modified:** Mar 19, 2026 19:30
**Purpose:** Authoritative source for Berkeley parcels, addresses, business licenses, and zoning districts

| Table | Rows | Notes |
|-------|------|-------|
| addresses_arcgis | 65,459 | Full address registry with owner info |
| parcels | 29,024 | Base parcel records |
| parcels_arcgis | 29,024 | ArcGIS export of parcels |
| parcels_full | 65,507 | Parcels with all addresses |
| parcels_addresses_joined | 65,297 | Denormalized parcel+address |
| parcel_zones | 29,024 | Parcel-to-zoning mapping |
| licenses | 13,004 | Business licenses |
| licenses_fts | 13,004 | Full-text search index |
| zoning_districts | 42 | Zoning code definitions |
| zoning_projects_with_parcels | 154 | Projects linked to parcels |
| corridor_master | 430 | Commercial corridor analysis |
| corridor_far | 332 | Floor-area-ratio by corridor |
| corridor_ownership | 332 | Ownership patterns |
| corridor_boundaries | 3 | Corridor geometries |
| development_potential | 41 | Underdeveloped site analysis |
| rent_control | 1,098 | Rent-controlled properties |

**Schema Notes:**
- APN format: `16-1428-2-2` (dash-separated)
- Contains GeoJSON geometry in `the_geom` columns
- Truncated column names from ArcGIS export (e.g., `SitusStree`, `SitusStr_1`)

---

### 2. berkeley_housing_analysis.db (1.1MB) — ACTIVE HOUSING PIPELINE

**Last Modified:** Apr 25, 2026 12:49
**Purpose:** Primary housing project tracking database; actively used by scripts and exports

| Table | Rows | Notes |
|-------|------|-------|
| projects | 174 | Housing project master list |
| project_map | 165 | Map-ready project records |
| project_geometries | 165 | Project boundaries/points |
| project_permits | 114 | Permits linked to projects |
| project_documents | 1,423 | Document attachments |
| permit_events | 2,306 | Timeline events (status changes) |
| permit_fees | 441 | Fee records by permit |
| building_permits | 94 | Building permit details |
| sfyimby_projects | 249 | SFYimby source data |
| apr_rhna_progress | 8 | RHNA progress by category |
| apr_streamlining | 8 | Streamlining law usage |
| apr_unit_categories | 25 | APR unit categorization |
| data_collection_log | 1 | ETL audit log |
| vocabulary_geometry_types | 9 | Geometry type codes |

**Schema Notes:**
- APN format: `058 214901904` (space-separated, different from berkeley.db!)
- 57-column `projects` table (denormalized, wide)
- Actively referenced by 12+ scripts in `scripts/`
- Used for APR (Annual Progress Report) generation

---

### 3. berkeley_housing_v2.db (1.4MB) — ABANDONED NORMALIZED SCHEMA

**Last Modified:** Apr 22, 2026 12:31
**Purpose:** Attempted normalized redesign of housing data; development stalled

| Table | Rows | Notes |
|-------|------|-------|
| projects | 174 | Slim 10-column normalized version |
| parcels | 148 | Deduplicated parcel records |
| permits | 118 | Normalized permit records |
| documents | 1,406 | Document metadata |
| organizations | 53 | Developers, architects, etc. |
| people | 0 | Empty — never populated |
| cities | 1 | Just Berkeley |
| project_events | 2,605 | Status timeline |
| project_geometries | 165 | Geometry records |
| project_parcels | 154 | Many-to-many linking |
| project_participants | 108 | Org-to-project roles |
| project_versions | 174 | Version tracking |
| project_classifications | 80 | Project type tags |
| project_assets | 0 | Empty |
| project_bundles | 0 | Empty |
| unit_program | 174 | Unit counts by project |
| unit_program_affordability | 164 | Affordability breakdown |
| external_system_links | 0 | Empty |
| _audit_migration_log | 0 | Empty audit trail |
| _audit_low_confidence | 0 | Empty |
| _quarantine_documents | 17 | Documents with issues |
| _quarantine_duplicate_addresses | 3 | Address conflicts |
| vocabulary_* (18 tables) | ~5-15 each | Lookup tables |

**Schema Notes:**
- Proper normalized 3NF design with foreign keys
- 18 vocabulary tables for controlled vocabularies
- Migration from v1 never completed (people, assets, external_links empty)
- Views exist (`v_projects_flat`, `v_project_permits`, etc.)

---

### 4. berkeley_address_centric.db (14MB) — MATERIALIZED VIEW FOR MAPPING

**Last Modified:** Feb 27, 2026 12:01
**Purpose:** Pre-joined address-centric view for web mapping applications

| Table | Rows | Notes |
|-------|------|-------|
| addresses | 62,226 | Full address list |
| addresses_with_projects | 62,234 | Addresses + project flags |
| projects | 156 | Project summary |
| streets_summary | 427 | Aggregate by street |
| development_by_street | 80 | Development heat map |
| news_coverage | 2,024 | Media mentions |
| database_stats | 1 | Metadata |

**Schema Notes:**
- Appears to be a derived/materialized database
- Stale (2 months old)
- Duplicate of a file in `datasette-deploy/`

---

### 5. berkeley_data.db (4.1MB) — LEGACY BUSINESS LICENSES

**Last Modified:** Nov 15, 2025 21:19
**Purpose:** Original business license import; superseded by `berkeley.db`

| Table | Rows | Notes |
|-------|------|-------|
| business_licenses | 13,004 | Same count as berkeley.db.licenses |

**Schema Notes:**
- 5+ months stale
- Data appears duplicated in `berkeley.db.licenses`
- Candidate for deletion

---

### 6. accela_reports.db (288KB) — SCRAPED ACCELA DATA

**Last Modified:** Mar 20, 2026 11:04
**Purpose:** Raw scraped data from Accela permit portal

| Table | Rows | Notes |
|-------|------|-------|
| active_zoning_projects | 153 | Zoning permit list |
| active_zoning_classified | 153 | Same with classification |
| record_details | 37 | Detailed permit records |
| permit_pipeline | 0 | Empty |
| project_documents | 0 | Empty |
| project_planners | 1 | Single planner record |
| owner_enrichment | 1 | Single owner record |
| active_landuse_v1_* | varies | Raw report imports |

**Schema Notes:**
- Staging area for Accela scraping
- Several empty tables (never used)
- `active_zoning_projects` schema matches `berkeley.db.zoning_projects_with_parcels`

---

### 7. berkeley_energy_use.db (176KB) — BUILDING ENERGY DISCLOSURE

**Last Modified:** Jan 6, 2026 19:06
**Purpose:** Berkeley BESO (Building Energy Saving Ordinance) compliance data

| Table | Rows | Notes |
|-------|------|-------|
| building_energy | 520 | Energy disclosure records |

**Schema Notes:**
- Standalone dataset
- 4 months stale
- Could be merged into berkeley.db

---

### 8. berkeley_housing_apr.db (84KB) — APR SNAPSHOT

**Last Modified:** Feb 22, 2026 16:22
**Purpose:** Frozen snapshot for Annual Progress Report submission

| Table | Rows | Notes |
|-------|------|-------|
| projects | 115 | APR project list |
| project_map | 115 | Map coordinates |
| apr_rhna_progress | 7 | RHNA categories |
| apr_streamlining | 7 | Streamlining stats |
| apr_unit_categories | 20 | Unit breakdowns |
| apr_table_a2 | 115 | HCD Table A2 data |

**Schema Notes:**
- Point-in-time snapshot for regulatory reporting
- Intentionally frozen (don't update)

---

### 9. berkeley_housing_map.db (56KB) — OLD MAP EXPORT

**Last Modified:** Dec 22, 2025 11:30
**Purpose:** Superseded map export; replaced by `project_map` in analysis db

| Table | Rows | Notes |
|-------|------|-------|
| projects | 84 | Old project list |
| map_view | 84 | Map coordinates |

**Schema Notes:**
- 4+ months stale
- Candidate for deletion

---

### 10. housing_projects.db (60KB) — ORIGINAL PROTOTYPE

**Last Modified:** Dec 14, 2025 09:52
**Purpose:** Original prototype database; fully superseded

| Table | Rows | Notes |
|-------|------|-------|
| housing_projects | 84 | Legacy project list |
| mappable_projects | 0 | Empty |

**Schema Notes:**
- 4+ months stale
- Candidate for deletion

---

### 11-12. Backup Databases

| Database | Size | Modified | Notes |
|----------|------|----------|-------|
| berkeley_housing_analysis_pre_parcel_import_2026-04-25.db | 1.0MB | Apr 25 | Pre-migration backup |
| berkeley_housing_analysis_pre_schema_alignment_2026-04-25.db | 1.1MB | Apr 25 | Pre-migration backup |

---

## Cross-Database Analysis

### Tables That Exist in Multiple Databases

| Table Name | berkeley.db | analysis.db | v2.db | addr_centric.db | apr.db | map.db | housing.db |
|------------|-------------|-------------|-------|-----------------|--------|--------|------------|
| **projects** | 154* | 174 | 174 | 156 | 115 | 84 | 84 |
| **parcels** | 29,024 | — | 148 | — | — | — | — |
| **project_geometries** | — | 165 | 165 | — | — | — | — |
| **project_map** | — | 165 | — | — | 115 | — | — |
| **permit_events** | — | 2,306 | 2,605 | — | — | — | — |
| **documents** | — | 1,423 | 1,406 | — | — | — | — |

*`zoning_projects_with_parcels` table

**Observation:** Project data is replicated across 7 databases with varying row counts (84 → 174), indicating different snapshots in time.

---

### Foreign Key Relationships (Logical, Not Enforced)

```
berkeley_housing_analysis.db.projects.apn
    ──should join──►  berkeley.db.addresses_arcgis.apn_norm

    BUT: Format mismatch!
    - analysis.db: "058 214901904" (space-separated)
    - berkeley.db:  "055182901100" (no separator) or "55-1829-11" (dashes)

berkeley_housing_v2.db.project_parcels.parcel_id
    ──FK──►  berkeley_housing_v2.db.parcels.id  (internal FK, works)

berkeley_housing_v2.db.parcels.apn
    ──should join──►  berkeley.db.parcels.APN

    BUT: Format mismatch again
```

**Critical Issue:** APN formats are inconsistent across databases, making cross-database joins unreliable without normalization functions.

---

### Database Activity Analysis

| Database | Last Modified | Script References | Status |
|----------|---------------|-------------------|--------|
| berkeley_housing_analysis.db | Apr 25 | 12+ scripts | **ACTIVE** |
| berkeley.db | Mar 19 | 0 direct | REFERENCE ONLY |
| berkeley_housing_v2.db | Apr 22 | 1 (migration script) | STALLED |
| accela_reports.db | Mar 20 | 1 | STAGING |
| berkeley_address_centric.db | Feb 27 | 0 | DORMANT |
| berkeley_energy_use.db | Jan 6 | 0 | DORMANT |
| berkeley_data.db | Nov 15 | 0 | **OBSOLETE** |
| berkeley_housing_map.db | Dec 22 | 0 | **OBSOLETE** |
| housing_projects.db | Dec 14 | 0 | **OBSOLETE** |
| berkeley_housing_apr.db | Feb 22 | 0 | FROZEN (intentional) |

**Scripts actively using databases:**
- `accela_workflow.py` → berkeley_housing_analysis.db
- `add_heights.py` → berkeley_housing_analysis.db
- `export_explorer_data.py` → berkeley_housing_analysis.db
- `generate_kml.py` → berkeley_housing_analysis.db
- `generate_apr.py` → berkeley_housing_analysis.db
- `migrate_to_database.py` → berkeley_housing_analysis.db
- `parse_attachments.py` → berkeley_housing_analysis.db
- `parse_timeline_data.py` → berkeley_housing_analysis.db
- `migration/migrate_v1_to_v2.py` → both analysis.db and v2.db

---

## Recommendations

### Question: Which database should be the long-term canonical store?

**Recommendation: A hybrid approach with two primary databases**

| Role | Database | Rationale |
|------|----------|-----------|
| **Parcel/Address Authority** | berkeley.db | Already has 65K addresses, 29K parcels, zoning districts. This is foundational civic data that rarely changes. |
| **Housing Pipeline Tracking** | berkeley_housing_analysis.db | Active development, all scripts target it, contains timeline/event data. Rename to `berkeley_housing.db`. |

**Do NOT use berkeley_housing_v2.db** despite its cleaner schema. The normalized design is theoretically superior but:
- Migration never completed (empty tables)
- No scripts use it
- Team would need to rebuild all tooling

### Consolidation Cost Estimate

| Task | Effort | Risk |
|------|--------|------|
| Delete obsolete databases (3 files) | 5 min | Low |
| Normalize APN formats across DBs | 2-4 hrs | Medium |
| Merge `berkeley_data.db` licenses → already in berkeley.db | 0 (already done) | — |
| Merge `berkeley_energy_use.db` → berkeley.db | 1-2 hrs | Low |
| Add FK indexes to analysis.db for parcel lookups | 1-2 hrs | Low |
| Document canonical schema | 2-4 hrs | Low |
| **Total consolidation** | ~8-12 hrs | Low-Medium |

### Immediate Cleanup (Safe to Delete)

```bash
# These are obsolete/superseded:
rm databases/berkeley_data.db           # Nov 2025, licenses duplicated
rm databases/berkeley_housing_map.db    # Dec 2025, superseded
rm databases/housing_projects.db        # Dec 2025, superseded

# Keep backups for 30 days, then delete:
# databases/berkeley_housing_analysis_pre_*.db
```

### Schema Normalization Priority

1. **APN Format** — Create a view or trigger to normalize APNs to a single format (recommend: `NNNNNNNNNNNN` 12-digit no separators)
2. **Address Normalization** — Standardize on uppercase, no punctuation
3. **Date Formats** — Ensure all dates are ISO 8601 (`YYYY-MM-DD`)

---

## Appendix: File Sizes and Dates

```
50M  Mar 19 19:30  databases/berkeley.db
14M  Feb 27 12:01  databases/berkeley_address_centric.db
4.1M Nov 15 21:19  databases/berkeley_data.db
1.4M Apr 22 12:31  databases/berkeley_housing_v2.db
1.1M Apr 25 12:49  databases/berkeley_housing_analysis.db
1.1M Apr 25 11:58  databases/berkeley_housing_analysis_pre_schema_alignment_2026-04-25.db
1.0M Apr 25 09:50  databases/berkeley_housing_analysis_pre_parcel_import_2026-04-25.db
288K Mar 20 11:04  databases/accela_reports.db
176K Jan  6 19:06  databases/berkeley_energy_use.db
84K  Feb 22 16:22  databases/berkeley_housing_apr.db
60K  Dec 14 09:52  databases/housing_projects.db
56K  Dec 22 11:30  databases/berkeley_housing_map.db
```

---

*Report generated by Claude Code — ready for design discussion*
