# Permit Reclassification + Group-Quarters Exclusion — 2026-06-01

**First data-modifying operation in the project.** Two *separate* fixes to
`berkeley_housing_v2.db`, gated and snapshotted. Pre-change snapshot:
`databases/keep_snapshot_2026-06-01_pre-permit-fix.db` (1,994,752 bytes, file
sha256 `6df7156c…`, v_projects_flat content-hash `430b2691…`, `integrity_check=ok`).
Analysis basis: `docs/audit/2026-05-31_permit_misclassification_survey.md`.

> **Corrected framing (2026-06-01).** An earlier draft of this note used two
> framings that the CKAN reconciliation later **refuted**. Both are retracted here:
> - ❌ *"corrected CY2024 matches the ~708 reference"* — **wrong**: 486 and 708
>   are **different scopes**, not the same quantity (see below).
> - ❌ *"the city's 708 is inflated by cross-year duplicates"* — **wrong**: the
>   city's CKAN CY2024 CO total (708) is **essentially clean**; the cited
>   "duplicates" are legitimate stage-progression (see "Reconciliation").
>
> The verified framing: **486 is the correct, de-duplicated, group-quarters-
> excluded count of the *major projects we track*; the gap to the city's 708 is
> small ADU/single-unit completions that are *un-ingested CPRA data we already
> hold* (recoverable), not duplicates and not a pipeline error.**

---

## Fix 1 — Permit milestone reclassification (DB write)

**Problem:** ~50% of permits driving `building_permit_issued` / `co_issued`
milestones were minor alteration permits (solar, windows, signs, water heaters,
demolition), over-promoting pipeline stage and inflating APR CO totals (e.g.
2138 Kittredge marked "Permitted" on a $690 bathroom-window permit).

**Mechanism (reversible):**
1. **Classification events** populated in `project_events`: `permit_classified_
   primary` (type 26) and `permit_classified_subsidiary` (type 27), linked by
   `permit_id`, `source_type='inferred'`, dated 2026-06-01. Applied to both BP
   and CO milestone permits.
   - **Initial fix:** 32 primary + 74 subsidiary = **106 events**.
   - **+1 from the 2352 re-anchor** (below) → **current total: 32 primary /
     75 subsidiary = 107 classification events** (verified live).
2. **`v_projects_flat` view updated** so `bp_issued_date` / `co_issued_date` =
   `MAX(event_date)` over milestone events whose permit is **NOT**
   subsidiary-classified. Original view saved at `/tmp/v_projects_flat_ORIGINAL.sql`.
   Manual `NO_DESC` completions (no permit) and HELD projects are kept.

**Rule:** SUBSIDIARY = solar/PV/modules, window/door, sign, water-heater/furnace/
heat-pump, siding/insulation/drywall, remodel, temp-power, meter, washer/dryer,
reroof, shoring/grading, EV-charger, repair (solar overrides the valuation≥$1M
fallback); **leading `demolish/demolition` is a hard disqualifier** (a demo
permit can never be a completion). PRIMARY = new construction / "new …
residence/home/building/ADU" / N-story or N-unit (digit or spelled-out) /
apartment building / valuation≥$1M w/o alteration keyword. 15 AMBIGUOUS were
hand-adjudicated (14→SUBSIDIARY, 1→PRIMARY: 2330 Blake 6-ADU new construction).

**Write-time verification (all passed; else rollback):** 181 rows; 2138 Kittredge
`bp_issued`→NULL (bathroom-window dropped); 2555 College `co`=2025-07-25
(structural kept); 2150 Kittredge `co`=2024-01-01 (manual kept, solar/sign
dropped). One redundant duplicate classification (permit 149, pre-existing from
2026-05-20) was removed.

### 2352 Shattuck (id179) re-anchored OUT of CY2024
NotebookLM + the CKAN mirror confirm the city reports **Logan Park's COs in
CY2022 (127u) and CY2023 (63u) — not 2024.** The record's only 2024 "CO" was
**`B2024-05208`** — an admin *"revised job card … 64 Modules count instead of
63"* (solar). Classified **subsidiary** → id179 `co_issued_date` is now **NULL**
(out of 2024). **`B2440` Shattuck (id176) remains HELD** pending Accela.

## Fix 2 — Group-quarters exclusion (separate, documented counting filter)

