# CPRA ingestion-script audit — Part 2

**Generated:** 2026-05-22T14:15:18
**Scope:** read-only audit of `scripts/migration/import_cpra_2023_2025.py` and `scripts/cpra_dedup.py`. Includes v2 schema cross-check (columns + indexes only, no row reads).

## 1. Script skeletons

### `scripts/migration/import_cpra_2023_2025.py`

- Lines: **923**

Module docstring (verbatim, lines 1-22):

```
CPRA 2023-2025 Import Script for Berkeley Housing v2

Imports building permit data from CPRA (California Public Records Act) response
into the v2 database. Based on locked decisions in:
  /Users/johngage/berkeley-data/docs/migration/cpra_import_plan.md (§14, §16)

Key decisions:
  - §14.1b: Master permits only (drop sub-permits)
  - §14.2b: Match existing projects + create new R-2 projects ≥5 units
  - §16: Tightened matching (exact StreetNumber + fuzzy StreetName ≥90%)
```

Functions:

| function | purpose |
|---|---|
| `setup_logging(dry_run)` | Configures file + console logger; returns `(logger, log_file_path)`. |
| `normalize_street_name(name)` | Uppercase, strip, drop trailing `ST/AVE/WAY/BLVD/DR/CT/PL/RD/LN`. |
| `normalize_street_number(num)` | Convert any numeric/string variant to integer-string (`'1581.0'` → `'1581'`). |
| `fuzzy_match_address(cpra_addr, v2_addr)` | Exact match on StreetNumber + rapidfuzz `fuzz.ratio` ≥90 on StreetName. |
| `get_v2_projects(conn)` | Loads v2 projects + their parcels' APNs (read-only). |
| `get_existing_permits(conn)` | Returns set of existing `permit_number` values from `permits` (snapshot before the loop). |
| `match_permit_to_project(permit_row, v2_projects, logger)` | First tries exact APN match; falls back to fuzzy address match. Honors `EXCLUDE_PROJECTS = {93}`. |
| `determine_permit_type(permit_row)` | Returns `'demo'` if work_type or description contains DEMO/DEMOLISH/RAZE, else `'building'`. |
| `insert_permit(conn, project_id, permit_row, dry_run, logger)` | The single permit-write site (`INSERT OR IGNORE INTO permits` with `source_system='cpra'`). |
| `insert_permit_event(conn, project_id, permit_id, event_type, event_date, permit_number, dry_run, logger)` | Writes a row to `project_events`. |
| `create_new_project(conn, project_info, dry_run, logger)` | For the 2 hardcoded `NEW_R2_PROJECTS`: inserts row in `projects`, ensures parcel exists, links via `project_parcels`. |
| `validate_import(conn, stats, logger)` | Post-INSERT validation. Checks expected counts (121 new permits, 2 new projects), FK integrity, no NULL `project_id` on cpra rows, **no duplicate permit_numbers**, and finaled_date completeness ratio. Returns `(is_valid, error_message)`. |
| `run_import(dry_run, limit)` | The orchestrating function. Loads CPRA, dedupes, filters to 2023-2025, drops false positives, loops to match+insert, then creates the 2 R-2 projects, then validates and COMMITs/ROLLBACKs. |
| `write_summary_report(path, stats, dry_run)` | Writes a markdown summary alongside the log. |
| `main()` | argparse + entry point. |

Imports: `argparse`, `logging`, `os`, `re`, `sqlite3`, `sys`, `traceback`, `datetime`, `pathlib.Path`, `pandas`, `rapidfuzz.fuzz` (optional), and `from cpra_dedup import load_cpra, dedupe_permits, normalize_apn`.

### `scripts/cpra_dedup.py`

- Lines: **270**

Module docstring (verbatim, lines 1-18):

```
CPRA Permit Deduplication Script

Deduplicates CPRA (California Public Records Act) permit data by grouping
sub-permits with their master permits. Each master permit generates multiple
sub-permits (revisions -REV, deferred submittals -DEF) that carry duplicated
unit counts.
```

Functions:

