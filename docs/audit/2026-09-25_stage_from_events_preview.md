---
title: Stage derived from events — preview, and the "Auto-Closed" mis-mapping
date: 2026-09-25
type: audit
status: open
area: docs/audit
---

# Stage derived from events — READ-ONLY preview

`scripts/migration/preview_stage_from_events.py`. Nothing written. Full list:
`data/reference/stage_from_events_review.csv`.

| | |
|---|---|
| projects | 1,099 |
| stage AGREES with the evidence | 1,036 |
| **stage would move** | **16** |
| evidence behind the stored stage (NOT moved) | 15 |
| no dated events, left alone | 47 |

## Two rules the first draft got wrong

**Jan-1 dates are placeholders, not evidence.** The draft proposed moving 2400 Bowditch (1,500
units) and Ashby BART (618 units) out of `pre_application` on the strength of "application
2026-01-01" and "2025-01-01". Those are v1-migration placeholders — the very reason the Table A
anchor is `application_complete`. Now ignored.

**Absence of an event is not evidence the step did not happen.** The draft proposed moving 2449
Dwight *back* from `under_construction` to `entitled` purely because no inspection row exists.
BP and inspection coverage are both partial, so a missing event means unobserved, not absent.
Stages are now proposed **forward only**; the 15 backward cases are reported as coverage gaps.

**And the withdrawal test must use the LATEST inspection.** `first_inspection_observed` records the
*first* one, so 2902 Adeline's 2025-05-28 looked older than its last `project_withdrawn`
(2026-01-23) while inspectors were on site through 2026-09-22. The `inspections` table is now
consulted directly.

## ⚠ The real finding: "Auto-Closed" is being read as "withdrawn"

**Five projects carry 3+ `project_withdrawn` events, every one summarised "Auto-Closed" and paired
with a "Documents Uploaded" status update.** That is Accela closing a document-upload record — a
routine administrative act — not an applicant abandoning a project.

| project | units | auto-closed events | stage shown |
|---|---|---|---|
| 1752 SHATTUCK Ave | 72 | 16 | completed |
| **2902 ADELINE St** | **54** | **14** | **withdrawn** |
| **2127 DWIGHT Way** | **58** | **12** | **withdrawn** |
| **2587 TELEGRAPH Ave** | **52** | **11** | **withdrawn** |
| **2016 ASHBY Ave** | **50** | **7** | **withdrawn** |

**214 units are displayed as withdrawn on berkeleybuild.com because of this.** They are not.
Checked directly against Accela:

- **2902 Adeline** — 311 inspections, the most recent **2026-09-22**.
- **2016 Ashby** — 32 inspections, most recent 2026-09-16.
- **2587 Telegraph** — "Phase 2 Superstructure, concrete floor slabs" (2024-09), enclosed study
  rooms added to *residential common corridors* (2025-05), elevator deferred submittal (2025-06),
  an **off-site leasing office approved 2025-06**, and a **blade-sign permit 2026-09-01**. A
  building with a leasing office and signage is finished or nearly so.

The stage derivation fixes 2902 Adeline and 2016 Ashby because they have inspection evidence. It
does **not** fix 2587 Telegraph or 2127 Dwight, which have none — those need the mapping itself
corrected. **Fixing the Accela status → `project_withdrawn` mapping is more urgent than the stage
derivation**, because it is producing false negatives on the public site today.

## The 16 proposed moves

Largest, for eye-checking:

| project | units | now | proposed | evidence |
|---|---|---|---|---|
| 1914 FIFTH St | 257 | in_review | completed | Building Final 2017-09-27 ⚠ |
| 2420 SHATTUCK Ave | 132 | in_review | completed | Building Final 2017-07-27 ⚠ |
| 2680 BANCROFT Way | 79 | entitled | permitted | BP issued 2024-05-03 |
| 2902 ADELINE St | 54 | withdrawn | under_construction | inspections to 2026-09-22 |
| 2016 ASHBY Ave | 50 | withdrawn | under_construction | inspections to 2026-09-16 |
| 2317 CHANNING Way | 22 | entitled | permitted | BP issued 2025-09-08 |

⚠ **1914 Fifth and 2420 Shattuck need a human decision.** Their Building Finals are on 2015-era
permits finaled in 2017, while both carry large unit counts and recent planning records (1914 Fifth
has PLN2026-0037). The final may belong to an earlier, smaller phase rather than the project the
unit count describes. I would hold both out of any write until checked.

## Recommendation

1. **Fix the Auto-Closed → `project_withdrawn` mapping first.** It is the only one of these
   currently showing readers something false.
2. Apply the 14 uncontested stage moves; hold 1914 Fifth and 2420 Shattuck.
3. Chase the 15 backward cases as coverage gaps, not as corrections.
