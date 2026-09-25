---
title: Completing the stage model — deemed-complete, inspections, Planning stream, occupancy
date: 2026-09-25
type: audit
status: open
area: docs/audit
---

# Completing the stage model

John's stage sequence, and whether v2 can carry it. **Correction first: I said "v2 models projects
that have a permit." That is wrong.** v2 has `pre_application` and `in_review` stages, and both
2955 Shattuck (74u) and 2455 Telegraph (68u) sit in `in_review` with no building permit. The reason
2336 Dwight is absent is narrower — nothing ingests the Accela **Planning** stream into projects.

`vocabulary_stage_types` already encodes the sequence. Three differences from John's list:
**(1)** v2 merges "submitted awaiting acceptance" and "accepted awaiting entitlement" into one
`in_review` stage; **(2)** v2 has no stage for **actual occupancy** (`completed` = "CO issued *or
equivalent*"); **(3)** v2 adds `stalled` / `withdrawn` as exits.

**The model is right. The transition data is sparse.** Of 1,099 projects, only **17** carry the full
chain application → entitlement → BP → CO. 838 are `completed` but only 106 ever recorded a
building-permit event. Ten event types have **zero rows**, including `first_inspection_observed` and
`final_inspection_passed`.

---

## 1. Deemed-complete — add the stage and the date

**Feasible, and the data is clean.** 160 `application_complete` events across 69 projects,
**0 inferred, 0 Jan-1 placeholders** — confirming the standing convention that event 3 is reliable
where event 2 (`application_submitted`) carries ~100 Jan-1 placeholders.

| year | our projects | HCD Table A (oracle) |
|---|---|---|
| 2024 | 36 | 39 rows / 39 APNs |
| 2025 | 8 | 32 rows / 15 APNs |

**Effect on APR Table A: it would go from empty to working.** Table A is currently a deliberate stub
—`generate_table_a()` runs `WHERE NULL LIKE ?` and returns 0 rows by construction, because
`v_projects_flat` has no `app_complete_date` column. So this does not *change* Table A; it
**creates** it, at roughly **92% coverage for CY2024** and **53% for CY2025**.

Two pieces of work: add `app_complete_date` to `v_projects_flat` (MIN of `application_complete`,
matching the filed_date fix of 2026-07-10), and add a stage between `in_review` and `entitled`.

⚠ **The standing Table A convention is load-bearing** — the date anchor is deemed-complete, NOT
submittal, because ~1,500 units of year-straddling majors land in HCD's reported year only under
deemed-complete. Also queued from that work: 2425 Durant is an HCD cross-year double-count; three
Accela dates still need pulling. Those should land in the same gated write.

## 2. Inspection events — derivable now, and transformative

The `inspections` table already exists: **47,413 rows, 1,206 permits, 625 projects**, running to
2026-09-22. `load_inspections.py` deliberately wrote nothing to `project_events`, leaving derivation
as a separate gated step. This is that step.

| event | today | derivable |
|---|---|---|
| `first_inspection_observed` | **0** | **625 projects** |
| `final_inspection_passed` | **0** | **602 projects** (approved `Building 1200 Building Final`) |
| `construction_start_observed` | 18 projects | — |

That takes the under-construction transition from 18 projects to 625. **This is the single biggest
improvement available**, and it needs no new acquisition.

⚠ Deriving `co_issued_date` from an approved Building Final is a **separate, ADR-changing step** and
must not be folded in. Adding the two events does not change any completion date.

## 3. The Accela Planning stream — the pre-permit pipeline

**15,105 distinct Planning records.** Filtering to housing language and to development record types
(ZP / PLN / DR* / LM* / ZCBP, excluding business licences, home occupations and short-term rentals):
**1,715 records, 2018–2026, ~120–170/year.** **1,231** sit at addresses with no v2 project.

This is what 2336 Dwight needs (`ZP2026-0091`, +8 net units, filed 2026-09-15) and the other five in
`data/reference/missing_multiunit_applications.csv` — 2201 San Pablo (60u), 2330 Prince (23u).

**Decision required before building:** does every housing Planning record become a project, or only
those proposing net new units? 1,231 new projects would more than double the table, and many are
additions and remodels rather than pipeline. Recommend: net-new-unit records become projects; the
rest extend `planning_queue_2026`.

## 4. Actual occupancy — the source exists and is already in hand

**Berkeley Rent Stabilization Board unit registry**, CPRA #26-2375, retrieved 2026-09-21, never
joined: **41,279 registered units** with a `Tenancy start date`, plus **112,353 tenancy-history
rows**, over 11,451 canonicalisable APNs.

Tested against v2 completions of 8+ units since 2023 — **9 of 18 sampled have rent-board units**, and
where they do the unit counts match closely and give a real occupancy date:

| project | v2 units | RB units | CO date | earliest tenancy | occupancy vs CO |
|---|---|---|---|---|---|
| 1951 Shattuck | 163 | 163 | 2024-10-24 | **2024-08-01** | **12 weeks BEFORE** |
| 2527 San Pablo | 63 | 63 | 2024-04-30 | 2024-04-18 | 12 days before |
| 2650 Telegraph | 45 | 45 | 2025-06-16 | 2025-06-20 | 4 days after |
| 2099 M L King Jr | 72 | 71 | 2024-05-17 | 2024-07-01 | 6 weeks after |
| 2701 Shattuck | 57 | 57 | 2024-07-18 | 2024-10-11 | 12 weeks after |
| 2150 Kittredge | 169 | 166 | 2024-03-20 | 2024-07-01 | 15 weeks after |

**Occupancy genuinely differs from CO, by roughly −3 to +4 months.** That is a real, measurable
stage-8 signal and it is a finding in its own right: the date a building is *finished* is not the
date people *live* in it.

**Two cautions.** (a) **Prior units on the parcel contaminate an APN join** — 3030 Telegraph returns
4 rent-board units with an earliest tenancy of **1980-05-31**, which is the building that was there
before. Occupancy must be derived from units registered *after* the BP, not from the parcel's
minimum. (b) Coverage is partial and skewed: ownership units and newly-completed 2025–26 buildings
(1752 Shattuck, 2000 Dwight, 2001 Ashby) are absent, because the registry covers **rentals** and
registration lags.

Other sources considered and rejected: Accela has **no** Certificate-of-Occupancy record type (the
"Zoning Certificate …" matches are unrelated); PG&E connection data is closed by design; assessor
`Imps` lags 1–2 years.

---

## Recommended order

1. **Inspection events** — biggest gain, data in hand, no acquisition, no date semantics changed.
2. **Deemed-complete** — small, clean, and it makes APR Table A exist. Bundle the queued Table A
   reconciliation items.
3. **Occupancy** — join the rent-board registry, deriving from units registered after the BP.
   New `occupancy` stage + `first_occupancy_observed` event.
4. **Planning stream** — largest and needs the scope decision above.

Each is a separate gated write: snapshot → read-only preview → STOP for John → transactional write
with verify-or-rollback → fresh-connection fingerprint.
