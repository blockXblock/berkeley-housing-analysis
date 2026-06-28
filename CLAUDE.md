# CLAUDE.md — Berkeley Housing Pipeline

Orientation for any session working in `~/berkeley-data`. Verify specifics against
`git log` and the DB before relying on them — this file is a map, not ground truth.

## What this project is
An **independent** reconstruction of Berkeley's housing-production pipeline
(entitlement → building permit → certificate of occupancy), built from **primary
sources**, used to produce/verify the HCD Annual Progress Report (APR) and a
public explorer (berkeleybuild.com) + Datasette.

## Canonical database
**`databases/berkeley_housing_v2.db`** — V2 normalized schema (46 tables):
`projects → project_versions → unit_program(+affordability) → project_parcels →
parcels`, plus `project_events` (timeline: entitlement/BP/CO milestones via
`vocabulary_event_types`), `permits`, `project_classifications`. The flat
compatibility view is **`v_projects_flat`** (what `generate_apr_v2.py` and
`export_explorer_data_v2.py` read).
- **V1 `berkeley_housing_analysis.db`** (flat `projects` table) is frozen/superseded.
- **`databases/berkeley.db`** = Alameda County **assessor parcels** (29,131 Berkeley
  parcels; `APN`/`BOOK`/`PAGE`/`PARCEL`/`SUB_PARCEL`, `the_geom`+`Latitude`/`Longitude`,
  `Imps`/`Land`/`TotalNetValue`, `UseCode`, `LatestDocumentDate`) — a reference store,
  not the pipeline DB. **Refreshed 2026-06-16 (Feb-2026-current data) from data.acgov.org;
  `Imps>0` is the built-signal — see rule 4 for the refreshed schema + 3-layer cross-walk.** ⚠ The
  canonical file is `databases/berkeley.db`; a stray **0-byte `./berkeley.db` at repo
  root is an empty stub** — ignore it (open the `databases/` one).
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
4. **APN cross-walk = 12-digit Alameda APN via the 3-LAYER normalizer (below) — NOT bare
   strip-non-digits.** (`normalize_apn()` strips v2-side digits only; using it alone for the
   cross-DB join gave **890/892 false-dead**, 2026-06-15.) Coords/geometry come from `berkeley.db`.
   **APNs are NOT stable identifiers** — parcels get **re-platted** and the old APN
   **vanishes from the assessor**, silently orphaning the join (e.g. Acheson
   re-platted to `57-2046-8-4/-9/-11-1`; an APN-join block-sweep would miss the
   308-unit development). **A stale-APN check (project APNs not in current assessor)
   is a STANDING guard before any APN-join analysis.**
   - **🟢 THE SINGLE CANON FUNCTION (use this, never a new per-script copy — all 4 consumers import it):**
     **`housing_rules.to_canonical_apn(raw, county)`** (`scripts/housing_rules/apn.py`). UPPERCASE,
     **ALPHANUMERIC-preserving** (APNs are alphanumeric in the general CA case — even Alameda has 25
     letter-APNs, book `48A`/`48H`; **NEVER digits-only**), emits the **OPTION-B STRUCTURE-PRESERVING**
     canonical (per-segment zero-padded, joined by the county's `canonical_separator`): Alameda →
     `057-2046-001-00`, `48A-7075-015-00`. Validates the county's REGISTERED `pattern` from `APN_FORMATS`
     (Alameda `^[0-9A-Z]{3}-[0-9A-Z]{4}-[0-9A-Z]{3,}-[0-9A-Z]{2,}$`; parses the APN STRING, not the
     NULL-prone component columns). **Generality guard:** county #2 = a registry row, not code.
   - **🟢 PARCEL-IDENTITY MVP WRITTEN 2026-06-16 (ADR-003, commit `a94b8e6`):** `parcels` now carries
     **`apn_raw`** (source-faithful, NEVER mutated) + **`apn_normalized`** (the B canonical, enforced by a
     county-scoped trigger) + `assessing_county`. **`parcel_lineage`** records prior→child events with
     `status` candidate/confirmed (the 25 Phase-2 re-points are now `apn_renumber` CANDIDATES, NOT facts —
     lineage stays candidate until confirmed vs a recorded county map). APN ≠ identity; lineage from maps,
     not string patterns. ADR-003: `docs/audit/2026-06-16_ADR-003_parcel_identity_model.md`; grow MVP→TARGET
     additively (`schema/parcel_apn_lineage_schema_TARGET.sql`). proj178 Acheson held (`apn_normalized=NULL`).
   - **THE matcher = the 3-layer cross-walk (all three required, not strip-non-digits):**
     **(a)** assessor hyphen-APN → 12-char segment-pad `book(3)+page(4)+block(3)+sub(2)`
     (`57-2046-1`→`057204600100`); **(b)** v2's OWN apn storage is INCONSISTENT
     (`057 204600100` vs `055-1822-013-3`) — normalize BOTH sides via `to_canonical_apn`; **(c)** address
     matching needs ordinal-word↔number (`SIXTH`=`6TH`) + house-# tolerance. Skipping any layer
     reproduces the 890/892-false-dead trap.
   - **🟢 `berkeley.db.parcels` REFRESHED 2026-06-16 from data.acgov.org** (Alameda Open Data
     Hub Parcels, `services5.arcgis.com/ROBnTHSNjoZ2Wm1P/.../Parcels/FeatureServer/0`,
     Feb-2026 current, 29,131 Berkeley parcels). **It WAS a ≤2019 ArcGIS cache** — note
     `DATE_UPDAT` is a **sparse per-parcel last-change** field (95% null, max 2019), **NOT a
     snapshot date**; the "≤2019" was inferred from zero post-2019 changes, and the proj136
     false-flag arc (an audit re-pointed 17 APNs against the stale cache; **15 rolled back**
     once proj136's stored `057204600100` proved correct) was its cost. Post-refresh: the
     **built-signal is `Imps>0`** (improvement $ value — proj136 = $70.4M; NOT
     `LatestDocumentDate`, which is recording-date and read 2021 for proj136). The
     **stale-reference guard now SHRINKS to the County's own ~weeks–months processing lag**
     for late-2025/2026 recordings (it does not vanish). Re-pull from the same endpoint to
     refresh; the parcel_crosswalk (prior-APN/split-merge lineage) is the queued durable fix.
   - **Stale/wrong APN classes (mismatch ⇒ FLAG-FOR-REVIEW, NEVER auto-re-point):**
     **(1) re-platted** — old APN superseded, new APN AFFIRMATIVELY documented at the exact
     address (Acheson Bldg D `2111 University`→`57-2046-11-1`): the **only** safe auto-
     re-point. **(2) stored-APN-right, assessor-cross-reference-misleading** — corner-lot
     addressed on its other frontage (PERMANENT: County situs `2108 Berkeley Way` persists
     even in the Feb-2026 refresh while Berkeley assigns `1951 Shattuck` — division of
     authority, the refresh does NOT fix it; the corner-lot false-positive rule is permanent)
     OR a stale-cache pre-build (proj136 — dissolved by the refresh): stored APN is CORRECT,
     the assessor lookup misleads → **do NOT re-point.**
     **(3) too-new** — stored APN simply absent from the 2019 snapshot. **Safety rule:**
     **absent-from-assessor → could be re-platted OR too-new; only affirmatively-documented
     re-plats are safe.** Everything else → **John-verify against a CURRENT snapshot.**
     **NEVER blanket-re-point by nearest-address/lat-lon** — it moves units onto a wrong/
     stale parcel. The project's stored APN is PRIMARY data; a re-point derived against the
     stale reference is not.
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
- **The CO-only import cohort** (**713 projects** — MEASURED 2026-06-16 by `scripts/shake_detectors.py`,
  not the earlier stale ~597 estimate; = active projects in id blocks **185-279 + 280-899** with **no
  pre-CO lifecycle event**, single-/two-unit ADUs ingested from CO/CPRA finaled records) has **NO
  lifecycle events** (only `co_issued` + inferred `permit_classified_*`). Any
  event-based **funnel / pipeline-yield / stage-conversion** metric is **MEANINGLESS**
  for them — they invert the funnel. **A JN must segment this cohort out before any funnel
  analysis** (the detector tags them `expected_co_only_cohort`, severity info).
- **`berkeley.db.UseCode` does NOT reliably mark multi-unit housing** (verified 2026-06-16): our
  tracked multi-unit *development* projects sit on **77xx/31xx/32xx/70xx/78xx** parcels
  (commercial/institutional/mixed codes), while **1xxx = single-family and 2xxx = small old
  duplexes** (the existing-stock universe is ~20,734 built-housing parcels). So UseCode is a **weak
  "is-this-housing" signal** — a housing project can carry a commercial code, and a residential code
  rarely marks a tracked development. **Use `Imps`-magnitude (improvement value) as the
  build/scale proxy instead** (`shake_detectors.py` block_cohort/usecode checks do this:
  large-untracked-non-SFR by Imps, NOT a residential-usecode filter).
- **Assessor `Imps=$0` on a CITY-FINALED completion = REASSESSMENT LAG, not unbuilt** (verified
  2026-06-16 on all 6 then-HIGH built_vs_vacant cases — proj134/158/161/174/299/358, 2025 COs):
  a `completes/evidentiary` permit that the City **finaled** proves the building is occupiable
  regardless of `Imps`. **A finaled permit is the built-signal that overrides `Imps=$0`** — the
  completion (and the 703) stands. **Two distinct `Imps=$0`-but-built sub-cases (both NOT unbuilt):**
  **(1) pure reassessment-lag** — new construction not yet reassessed (lags **1–2 years**, longer than
  the detector's 270-day window); **(2) demo→rebuild** — the old building was demolished (a `demol`
  permit zeros `Imps`) and the new build is finaled but not yet posted (proj174, proj208). The
  detector now **weights the finaled permit ABOVE Imps**: completion WITH a finaled `completes`
  permit + `Imps=$0` → `assessor_lag_finaled` / `assessor_lag_demo_rebuild` (low); WITHOUT a finaled
  permit + `Imps=$0` + not-recent → **HIGH** (the genuinely-suspect wrong-verdict candidate).

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
- **`housing_rules` = a PACKAGE at `scripts/housing_rules/`** (`lookups.py`, `classifiers.py`, `apn.py`, `permit_role.py`, `__init__.py`, `test_smoke.py`, `test_permit_role.py`) — **NOT a file** (`ls scripts/housing_rules.py` will mislead). Import: `sys.path.insert(0,'scripts'); import housing_rules`. Committed `7165f3b`; smoke test passes via `python -m scripts.housing_rules.test_smoke`. **The v4 housing-role classifier is `housing_rules.permit_role.classify(work_type, description, adu_flag, occtype, units_added, units_removed, permit_number) -> (role, is_master, note)` (+ `net_units`), lifted here from the build_jn_c cell-string 2026-06-27 (commit `aa6ded0`) to end the June-18 "drift to where nothing imports it" anti-pattern — IMPORT it, NEVER re-define it as a notebook/cell string. Tests: `python -m scripts.housing_rules.test_permit_role` (16 vocab + 9 deflation).** **Income tiers**: 5 through 2024, `ACUTELY_LOW` added 2025+. **RHNA-credit boundary (load-bearing — matches `generate_apr_v2.py`):** a unit is credited to the **6th cycle if its FIRST building permit was issued ON/AFTER `2022-06-30`** (the projection-period START, used as the 6th-cycle lower bound, **NO upper cap before 2031**); before `2022-06-30` = 5th cycle. Credit is on the **BP-ISSUED event, NOT CO/completion**. Use **FIRST-BP issuance = `MIN(non-subsidiary building_permit_issued event)`** per project — **NOT MAX** (the `v_projects_flat.bp_issued_date` MAX field wrongly flips a 5th-cycle-first-permitted project to 6th on a later revision). The `2023-01-31` date is the 6th-cycle **PLANNING-period start** (a DIFFERENT thing from credit-eligibility) — do **NOT** use it for RHNA credit. **`is_projection_period`** (the narrow `2022-06-30→2023-01-30` window) is **NOT** the RHNA-credit filter — credit spans `2022-06-30` through the full cycle.
- **RHNA-BP credit is COVERAGE-LIMITED:** v2 models **~28 tracked projects with a materialized primary BP** vs Berkeley's **hundreds** of housing BPs (the ADU/infill tail is not modeled as projects). So the tracked-project 6th-cycle figure (**1,198 units / 13.4% as of 2026-06-16**) is an **internal lower bound, NOT Berkeley's actual RHNA progress**. The **RHNA PROGRESS BAR is HELD (not published)** — publishing a coverage-limited number as city progress would understate reality. The **full-city-BP-stream acquisition** (Berkeley open-data/Accela BP feed incl. the ADU/infill tail) is the queued prerequisite for a trustworthy bar. **CO-completion metrics (703, the net-new-CO annual tiles, all-time CO 3,611) ARE complete** (full CPRA feed) and remain the trustworthy headline; only the BP-RHNA side is coverage-limited.
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
- **`scratch/` first** for uncertain work (a gitignored, reboot-surviving dir at repo root — use dated subdirs like `scratch/2026-06-19/`; do NOT use `/tmp`, which macOS purges on restart — that cost us a session's builders 2026-06-19); validate logic as a script before packaging as a notebook.

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
