# CPRA 2026 ingest — READ-ONLY preview

Generated 2026-09-25 · database opened read-only · **nothing written**

## Current v2 state

| | |
|---|---|
| permits | 995 |
| live projects | 909 |
| newest finaled permit | 2025-12-22 |
| projects with a 2024 CO | 87 |
| projects with a 2025 CO | 98 |
| projects with a 2026 CO | 2 |

## A. BP_Annual Permit Report 2025 → 2026-07-07

**8,039 rows.** Classifier roles **with the full inputs this file supplies**, against the same rows classified from description alone (all the Accela list scrape offers):

| role | full inputs | description only |
|---|---|---|
| alteration | 5,018 | 0 |
| ambiguous | 1,236 | 6,651 |
| demolition | 109 | 0 |
| new_unit | 447 | 184 |
| non_housing | 25 | 0 |
| subsidiary | 1,204 | 1,204 |

**Ambiguity falls 82.7% → 15.4%** — the measured value of the Work Type / OccType / UnitsAdded columns.

### Housing-creating permits (`new_unit`)

| | permits | units added |
|---|---|---|
| total `new_unit` | 447 | +1317 |
| already in v2 | 119 | +1022 |
| **new, matches an existing project by APN** | **24** | +79 |
| **new, NO project in v2** | **304** | +216 |
| — on distinct APNs | 272 | |

APN present on every `new_unit` row: 447/447 — so the crosswalk carries the join and no fuzzy address matching is needed.

- **2025 completions:** 136 finaled housing permits, **+562 units** (35 not currently in v2)
- **2026 completions:** 113 finaled housing permits, **+186 units** (109 not currently in v2)

Largest 2026 completions v2 is missing:

| finaled | permit | units | address | description |
|---|---|---|---|---|
| 2026-04-16 | B2023-06416 | +144 | 3030 TELEGRAPH Ave | Construction of a 5-story, mixed-use building with (144) d |
| 2026-02-24 | B2014-01391 | +2 | 1471 SCENIC AVE | NEW SINGLE FAMILY DWELLING W/ATTACHED ACCESSORY DWELLING U |
| 2026-04-16 | B2020-02735 | +2 | 3411 ADELINE St | Build two-unit, two-story ADU at rear. |
| 2026-03-27 | B2023-04424 | +2 | 1403 CARLETON St | ADU conversion adding 2 units to an existing apartment bui |
| 2026-04-27 | B2024-02481 | +2 | 2021 CHANNING Way | Duplex ADU at rear of lot. |
| 2026-01-29 | B2017-02782 | +1 | 791 HILLDALE Ave | New 407 SF ADU |
| 2026-02-10 | B2019-03876 | +1 | 2918 OTIS St | Raise and remodel existing single family residence; create |
| 2026-04-09 | B2022-00032 | +1 | 655 VISTAMONT Ave | This project is to create a new ground up attached accesso |

## B. 2026 Master Permits Log — the entitlement side

**589 rows over 9 sheets.** These are applications, not permits.

**⚠ This file is far thinner than its headers promise.** Fill rate per column, `ZPs` sheet:

| column | filled |
|---|---|
| Application Number | 100% |
| Application  Type | 100% |
| Site Address | 100% |
| Applicant | 99% |
| Res./Comm/ MU/Public | 100% |
| Description | 100% |
| Date Received | 100% |
| Date  Deemed Complete | 0% |
| Date of  Public Hearing | 0% |
| Date of  Final Action | 0% |
| Date of NOD | 0% |
| Appeal | 0% |
| Date Permit Effective | 0% |
| Design  Review | 0% |
| CEQA Determination | 0% |
| New Units (Y/N) | 0% |
| Demolished Units | 0% |
| Total Units in Project | 0% |
| BMR Units Total | 0% |
| BMR: ELI | 0% |
| BMR: VLI | 0% |
| BMR: LI | 0% |
| BMR: MI | 0% |
| Density Bonus (Y/N) | 0% |
| Waivers | 0% |
| Concessions | 0% |
| Density Bonus % Applied | 0% |
| Streamlining Provision (SB 9, SB 6, AB 2011, SB 4, SB 35) | 0% |
| Preliminary Application | 0% |
| Landmarked? (Y/N) | 0% |
| Status Notes/CLOSED | 0% |

Every column after `Date Received` — the entitlement dates (`Date Deemed Complete`, `Date of Final Action`, `Date of NOD`, `Date Permit Effective`), all unit counts, all BMR tiers, density bonus, waivers, concessions and the SB 9 / SB 6 / AB 2011 / SB 4 / SB 35 streamlining flag — is **100% empty**. The same holds for `Open 2025 ZPs`.

**Correction.** `docs/audit/2026-09-25_tour_grade_data_readiness.md` called this the richest unit/BMR/density-bonus source we hold. That was read off the HEADERS. The data is not there, and that note is corrected. It does **not** close the queued entitlement-event gap either, because the approval dates are exactly what is missing.

| sheet | rows | usable content |
|---|---|---|
| Open 2025 ZPs | 84 | Application Number, Application  Type, Site Address, Applicant, Res./Comm/ MU/Public, Desc |
| ZPs | 74 | Application Number, Application  Type, Site Address, Applicant, Res./Comm/ MU/Public, Desc |
| PLN Pre-App -ZRL-Mills | 167 | Application Number, Application  Type, Site Address, Applicant, Description, Date Received |
| PLN Prelim App- Ministerial | 24 | Application Number, Application  Type, Site Address, Applicant, Description, Date Received |
| Open 2025 PLN ZRL | 134 | Application Number, Pre-App, Application Status, Site Address, Applicant, Project Descript |
| Landmarks | 22 | Project Number, Project Type, Site Address, Description, Date Received, Staff Planner |
| Design Review | 80 | Project Number, Project Type, Site Address |
| SB 684 Map Apps | 3 | Application Number, Map ApplicationNumber, Site Address, Applicant, Description, Date Rece |
| Condo | 1 | Application Number, Application  Type, Site Address, Applicant, Description, Date Received |

**What it is still worth.** 589 application records with number, type, address, applicant and date received — enough to create `application_submitted` events and populate `filed_date` for applications v2 does not know about, and enough to tell us *which* projects are in the planning queue right now. That is real but modest, and it is an intake feed, not an entitlement feed.

## What an ingest would change

- **`permits` 995 → ~1,323** if scoped to housing-creating permits (+328). Loading all 8,039 rows instead would take it to ~8,915, mostly re-roofs and panel upgrades — not recommended for a project-oriented serving DB.
- **`projects` 909 → ~1,181** (+272), a **30% increase**. These are the un-modelled ADU/infill tail CLAUDE.md names as v2's known coverage limit.
- **2026 COs: 2 → ~113 projects**, unblocking the 2026 CO tour.
- **Published numbers move.** The CO-completion tiles are the site's trustworthy headline; adding real completions makes them more accurate but they will not match today's figures. That is a deliberate, gated change, not drift.

## Decisions John must make before any write

1. **Scope.** Housing-creating permits only (recommended), or the full 8,039 rows?
2. **Create 272 new projects** for the ADU/infill tail, or attach permits and leave them project-less (which would NOT unblock the CO tour, since `v_projects_flat` is project-oriented)?
3. **Entitlement ingest** — same pass, or a separate gated write after the BP load is verified?
4. **Re-baseline** the APR / Explorer exports and the deploy gate after the write, since headline counts move.

_No database writes were performed. The connection was opened `mode=ro`._
