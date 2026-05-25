# Berkeley Housing Pipeline: Migration Plan (v1 flat → v2 normalized)

**Status:** Draft. Awaiting John's review before Claude Code executes Phase 0.

**Scope:** Migrate `/Users/johngage/berkeley-data/databases/berkeley_housing_analysis.db` from its current flat-table-centric structure (reportedly 174 projects, 12,850 units, ~54 columns on the main table) to the normalized schema defined in `schema/core.sql`, seeded by `schema/vocabularies_berkeley.sql`, with compatibility views in `schema/views_compat.sql`.

**Non-scope:** Framework extraction (deferred until after Phase 5). CI data-quality automation (`scripts/validate/`) — deferred to Phase 7 as a follow-up. Web ingestion layer for external contributors — not built now; `asserted_by` field is already the extension point.

---

## Design principles in force during migration

1. **Reversibility over speed.** Every phase before cutover (0–3) is reversible. Phase 4 is the bridge; Phases 5–6 are forward-only. A mistake discovered in Phase 3 is cheap; a mistake discovered after Phase 4 is expensive.
2. **Database as single source of truth.** After cutover, all data lives in SQLite. CSV/JSON/KML are generated. No hand-edited spreadsheets in the loop.
3. **Foreign keys enforced always.** Every script that opens the DB must issue `PRAGMA foreign_keys = ON;` as its first statement. There is no exception to this rule.
4. **Two-pass insert pattern.** `projects.current_version_id` and `project_versions.source_event_id` are NULL on initial insert and populated in a second pass. The migration script must respect this order.
5. **Provenance captured on every fact-bearing row.** Even for migrated data, populate `asserted_by = 'migration_v1_to_v2_YYYYMMDD'` and `asserted_at = <run timestamp>`. The question "how do we know this?" must always have an answer, even if the answer is "imported from the legacy flat table."
6. **Vocabularies seeded before data migration.** Phase 1 fully seeds vocabulary tables. No data migration script should insert vocabulary rows on the fly.

---

## Phase 0: Preparation

**Goal:** Three independent backups of the current database, plus a new empty v2 database file ready to receive migrated data. Nothing in production changes.

**Reversibility:** Trivial. Delete the new DB file; original is untouched.

> **Note (added 2026-05-24):** The migration plan originally envisioned renaming `berkeley_housing_analysis.db` → `berkeley_housing_v1.db` at cutover. That rename was deferred indefinitely. The canonical v1 path remains `databases/berkeley_housing_analysis.db`. References to `berkeley_housing_v1.db` below describe a planned-but-unexecuted state. Do not attempt to open `berkeley_housing_v1.db` directly — SQLite will fail-open and create an empty stub.

**Steps:**

1. Create the backup directory:
   ```bash
   cd /Users/johngage/berkeley-data
   mkdir -p backups/pre-migration-$(date +%Y%m%d)
   ```

2. Three-way backup:
   ```bash
   # (a) File copy
   cp databases/berkeley_housing_analysis.db \
      backups/pre-migration-$(date +%Y%m%d)/berkeley_housing_v1_fullcopy.db

   # (b) SQL dump (text, diff-able, git-friendly)
   sqlite3 databases/berkeley_housing_analysis.db .dump \
      > backups/pre-migration-$(date +%Y%m%d)/berkeley_housing_v1_dump.sql

   # (c) Schema-only dump (for reference when building migration map)
   sqlite3 databases/berkeley_housing_analysis.db .schema \
      > backups/pre-migration-$(date +%Y%m%d)/berkeley_housing_v1_schema.sql
   ```

3. Commit backups to git (use git LFS only if dump exceeds 100 MB; otherwise plain git is fine):
   ```bash
   git add backups/
   git commit -m "backup: pre-migration snapshot $(date +%Y-%m-%d)"
   ```

4. Inventory the current schema. Claude Code should produce `docs/migration/v1_column_inventory.md` listing every table, every column, row counts, null counts, and distinct-value counts for string columns likely to become vocabulary references (status, permit_type, etc.). This is the raw material for the migration map.

