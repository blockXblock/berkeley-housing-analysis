# Next-Session Priming — 2026-06-01

**First action for a fresh session:** read `CLAUDE.md`, then this doc, then
`git log --oneline -8`. The persistent memory (5 rules) also auto-loads. PROGRESS.md
is stale (2026-05-28) — trust this + the audit docs + git instead.

## Where we are (verify against git/DB before acting)

**The permit-misclassification fix is DONE — committed, NOT pushed.**
- Commit `cb2ba32 fix(v2-db): permit milestone reclassification + group-quarters exclusion`.
- Subsidiary permits (solar/window/sign/water-heater/demo) no longer drive
  BP/CO milestones in `berkeley_housing_v2.db`; `v_projects_flat` was modified
  (`NOT EXISTS` subsidiary exclusion). 32 primary + 74 subsidiary classification
  events written. **Snapshot:** `databases/keep_snapshot_2026-06-01_pre-permit-fix.db`
  (full rollback available; or drop the `source_type='inferred'`/2026-06-01 events
  + restore the view from `/tmp/v_projects_flat_ORIGINAL.sql`).
- Change-note: `docs/audit/2026-06-01_permit_and_group_quarters_fix.md`.
- **2352 Shattuck (id179) and 2440 Shattuck (id176) are HELD** pending Accela —
  do not classify/write them. (NotebookLM confirmed 2352/Logan Park completed
  CY2022–2023 per the city, not 2024 — its 2024 "CO" was an admin solar
  job-card, now subsidiary.)

**APR result after fix + group-quarters:** CY2024 CO ≈ 486 (excl. 2352) / 723
(incl. held 2352); CY2025 ≈ 497. References: city CKAN CY2024 = 708 (clean),
CY2025 = 984 raw → ~482 de-duplicated (the dup problem is in 2025, within-year).

**CO reconciliation conclusion (`docs/audit/2026-06-01_...` arc):** the
486-vs-708 CY2024 gap is **100% scope (Bucket A), 0% recoverable-missing-CO
(Bucket B = 0)**. The ~96 missing units are small ADU/single-unit completions.

## The next build (designed, NOT built): CPRA ADU ingestion
- The 96 Bucket-A CY2024 completions are **in our CPRA file already** (96/96 present,
  95/96 with a 2024 finaled date) — un-ingested, **recoverable**.
- **Schema is ready as-is** (verified). Ingest from PRIMARY sources only:
  CPRA permits (`NumberUnits`, `ADU` flag, dates, `OccType`) + Alameda assessor
  `berkeley.db` (coords + `the_geom` via `normalize_apn`→`apn_norm`, 179/179 resolved).
- **Two fields are unknown from primary** → record "unknown with provenance",
  do NOT fill from CKAN: `unit_program.bedroom_count`, `tenure_type_id`.
- Build it with the snapshot → preview → gated transactional-write discipline.

## Open / deferred (not blocking)
- Push decision: `dev` is ahead of `origin/dev` by 2 (`cb2ba32`, `6897e2e`) —
  awaiting John's review before push.
- Data-landscape dispositions (keep/merge/retire across 40 DBs) — inventory done
  (`docs/audit/2026-06-01_data_landscape_examination.md`), decisions are a
  separate step; nothing executed.
- v2.1 deferrals (workflow-state split, construction substage, classifications
  normalization) — orthogonal to ADU ingestion.
- Earlier-session collateral: T7 reformat + Toshiba archive copy were completed
  and verified last session (separate from the DB work).

## Standing rules (also in CLAUDE.md + memory)
Read-only by default · snapshot+preview+gate before any DB write · CKAN is the
verification target never a source · APN join via `apn_norm`/`normalize_apn` ·
never push without instruction · `/dev/diskN` is volatile (re-verify).