| function | purpose |
|---|---|
| `normalize_apn(apn)` | Strips non-digits. |
| `extract_master_permit(permit_number)` | Strips `-(REV\|DEF\|ADD)\d*` suffix via regex `^([A-Z]\d{4}-\d{5})(?:-[A-Z]+\d*)?$`. |
| `is_sub_permit(permit_number)` | Returns True if the number matches `-(REV\|DEF\|ADD)\d*$`. |
| `load_cpra(input_path)` | `pd.read_excel(path, header=7)` + adds 5 derived columns: `norm_apn`, `master_permit`, `is_sub_permit`, `IssueYear`, `SubmitDate`. |
| `dedupe_permits(df, filter_func=None, output_path=None)` | Groups by **`(norm_apn, master_permit)`**; for each group, picks the master row (no suffix) or the earliest sub-permit by SubmitDate; returns one row per group with `apn / master_permit / permit_count / units_added / issue_year / issue_date / finaled_date / submit_date / work_type / sub_type / occ_type / description / address / adu_flag / detached / job_valuation`. |
| `dedupe_r2_permits(df, years=None)` | Convenience: filter to OccType contains 'R-2' AND UnitsAdded > 0 AND IssueYear in years. **NOT used by the ingestion script.** |
| `dedupe_adu_permits(df, years=None, construction_only=True)` | Convenience ADU filter. **NOT used by the ingestion script.** |
| `main()` | Standalone CLI: prints R-2 and ADU summary stats per year if no output path. |

Imports: `pandas`, `re`, `sys`, `pathlib.Path`.

## 2. End-to-end data flow trace (from `run_import`)

Step-by-step, with line references in `import_cpra_2023_2025.py`:

1. **Load source** (line 559): `cpra_raw = load_cpra(CPRA_FILE)`. Calls `pd.read_excel(..., header=7)` — **matches Part 1's finding** that row 8 is the header. Adds `norm_apn`, `master_permit`, `is_sub_permit`, `IssueYear`, `SubmitDate`. Yields **14,149 rows × 31 columns** (26 source + 5 derived).

2. **Dedupe** (line 564): `cpra = dedupe_permits(cpra_raw)`. Groups by `(norm_apn, master_permit)`. Output is one row per group; the master row's data is used when available, else the earliest sub-permit. **Sub-permit (-REV/-DEF/-ADD) unit counts are dropped.** Output columns are a transformed subset: `apn, master_permit, permit_count, units_added, issue_year, issue_date, finaled_date, submit_date, work_type, sub_type, occ_type, description, address, adu_flag, detached, job_valuation`.

3. **Filter to 2023-2025** (line 568): `cpra = cpra[cpra['issue_year'].isin([2023, 2024, 2025])]`. Drops rows with `issue_year` NaN or outside the three years.

4. **Drop false-positive permits** (line 573): `cpra = cpra[~cpra['master_permit'].isin(SKIP_PERMITS)]` where `SKIP_PERMITS = {'B2025-03731', 'B2024-05284', 'B2024-04593'}`. Per §16 comment: "inflated unit counts from existing buildings".

5. **Optional `--limit`** (line 580): `cpra = cpra.head(limit)`.

6. **Open v2** (line 585): `sqlite3.connect(V2_DB)` + `PRAGMA foreign_keys = ON`. Read-only loading of `v2_projects` and `existing_permits` happens **before** any transaction begins.

7. **Pre-compute source finaled count** (lines 612-637): walk the filtered `cpra` and the 2 `NEW_R2_PROJECTS`; for each that will be matched, count `finaled_date` non-null. Used later for the validation threshold check (`finaled_date_min_ratio = 0.80`).

8. **BEGIN TRANSACTION** (line 645, non-dry-run only): single-transaction mode; either everything commits or everything rolls back.

9. **Main loop** (lines 652-700): for each row in `cpra`:
    - **Skip-if-exists** (line 659): `if permit_number in existing_permits: continue`. This is the in-Python dedup against pre-existing v2 permits.
    - **Match to project** (line 665): `match_permit_to_project()` tries exact APN, then fuzzy address (≥90%). If `project_id` is None, increment `unmatched` counter and log; **do NOT insert**.
    - **Insert permit** (line 671): `insert_permit()` → `INSERT OR IGNORE INTO permits ...` with `source_system='cpra'`.
    - **Insert issued event** (lines 676-683): `INSERT INTO project_events` with `event_type_id=14 (building_permit_issued)` or `event_type_id=13 (demo_permit_issued)`, `event_date=issued_date`, `permit_id`, `is_inferred=0`.
    - **Insert CO event** (lines 686-693): if `finaled_date` non-null, another `project_events` insert with `event_type_id=17 (co_issued)`.

