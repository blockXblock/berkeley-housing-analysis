---
title: "Machinery and schema audit — scripts, databases, and how they meet"
date: 2026-09-26
type: audit
status: record (read-only diagnosis; nothing written to any DB)
---

# Machinery and schema audit

**Scope.** 304 project `.py` files (≈67,600 lines; `.venv*` excluded), 131 notebooks
(pattern-scanned, not executed), and the schemas of the 29 non-snapshot DB files. The
scripts were read in four partitions; the highest-impact claims below were re-verified
directly against the live DB before being written here.

**Verdict.** The data model has good bones and the working rules in `CLAUDE.md` are sound.
But the rules are enforced in **prose, not code**. Each concept the project depends on
(completion, units, stage, project, address, APN, RHNA cycle, UC exclusion) is re-defined
inside the scripts that consume it, so the published outputs contradict one another. Two
ingests also let the CKAN oracle decide which projects exist. The machinery is not too
large; it lacks a layer between the scripts and the databases.

---

## 1. Contradictions visible in published or publishable output

| # | Concept | Disagreement | Evidence |
|---|---|---|---|
| 1 | RHNA progress | APR JSON carries **2,511 u / 28.1%** (Table B, no cycle boundary) and **1,665 u / 18.6%** (RHNA table, ≥2022-06-30) side by side, while the bar is HELD. Neither honors `--year`. | `generate_apr_v2.py:227` vs `:372` |
| 2 | Affordability tiers | APR Table B hard-zeros LI/MOD ("we have no LI or MOD columns"); the view has them and the Explorer publishes them. | `generate_apr_v2.py:231-234` vs `export_explorer_data_v2.py:150-154` |
| 3 | Completed | Explorer uses `co_issued_date`; KML skyline and legend use `status_code`. **71 projects are stage=completed with no completion date.** | `export_explorer_data_v2.py:276-292` vs `restyle_by_status.py:141`, `sync_status_from_v2.py:53` |
| 4 | Completion placeholder | `2024-01-01` migration stub still surfaces through view tier 4 (proj137, 2000 University, 82 u). Explorer/APR filter it; pipeline-state and players pages don't. | `gen_pipeline_state_page.py:61`, `gen_players_page.py:37` |
| 5 | Stalled | Three definitions: entitled+no BP (APR); entitled >36 mo + no BP (Explorer); stage=='stalled' (Explorer :351). | `generate_apr_v2.py:470-480`, `export_explorer_data_v2.py:270,351` |
| 6 | Completed units 2018–25 | v2 **4,225** · v3 **4,310** · v4 **4,229** — three definitions of completion and units. Public text also cites 2024 = 783 (v3), 709, and 612 (live v2). | `test_s9_gate.py:55`, `build_jn_k.py:4`, `build_jn_open_data.py:175` |
| 7 | Pipeline binning | Players page claims "same binning" as pipeline-state page but lacks the inspection overlay and bins "unstated" differently. | `gen_players_page.py:29` |
| 8 | Master permit | `cpra_dedup` treats `-ADD` as a child; `permit_role` does not; v4 has a third rule. v3 and v4 dedup differently. | `cpra_dedup.py:42-50`, `permit_role.py:98` |
| 9 | Net units | Two incompatible `net_units` (v3 predicates vs `housing_rules`), plus "Rule C" copies in ingests and `units_for` in the 2026 ingest. | `build_v2/housing_predicates.py:42`, `permit_role.py:144` |
| 10 | Application date | Master Log and Planning ingests both write `application_submitted` for the same record; 73 pairs are doubled, 16 with different dates. `filed_date = MIN` picks whichever is earlier. | `ingest_master_permits_log_2026.py:137`, `ingest_planning_scope_a.py:86` |

## 2. Circularity (the rule: CKAN verifies, never derives)

- **CKAN chose which projects exist in v2.** 413 projects carry the event
  *"Permit classified PRIMARY (CKAN-anchored …)"*. The ADU ingests built their candidate set
  from `hcd_apr_mirror.table_a2`, and CPRA only filled in fields. Their provenance strings
  say "primary sources only". A later match against the city's APR is therefore partly true
  by construction. (`adu_ingest_cy2024_2026-06-01.py:26-32`,
  `adu_ingest_cy2023_preview_2026-06-03.py:62-76`, `prepolicy_adu_solid_2026-06-03.py:58-75`,
  `write_op1234_cy2025_2026-06-01.py:61-81`.)
- **A unit count written from CKAN:** proj91 `total_units=45`, labelled in the script itself
  as "CKAN-DERIVED" (`cy2023_pass2_corrections_2026-06-03.py:35-40`).