5. Create the v2 DB file:
   ```bash
   cd /Users/johngage/berkeley-data
   sqlite3 databases/berkeley_housing_v2.db < schema/core.sql
   sqlite3 databases/berkeley_housing_v2.db < schema/vocabularies_berkeley.sql
   sqlite3 databases/berkeley_housing_v2.db < schema/views_compat.sql
   sqlite3 databases/berkeley_housing_v2.db "PRAGMA foreign_key_check;"  # must return empty
   ```

**Phase 0 exit criteria:**
- Three backups exist and are committed.
- `v1_column_inventory.md` documents every legacy column.
- `berkeley_housing_v2.db` exists, schema + vocabularies + views loaded, FK check clean.
- `berkeley_housing_analysis.db` is byte-identical to its pre-phase-0 state.

---

## Phase 1: Vocabulary review

**Goal:** Validate and extend Berkeley-specific vocabulary seeds against the reality of legacy data before any rows are migrated.

**Reversibility:** Trivial. Re-seed vocabularies by dropping and re-executing `vocabularies_berkeley.sql`.

**Steps:**

1. Review every `-- REVIEW:` comment in `vocabularies_berkeley.sql`. Cross-check:
   - `vocabulary_permit_types` codes against actual `permit_number` prefixes in legacy data (`SELECT DISTINCT substr(permit_number, 1, 4) FROM ...`)
   - `vocabulary_permit_status_types` against distinct `status` strings in the legacy flat table
   - `vocabulary_stage_types` against distinct stage/status values
   - `vocabulary_role_types` against developer/architect/owner columns
   - `vocabulary_special_population_types` against HCD APR Table A2 rows produced so far
2. Extend vocabularies as needed. Add rows via `INSERT OR IGNORE` statements appended to `vocabularies_berkeley.sql`; do not mutate existing codes.
3. Produce a **migration map** document at `docs/migration/v1_to_v2_column_map.md`. For each legacy column, specify:
   - Target table and column in v2 (or "dropped" with reason)
   - Target vocabulary table and lookup strategy if the column becomes an `_id` FK
   - Transformation logic (trim, lowercase, parse date, etc.)
   - Handling of NULLs and edge cases

**Phase 1 exit criteria:**
- All `-- REVIEW:` comments resolved (either converted to `-- VERIFIED` or the value updated).
- `docs/migration/v1_to_v2_column_map.md` exists and covers every legacy column.
- Updated `vocabularies_berkeley.sql` re-seeded successfully into v2 DB.

---

## Phase 2: Data migration (authoring + dry run)

**Goal:** Produce `scripts/migration/migrate_v1_to_v2.py` and run it against v2 DB. Verify totals preserve.

**Reversibility:** Trivial. Drop and recreate `berkeley_housing_v2.db`. Legacy DB never touched.

**Migration order (respects FK dependencies and two-pass rule):**