10. **Create new R-2 projects** (lines 706-768): loop over 2 hardcoded `NEW_R2_PROJECTS`. For each, `create_new_project()` inserts into `projects`, ensures the APN exists in `parcels` (INSERT-or-find), links via `INSERT OR IGNORE INTO project_parcels`, then re-runs the permit + events block inline.

11. **Validate** (line 799): if not dry-run, `validate_import()` checks: post-import counts (`v2_permits_after=239`, `v2_projects_after=181`), FK integrity, no NULL `project_id` on cpra rows, **no duplicate permit_numbers**, `db_finaled_count / source_finaled_count >= 0.80`.

12. **COMMIT or ROLLBACK** (lines 801, 805, 817): all-or-nothing.

## 3. Source → v2 column mapping

(Source columns from Part 1, transformations from the data-flow trace above. "Discarded" rows are loaded but not written to v2.)

| source_column | transformation | v2_table.column | notes |
|---|---|---|---|
| PermitNumber | `master_permit` derived (suffix stripped) by `extract_master_permit` | `permits.permit_number` | The master is what gets inserted; sub-permits (-REV/-DEF/-ADD) are collapsed into the master. |
| Submittal Date | loaded as `SubmitDate` but **discarded** | (none) | `permits.filed_date` is never written — it stays NULL for all cpra rows. |
| Issuance Status | **discarded** | (none) | Constant `'Issued'` in source; row gets `permit_status_type_id=5 (issued)` based on finaled_date presence, not this column. |
| `Unnamed: 3` (spacer) | discarded | (none) | All-null in source. |
| Issuance Date | parsed via `pd.to_datetime`, formatted as `%Y-%m-%d` | `permits.issued_date` + `project_events.event_date` (issued event) | |
| Finaled Status | **discarded** | (none) | Constant `'Finaled'`; status_id is derived from `finaled_date` presence (line 325-328). |
| Finaled Date | parsed via `pd.to_datetime`, formatted as `%Y-%m-%d` | `permits.finaled_date` + `project_events.event_date` (co_issued event) | When non-null: status_id=7 (finaled); when null: status_id=5 (issued). |
| Completed | discarded | (none) | Only 4 non-null rows in source. |
| **Completed Date** | **discarded** | (none) | **All-null in source; script never reads it.** v2's `finaled_date` is populated from Finaled Date, not Completed Date — this is correct given the source state. |
| Parcel Number | `norm_apn` derived (digits only); used for matching | `parcels.apn` for NEW_R2_PROJECTS only (otherwise consumed for matching to existing v2 parcels) | Not written for the standard match path; only for the 2 new R-2 projects. |
| StreetNumber | normalized to integer-string; part of `address` join in `cpra_dedup` | (none directly) | Used for fuzzy matching only. |
| StreetName | normalized for fuzzy match | (none directly) | Used for fuzzy matching only. |
| `Unnamed: 12` (spacer) | discarded | (none) | All-null. |
| StreetType | part of `address` join | (none directly) | Casing duplicates (`St`/`ST`, `Ave`/`AVE`) flow through unchanged. |
| JobValuation | passed through as `job_valuation` | `permits.valuation` | NaN → NULL. |
| WorkDescription | passed through as `description`; also scanned for DEMO keywords | `permits.description`; also influences `permit_type_id` | |
| `Unnamed: 16` (spacer) | discarded | (none) | All-null. |
| **ADU** | passed through to `adu_flag` in deduped DF | **discarded** | Available to the script but not written to any v2 column. Lost in ingest. |
| **Detached** | passed through to `detached` in deduped DF | **discarded** | Available but not written. |
| Work Type | scanned for DEMO keywords | influences `permits.permit_type_id` (5=building or 6=demo) | The literal value isn't stored; only the building-vs-demo classification is. |
| **OccType** | passed through to `occ_type` in deduped DF | **discarded** | Carried as far as the deduped DataFrame; the import script never reads `occ_type`. No normalization applied to the 18 distinct values (incl. 128 `'undefined'`, 3 `'97R3'`, etc.). |
| **SubType** | passed through to `sub_type` in deduped DF | **discarded** | Same. The Mixed Use vs Residential signal is lost. |
| NumberUnits | discarded | (none) | Source unit counts are not propagated to v2 by this script. |
| **UnitsAdded** | summed implicitly in `cpra_dedup` (used in convenience filters, not in main flow) | **discarded** | NEW_R2_PROJECTS hardcodes its own `units` value (13 and 6), so the source UnitsAdded value never reaches v2. |
| UnitsRemoved | discarded | (none) | |
| CO Required | discarded | (none) | |