- **A classifier tuned against the oracle:** `permit_role` RULE 5.5 was "validated vs HCD APR
  oracle". The v4 prototype score adds confidence when a parcel appears in CKAN.
- **v3 is not independent of v2.** S0 builds its match index from v2, and S1/S3/S4/S5 read
  v2 units, events, descriptions and documents. So S8's "v2 vs v3" is partly v2 against
  itself.
- **Correct oracle use exists** (`oracle_watch`, `build_jn_e`, `eval_cpra_2026_accuracy`,
  `reconcile_apr_vs_city`, `export…get_city_apr`), so the right pattern is already in the repo.

## 3. Fragility and hazards

**Hazards: running these would damage data.**
- `migration/migrate_v1_to_v2.py:98-101` **unlinks the live v2 DB** and rebuilds it from a
  36-table schema that has none of `merged_into_id`, `completion_verdict` or
  `apn_normalized`. It is not sequestered.
- `04_reporting/D2_dashboard_data_export.ipynb` overwrites the published datasette DB with
  v1 CSV data.
- `parcels_active_housing_permits.ipynb` and `permitpipeline.ipynb` replace tables in
  `berkeley.db` and `accela_reports.db`.
- `update_housing_data.py` overwrites `housing_projects_FINAL.csv` and the v1 `projects` table.
- Dead scripts (`extract_fees.py`, `parse_attachments.py` and others) connect to
  non-existent paths. `sqlite3.connect` would silently create empty stray DBs.

**Integrity defects in live v2** (verified 2026-09-26):
- **185 parcels have `assessing_county='alameda'`** (lowercase, from `ingest_cpra_2026.py:51`).
  The canonical-APN triggers fire only on `'Alameda'`, so the guard never ran on these rows.
- **Classifier stamps are mixed:** `@112cb03` ×977, `@4eb77df+cpra_2026_ingest` ×70 (but
  4eb77df is `housing_rules.permit_role`, a *different* classifier), 3 suffixed variants, and
  150 NULL. ADR-002's staleness query cannot work across these.
- **4,723 inspection rows (183 permits) have NULL `project_id`** although their permits now
  exist. The link is resolved once, at load time, so these permits get no inspection events.
- **287 events now have `units_affected`.** CLAUDE.md's "100% NULL" structural fact is stale.
- **The 2026 CPRA ingest cannot safely run over all five files as written.** It reads one
  hardcoded file, its `have` set is not updated within a run (duplicates across files would
  insert twice), it drops rows with no APN silently, and its dry-run writes CSVs.
  PROGRESS.md's "additive and safe" is not true of the current code.
- **Preview ≠ commit** in both 2026 ingest pairs. The reviewed numbers cannot equal what was
  written. Only `preview_stage_from_events.py` shares one code path for preview and apply.

**Fragility**
- **110 scripts hardcode `databases/berkeley_housing_v2.db`** (81 literal occurrences),
  there is no config module, and several hardcode *named snapshot* files.
- **Vocabulary ids are hardcoded** (`UC_CLASSIFICATION_ID=6`, event ids 17/26, stage id 6), and
  **UC project ids `(165,170,171,177)` are hardcoded** in five writers. The rule is flag, not id.
- **Frozen expected totals** are asserted in the one-time writers and v3 gates (4310, 568,
  631/709/216…). None would pass today.
- **`/tmp` dependencies:** view rebuilds read `/tmp/v_projects_flat_ORIGINAL.sql`, and
  queues default to `/tmp`.
- **Production imports `experiments/`:** 11+ live scripts import
  `experiments/accela_scrape` through cwd-relative `sys.path` hacks.
- **Notebook logic lives in string literals,** and one generator regex-parses another
  generator's *source* to recover a constant (`build_jn_d_viz.py:28,79`).
- **Stale in-code docs:**
  - Scripts point readers at the superseded exporter (`export_explorer_data_v2.py:13,996`).
  - `generate_apr_v2.py:329` says the view uses MAX (it uses MIN).
  - `permit_role.py` still claims "behavior-identical" and "prose-blind", and lists a consumer
    that does not exist.

**Duplication count.** Every "single source" in `housing_rules` has live rivals:

| Concept | Shared home | Live re-implementations |
|---|---|---|
| APN | `to_canonical_apn` | digits-only `normalize_apn` in `cpra_dedup` (**imported by live ingests** and v3); 6 × `napn`; `block_headroom.apn_key`; ~15 `canon()` wrappers that swallow the county guard |
| Address | `normalize_address` | **≥14 copies**, all different; none of the migration ingests use the shared one |
| Completion | (none in `housing_rules`) | `permit_role_classifier` (v2 verdict), v3 S2/S3, v4 roles, middle-housing tracker, reconcile_project_status, LLM scripts |
| RHNA boundary | `rhna_credit_cycle` | only v3 calls it; APR, apr_hcd and verify scripts re-type `'2022-06-30'` |
| UC exclusion | `uc_project` flag | re-typed SQL ×4, id `6` ×2, id list ×5 |
| `2024-01-01` stub | view tiers 1–3 | re-filtered in 6+ consumers; tier 4 leaks it |

