# CLAUDE.md — Berkeley Housing Pipeline

Orientation for any session working in `~/berkeley-data`. Verify specifics against
`git log` and the DB before relying on them — this file is a map, not ground truth.

## What this project is
An **independent** reconstruction of Berkeley's housing-production pipeline
(entitlement → building permit → certificate of occupancy), built from **primary
sources**, used to produce/verify the HCD Annual Progress Report (APR) and a
public explorer (berkeleybuild.com) + Datasette.

## Canonical database
**`databases/berkeley_housing_v2.db`** — V2 normalized schema (45 tables):
`projects → project_versions → unit_program(+affordability) → project_parcels →
parcels`, plus `project_events` (timeline: entitlement/BP/CO milestones via
`vocabulary_event_types`), `permits`, `project_classifications`. The flat
compatibility view is **`v_projects_flat`** (what `generate_apr_v2.py` and
`export_explorer_data_v2.py` read).
- **V1 `berkeley_housing_analysis.db`** (flat `projects` table) is frozen/superseded.
- **`berkeley.db`** = Alameda County **assessor parcels** (coords, `the_geom`,
  `apn_norm`, UseCode) — a reference store, not the pipeline DB.
- **`hcd_apr_mirror.db`** = Berkeley's submitted APR mirrored from CKAN — the
  **VERIFICATION TARGET, never a data source** (see rules below).
- There are ~40 DB files total; most are dated snapshots/backups. Inventory:
  `docs/audit/2026-06-01_data_landscape_examination.md`.

## Primary sources → DB (lineage)
- `data/processed/housing_projects_FINAL.csv` (curated) + `data/raw/accela_status/*.txt`
  (Accela scrapes) → V1 (`migrate_to_database.py`, `accela_workflow.py`).
- `data/raw/cpra-downloads/BP_Annual Permit Report-*.xlsx` (CPRA permits, 2018–2025)
  → V2 (`scripts/migration/import_cpra_2023_2025.py`, `scripts/cpra_dedup.py`).
- V1 → V2 via `scripts/migration/migrate_v1_to_v2.py`.

## Non-negotiable working rules
1. **CKAN/HCD is the verification target, never a data source.** Build only from
   CPRA + Alameda assessor. Where primary sources are silent (tenure, bedrooms),
   record **"unknown with provenance"** — never fill from CKAN.
2. **Snapshot before any DB write.** `cp` to `databases/keep_snapshot_<date>_pre-<change>.db`,
   confirm size + `PRAGMA integrity_check`. Then a **read-only preview → STOP for
   John's go-ahead → transactional write with verify-or-rollback.** John reviews
   classifications before any irreversible write.
3. **Read-only by default.** No merge/archive/delete/ingest/schema-change without
   an explicit go-ahead. Diagnose first; act second.
4. **APN cross-walk = 12-digit Alameda `apn_norm`**; matcher is
   `normalize_apn()` = strip non-digits. Coords/geometry come from `berkeley.db`.
5. **Never commit/push without instruction.** `dev` branch only; no push until
   John says so. Diagnostic docs land in `docs/audit/` (commit-ready, unpushed).
6. **`/dev/diskN` numbers are volatile** — re-verify by stable identity before any
   raw-device/disk op (drives, copies).

## Where things live
- Notebooks: `00_config … 05_feasibility/`, `04_reporting/` (D5/D6/D7 APR work).
- Scripts: `scripts/` (generators, scrapers, importers), `scripts/migration/`.
- Audit trail (read this for current analytical state): `docs/audit/` — the
  `2026-05-31_*` and `2026-06-01_*` docs are the latest deep arc.
- `PROGRESS.md` exists but may be stale; prefer the dated audit docs + `git log`.

## Current state pointer
See `docs/audit/2026-06-01_next_session_priming.md` (and the persistent memory
that auto-loads) for exactly where the work stands and what's next.