1. **Cities**: ensure Berkeley row exists (already seeded).
2. **Vocabularies**: already seeded; no-op.
3. **Parcels**: one row per distinct APN in legacy data, scoped to Berkeley.
4. **Organizations**: deduplicate by `normalized_name`. Create organization rows from legacy developer/architect/owner columns, applying the normalization function in `scripts/migration/normalize_org_name.py`.
5. **People**: only if legacy data has named individuals (likely rare).
6. **Documents**: one row per distinct document URL in legacy data. Set `url_status = 'unknown'` initially; Phase 3 of the document mirroring subsystem will verify and populate.
7. **Projects** (first pass): insert with `current_version_id = NULL`, `current_stage_type_id` set from legacy status via the stage-code mapping.
8. **Project versions** (first pass): for each project, insert one version with `version_type_id = entitled` (or whatever the legacy flat table most closely represents) and `source_event_id = NULL`. Populate program facts (total_units, height, etc.) from legacy columns. Set `is_current = 1`.
9. **Project-version completion**: `UPDATE projects SET current_version_id = (the version row's id)` for every project.
10. **Unit program**: from legacy unit-mix columns or description parsing. If legacy data doesn't break down by bedroom count, create a single `unit_program` row with `bedroom_count = NULL` flagged in notes — do NOT fabricate. (NOTE: `bedroom_count` is NOT NULL in the schema. For unknown bedroom distributions, use a convention: insert one row with `bedroom_count = 1` and `notes = 'bedroom distribution unknown, placed as 1BR for schema compliance'`, OR relax the NOT NULL constraint. Claude Code to decide during Phase 2 authoring after inspecting actual legacy data.)
11. **Unit program affordability**: from legacy VLI/LI/MOD columns. Map each into `unit_program_affordability` rows.
12. **Project parcels**: link each project to its APN parcel(s).
13. **Project geometries**: from legacy lat/lon, create `centroid_point` geometries. From legacy polygon fields (if present), create `apn_parcel` or `building_footprint` geometries.
14. **Permits**: from legacy permit columns and related permit tables.
15. **Project events**: this is the **interpretive** step. Legacy date columns (`filed_date`, `entitled_date`, `bp_issued_date`, `co_issued_date`, etc.) become `project_events` rows. The mapping is: every legacy date column + project row yields zero or one event row. `asserted_by = 'migration_v1_to_v2'`, `confidence_type_id = high` if the date was from an official source column, `medium` if interpretive.
16. **Project-version second pass**: for each non-proposal project_version, find the matching entitlement event and `UPDATE project_versions SET source_event_id = <event.id>`.
17. **Participants**: join organizations to projects via legacy developer/architect/owner columns → `project_participants` with appropriate `role_type_id`.

**Validation to run after every migration run:**

```sql
-- Counts match
SELECT 'v1 projects' AS src, (SELECT COUNT(*) FROM v1.projects_flat_table) AS count
UNION ALL SELECT 'v2 projects', COUNT(*) FROM projects;

-- Total units preserved
SELECT
  (SELECT SUM(units) FROM v1.projects_flat_table) AS v1_units,
  (SELECT SUM(total_units) FROM project_versions WHERE is_current = 1) AS v2_units;

-- No orphan FKs
PRAGMA foreign_key_check;

-- Every non-proposal version has a source event
SELECT COUNT(*) AS violation_count
FROM project_versions pv
JOIN vocabulary_project_version_types t ON t.id = pv.version_type_id
WHERE t.code != 'proposal' AND pv.source_event_id IS NULL;
-- Expected: 0 after second pass

-- Every project has exactly one current version
SELECT project_id, COUNT(*) AS current_count
FROM project_versions
WHERE is_current = 1
GROUP BY project_id
HAVING COUNT(*) != 1;
-- Expected: empty result

-- Every current geometry is unique per (project, type)
-- (enforced by partial index, but verify)
SELECT project_id, geometry_type_id, COUNT(*) AS n
FROM project_geometries WHERE is_current = 1
GROUP BY project_id, geometry_type_id HAVING COUNT(*) > 1;
-- Expected: empty

-- Sum of affordability + market units equals total_units per project
SELECT
  pv.project_id,
  pv.total_units,
  (SELECT COALESCE(SUM(a.unit_count), 0)
   FROM unit_program u
   JOIN unit_program_affordability a ON a.unit_program_id = u.id
   WHERE u.project_version_id = pv.id) AS affordability_sum,
  ABS(pv.total_units - (SELECT COALESCE(SUM(a.unit_count), 0)
   FROM unit_program u
   JOIN unit_program_affordability a ON a.unit_program_id = u.id
   WHERE u.project_version_id = pv.id)) AS diff
FROM project_versions pv WHERE is_current = 1
HAVING diff > 2;
-- Expected: minimal rows; >2-unit discrepancies flag for review
```

**Phase 2 exit criteria:**
- `scripts/migration/migrate_v1_to_v2.py` runs cleanly end-to-end.
- All validation queries pass (or produce a short, understood list of known exceptions documented in `docs/migration/known_exceptions.md`).
- Total-units preserved within ±0 exact match (if not, every discrepancy is documented).