---

## 4. Schema coherence

### The DB files (29, excluding `keep_snapshot_*`)

| Role | Files | Assessment |
|---|---|---|
| Canonical | `berkeley_housing_v2.db` | Good normalized core (projects → versions → unit_program → affordability; events; permits; parcels). |
| Tracks | `v3.db` (32 `s0_…s9_` stage tables), `v4.db` (27 tables, **25 empty**; 82,923 events) | v3 persists pipeline scratch as a DB; v4 is a designed schema half-built. |
| Parcel reference | `berkeley.db` (`parcels` **and** `parcels_arcgis`, `addresses_arcgis`, zoning, licenses, corridor tables), `parcel_facts.db` (assessor roll, owners, transfers), `accela_reports.owner_enrichment` | Parcel and owner facts live in **four** places, plus v2 `parcels`, `project_assessed_value` and `owner_current`. |
| Oracle | `hcd_apr_mirror.db`, `hcd_apr_mirror_2026-06-17_fresh.db` | Consumers disagree on which one (pinned vs newest-by-glob). |
| Work queues | `cic_recon_queue*.db` ×4, `co_inspection_queue*.db` ×3 | Operational state spread across dated files. |
| Legacy | v1 `berkeley_housing_analysis.db` (+2 pre-copies), `berkeley_address_centric.db`, 9 dated `v2_*` copies | Should be snapshots or archive, not peers. |

### Inside v2: where it is duplicative, confused or contradictory

1. **Stage lives in at least four places with different vocabularies.**
   - `projects.current_stage_type_id` (8 codes)
   - `project_stages` (its own CHECK vocabulary: `submitted`, `deemed_complete`,
     `construction_start`…, **not** an FK to the stage vocabulary; it also carries a
     denormalized `apn_norm`)
   - `co_issued_date` derived in the view
   - the new 7-rung script

   Result: **71 "completed" projects have no completion date.** `project_stages` says 722
   completed and 764 permitted, and the flat view says 839 and 139.
2. **Evidence and interpretation share one table.** `project_events` holds both observations
   and inferences: **707 of 813 `co_issued` events are inferred**, and all 738
   `permit_classified_primary` rows are classifications stored as "events". ADR-002
   separated these for permits; it was never done for events.
3. **The completion definition is written twice inside the view.** The 4-tier precedence is
   duplicated as 8 correlated subqueries (normal and contested), each carrying the
   `'2024-01-01'` literal.
4. **The flat view silently drops a category.** `UNKNOWN` affordability (712 rows, 1,592 u)
   has no column, so ELI+VLI+LI+MOD+market ≠ total for affected projects. *(Correction to my
   earlier summary: active-pipeline "market" units are explicitly `ABOVE_MOD`, not unknowns
   counted as market; the unknowns sit mostly in completed ADU rows.)*
5. **Parcel facts are copied into project rows.** Owner (`project_participants.owner_current`)
   and assessed value (`project_assessed_value`) are *parcel* attributes snapshotted per
   project, while `berkeley.db` and `parcel_facts.db` hold the same facts.
6. **Aspirational empty tables:** `project_assets`, `project_bundles`, `external_system_links`,
   `_audit_migration_log` (0 rows); `people` (7); `structures` (21); `project_addresses`
   covers 175 of 1,106 projects.
7. **Operational tables in the canonical DB:** `planning_queue_2026` and two `_quarantine_*`
   tables.
8. **Weak constraints:** case-sensitive county triggers; text CHECKs instead of FKs;
   "developer" split between `developer_of_record` and `applicant` roles (architects often
   file as applicant).
9. **Project rows are parcel histories.** A parcel's older permits attach to whatever project
   later sits on it (the 1914 Fifth / 2420 Shattuck case). Nothing in the schema scopes
   evidence to a project's own time window; each consumer has to remember to.

v4's design (events plus separately stored classifications) is the most principled of the
three, but it holds no entities. Each track fixes a real flaw in v2 by building beside it
rather than into it, and that is the root of the three-way disagreement.

---

## 5. How scripts should meet databases — recommended architecture

Principle: **definitions live in one place; scripts consume definitions, never re-derive
them; the DB layer enforces the rules the prose currently asks for.**

### Step 0 — make it safe (small, do first)
- Sequester or neuter: `migrate_v1_to_v2.py`, `D2_dashboard_data_export.ipynb`, the v1 writer
  notebooks, `update_housing_data.py`, the dead stray-DB scripts, and the 11 dated one-time
  writers.
