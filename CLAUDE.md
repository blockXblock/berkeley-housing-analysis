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
   **APNs are NOT stable identifiers** — parcels get **re-platted** and the old APN
   **vanishes from the assessor**, silently orphaning the join (e.g. Acheson
   re-platted to `57-2046-8-4/-9/-11-1`; an APN-join block-sweep would miss the
   308-unit development). **A stale-APN check (project APNs not in current assessor)
   is a STANDING guard before any APN-join analysis**; re-point dead links by
   address/geometry match.
5. **Never commit/push without instruction.** `dev` branch only; no push until
   John says so. Diagnostic docs land in `docs/audit/` (commit-ready, unpushed).
6. **`/dev/diskN` numbers are volatile** — re-verify by stable identity before any
   raw-device/disk op (drives, copies).

## Tool vocabulary (reserved names — never blur)
- **HARVESTER** = the Playwright framework (autonomous, `__doPostBack`/pagination/capID-discovery, bulk inspection + PDF-to-R2 retrieval). The tool for **bulk** Accela extraction. (`scripts/scrape_inspections.py` + `experiments/accela_scrape/inspection_scraper.py` / `url_discovery_scraper.py`.)
  - **A `no-capID` / 0-result is NOT evidence of absence until retried.** These failures are often transient (Accela discovery flakiness) — e.g. 2026-06-15, 5/6 "discovery-failed" large buildings all resolved on a plain retry. **Retry the harvester before concluding a record is missing**, and before escalating to the (more expensive) CIC spot-check. Only a *consistent* post-retry 0-result, or a scrape that returns inspections but no building-final, is a real finding.
- **SCRAPER = CIC = Claude in Chrome** (interactive, near-manual, one-permit spot-checks). The **OPPOSITE** of harvester. Never call a Playwright job "the scraper."
- **CPRA INGESTION** = xlsx-feed → v2 load (not browser-based).

## Merge / dedup discipline (shadows vs real ADU pairs)
- **Soft-retire via `projects.merged_into_id`** (added 2026-06-15) is the STANDING
  merge method. To merge a phantom duplicate into its real survivor: re-point
  **unique-evidence** FKs (events/permits/docs) to the survivor, **delete duplicate
  structural FKs** (the absorbed shares the survivor's parcel/address/geometry —
  re-pointing those would duplicate them), set `merged_into_id = survivor`, and
  `v_projects_flat` filters `WHERE p.merged_into_id IS NULL`. Reversible (the
  absorbed row + its version survive, just filtered out). FK re-point BEFORE retire;
  verify 0 orphans (no evidence/structural FK points to a retired id).
- **SHADOW vs ADU-PAIR RULE (never merge a real building away):** a same-APN +
  same-address + same-units pair is a **shadow** (mergeable duplicate) **ONLY if it
  does NOT have two distinct real permits with two distinct CO dates.** Two real
  `completes/evidentiary` permits + two distinct COs = **two real buildings**
  (main-house + ADU on one lot) — **PROTECT, never merge** (this caught 3 real ADUs
  from erasure 2026-06-15: 624/869, 645/880, 362/888). If units differ (e.g. 73 vs
  66) it is a **CONFLICT**, not a clean merge — report, never auto-merge.

## Structural facts (load-bearing for JN-builders — verified 2026-06-15)
- **`project_events.units_affected` is 100% NULL** → unit-conservation / cross-stage
  unit-drift is **IMPOSSIBLE from events**; `total_units` (versions / `v_projects_flat`)
  is the **ONLY** unit signal. (This is the confirmed root cause D6 was under-powered.)
- **The CO-only import cohort** (~597 projects, contiguous id blocks **185-279 +
  280-899**, single-/two-unit ADUs ingested from CO/CPRA finaled records) has **NO
  lifecycle events** (only `co_issued` + inferred `permit_classified_*`). Any
  event-based **funnel / pipeline-yield / stage-conversion** metric is **MEANINGLESS**
  for them — they invert the funnel (~764 "completed" vs ~57 "permitted"). **A JN must
  segment this cohort out before any funnel analysis.**

## UC student-housing rule (consolidated — primary-sourced)
- UC projects are **IN the total pipeline count but EXCLUDED from RHNA/APR** — UC is
  exempt from city permitting (UC Regents approve, UC issues its own building permit;
  Anchor House FAQ, v2 `documents` id 2178). **Filter on the `uc_project`
  classification flag, NEVER a hardcoded id** (auto-catches the 3 under-construction UC
  towers 165/171/177 when they complete). **UC counted in BEDS, not units, no ratio**
  (proj170 Anchor House = **772 beds** / 244 apartments). The exclusion is applied in
  `generate_apr_v2.py` to all RHNA-counting queries; the pipeline total keeps UC.

## Data-source roles (role-crossing is the circularity bug)
- **HCD CKAN mirror (`hcd_apr_mirror.db`) = ORACLE / reconcile-target ONLY.** NEVER a classification or derivation input. Using "the city's APR agrees" as evidence is **circular**.
- **CPRA permits / Alameda assessor / inspections / permit descriptions = independent inputs** (what we derive FROM).
- **CONSISTENCY / `contested` signals come from independent sources disagreeing — NEVER from CKAN.**

