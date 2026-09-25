---
title: Inspection events derived — and two "withdrawn" projects that are actively being built
date: 2026-09-25
type: audit
status: open
area: docs/audit
---

# Inspection events derived

`scripts/migration/derive_inspection_events.py`, gated by John 2026-09-25. Snapshot:
`keep_snapshot_2026-09-25_pre-inspection-events.db`.

**+1,264 events.** `first_inspection_observed` 0 → **625 projects**; `final_inspection_passed`
0 → **639 events over 602 projects**. Nothing else was touched.

| | before | after |
|---|---|---|
| projects with a construction event | 18 | **629** |
| projects with the build → occupy chain | 9 | **46** |
| full chain application→entitlement→BP→CO | 17 | 18 |

The full chain barely moves because it is now limited by **application (180) and entitlement (59)
coverage**, not by construction. That is what the Accela Planning ingest and the deemed-complete
work address.

## Verification

- **0 completion, BP, filed or entitlement dates changed.** This step deliberately does not derive
  `co_issued_date` from a Building Final; that is ADR-changing and separate.
- **0 projects with a first inspection dated AFTER their CO** — chronologically sound.
- **517 of 552** projects with both signals have their Building Final on the **same day** as their
  recorded CO (median gap 0 days), independently corroborating the existing completion layer.
- Only 7 have a first inspection before `bp_issued_date`, expected while BP coverage is partial.
- integrity ok · 0 FK violations · documents unchanged at 2,255 across 790 projects.

A `GROUP BY ... HAVING MIN(date)` with a bare `permit_number` was replaced with an explicit window
function. It returned the correct permit for all 625 projects, but by SQLite's undefined
bare-column behaviour rather than by the query saying what it meant.

## ⚠ The evidence contradicts the stage field on large projects

The stage was never derived from events, and with construction now visible the disagreements are
concrete. **Two projects totalling 104 units are marked `withdrawn` while inspectors are on site:**

| project | units | stage | inspections | latest inspection |
|---|---|---|---|---|
| **2902 ADELINE St** | 54 | **withdrawn** | 311 | **2026-09-22** |
| **2016 ASHBY Ave** | 50 | **withdrawn** | 32 | **2026-09-16** |
| 1598 UNIVERSITY Ave | 207 | completed (no CO) | 678 | 2026-05-20 |
| 2538 DURANT Ave | 83 | completed (no CO) | 443 | 2026-05-21 |
| 2441 LE CONTE Ave | 65 | completed (no CO) | 3 | 2025-09-25 |
| 1914 FIFTH St | 257 | in_review | 7 | 2017-09-27 |
| 2420 SHATTUCK Ave | 132 | in_review | 25 | 2017-08-03 |

2902 Adeline was inspected **three days ago**. The site currently shows it as withdrawn.

**Not fixed in this write** — moving stages is its own gate. The script carries `--with-stage`,
which today moves only the 4 `permitted` projects that have a first inspection. The larger and more
valuable correction is a **stage derived from the event stream** rather than materialised
independently: `first_inspection_observed` and no completion → `under_construction`; a completion →
`completed`. That would also address the 71 pre-existing projects marked `completed` with no CO date.

**Recommended next:** derive the stage from events as a gated write, listing every proposed move for
review before it is applied.
