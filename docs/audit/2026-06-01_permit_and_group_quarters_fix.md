# Permit Reclassification + Group-Quarters Exclusion — 2026-06-01

**First data-modifying operation in the project.** Two *separate* fixes to
`berkeley_housing_v2.db`, gated and snapshotted. Pre-change snapshot:
`databases/keep_snapshot_2026-06-01_pre-permit-fix.db` (1,994,752 bytes, exact
match, `integrity_check=ok`). Analysis basis:
`docs/audit/2026-05-31_permit_misclassification_survey.md`.

---

## Fix 1 — Permit milestone reclassification (DB write)

**Problem:** ~50% of permits driving `building_permit_issued` / `co_issued`
milestones were minor alteration permits (solar, windows, signs, water heaters,
demolition), over-promoting pipeline stage and inflating APR CO totals (e.g.
2138 Kittredge marked "Permitted" on a $690 bathroom-window permit).

**Mechanism (reversible):**
1. **Populated classification events** in `project_events` — `permit_classified_
   primary` (type 26, **32 permits**) and `permit_classified_subsidiary` (type 27,
   **74 permits**), linked by `permit_id`, `source_type='inferred'`, dated
   2026-06-01. Applied to both BP and CO milestone permits (one classification
   per permit covers both its events).
2. **Updated the `v_projects_flat` view** so `bp_issued_date` / `co_issued_date`
   = `MAX(event_date)` over milestone events whose permit is **NOT**
   subsidiary-classified. Original view saved at
   `/tmp/v_projects_flat_ORIGINAL.sql` (restore from snapshot if needed).
   - Manual `NO_DESC` completion events (no linked permit) are **kept**
     (researcher-asserted).
   - HELD projects (179/176) carry no classification → milestones **unchanged**.

**Classification rule (final, adjudicated):**
- SUBSIDIARY: solar/PV/modules, window/door, sign, water heater/furnace/heat
  pump, siding/insulation/drywall, remodel, temp power, meter, washer/dryer,
  reroof, shoring/grading, EV charger, repair. Solar **overrides** the
  valuation≥$1M fallback.
- **Demolish disqualifier:** a leading `demolish/demolition` → SUBSIDIARY,
  overriding structural keywords (a demo permit can never be a completion).
  Anchored to leading text so it does not catch "(See demolition Permit…)"
  cross-references in genuine new-construction permits.
- PRIMARY: new construction / "new … residence/home/building/ADU" / N-story or
  N-unit (digit **or** spelled-out) / apartment building / valuation≥$1M w/o
  alteration keyword.
- 15 AMBIGUOUS were hand-adjudicated (14 → SUBSIDIARY, 1 → PRIMARY: 2330 Blake
  6-ADU new construction).

**Verification at write time (all passed; else rollback):** view returns 181
rows; 2138 Kittredge `bp_issued`→NULL (bathroom-window dropped); 2555 College
`co`=2025-07-25 (structural kept); 2150 Kittredge `co`=2024-01-01 (manual kept,
solar/sign dropped); 2352 Shattuck `co`=2024-12-10 (HELD, unchanged).

**Note:** permit 149 (B2024-00543) already had a subsidiary classification from a
prior session (2026-05-20); the redundant 2026-06-01 duplicate was removed.

## Fix 2 — Group-quarters exclusion (separate, documented)

**Rule (HCD):** student housing / dormitories cannot count as HCD units. Exclude
`is_uc_project = true` projects from APR unit totals.

**The 4 UC/group-quarters projects** (`is_uc_project=1`):

| id | project | units | CO'd? |
|---|---|---|---|
| 171 | 2400 Bowditch St | 750 | no (Pre-Application) |
| 177 | 2556 Haste St | 556 | no (Under Construction) |
| 165 | 2200 Bancroft Way | 550 | no (Under Construction) |
| 170 | 1950 Oxford St | 300 | **yes, CY2024** |
| | **total** | **2,156** | only Oxford (300) hits a CO year |

**Reconciliation:** these 2,156 *units* are the same 4 projects the explorer
validation flagged (2,156). The user's earlier "~5,250 beds across 4 major
projects" is **beds**, not units — consistent with the documented 2-beds≈1-unit
approximation (2,156 units ↔ ~4,300–5,250 beds). Same projects; the gap is the
units-vs-beds representation and does not affect the exclusion (which drops whole
projects). The exclusion is a **counting filter**, applied at report time, not a
data mutation.

---

## Result — APR CO net-units (from re-run `generate_apr_v2.py`)

| Year | pre-fix | permit-only | permit + GQ | ref |
|---|---|---|---|---|
| **CY2024** (holding 2352) | 1233 | 1023 | **723** | ~708 |
| CY2024 (excluding 2352) | — | 786 | 486 | — |
| **CY2025** (holding=excl) | 666 | 497 | **497** | ~482 |

- **CY2024 = 723** (permit+GQ, holding 2352) — **lands near ~708.** ✓
- **CY2025 = 497** (no UC CO'd in 2025) — **lands near ~482.** ✓
- Fix 1 alone: 1233→1023 (CY2024), 666→497 (CY2025). Fix 2 removes Oxford's 300
  from CY2024 (1023→723). The two fixes are independent and separately reversible.

## 2538 Durant → zero CO (intended)

2538 Durant's only `co_issued` event was a "Demolish Apartment Building" permit —
a false completion. After the demolish-disqualifier, it has **zero** CO, which is
**correct**: the April field survey lists it *Under Construction (topped out)*,
i.e. not complete. The fix removed a spurious completion, not a real one.

## Held — pending Accela (NOT written/classified)

- **2352 Shattuck (id179, 237u)** — CO rests on a "revised job card" (admin).
  Holding it keeps CY2024 at 723; excluding it → 486. User verifying vs Accela.
- **2440 Shattuck (id176, 40u)** — solar CO but has a 2023 Phase-II structural
  permit. Left exactly as-is.

## Reversibility

Restore the whole DB from `keep_snapshot_2026-06-01_pre-permit-fix.db`, or drop
the 106 classification events (`source_type='inferred'`, dated 2026-06-01) and
recreate the view from `/tmp/v_projects_flat_ORIGINAL.sql`.

*Committed to dev; not pushed — pending review of this note + the re-run totals.*