**Rule (HCD):** student housing / dormitories cannot count as HCD units. Exclude
`is_uc_project = true` projects from APR unit totals.

| id | project | units | CO'd? |
|---|---|---|---|
| 171 | 2400 Bowditch St | 750 | no (Pre-Application) |
| 177 | 2556 Haste St | 556 | no (Under Construction) |
| 165 | 2200 Bancroft Way | 550 | no (Under Construction) |
| 170 | 1950 Oxford St | 300 | **yes, CY2024** |
| | **total** | **2,156** | only Oxford (300) hits a CO year |

(Same 4 projects the explorer validation flagged = 2,156 *units*; the "~5,250
beds" figure is beds, not units — the 2-beds≈1-unit approximation. Counting
filter at report time, not a data mutation.)

---

## Result — APR CO net-units

| Year | pre-fix | permit-fix | permit + GQ + 2352-out | city CKAN |
|---|---|---|---|---|
| **CY2024** | 1233 | 786 (excl. 2352) | **486** | 708 (clean) |
| **CY2025** | 666 | 497 | **497** | 984 raw → ~482 de-duplicated |

- **CY2024 = 486** is the correct major-project count: permit-fix applied,
  group-quarters excluded (−300 Oxford), 2352 re-anchored to its true CY2022–2023.
- **CY2025 = 497** ≈ the de-duplicated city figure (~482).

## Reconciliation against CKAN — what the gap actually means

A full CO reconciliation (city CKAN ↔ our v2, by APN + address) decomposed the
486-vs-708 gap into buckets:

| Bucket | CY2024 | meaning |
|---|---|---|
| **A** out of scope | **220 u / 96 proj** | small ADU/single-unit completions not in v2 |
| **B** in v2, have BP, no CO | **0 u** | **the recoverable-from-v2 gap — none** |
| **C** wrong year | 0 u | no year-misattribution |
| **D** in v2, correct year | 486 u / 4 proj | we capture these correctly |

- **The 708 is essentially clean in CKAN** (1 trivial within-year dup, +1u). The
  earlier "cross-year duplicate" examples are **stage-progression**, CO in one
  year each: 2150 Kittredge (entitled 2020 → BP 2021 → **CO 2024 only**), 1837
  Berkeley Way (→ **CO 2024 only**), 2555 College (→ **CO 2025**), 2538 Durant
  (**BP 2024, no CO** — city does *not* report it complete). The real within-year
  duplication is in **CY2025** (city 984 raw → ~482).
- **486 is not a "de-duplicated 708"** — it is a clean **major-project subset**;
  the city's 708 is larger because it includes ~220u of small completions our
  pipeline (which targets major projects) never ingested.

### The gap is RECOVERABLE — un-ingested CPRA data we already hold
A follow-up check found **96/96 of the Bucket-A CY2024 completions are present in
our CPRA file** (`data/raw/cpra-downloads/BP_Annual Permit Report-*.xlsx`), **95/96
with a 2024 finaled date.** So Bucket A is not "data we never received" — it is
**un-promoted CPRA permits**, addressable by the planned ADU ingestion (build
from CPRA + Alameda assessor; CKAN stays the verification target). Bucket B = 0
means nothing is recoverable *from within v2* — the recovery is at the raw-CPRA
ingestion layer.

## 2538 Durant → zero CO (intended)
2538 Durant's only `co_issued` event was a "Demolish Apartment Building" permit —
a false completion. After the demolish-disqualifier it has **zero** CO, which is
**correct**: the April field survey lists it *Under Construction (topped out)*.

## Held — pending Accela (NOT classified)
- **2352 Shattuck (id179)** — resolved by NotebookLM/CKAN to CY2022–2023, so
  re-anchored out of 2024 (above). Its underlying 2020 Phase-II BP is unchanged.
- **2440 Shattuck (id176)** — left exactly as-is (solar CO but a 2023 Phase-II
  structural permit); still held.

## Reversibility
Restore the whole DB from `databases/keep_snapshot_2026-06-01_pre-permit-fix.db`
(content-hash `430b2691…`), or drop the `source_type='inferred'`/2026-06-01
classification events + recreate the view from `/tmp/v_projects_flat_ORIGINAL.sql`.

*Committed to dev. The reproducible write script is `scripts/fix_permit_classification_2026-06-01.py`.*