Computed values written to v2 that don't have a single source column:
- `permits.source_system = 'cpra'` (hardcoded literal at line 359)
- `permits.permit_type_id` ∈ {5, 6} from `determine_permit_type` (line 320)
- `permits.permit_status_type_id` ∈ {5, 7} from `finaled_date` presence (lines 325-328)
- `project_events.event_type_id` ∈ {13, 14, 17} from `permit_type` and date presence
- `project_events.summary = f"{event_type.title()}: {permit_number}"`
- `project_events.is_inferred = 0`

Columns the script could write but doesn't:
- `permits.source_permit_id` (never set — would be useful for Accela cross-ref but no source field is available)
- `permits.filed_date` (Submittal Date is loaded but discarded)
- `permits.source_url` (never set)
- `permits.notes` (never set)
- `project_events.units_affected`, `event_end_date`, etc. (never set)

## 4. Specific risk audits

### 4a. Multi-parcel duplicate handling

Part 1 found **6 PermitNumbers that appear on 2 rows each, with different `Parcel Number` values per row** (e.g., `B2025-05472` × 2 parcels, `B2023-04532` × 2 parcels, etc.). Trace through the script:

- `cpra_dedup.dedupe_permits` groups by `(norm_apn, master_permit)`. Two different APNs ⇒ two different groups ⇒ the **same `master_permit` appears in the deduped DataFrame on 2 different rows** (one per APN).
- The main loop's `if permit_number in existing_permits: continue` (line 659) only checks the **pre-import** snapshot — it doesn't track in-flight inserts during this run.
- `insert_permit` uses `INSERT OR IGNORE INTO permits` (line 355), **but `permits.permit_number` has NO UNIQUE constraint** (verified: only a non-unique index `idx_permits_number`). Without a UNIQUE constraint, `INSERT OR IGNORE` does nothing — it would proceed to insert both rows.
- Each row would resolve to potentially different `project_id` (since the two APNs may map to different v2 projects).
- **Safety net:** `validate_import()` runs a `SELECT permit_number, COUNT(*) ... HAVING cnt > 1` check (lines 474-480). If duplicates exist post-INSERT, validation fails and the **entire transaction rolls back**.

Why this didn't blow up in production (May 11/12 runs): the 6 multi-parcel permits in the source are all small-work permits (furnace changeout, concrete landing replacement, kitchen remodel, etc.) — none of them match any of v2's 179 tracked **multi-unit housing projects** via APN or fuzzy address. They take the "NO MATCH" branch and are never inserted at all.

**Verdict: RISK (latent).** If v2's project set ever expands to include parcels covered by a multi-parcel permit (or a future CPRA includes a multi-parcel permit for an existing v2 project), the import would either: insert duplicates (validation catches → entire transaction rollback) or, depending on which row wins matching, link one parcel only. No silent data loss today, but the `INSERT OR IGNORE` is misleading — the actual safety mechanism is the post-insert validation, not the per-row clause.

### 4b. Completed Date handling

Search the script for `Completed`:
- Neither `import_cpra_2023_2025.py` nor `cpra_dedup.py` reads the `Completed` or `Completed Date` columns.
- `permits.finaled_date` is populated from the source's **`Finaled Date`** column (line 686-693 in main loop and line 733 in the NEW_R2_PROJECTS block).
- This matches the request doc's complaint that "previous response had empty CO Date column" — the script correctly relied on `Finaled Date` (the populated one) instead.

**Verdict: OK.**

### 4c. OccType data quality

Part 1 found 18 distinct OccType values including 128 `'undefined'`, 3 `'97R3'`, 10 bare `'R-2'`, 8 bare `'R-3'`, and 1 self-described `'I-1 Not used, see R-2.1'` system note.

