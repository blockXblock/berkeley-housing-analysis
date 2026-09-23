---
title: "How to verify a large multi-unit project"
date: 2026-09-22
type: methodology
status: durable
area: docs/methodology
---

# How to verify a large multi-unit project

The question John asked 2026-09-22: *what is our strategy to verify any large multi-unit?* This is the
answer as a repeatable procedure. It applies to one project at a time — the batch tooling
(`multiunit_master_list.py`, `derive_co_from_inspections.py`) produces candidates; this verifies them.

**The governing idea: every stage needs an INDEPENDENT dated artifact.** A status label is not evidence.
CKAN/HCD is never evidence (CLAUDE.md rule 1) — it is the thing we are checking ourselves against.

---

## The six checks, in order

### 1. Identity — what parcels, what addresses?
A large project is rarely one parcel or one street number. Resolve the **full parcel set**, not the
primary: `to_canonical_apn` on every source, then group by **assessor block** (book-page), because an
assemblage spans adjacent parcels. *Type case:* 1998 Shattuck (599u) is v2 project 119 stored as **1974**
Shattuck; the two are `057-2053-003-01` and `057-2053-002-00` — different parcels, same block, and v2
links only one of them. Never merge on address proximity alone: 2577 San Pablo (28u) sits near v2's 2601
San Pablo (223u) and is a different building.
**Standing guard:** run the stale-APN check (project APNs absent from the current assessor) before any
APN-join analysis; absent-from-assessor means re-platted OR too-new, and only affirmatively documented
re-plats are safe to re-point.

### 2. Entitlement — is there a Planning record, and what happened to it?
The ZP/UP/DR record and its **current** status from the record's own CapDetail page
(`refresh_record_status.py`), not the date-range census, which freezes status at scrape time. Expect
several records per project (PLN pre-app → ZP use permit → DRCP/DRCF design review), often sharing a
verbatim description. Statuses that matter: Approved, **Appealed**, Pending Final Action, Withdrawn, Void.

### 3. Building permit — issued, and for how many units?
CPRA `BP Annual Permit Report` is the backbone. Two traps:
- **`UnitsAdded` is inflated ~12.8× on large projects** — every `-DEF`/`-REV` child repeats the parent's
  full unit count. Always route through `housing_rules.permit_role.classify` + `net_units`.
- A large project has **several primary permits** (phases, buildings, shell vs interior). Get them all.

### 4. Construction — does the inspection trail exist?
The sequence itself is evidence: foundation → framing → insulation → drywall → finals. A project claiming
to be under construction with **no** inspections after the BP issue date is a finding. A 0-result is not
absence until retried (Accela discovery is flaky — 5/6 "discovery-failed" large buildings resolved on a
plain retry, 2026-06-15).

### 5. Completion — the dated CO
**`Building 1200 Building Final`, result `Approved`, with its date.** Berkeley finals permits rather than
issuing a traditional CO under Accela, so this inspection IS the CO event, and the APR needs the year.
- **Only `Approved` counts.** The same row can be `Site Cancellation`, `Cancelled`, `Disapproved` or
  `Partially Approved` (a Site-Cancellation final fooled us once — 2026-05-19 recon note).
- **Do NOT use `Finaled Status` alone**: it sits on 2,060 primary permits with no date, and grew
  706 → 985 in the 2023-25 window *between two productions of the same report*.
- `CO Required` (Yes on 810 permits) says a CO is *required* — a scope filter, never proof of issuance.
- **Per PERMIT, not per project.** A multi-building project has one final per building, and v2's single
  `co_issued_date` cannot hold both: Acheson North finaled 2022-01-14, South 2023-08-08 (+1061 days).
  Report the building, then decide what the project-level date means.

### 6. Corroboration — did the building physically arrive?
Assessor `Imps > 0` is the built-signal (`berkeley.db`, refreshed 2026-06-16). But **a City-finaled permit
OVERRIDES `Imps = $0`**: reassessment lags 1–2 years, and a demo→rebuild zeros `Imps` until the new build
posts. `Imps=$0` + no finaled permit + not recent = the genuinely suspect case.

---

## What each check can and cannot settle

| question | settled by | never settled by |
|---|---|---|
| Is it one project or two? | parcel set + assessor block + shared description | address string proximity |
| Was it approved? | ZP/UP status on CapDetail today | v2 `status_label` |
| How many units? | `net_units` over primary permits; entitlement doc for the approved count | raw `UnitsAdded` |
| Is it built? | approved Building Final + assessor `Imps` | `Finaled Status` |
| **When** was it complete? | the Building Final **date** | `Finaled Status`, stage labels, CKAN |
| Does the City agree? | — | (CKAN is the oracle, not evidence) |

## Escalation
Harvester (bulk Playwright) → retry once → per-record CapDetail read → **only then** the CIC/Chrome
spot-check, which is the expensive, near-manual last resort. Never start at CIC.

## Three traps that text inference walks into (all found by ground truth, 2026-09-23)

Each of these produced a confident, wrong answer that only John's local knowledge caught. Treat any
role or status derived from permit description text as a SCREEN, never as evidence.

1. **A finaled permit is not a finaled building.** 1914 Fifth St has three approved Building Finals
   (2017) — a warehouse demolition, a site-work demo and a parking-lot grading permit. The site is a
   parking lot today. *Guard:* only a permit that can create a dwelling may carry a completion.
2. **A demolition's stated REASON is not the permit's purpose.** 2403 San Pablo's demolition permits
   read "...All structures and paving on site to be removed **for new construction**." A pattern
   matching "new construction" credited three demolitions with the building's completion — while the
   real 36-unit permit, `B2024-00143` ("Privately funded, 4-story, mixed use, (36) unit condominium
   project"), tested negative because "(36) unit" carries a parenthesis. The test was exactly
   backwards. *Guard:* a description that OPENS with demolition is a demolition, whatever follows.
3. **`Imps > 0` does not transfer from parcels to projects.** On a redevelopment site the assessor's
   improvement value is the EXISTING building: 2700 Shattuck $11.9M, Ashby BART $5.5M, 2127 Dwight
   $22.7M — all pre-project structures. A first pass flagged 19 projects / 2,463 units as
   probably-built on that basis; every one was wrong. *Guard:* Imps means something only once a
   new-construction permit exists and the project is past entitlement.

**The standing conclusion:** the strongest evidence in this pipeline is structured (CPRA `Work Type` +
`UnitsAdded` through `classify`, inspection `type_code` + `result` + date). Free-text descriptions are
written by applicants to describe intent, not to be parsed. And **`field_survey_date` /
`field_survey_notes` exist in `v_projects_flat` and are unused** — they are the right home for the
ground truth that caught all three of these.

## Known unresolved
- **Multi-building projects have no home in the schema.** One `co_issued_date` per project cannot
  represent two buildings finaled 19 months apart. Until the model carries buildings, report per permit
  and treat the project-level date as a summary, flagged.
- **ADUs verify identically** (same `Building 1200 Building Final`, same full sequence — measured on 76
  ADU permits, 45 with approved finals), but **2,765 ADU-flagged permits carry a blank `UnitsAdded`** and
  therefore fall outside any units-based target list. `classify` rates 320 of them confident `new_unit`
  and 2,445 `ambiguous` (the dirty-flag case). Those 320 are real housing and need the same treatment.