---

## Phase 3: Reconcile export scripts

**Goal:** `scripts/export_explorer_data.py` and `scripts/generate_kml.py` produce byte-comparable output from v2 DB (via compat views) as they did from v1 DB.

**Reversibility:** Scripts are in git. Revert with `git checkout`.

**Steps:**

1. Update `export_explorer_data.py` to read from `v_projects_flat`, `v_project_unit_mix`, `v_project_affordability`, `v_project_permits` instead of direct table queries on the legacy flat table.
2. Update `generate_kml.py` to read from `v_project_geometries_current`.
3. Run both against v2 DB. Compare output to the last known-good output from v1 DB:
   ```bash
   # v1 output (preserved at last export)
   diff data/exports/explorer_data.js.v1 data/exports/explorer_data.js.v2
   ```
4. Every diff must be explained:
   - Either a legitimate improvement (more complete data now surfaced)
   - Or a bug in the view definition that needs fixing
   - Not acceptable: "we don't know why this row dropped."
5. If a view is missing a column the export script needs, add it to `views_compat.sql`. This is expected; the view definitions were designed from inference, not from actually reading the export scripts.

**Phase 3 exit criteria:**
- Both export scripts run against v2 with no errors.
- All output diffs are explained and acceptable.
- Any necessary view additions are merged into `views_compat.sql`.

---

## Phase 4: Cutover

**Goal:** Make v2 the production database. Preserve v1 as an archive.

**Reversibility:** The archive copy means cutover can be reversed within 24 hours by swapping back. After 24 hours, any further changes only exist in v2.

**Steps:**

1. Stop any scheduled jobs (GitHub Actions, cron) that write to the DB.
2. Make a final snapshot of v1 in its live state (in case it drifted during Phases 1–3):
   ```bash
   cp databases/berkeley_housing_analysis.db \
      archived/berkeley_housing_v1_cutover_$(date +%Y%m%d).db
   ```
3. Rename:
   ```bash
   mv databases/berkeley_housing_analysis.db \
      archived/berkeley_housing_v1_$(date +%Y%m%d).db
   mv databases/berkeley_housing_v2.db \
      databases/berkeley_housing_analysis.db
   ```
4. Redeploy the Datasette instance pointing at the new DB.
5. Redeploy berkeleybuild.com explorer using the regenerated `explorer_data.js`.
6. Redeploy the Fly.io inventory app if it reads from this DB (probably unrelated, but verify).

**Phase 4 exit criteria:**
- `databases/berkeley_housing_analysis.db` is the v2-normalized DB.
- Archive contains the dated v1 file.
- Datasette and explorer site both serve from new DB.
- Spot-check: three arbitrary projects load correctly in the explorer with all expected fields.

---

## Phase 5: Documentation

**Goal:** Write the reference docs now that the schema is proven to work on real data.

**Steps:**

1. `docs/architecture.md`: the four-layer architecture (source → mirror → canonical → derived → presentation), the document mirroring subsystem, the geometry versioning model, the bundle layer, the city-config separation.
2. `docs/project-brief.md`: short, stable, aspirational. Purpose, goals, working principles, license, success criteria.
3. `docs/schema/housing_core_schema.md`: revised from the various drafts in the design conversation, reflecting the final schema as executed. Includes insert order, provenance mixin, validation rules, AMI conventions.
4. Commit a publication snapshot:
   ```bash
   mkdir -p snapshots/post-migration-$(date +%Y%m%d)
   sqlite3 databases/berkeley_housing_analysis.db .dump \
     > snapshots/post-migration-$(date +%Y%m%d)/database.sql
   cp data/exports/*.{csv,json,js} snapshots/post-migration-$(date +%Y%m%d)/
   ```

**Phase 5 exit criteria:**
- Three documents committed and reviewed.
- Post-migration snapshot exists and is tagged in git.

---

