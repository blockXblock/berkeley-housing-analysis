# project_stages — Per-Project Pipeline Timeline (derived layer) — 2026-06-06

**Ninth & tenth data-modifying operations** (additive table + spot-check correction). Adds a
derived, isolated **`project_stages`** table holding per-project stage dates for the pipeline
animation — built entirely from data already on hand. **No completion counts changed** (verified
byte-identical), because the table is not referenced by `v_projects_flat`.

## What was written
`project_stages(id, project_id, apn_norm, stage, stage_date, source, confidence, permit_id, note)`
- `stage ∈ {submitted, entitled, permitted, completed}` · `confidence ∈ {high, apn_fallback, low}`
- **1,720 rows** across 885 projects, populated from existing sources only:

| Stage | Projects | Source | Note |
|---|--:|---|---|
| Submitted | 169 | `planning_scrape` | prior Accela Planning scrapes |
| Entitled | 59 | `planning_scrape` | prior Accela Planning scrapes |
| **Permitted** | 767 | `cpra_bp_issue` (766) + `v2_bp_event` (1) | **BP-issue date from CPRA files — same rows we already use for the finaled/CO date** |
| **Completed** | 725 | `v2_co` | the canonical counted CO (`v_projects_flat.co_issued_date`) |

Completed = 725 (not 746): the 21-row gap is subsidiary-only CO events correctly excluded from
completion counting — the timeline uses the same definition as the CO logic.

**Timeline completeness:** full all-4 = 11 · 3-of-4 = 25 · 2-of-4 = 755 (the Permitted+Completed
bulk) · 1-of-4 = 91 · 0 = 3.

## Spot-check of the 5 `apn_fallback` Permitted dates (all resolved → apn_fallback now 0)
The APN fallback (any "New" permit on the parcel) can mis-pick on multi-permit parcels. Checked each
against all New permits on the parcel:
- **proj136 (1951 Shattuck) — CORRECTED.** Fallback grabbed **B2021-05057** (*"Grading, shoring,
  excavation"* = site-prep). Real structural permit is **B2019-05608** (*"Phase 1… Basement and first
  floor,"* 163u). Permitted date 2022-06-08 → **2022-09-08**, confidence → `high`.
- **proj169 (3020 San Pablo) — DATE REMOVED.** Only permit on parcel is the legacy **B2015-00694**
  (no final, no units, below the CPRA 2018 horizon) — the same permit previously found unverifiable.
  Per "don't carry the bad date": `stage_date = NULL`, confidence → `low`, note records why.
- **proj77 / proj138 / proj175 — CONFIRMED `high`.** B2020-01978 (New Detached ADU), B2021-03950
  (72-unit New Mixed Use Building), B2014-05752 (the parcel's 36-unit building) — each is the
  project's primary structural permit. Re-labelled `high` with a spot-check note.

## The real gap (for the Chrome enrichment)
**Permitted and Completed are filled from data on hand; the genuine gap is Submitted + Entitled**,
which live in the Planning record (not building permits). 705 completed projects lack both. The
missing units concentrate in **~10 private majors (≥15u)** — the focused Chrome target — e.g.
2100 San Pablo (96u), 2590 Bancroft (87u), 3000 San Pablo (78u), 2352 Shattuck South (69u),
2527 San Pablo (63u), 2701 Shattuck (57u), 2067 University (50u), 2023 Shattuck (48u), 2028 Bancroft
(37u), 1717 University (15u). (proj170 / 1950 Oxford 300u is UC group-quarters — excluded from
counts, low enrichment priority.)

## Gated-write record
- Pre-snapshot `keep_snapshot_2026-06-06_pre-project-stages.db` (**0371c3be**).
- Write 1 (create + populate): verify — inserted 1,720, CO fingerprint unchanged, FK=0, integrity ok
  → committed. SHA → **eede96a1**. Snapshot `keep_snapshot_2026-06-06_post-project-stages.db`.
- Write 2 (spot-check correction, 5 rows): verify — rows 1,720→1,720, CO fingerprint unchanged,
  apn_fallback 5→0 → committed. SHA → **10a87a8b**. Snapshot `keep_snapshot_2026-06-06_post-stages-spotcheck.db`.

## Reversal
Restore: `cp keep_snapshot_2026-06-06_pre-project-stages.db databases/berkeley_housing_v2.db`
(removes `project_stages` entirely; completion logic untouched regardless).

*Push held. project_stages is a derived timeline layer; CO counts (2018-2026) unchanged throughout.*