- Gated data fixes (snapshot → preview → John):
  - lowercase `alameda` → `Alameda`, with the trigger re-run
  - the proj137 stub
  - re-link the 4,723 orphaned inspections
  - backfill `completion_verdict_by` with true classifier identities
- Fix `ingest_cpra_2026.py` (multi-file input, within-run dedup, dry-run that truly writes
  nothing, the real `classifier_hash()`) **before** the five-file re-run in PROGRESS.md.

### Step 1 — one access layer: `housing_rules.db`
- `connect(role)` where role ∈ {`canonical`, `parcel_ref`, `oracle`, `v4`, `queue`}. Paths
  come from one config file, and connections open **read-only (`mode=ro`) by default**.
- `with gated_write(conn, label) as tx:` codifies the existing ritual: snapshot, integrity
  check, transaction, a caller-supplied verify, rollback on failure, fresh-connection
  fingerprint. Preview and commit call the **same function**, with `commit=False|True`.
- `vocab(conn, 'event_types', 'co_issued')` looks ids up by code. No integer ids in scripts.
- The oracle connection returns a read-only handle that write helpers refuse to accept.

### Step 2 — one definitions layer
- **SQL definitions as named views in v2**, which consumers read and never re-implement:
  - `v_completion` (one tier function, stub excluded at every tier)
  - `v_first_bp`
  - `v_rhna_credit` (cycle from first BP)
  - `v_stage` (derived from evidence; retire `project_stages` and the materialized
    `current_stage_type_id`, or regenerate them from the view)
  - `v_units` (including UNKNOWN)
  - `v_is_uc`
- **Python definitions in `housing_rules`**: `completion_verdict` (move
  `permit_role_classifier` in, with one hash), one `net_units`, one `master_permit`, one
  `normalize_address`. Delete the rivals.
- **A contract test** (`test_no_redefinitions.py`) fails CI if any script outside
  `housing_rules`:
  - contains `'2022-06-30'` or `'2024-01-01'`
  - defines `normalize_address`, `napn` or `normalize_apn`
  - hardcodes a vocabulary or UC project id
  - imports `experiments.`

### Step 3 — separate evidence from interpretation (apply ADR-002 to the whole DB)
- **Evidence tables are append-only**, each row carrying a `source` from {cpra, accela,
  assessor, inspection, human} (permits, inspections, observed events, documents, parcels).
- **Classifications live in one table:** subject, kind, value, classifier_hash, and the
  evidence ids used. Stage, completion, role and "primary permit" all go here. They can be
  regenerated, and staleness is one query.
- **A trigger rejects `source='ckan'` on any evidence or classification write.** The oracle
  then physically cannot become an input.
- The 413 CKAN-selected projects need an independent CPRA/assessor basis, re-established or
  flagged.

This is v4's design applied to v2. **Fold v4 into v2 as its evidence layer rather than
maintaining a parallel DB.** v3 then becomes the curriculum pipeline that imports the same
`housing_rules` and rebuilds *without* reading v2.

### Step 4 — one pipeline, not 300 entry points
- A small runner (`make` or `python -m housing.pipeline`) with registered, idempotent steps:
  `ingest:*` → `classify` → `publish:*`. Every publisher reads only views, and **all
  publishers run from the same DB state in one invocation**, so the APR, the Explorer, the
  KML and the state pages cannot drift apart.
- **A cross-output agreement test**, anchored to invariants: the APR's RHNA figure equals the
  Explorer's, and the "completed" count agrees across the Explorer, KML and state pages.
- **Folder layout:**
  - `scripts/` = pipeline steps and tools
  - `scripts/superseded/` = everything one-time
  - the harvester promoted out of `experiments/` into a package
  - notebooks read-only against published views; one-time writes live only in the
    `corrections/` ledger

### Step 5 — consolidate the DB estate
- One **parcel reference** DB: merge `berkeley.db`'s parcel, address and assessor tables with
  `parcel_facts.db` and `accela_reports.owner_enrichment`. v2 references parcels by
  canonical APN and stops copying owner and assessed value into project rows (serve them
  through a view).
- One **ops** DB for queues. One oracle file per pull (named by pull date, chosen through
  config).
- Move `keep_snapshot_*` and dated copies into `databases/snapshots/` with a retention
  policy.
- Record the resulting roles table in CLAUDE.md and update the stale `units_affected` fact.

**Suggested order:** Step 0 → Step 1 → the contract test from Step 2 (which will
itemize remaining duplication) → views → Step 4 → Step 3 and v4 fold-in → Step 5. Steps 0–2
are mostly mechanical and would remove most of the public contradictions in §1.
