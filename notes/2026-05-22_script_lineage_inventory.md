# Script Lineage Inventory

**Generated:** 2026-05-21
**Scope:** scripts/, scripts/migration/, analysis/audit_2026-05-16/, root .py files

## Summary

| Location | .py files |
|----------|-----------|
| scripts/ (excluding migration/) | 25 |
| scripts/migration/ | 2 |
| analysis/audit_2026-05-16/ | 8 |
| repo root | 1 |
| **Total** | **36** |

---

## Active scripts (in scripts/)

### scripts/accela_workflow.py

**Size:** 3,598 lines (OVER 2000 LINE THRESHOLD - summary only)
**Last modified:** 2026-03-31 17:17
**Docstring summary:** "Accela Data Collection Workflow - Generates search URLs and parses Processing Status text"

**Inputs:**
- databases/berkeley_housing_analysis.db (projects table)
- data/raw/accela_status/*.txt (text files from Accela)

**Outputs:**
- data/outputs/accela_collection_checklist.csv
- data/outputs/accela_collection_checklist.html

**CLI:** Yes, argparse. Subcommands: generate, parse, save, save_batch

**Main function:** Generates Accela search URLs for projects, parses pasted Processing Status text, saves parsed data back to database. Multi-mode workflow tool.

**Notable patterns:** 3600+ lines suggests accumulated functionality. References both v1 database path and FINAL.csv.

---

### scripts/add_heights.py

**Size:** 220 lines
**Last modified:** 2026-04-14 17:45
**Docstring summary:** (no module docstring visible)

**Inputs:**
- databases/berkeley_housing_analysis.db

**Outputs:**
- Updates projects table in-place

**CLI:** No argparse visible

---

### scripts/add_labels_to_kml.py

**Size:** 240 lines
**Last modified:** 2026-05-18 12:25
**Docstring summary:** (would need to read)

**Inputs:**
- databases/berkeley_housing_analysis.db
- KML files

**Outputs:**
- Modified KML files

---

### scripts/build_scrape_queue.py

**Size:** 234 lines
**Last modified:** 2026-05-20 18:27
**Docstring summary:** "Build the scrape queue for the inspection orchestrator"

**Inputs:**
- databases/berkeley_housing_v2.db (read-only)

**Outputs:**
- /tmp/cic_recon_queue.db (or specified --queue-db path)

**CLI:** Yes, argparse. --v2-db, --queue-db

**Main function:** Reads in-scope B-permits from v2, populates scrape_queue table. Classifies by URL availability.

**Notable patterns:** Uses v2 database (normalized schema), not v1.

---

### scripts/convert_all_arcgis.py

**Size:** 40 lines
**Last modified:** 2025-11-06
**Docstring summary:** Converts ArcGIS files

**Inputs:** ArcGIS files
**Outputs:** Converted files

---

### scripts/convert_boundaries.py

**Size:** 26 lines
**Last modified:** 2025-11-07
**Docstring summary:** Converts boundary files

---

### scripts/cpra_dedup.py

**Size:** 270 lines
**Last modified:** 2026-05-13 14:53
**Docstring summary:** CPRA deduplication

---

### scripts/discover_new_projects.py

**Size:** 391 lines
**Last modified:** 2026-03-29 09:36
**Docstring summary:** "Discover new housing projects not in our database"

**Inputs:**
- data/processed/housing_projects_FINAL.csv
- data/raw/corridor_scans/*.txt

**Outputs:**
- data/processed/new_projects_discovered.csv (optional)
- stdout comparison

**CLI:** Yes, argparse. --scan-file, --compare-only

**Main function:** Compares scan files against FINAL.csv to find new projects.

---

### scripts/export_explorer_data.py

**Size:** 415 lines
**Last modified:** 2026-04-13 11:03
**Docstring summary:** "Export Explorer Data Script - Single Source of Truth. This is the ONLY script that should be used to generate explorer_data.js."

**Inputs:**
- databases/berkeley_housing_analysis.db (projects, permit_events, permit_fees, project_documents tables)

**Outputs:**
- docs/explorer_data.js (DATA.projects, DATA.events, DATA.fees, DATA.staff, DATA.players, DATA.timeline, DATA.documents)

**CLI:** No argparse; direct execution

**Main function:** Queries v1 database tables, builds comprehensive DATA object, writes to JavaScript file for explorer.html consumption.

**Notable patterns:**
- Hardcoded path: `/Users/johngage/berkeley-data`
- Claims "Single Source of Truth" but export_explorer_data_v2.py also exists
- Queries v1 database (flat tables)

---

### scripts/export_explorer_data_v2.py

**Size:** 757 lines
**Last modified:** 2026-05-13 14:53
**Docstring summary:** "Export Explorer Data Script - Single Source of Truth" (identical claim to v1 script)

**Inputs:**
- databases/berkeley_housing_v2.db (normalized schema: projects, project_versions, project_events, fees, documents, etc.)

**Outputs:**
- docs/explorer_data_v2_working.js (different filename from v1!)

**CLI:** No argparse; direct execution

**Main function:** Queries v2 normalized database, translates to v1-compatible DATA shape for explorer.html. Includes inactive-state detection logic.

**Notable patterns:**
- Hardcoded path: `/Users/johngage/berkeley-data`
- Complex joins across normalized tables
- Maps v2 vocabulary codes to v1 display strings
- Writes to `_v2_working.js`, not the main `explorer_data.js`

---

### scripts/extract_fees.py

**Size:** 553 lines
**Last modified:** 2026-03-30 22:31
**Docstring summary:** "Fee Extraction Script for Berkeley Housing Pipeline"

**Inputs:**
- data/raw/accela_status/*.txt

**Outputs:**
- data/berkeley_housing.db (permit_fees table) — NOTE: different path than other scripts!

**CLI:** No argparse visible

**Main function:** Parses fee data from Accela text files, inserts into permit_fees table.

**Notable patterns:**
- DB_PATH points to `data/berkeley_housing.db` not `databases/berkeley_housing_analysis.db` — PATH MISMATCH
- Drops and recreates permit_fees table on each run

---

### scripts/generate_apr.py

**Size:** 538 lines
**Last modified:** 2026-04-02 18:26
**Docstring summary:** "Generate APR (Annual Progress Report) Tables"

**Inputs:**
- data/berkeley_housing_analysis.db — NOTE: path mismatch (data/ vs databases/)

**Outputs:**
- APR tables (Table A, Table A2, Table B)
- CSV and JSON outputs

**CLI:** Yes, argparse. --year, --output

**Notable patterns:**
- DB_PATH = `data/berkeley_housing_analysis.db` — different from most scripts which use `databases/`

---

### scripts/generate_apr_v2.py

**Size:** 624 lines
**Last modified:** 2026-05-20 11:30
**Docstring summary:** APR generation for v2 database

**Inputs:**
- databases/berkeley_housing_v2.db

**Outputs:**
- APR tables

---

### scripts/generate_kml.py

**Size:** 365 lines
**Last modified:** 2026-05-18 12:25

**Inputs:**
- databases/berkeley_housing_analysis.db

**Outputs:**
- KML files

---

### scripts/generate_master_list.py

**Size:** 316 lines
**Last modified:** 2026-03-29 09:27
**Docstring summary:** Generates master project list

**Inputs:**
- databases/berkeley_housing_analysis.db
- data/processed/housing_projects_FINAL.csv

**Outputs:**
- data/processed/project_master_list.csv

---

### scripts/manage_outreach.py

**Size:** 384 lines
**Last modified:** 2026-04-03 11:34

---

### scripts/migrate_to_database.py

**Size:** 434 lines
**Last modified:** 2026-04-01 14:02
**Docstring summary:** "Database Migration Script - Single Source of Truth. Migrates all data to berkeley_housing_analysis.db"

**Inputs:**
- data/processed/housing_projects_FINAL.csv
- data/processed/project_fees.json

**Outputs:**
- databases/berkeley_housing_analysis.db (creates/updates projects table)

**CLI:** No argparse

**Main function:** Creates projects table schema, imports from FINAL.csv, links permit_events by address, imports fees from JSON.

**Notable patterns:**
- Hardcoded developer/architect associations in code
- Third script claiming "Single Source of Truth"

---

### scripts/parse_attachments.py

**Size:** 195 lines
**Last modified:** 2026-04-09 09:46

**Inputs:**
- databases/berkeley_housing_analysis.db

---

### scripts/parse_buildingeye_text.py

**Size:** 244 lines
**Last modified:** 2026-02-23

---

### scripts/parse_timeline_data.py

**Size:** 607 lines
**Last modified:** 2026-04-01 20:03
**Docstring summary:** "Comprehensive Timeline Data Parser - Extracts ALL timeline data from Accela status text files"

**Inputs:**
- data/berkeley_housing_analysis.db — NOTE: path mismatch (data/ vs databases/)
- data/raw/accela_status/*.txt

**Outputs:**
- permit_events table
- projects table (bp_filed_date, bp_issued_date, co_date)
- permit_fees table

**Notable patterns:**
- DB_PATH = `data/berkeley_housing_analysis.db` — inconsistent with other scripts

---

### scripts/permit_role_classifier.py

**Size:** 580 lines
**Last modified:** 2026-05-18 12:25
**Docstring summary:** Permit role classification logic

**Inputs:**
- databases/berkeley_housing_v2.db

---

### scripts/scrape_inspections.py

**Size:** 532 lines
**Last modified:** 2026-05-20 18:27
**Docstring summary:** "Inspection Scraper Orchestrator"

**Inputs:**
- /tmp/cic_recon_queue.db (or specified --queue-db)
- experiments/accela_scrape/inspection_scraper.py (module)

**Outputs:**
- data/raw/accela_inspections/{permit_number}.json
- logs/scrape_inspections_*.log
- Updates queue database

**CLI:** Yes, argparse. --queue-db, --output-dir, --log-dir, --limit, --headed, --no-sleep

---

### scripts/staff_mailing.py

**Size:** 185 lines
**Last modified:** 2026-04-04 18:17

---

### scripts/test-sfyimby-datasette.py

**Size:** 2 lines
**Last modified:** 2026-04-13

---

### scripts/validate_scraped_file.py

**Size:** 377 lines
**Last modified:** 2026-03-29 09:49

---

## Migration scripts (in scripts/migration/)

### scripts/migration/migrate_v1_to_v2.py

**Size:** 1,685 lines
**Last modified:** (from migration creation)
**Docstring summary:** "Migration Script: v1 (flat) → v2 (normalized)"

**Inputs:**
- databases/berkeley_housing_analysis.db (v1, read-only)
- schema/core.sql
- schema/vocabularies_berkeley.sql
- schema/views_compat.sql

**Outputs:**
- databases/berkeley_housing_v2.db (creates new)
- docs/migration/ (audit reports)

**CLI:** No argparse; direct execution

**Main function:** Creates v2 normalized database from v1 flat tables. Two-pass inserts, provenance tracking, synthetic event creation for inferred dates.

---

### scripts/migration/import_cpra_2023_2025.py

**Size:** 923 lines
**Docstring summary:** CPRA data import for 2023-2025 period

**Inputs:**
- CPRA data files
- databases/berkeley_housing_v2.db

**Outputs:**
- Updates v2 database

---

## Recent audit scripts (in analysis/audit_2026-05-16/)

All audit scripts are read-only analysis tools. 8 files total, 1,375 lines combined.

| Script | Lines | Purpose |
|--------|-------|---------|
| ambiguous_fields_dump.py | 110 | Dump fields for ambiguous permits |
| completes_fields_dump.py | 115 | Dump fields for completing permits |
| conflict_dryrun.py | 138 | Dry-run conflict detection |
| does_not_complete_sample_dump.py | 119 | Sample non-completing permits |
| inspect_post_patch_ambiguous.py | 159 | Post-patch inspection |
| schema_inventory.py | 171 | Schema documentation |
| valuation_distribution.py | 275 | Valuation analysis by classifier |
| valuation_full_corpus.py | 288 | Full corpus valuation analysis |

All read from databases/berkeley_housing_v2.db.

---

## Root-level scripts

### update_housing_data.py

**Size:** (at repo root)
**Purpose:** Likely a wrapper or entry point

---

## Archived scripts

### scripts/export_explorer_data_v2.py.bak

**Size:** 14,420 bytes
**Last modified:** 2026-05-12 17:18
**Note:** Backup of export_explorer_data_v2.py from before May 13 changes

---

## Intermediate data files

### data/processed/housing_projects_FINAL.csv

- **Size:** 82,310 bytes
- **Last modified:** 2026-04-11 15:46
- **Header:** `id,address_display,apn,owner,net_units,new_units,old_units,year,permits,description,status,num_permits,project_size_category,slug,address_norm,latitude,longitude,unit_category,tenure,sb35_flag,sb330_flag,ab2011_flag,density_bonus,density_bonus_pct,vli_units_extracted,height_stories,height_feet,app_filed_date,app_complete_date,entitled_date,total_processing_days,accela_status,accela_status_date,bp_issued_date,co_date,construction_start_date,estimated_completion_date,construction_status,app_packet_size_mb,construction_data_reliability,is_uc_project`
- **Referenced by:** migrate_to_database.py, discover_new_projects.py, generate_master_list.py, accela_workflow.py

### data/processed/project_fees.json

- **Size:** 171,687 bytes
- **Last modified:** 2026-03-30 22:31
- **Referenced by:** migrate_to_database.py

### data/processed/explorer_data.json

- **Size:** 531,819 bytes
- **Last modified:** 2026-03-30 20:56
- **Note:** JSON version of explorer data (separate from .js)

### data/processed/explorer_data_v2.json

- **Size:** 408,815 bytes
- **Last modified:** 2026-03-30 21:07

### data/processed/explorer_data_comprehensive.json

- **Size:** 946,264 bytes
- **Last modified:** 2026-03-31 09:06

### data/processed/scraping_queue.csv

- **Size:** Small
- **Header:** `address,permit_number,units,what_is_missing,accela_search_term,priority,completeness_score`

### data/processed/scraping_log.csv

- **Header:** `timestamp,filename,permit,address,validation_result,errors,warnings`

### data/processed/project_master_list.csv

- **Size:** 22,514 bytes
- **Last modified:** 2026-04-13
- **Referenced by:** generate_master_list.py (output)

### data/processed/snapshots/

Contains timestamped CSV exports of database tables:
- 2026-05-03_morning_baseline/
- 2026-05-03_post_handtraced/
- 2026-05-03_post_v8_kml/

Each contains: projects.csv, permit_events.csv, permit_fees.csv, project_documents.csv, etc.

---

## Cross-references summary table

| Script | Primary Inputs | Primary Outputs |
|--------|----------------|-----------------|
| export_explorer_data.py | berkeley_housing_analysis.db | docs/explorer_data.js |
| export_explorer_data_v2.py | berkeley_housing_v2.db | docs/explorer_data_v2_working.js |
| migrate_to_database.py | FINAL.csv, project_fees.json | berkeley_housing_analysis.db |
| migrate_v1_to_v2.py | berkeley_housing_analysis.db | berkeley_housing_v2.db |
| extract_fees.py | accela_status/*.txt | data/berkeley_housing.db |
| parse_timeline_data.py | accela_status/*.txt | data/berkeley_housing_analysis.db |
| build_scrape_queue.py | berkeley_housing_v2.db | cic_recon_queue.db |
| scrape_inspections.py | cic_recon_queue.db | accela_inspections/*.json |
| generate_apr.py | data/berkeley_housing_analysis.db | APR tables |
| generate_apr_v2.py | berkeley_housing_v2.db | APR tables |
| discover_new_projects.py | FINAL.csv, scan files | new_projects_discovered.csv |
| accela_workflow.py | berkeley_housing_analysis.db | accela_collection_checklist.csv |

---

## Contradictions and conflicts

### 1. Multiple "Single Source of Truth" claims

Three scripts claim to be the single source of truth:
- `export_explorer_data.py`: "This is the ONLY script that should be used to generate explorer_data.js"
- `export_explorer_data_v2.py`: Same claim in docstring
- `migrate_to_database.py`: "Database Migration Script - Single Source of Truth"

### 2. Database path inconsistencies

| Script | DB_PATH used |
|--------|--------------|
| Most scripts | `databases/berkeley_housing_analysis.db` |
| extract_fees.py | `data/berkeley_housing.db` (DIFFERENT) |
| generate_apr.py | `data/berkeley_housing_analysis.db` (DIFFERENT) |
| parse_timeline_data.py | `data/berkeley_housing_analysis.db` (DIFFERENT) |

The `data/` vs `databases/` inconsistency means some scripts may be writing to a different database than others read from.

### 3. Parallel database systems with unclear primacy

- **v1:** `berkeley_housing_analysis.db` (flat tables)
- **v2:** `berkeley_housing_v2.db` (normalized schema)

Both have active scripts. No clear deprecation of v1.

### 4. export_explorer_data.py vs export_explorer_data_v2.py output conflict

- v1 script writes to: `docs/explorer_data.js`
- v2 script writes to: `docs/explorer_data_v2_working.js`

They don't overwrite each other, but explorer.html presumably loads one or the other. Which is authoritative?

### 5. extract_fees.py drops and recreates permit_fees table

Line 31-32:
```python
cursor.execute("DROP TABLE IF EXISTS permit_fees")
cursor.execute("CREATE TABLE permit_fees ...")
```

Running this script destroys existing fee data. Other scripts expect permit_fees to persist.

### 6. Hardcoded paths throughout

Multiple scripts have:
```python
BASE_DIR = Path('/Users/johngage/berkeley-data')
```

This breaks portability and makes the scripts non-relocatable.

### 7. FINAL.csv is both input and conceptually "final"

Scripts read from `housing_projects_FINAL.csv` but the file has 14 backup versions in the same directory, suggesting it's frequently modified. The "FINAL" name is misleading.

### 8. project_fees.json vs permit_fees table

- `migrate_to_database.py` reads from `project_fees.json`
- `extract_fees.py` writes to a `permit_fees` table
- Different schemas, different sources. Unclear which is authoritative for fee data.

### 9. accela_workflow.py is 3600+ lines

This single file likely contains multiple responsibilities that should be separated. Size suggests accumulated technical debt.

### 10. No script writes to data/processed/explorer_data.json

The JSON file exists (531KB) but no script in scope appears to generate it. Either it's manually created, generated by a notebook, or by a script not in the inventory.
