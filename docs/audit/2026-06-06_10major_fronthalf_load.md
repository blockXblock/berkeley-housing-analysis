# 10-Major Front-Half Load + project_stages schema widening — 2026-06-06

**Eleventh data-modifying operation.** Loaded Chrome-verified, BP-cross-checked front-half stage dates
(submitted / deemed_complete / entitled) for the 10 private major completions, and widened the
`project_stages` CHECK constraints to support the front-half model. Pre-snapshot
`keep_snapshot_2026-06-06_pre-10major-fronthalf.db` (**10a87a8b**). Canonical after: **`6ed8e01c`**.
Post-snapshot `keep_snapshot_2026-06-06_post-10major-fronthalf.db`.

## What changed
- **Schema widening** (table recreate, 1,720 existing rows preserved):
  - `stage` CHECK += **`deemed_complete`**, **`construction_start`** (was submitted/entitled/permitted/completed).
  - `confidence` CHECK += **`approximate`** (was high/apn_fallback/low).
- **+30 rows** (submitted + deemed_complete + entitled × 10), `source='planning_scrape'`. Coverage:
  submitted 169→**179**, entitled 59→**69**, **deemed_complete 0→10**.

## The 10 majors (verified table; APN-keyed)
2100 San Pablo (467), 2590 Bancroft (404), 3000 San Pablo (168), 2352 Shattuck S (887),
2527 San Pablo (228), 2701 Shattuck (219), 2067 University (466), 2023 Shattuck (380),
2028 Bancroft (403), 1717 University (428). Data-quality notes carried on the rows:
- **219** — `entitlement_type=design_review_only`; no Use Permit (prior UP2012-0039/70u DENIED);
  DRCF2020-0004 is the entitlement.
- **228** — appealed; entitled = **City Council 2018-01-23** (staff decision was 2017-07-27).
- **403** — submitted+deemed_complete `confidence=approximate` (retroactive "updating open record"
  entry; Case-Closed timestamp precedes submission); entitled = Staff Decision 2019-02-27 (reliable).
- **428** — note: entitled for 28u (ZP2016-0101), **built 15u** (BP B2020-00206) — entitled>built gap.
  Completion count unchanged (15u, matches BP+APR).
- **887** — entitlement ZP2018-0135 covers full 237u North+South; this row = South 69u phase.

## Verification (committed because all passed)
- **survive-the-rebuild:** the 1,720 pre-existing rows are byte-identical after the table recreate.
- **+30 rows** (1,720→1,750); deemed_complete=10; FK violations=0; integrity=ok.
- **CO completion fingerprint byte-identical** — CY2023=701, CY2024=709, CY2025=531, CY2026=216,
  2018-22 unchanged. project_stages is not referenced by `v_projects_flat`; completion logic untouched.

## Reversal
Restore: `cp keep_snapshot_2026-06-06_pre-10major-fronthalf.db databases/berkeley_housing_v2.db`
(reverts the schema widening + the 30 rows; completion counts unaffected regardless).

## Next (not done)
- Collected-but-unloaded second tranche: **29 projects** with unloaded entitled dates (incl. 2920
  Shattuck 221u, 2601 San Pablo 223u) + **72** with unloaded deemed_complete, sitting parsed-ready in
  `data/raw/accela_status/` (74 Processing-Status .txt files). 1914 Fifth (257u) has only a PLN pre-app.
- 2435 San Pablo (+41u CY2025) major still pending. construction_start stage now allowed but unused.

*Push held.*