- `cpra_dedup.dedupe_permits` carries `OccType` through as `occ_type` in the deduped DataFrame (line 142).
- `import_cpra_2023_2025.py` **never reads `occ_type`**. (Confirmed by grep: the column name doesn't appear anywhere in the script.)
- The `dedupe_r2_permits` convenience function uses `OccType.str.contains('R-2')` for filtering — but this function is **not called** by the ingestion script.
- Implication: the OccType signal is loaded, carried through dedup, then dropped. No normalization. The `'undefined'` and other data-quality issues never reach v2, but neither does the *clean* R-2 / R-3 signal that distinguishes single-family from multi-unit.

**Verdict: RISK.** OccType is the cleanest housing-type signal in the source (more reliable than parsing WorkDescription) and the script doesn't use it. Single-family permits and multi-unit permits are treated identically by the ingestion path. This may explain why the script must rely on the hardcoded `NEW_R2_PROJECTS` list and the EXCLUDE_PROJECTS set to handle edge cases.

### 4d. Date column semantics

- **Source date columns:** Submittal Date, Issuance Date, Finaled Date, Completed Date (empty).
- **Ingestion reads:** `issue_date` (= source Issuance Date) and `finaled_date` (= source Finaled Date).
- **Ingestion writes:**
  - `permits.issued_date` ← parsed Issuance Date, `%Y-%m-%d`
  - `permits.finaled_date` ← parsed Finaled Date, `%Y-%m-%d`
  - `project_events.event_date` × two events per permit (issued + optional co_issued)
- **Discarded:** `Submittal Date` (loaded but never written → `permits.filed_date` is NULL for all 174 cpra rows).
- **Date-range filter applied:** `cpra['issue_year'].isin([2023, 2024, 2025])`. The 4 source rows with Issuance Date past 2025-12-31 (in 2026) would have `issue_year=2026` and be filtered out here.
- **`filed_date` is never populated for cpra-sourced rows.** This is the data-quality finding I noted earlier in the B-permit URL inventory (1 of 90 has filed_date; the lone non-null was the legacy accela-sourced B2019-05574).

**Verdict: RISK (partial).** Date handling for issued/finaled is correct. But `Submittal Date` → `permits.filed_date` is the natural mapping and is missed. The URL discovery workstream's design sketch notes filed_date is a primary backfill target — but the data is already in the source file and was discarded by the ingestion step.

### 4e. The 14,149 → ~174 reduction (98.8%)

Reduction pipeline (largest drop-off first):

1. **`(norm_apn, master_permit)` dedup** in `cpra_dedup.dedupe_permits` — collapses sub-permits (-REV/-DEF/-ADD) into their masters within each parcel. Source has 14,149 (permit × parcel) rows; output has approximately one row per (parcel, master_permit). Magnitude: collapses thousands of sub-permit rows.
2. **`issue_year ∈ {2023, 2024, 2025}` filter** (line 568). Drops rows whose Issuance Date is outside the three target years (in source: 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2026, plus nulls). Drops on the order of ~1,400 rows based on Part 1's year distribution.
3. **`master_permit ∉ SKIP_PERMITS` filter** (line 573). Drops exactly 3 hardcoded false positives.
4. **In-Python `permit_number in existing_permits` skip** (line 659). Drops permits already in v2 — at the time of the May 11 dry-run, the VALIDATION constants imply 118 were already there. So this skip applies to those.
5. **"NO MATCH" — the dominant filter** (line 694). For each candidate, `match_permit_to_project` tries exact APN against v2's project-parcel set and fuzzy address (≥90% on street name + exact street number) against v2's 179 project addresses. **Permits not matching any of the 179 v2 projects are silently dropped** (incremented in `stats['unmatched']`, not inserted). This is by far the biggest reduction — Berkeley's 2023-2025 building permit universe vastly exceeds the 179 tracked multi-unit housing projects in v2.
6. **VALIDATION constants** confirm the expected post-import counts: `permits_to_insert: 121` (=118 APN match + 1 fuzzy match + 2 from NEW_R2_PROJECTS). Adding the 118 already-existing permits, the post-import permit total is 239 = 118 + 121, matching `v2_permits_after: 239`. The user prompt says v2 has "~174 permits with source_system='cpra'" — close to but not identical to 121 (the new inserts); the discrepancy is likely sub-permit handling outside this script (e.g., subsequent inserts or different audit baseline).

**Verdict: OK.** The reduction is intentional and structured: the script imports only those CPRA permits that map to one of v2's tracked multi-unit housing projects. The dominant filter is the project-matching step, not date or sub-permit filtering.

### 4f. `cpra_dedup.py`'s actual role

- **Dual-use:** standalone CLI (`python cpra_dedup.py input.xlsx [output.csv]`) AND imported library.
- **Imported by** `import_cpra_2023_2025.py:36`: `from cpra_dedup import load_cpra, dedupe_permits, normalize_apn`.
- **What gets called:**
  - `load_cpra(CPRA_FILE)` — line 559
  - `dedupe_permits(cpra_raw)` — line 564, without `filter_func`, without `output_path`
  - `normalize_apn(...)` — called via `get_v2_projects` (line 234) and `match_permit_to_project` (line 257)
- **Convenience filter functions (`dedupe_r2_permits`, `dedupe_adu_permits`, `is_adu`, `is_construction`) are NOT used by the production ingestion path.** They exist for ad-hoc analysis via the CLI.
- **Multi-parcel handling:** `dedupe_permits` groups by `(norm_apn, master_permit)` — this is the design choice that produces the latent multi-parcel risk described in §4a. From the dedup module's perspective the design is sound (parcel-level dedup is what "one project per APN" implies); the risk emerges only when the downstream consumer (the ingestion script) treats the deduped rows as if `master_permit` were globally unique.

**Verdict: OK** (utility module behaves as documented; the multi-parcel risk is in how the ingestion script *uses* its output, not in the module itself).

## 5. v2 schema cross-check

Tables the script writes to: `permits`, `projects`, `project_events`, `parcels`, `project_parcels`.

### `permits` table

- `id INTEGER PRIMARY KEY` — auto-assigned by INSERT.
- `project_id INTEGER NOT NULL` — provided by the script.
- `source_system TEXT NOT NULL` — provided (`'cpra'`).
- `permit_number TEXT` — written; **no UNIQUE constraint** (only `idx_permits_number` which is non-unique). The script's `INSERT OR IGNORE` clause therefore does NOT enforce per-permit uniqueness — the post-insert validation does (see §4a).
- `permit_type_id INTEGER` — written (5 or 6).
- `permit_status_type_id INTEGER` — written (5 or 7).
- `filed_date TEXT` — **never written** by the script; `Submittal Date` available in source.
- `issued_date TEXT` — written.
- `finaled_date TEXT` — written.
- `valuation REAL` — written.
- `description TEXT` — written.
- `source_permit_id`, `source_url`, `expires_date`, `notes` — never written.

### `projects` table

- `id PRIMARY KEY` — auto.
- `city_id NOT NULL` — script hardcodes `1` (line 404). Berkeley = city_id 1.
- `canonical_address NOT NULL` — script provides; **UNIQUE(city_id, canonical_address)** means a re-run that re-creates the 2 NEW_R2_PROJECTS with same addresses would trigger a constraint violation. Mitigation is the existing 'skip if exists' logic plus the all-or-nothing transaction.
- `canonical_name` — script provides (same as address for the 2 new projects).
- Other columns (`latitude`, `longitude`, `current_stage_type_id`, etc.) — left at default for new projects.

### `project_events` table

- `id PRIMARY KEY` — auto.
- `project_id NOT NULL` — script provides.
- `event_type_id NOT NULL` — script provides (13, 14, or 17).
- `is_inferred NOT NULL DEFAULT 0` — script provides `0` explicitly.
- `event_date` — provided; not NOT NULL.
- `permit_id` — provided; **NULL during dry-run** (because `insert_permit` returns None in dry-run).
- `summary` — provided.
- No conflict-handling clause; straight INSERT. Re-running the script after a partial COMMIT would produce duplicate events — but the script's design is all-or-nothing per transaction, so this case shouldn't arise.

### `parcels` and `project_parcels` tables

- `parcels`: `apn NOT NULL`, `city_id NOT NULL`, UNIQUE on `(city_id, apn)`. Script checks-then-inserts (line 412-422) — race-free within a single transaction.
- `project_parcels`: `project_id NOT NULL`, `parcel_id NOT NULL`, `is_primary NOT NULL DEFAULT 0`. Uses `INSERT OR IGNORE` with UNIQUE on `(project_id, parcel_id)` so re-inserts are safely no-op.

No NOT NULL constraints are violated by the script's INSERT shapes.

## 6. Bottom-line findings (verdicts)

1. **Multi-parcel duplicate handling** — **RISK (latent).** `cpra_dedup` emits one row per `(APN, master_permit)`, so multi-parcel permits become 2 deduped rows with the same master_permit. The ingestion script's `INSERT OR IGNORE` is misleading (no UNIQUE on `permits.permit_number`, so IGNORE is a no-op) — the actual safety is the post-insert validation that detects duplicates and rolls back the whole transaction. In production no multi-parcel permits matched any v2 project, so the risk hasn't fired. Would fire if v2's project set expands to cover multi-parcel small-work permits.

2. **Completed Date** — **OK.** The script never reads `Completed Date` (the empty column). `permits.finaled_date` is populated from `Finaled Date` (the populated column), which is correct given the source state.

3. **OccType cleanup** — **RISK.** OccType is loaded by `cpra_dedup` and carried through the deduped DataFrame, but the ingestion script never reads `occ_type` — it's discarded. The 128 `'undefined'`, 3 `'97R3'`, etc. data-quality issues never enter v2 (good), but the *clean* R-2 / R-3 / R-3.1 signal is also discarded (bad — it's the strongest housing-type signal in the source). The script falls back on parsing WorkDescription and matching against the hardcoded `NEW_R2_PROJECTS` list / `EXCLUDE_PROJECTS` set, which is brittle.

