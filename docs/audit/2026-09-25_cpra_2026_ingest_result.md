---
title: CPRA 2026 ingest — result and accuracy evaluation
date: 2026-09-25
type: audit
status: open
area: docs/audit
---

# CPRA 2026 ingest — result and accuracy evaluation

Two CPRA productions that had been sitting unloaded in the repo were ingested into v2, gated by
John on 2026-09-25 ("full housing scope" + "ingest intake, re-request the rest"). This records what
went in, what it fixed, **a real regression the evaluation caught and how it was corrected**, and
what is still wrong.

Snapshots: `keep_snapshot_2026-09-25_pre-cpra-2026-ingest.db`,
`keep_snapshot_2026-09-25_pre-masterlog-ingest.db`. Preview:
`2026-09-25_cpra_2026_ingest_preview.md`.

---

## What the BP feed bought us: the classifier stopped guessing

`BP_Annual Permit Report-2025-2026-07-07.xlsx` carries `Work Type`, `OccType`, `ADU`, `UnitsAdded`
and `UnitsRemoved` — the inputs `housing_rules.permit_role.classify` is built for and the Accela
list scrape does not have. Over the same 8,039 rows:

| role | description only | full inputs |
|---|---|---|
| **ambiguous** | **6,651 (82.7%)** | **1,236 (15.4%)** |
| new_unit | 184 | 447 |
| alteration | 0 | 5,018 |
| demolition | 0 | 109 |
| subsidiary | 1,204 | 1,204 |

**Ambiguity 82.7% → 15.4%.** That is the measured value of the columns, and the argument for
extending the CapDetail extractor to capture the same fields for records this feed does not cover.

## The regression the evaluation caught

The first build loaded all 447 `new_unit` rows. Scored against the HCD APR mirror (the verification
target, never a source), **2025 recall went DOWN 1.0 point and one project lost its oracle match.**
Chasing that found two distinct bugs, both mine:

**1. The classifier's ADU rule fires on a flag that means something else.** In this feed `ADU=Yes`
marks a parcel that *has* an ADU, not a permit that *creates* one. Combined with conversion
language, `B2025-03811 "CONVERT EXISTING METER PANEL FROM OVERHEAD ELECTRIC SERVICE"` came back
`new_unit` — with the source's own **`UnitsAdded = '0'`** sitting right there. **100 of 447 rows
were like this**: pools, seismic upgrades, temporary power, a burned bus bar, water lines.

**2. Attaching a later permit to a completed project moved its completion date.** `co_issued_date`
is MAX over finaled events, so a 2026 meter-panel swap on a house finaled in 2018 rewrote that
house as a **2026 completion**. 14 projects had their CO date changed; 5 jumped year, including
**proj483 (122 Avenida Dr): 2018-05-29 → 2026-04-21**. Two of those were genuine later ADUs, which
CLAUDE.md's SHADOW-vs-ADU-PAIR rule says are *separate buildings* — protect, never merge.

Left alone this would have made v2 **wrong** where it had been merely incomplete, which is worse.

### The fixes

- **Veto at the ingest boundary, not in the classifier.** `housing_rules.permit_role` is the shared
  v4 classifier with its own tests; CLAUDE.md says import it, never redefine it. So the ingest
  refuses rows where the source states `UnitsAdded = 0`, and rows where `UnitsAdded` is absent *and*
  the description is plainly non-dwelling work (solar, re-roof, meter, water line, temp power,
  seismic, pool, fence, driveway, permit extension). **121 rows vetoed**, each written to
  `data/reference/cpra_2026_vetoed_zero_units.csv` for review rather than silently dropped — one of
  them (`B2025-02361`, "new two-story mixed-use building with 1 dwelling", `UnitsAdded=0`) looks
  like a city data-entry error and should be re-added as a documented correction.
- **Sibling projects.** When a matched project already has a completion and the incoming permit
  finals later, the permit gets its **own project on the same parcel**, addressed
  `<address> [<permit>]` so it stays traceable. 3 siblings created.

**Verified: 0 projects changed CO year in the corrected build.**

## Where the numbers landed

| | before | after |
|---|---|---|
| permits | 995 | 1,211 |
| projects | 916 | 1,101 |
| project_events | 3,916 | 4,269 |
| **projects with a 2026 CO** | **2** | **45** |
| 2025 CO units | 530 | 588 |

Scored against the APR oracle for 2025: **recall holds at 92.9%**, unit coverage rises
**53.9% → 59.8%** of the oracle's 984.

**Precision reads lower (93.9% → 79.3%) and that is mostly not an error.** The 20 projects we
report as 2025 completions that the APR does not include are largely real and large — **2001 Ashby
(87 units), 2000 Dwight (113), 1367 University (39), San Pablo Ave (40)** — plus genuine ADUs. The
APR is the city's own filing and has its own gaps; against an incomplete oracle, "precision" scores
*agreement*, not correctness. It is reported here rather than hidden, but it should not be read as
20 mistakes.

## The Master Permits Log: thin, and it creates nothing

`2026 Master Permits Log.xlsx` promises unit counts, BMR tiers, density bonus, SB 9 streamlining and
entitlement dates. **Every one of those columns is 100% empty** — measured, not assumed. What
survives is application intake.

So this ingest **creates no projects and no permits**. 514 rows go into a new reference table
`planning_queue_2026`, and `application_submitted` events are added only where a ZP/PLN record with
housing language matches an existing project — **54 events**. A sign-permit application posted onto
a housing project would have landed a bogus application event, and `filed_date` is
MIN(application_submitted), so a bad event moves a published date.

**Re-request queued** (John's call, 2026-09-25): ask the city to populate the columns its own
template defines — New Units, Demolished Units, Total Units, BMR by tier, Density Bonus, Date of
Final Action, Date Permit Effective. Check Gmail `from:nextrequest.com` first; three productions
sat unretrieved Jul–Sep 2026.

## Still wrong, and not hidden

- **2024 units read 1,466 against the oracle's 708 — 207%.** Pre-existing, untouched by this ingest,
  and unexplained. It is the largest single disagreement with the oracle and deserves its own pass.
- **20 rows carry a unit count of 1 as a documented floor** (`floor_new_unit_role`), where neither
  `UnitsAdded` nor `NumberUnits` was usable. Listed in
  `data/reference/cpra_2026_units_needs_review.csv`. A `new_unit` permit creates at least one
  dwelling, so 1 is a floor, not a guess — but it is a floor.
- **8 of 185 new projects have no coordinates** and will not appear on the map.
- **The BP feed ends 2026-07-07.** August and September 2026 completions are not in v2.
- **`bp_issued_date` now populates from 213 new BP-issued events.** The RHNA 6th-cycle boundary
  (first BP on/after 2022-06-30) should be re-checked before any RHNA figure is quoted; the bar
  stays held regardless, since coverage is still partial.