## Canonical file/package locations (verify by `ls`, never assume)
- **`housing_rules` = a PACKAGE at `scripts/housing_rules/`** (`lookups.py`, `classifiers.py`, `__init__.py`, `test_smoke.py`) — **NOT a file** (`ls scripts/housing_rules.py` will mislead). Import: `sys.path.insert(0,'scripts'); import housing_rules`. Committed `7165f3b`; smoke test passes via `python -m scripts.housing_rules.test_smoke`. **Cycle boundary**: 6th-cycle start `2023-01-31` (later cycle owns the shared boundary). **Income tiers**: 5 through 2024, `ACUTELY_LOW` added 2025+. **Projection period is a NARROW window** (6th = 2022-06-30→2023-01-30), not the full cycle span — use `is_projection_period` for RHNA-counted comparisons, not `cycle_for_date`.
- **Canonical DB**: `databases/berkeley_housing_v2.db`. **Completion = `v_projects_flat.co_issued_date`** (verdict-driven), **NOT** `status_code`/stage (`current_stage_type_id` is a separate, drift-prone materialization that no longer drives the published completion display).
- **Served site file**: `docs/explorer_data.js`, generated by **`export_explorer_data_v2.py`** (the v2 script, reads the view). The non-v2 `export_explorer_data.py` is **SUPERSEDED/sequestered** to `scripts/superseded/` — do not run it (it reads raw events and bypasses the verdict fix).

## Architecture decisions (settled — do not re-litigate; full text in `docs/audit/architecture_decisions.md`)
- **ADR-001**: completion-date precedence centralized in `v_projects_flat` (4-tier).
- **ADR-002 SETTLED**: completion verdict **MATERIALIZED** on `permits`, **3-valued** (`completes`/`does_not`/`ambiguous`), overwrite-discipline. **Three-layer guard**: EVIDENCE append-only · VERDICT overwrite · DECISIONS append-only. `completion_verdict_by` carries the **classifier hash** (the staleness query: `verdict_by != current` finds stale verdicts).
- **Current classifier**: `permit_role_classifier @ 112cb03` (committed dev). 8-year verdict layer materialized at this hash.

## .py disposition rule
- **MACHINERY** (runs again) → correct in place.
- **ONE-TIME ops + SUPERSEDED-function scripts** → sequester to `scripts/superseded/` with a provenance banner, never re-run.
- **DATA ERRORS** → a new gated write, **not** a re-run of the old script.
- Sequester only **AFTER** the replacement is live.

## Media disposition rule
- **`.mp4` video outputs are NOT tracked in the repo** — they live on the
  **YouTube channel feeding berkeleybuild.com**. `*.mp4` / `*.mp4.backup*` are
  gitignored. Any stray repo-tracked mp4 (e.g. old `*.mp4.backup-*`) is a stale
  old-approach artifact → delete.
- **KML geometry/tour SOURCE lives in `berkeley-data` and IS tracked**
  (`docs/tours/*.kml`, `docs/kml_versions/*`) — canonical source, not derived.
  A small asset a KML *references* (e.g. `transparent-1x1.png`, the
  hide-default-icon trick) is a tracked **input dependency**; an image
  *rendered from* a KML would be derived → don't track.

## Discipline (every session)
- **Verify artifacts, never trust a summary** (CC's or chat-Claude's) — count rows, check dates, `ls` the actual path before asserting it exists. An empty grep ≠ absence; a `.py` check misses a package dir.
- **Snapshot → read-only preview → STOP-for-John → guarded write** (per-permit `rowcount==1`, verify-or-rollback) **→ fresh-connection fingerprint.**
- **John owns ALL irreversible ops** (push, deploy, Cloudflare purge). Never push/commit without explicit instruction; `dev` only.
- **`/tmp` first** for uncertain work; validate logic as a script before packaging as a notebook.

## State-update discipline (the "keeps updating" mechanism — no always-on agent)
- **At the END of every gated step that changes state, UPDATE `PROGRESS.md`** (current state + next steps) **before reporting to John.** Not optional — it is part of completing a step.
- **When near compaction** (long session, context filling), WRITE current state to `PROGRESS.md` AND the `.claude` memory file FIRST, so rehydration reads ground truth.
- **`CLAUDE.md` changes only when a canonical fact changes** (new ADR, new tool, a sequester) — rare, deliberate.
- **Commit `PROGRESS.md` and `CLAUDE.md` to dev regularly** so they're durable. These files are the canonical source; **memory is not**.

## Where things live
- Notebooks: `00_config … 05_feasibility/`, `04_reporting/` (D5/D6/D7 APR work).
- Scripts: `scripts/` (generators, scrapers, importers), `scripts/migration/`.
- Audit trail (read this for current analytical state): `docs/audit/` — the
  `2026-05-31_*` and `2026-06-01_*` docs are the latest deep arc.
- `PROGRESS.md` exists but may be stale; prefer the dated audit docs + `git log`.

## Current state pointer
**Read `PROGRESS.md` (repo root) first** — it is the live current-state snapshot, updated
at the end of every gated step (see *State-update discipline* above). The dated
`docs/audit/` docs + `git log` are the deeper trail; auto-loaded memory is a hint, not ground truth.