4. **Date column semantics** — **RISK (partial).** Issued and finaled dates are handled correctly. **`Submittal Date` is loaded but discarded; `permits.filed_date` is therefore NULL for all cpra-sourced rows.** This is a real gap (the data exists in the source) and matches the URL-discovery workstream's finding that filed_date is missing for 89 of 90 in-scope B-permits.

5. **The 98.8% reduction** — **OK.** The dominant filter is the project-matching step (`match_permit_to_project`): the script only ingests permits that map to one of v2's 179 tracked multi-unit housing projects via APN or fuzzy address (≥90%). Berkeley's full permit universe is many times larger than the tracked-projects set, so most rows correctly drop out. Per the VALIDATION constants, expected new permits = 121 (118 APN + 1 fuzzy + 2 from NEW_R2_PROJECTS).

6. **`cpra_dedup.py`'s role** — **OK.** Dual-use module: standalone CLI for ad-hoc R-2/ADU summaries AND library imported by the ingestion script (which uses only `load_cpra`, `dedupe_permits`, `normalize_apn`). The convenience filter functions (`dedupe_r2_permits`, `dedupe_adu_permits`) are unused in production. Behaves as documented.

7. **Other findings (RISK / UNKNOWN):**
    a. **`permits.source_permit_id` is never written.** This is a missed opportunity — even though the CPRA file doesn't carry Accela's capID triplet, an internal identifier like `master_permit + apn` or a per-row hash could disambiguate the multi-parcel case. **RISK (minor).**
    b. **`permits.source_url` is never written.** Confirms the prior finding that only 2 of 244 v2 permits have a source_url, both `accela`-sourced. The cpra ingestion is the source-of-truth for the 174 cpra-tagged permits but it provides no link back to Accela's UI.
    c. **`stats['source_finaled_count']` pre-computation re-runs the full `match_permit_to_project` loop** (lines 616-625) and *also* the main loop runs it again (line 665). For 14,149 source rows × 179 v2 projects this is `O(N×M)`. The May 11 dry-run took ~3 min per the log timestamps; not a problem at this scale, but the work is duplicated.
    d. **UnitsAdded is discarded by the ingestion path** — only `cpra_dedup.dedupe_r2_permits` (unused) reads it. v2 likely tracks unit counts elsewhere (e.g., `unit_program`); confirming that's populated for these projects is out of scope here but worth flagging for Part 3.
    e. **No `--commit` flag.** The script defaults to live mode (you have to pass `--dry-run` to simulate). Combined with the all-or-nothing transaction, this is fine — but it's the opposite convention from many migration scripts (where commit is opt-in).