## Phase 6: Follow-ups and future work

Not blocking, but tracked:

- `scripts/validate/`: CI data-quality checks. Should include the validation queries from Phase 2 as an automated suite. Runs on every push via `.github/workflows/validate.yml`. Build fails on regressions.
- `scripts/documents/`: the three-tier mirror pipeline (IA, R2, Drive). `discover.py`, `fetch.py`, `mirror_ia.py`, `mirror_r2.py`, `verify_urls.py`, `reconcile.py`. Weekly cron via GitHub Actions.
- `scripts/bundles/build_project_bundle.py`: AI-ready per-project bundle generator.
- `scripts/validate/check_referential_cycles.py`: enforces the two non-SQL-expressible FK rules (the `current_version_id` and `source_event_id` cross-project checks).
- `scripts/validate/check_version_events.py`: enforces the non-proposal-versions-must-have-source-event rule.
- Framework extraction: defer until two or more cities are ready to adopt. At that point, extract universal pieces into a separate repo.
- License decision: commit to Apache 2.0 (code) + CC-BY 4.0 (data) at the top of the project when you're ready. Add `LICENSE` and `LICENSE-data` files.

---

## Insert order reference (for migrate script authors)

This is the dependency graph that the migration script must respect:

```
cities
  └─ parcels
  └─ projects (with current_version_id = NULL)
      └─ documents
      └─ permits
      └─ project_parcels
      └─ project_versions (with source_event_id = NULL, is_current = 1)
          └─ unit_program
              └─ unit_program_affordability
          └─ project_events
              └─ UPDATE project_versions SET source_event_id
          └─ UPDATE projects SET current_version_id
      └─ project_geometries
      └─ project_assets
      └─ project_participants (depends on organizations, people, project_versions)
  └─ organizations
      └─ people
```

---

## Validation queries reference

Collected here for reuse by `scripts/validate/` in Phase 6.

Available as standalone SQL files once Phase 6 begins. For Phase 2 they are inline in the migration script.

- `check_fks.sql`: `PRAGMA foreign_key_check;` — must return empty
- `check_one_current_version.sql`: one `is_current = 1` per project in `project_versions`
- `check_one_current_geometry.sql`: one `is_current = 1` per (project, geometry_type)
- `check_non_proposal_versions_have_source_event.sql`: see Phase 2 above
- `check_affordability_sums.sql`: sum of unit_program_affordability + any unrestricted balance equals total_units within tolerance
- `check_url_status_freshness.sql`: every `documents.url_last_verified` within last 30 days (warn, don't fail)
- `check_orphan_events.sql`: every `project_events` row has non-null `source_type` if `is_inferred = 0` (warn)
- `check_normalized_name_populated.sql`: every organization has `normalized_name` set

---

## Open questions for John before Claude Code executes

1. **Unit program NOT NULL on bedroom_count:** the schema declares it NOT NULL. If the legacy flat table stores total units without a bedroom breakdown (likely for most projects), the migration will need either (a) a placeholder row with a documented convention, or (b) a schema relaxation to allow NULL. **Recommendation: keep NOT NULL, use a placeholder bedroom_count with an explicit "unknown" convention in the notes column.** This keeps the schema honest and forces the eventual enrichment work to be visible as a data-quality gap. Claude Code to confirm approach when inspecting legacy data.

2. **APN data in legacy table:** the parcels table requires APN. Are APNs reliably populated in the legacy flat table? If not, Phase 2 will skip parcel rows for projects missing APN and the `project_parcels` junction will be sparse. That's acceptable but needs to be called out.

3. **Documents in legacy:** are there document URLs already stored, or does the documents table start empty? If empty, Phase 2 creates no `documents` rows, and the `v_project_documents` view returns empty for every project until the document mirror subsystem (Phase 6) is built.

4. **`sfyimby_projects` table in legacy DB:** should it be migrated into the normalized schema, ignored as a separate concern, or kept as a side-table under `data/exports/`? Claude Code to surface this during Phase 0 inventory.
