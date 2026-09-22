---
title: "Every multi-unit project, current — what we hold, what was never fetched, the sweep, the CPRA asks"
date: 2026-09-21
type: plan
status: draft
area: notes
---

# Every multi-unit project, current — what we hold, what was never fetched, the sweep, the CPRA asks

**Trigger:** the Excalidraw stage-duration drawing (`scripts/excalidraw_stage_durations.py`) shows 40
rows against 214 multi-unit projects in v2. John's worry: the project/permit data is stale. Diagnosis:
the drawing is limited by **milestone coverage** (only 84 of 214 multi-unit projects have ≥2 dated
milestones; `bp_issued` is populated on 36 of 909 projects), not by the export (2026-09-08, matches
the DB). The fix is upstream: a current, citywide multi-unit list with entitlement + BP + status.

Every number below was derived read-only today (`scratch` scripts in the session scratchpad; nothing
written to any DB).

---

## 1. Premises, corrected against the data

| claim | what the data says |
|---|---|
| "11 years of building permits" | **8 years, issued/finaled only.** CPRA feed (#26-1368 + the 2023-25 file): 30,764 permits, issued 2016–2025 (bulk 2018–), `Issuance Status` = `Issued` on every row. **Expired / cancelled / withdrawn / never-issued permits are absent by construction.** Ends 2025-12-31 (+4 rows Jan 2026). |
| "same range of planning permits" | **No planning feed exists.** v2 holds ~100 planning records (63 ZP, 14 PL, 12 DR, 10 ZC), all hand-pulled for already-tracked projects. #26-1972 produced the Planning "Master Permits Log" (487 applications, 2025 tail, structured fields blank). |
| "we should know which permits have expired" | Not from CPRA — but **yes from the Accela census** (§3): 12,889 `Closed Expired` building records 2015–2026. |

## 2. Three fulfilled CPRA productions were never downloaded

NextRequest fulfilment emails arrived and sat unread; the July note recorded the wrong request number
(#26-1972 for both halves — the BP refresh was actually **#26-1971**). Links expire after 30 days but
the files remain behind sign-in at records.cityofberkeley.info.

| # | subject | fulfilled | files | on disk? |
|---|---|---|---|---|
| **26-1971** | **BP Annual Permit Report refresh, 2025-01-01 → fulfilment** | **2026-07-07** (4 days!) | `BP_Annual Permit Report.xlsx`, `(1).xlsx`, `(2).xlsx` | **NO** |
| 26-2375 | Rent Board unit-registration database | 2026-08-17 | `2026-07-13 Unit Full Details.xlsx`, `UnitHistory_ 2026 Database Export.xlsx` | **NO** (PROGRESS.md 08-27 still says "pending") |
| 26-2367 | Corridors Zoning Update parcel GIS (Raimi) | 2026-08-26 | an Esri file geodatabase (~100 files) + `gdb`, `timestamps` | **NO** |
| 26-1972 | Planning pathways / completeness / fees | 2026-08-05 | `2026 Master Permits Log.xlsx` | yes (`scratch/2026-08-09/`) |
| 26-2321 | follow-up to 26-1972 (the either/or) | 2026-09-04 closed | answer: *"our report does list the provision … we currently do not have a way to track these"* | — |
| 26-2306 | Clariti contract | 2026-08-13 | released | (check) |

**Action 0 (John, sign-in required): download all three. #26-1971 first.** Note the #26-1971 ask
included *"Current permit status (issued, finaled, expired, cancelled)"* — if the City honoured it, the
all-status BP request in §5 is moot.

**Process fix:** a NextRequest fulfilment is a gated event — log the request number + fulfilment date +
file names in `data/raw/cpra-downloads/README.md` the day it lands. (Memory note written.)

## 3. The Accela census already exists — and it carries status

`data/raw/accela/date_range/` (built 2026-07-03/04 by `experiments/accela_scrape/backfill_building.py`,
`backfill_planning.py`, `sweep_recent_permits.py`; 4-day windows, append-only, resumable; 22 empty
holiday windows). Coverage **2015-01-01 → 2026-07-03**, both modules. Consumed so far only by JN-J
(attrition) and `adu_mh_cohort.py`.

**Building: 61,818 distinct permits** — Finaled 39,772 · **Closed Expired 12,889** · Issued 7,820 ·
Corrections List 653 · Under Review 257 · Approved w/Conditions 181 · Ready to Issue 172 · …
Crossed with the CPRA feed's 5,380 issued-not-finaled primaries: **5,204 found; 3,694 Closed Expired,
1,277 still Issued, 230 Finaled since the feed.** So the "unknown" set is already resolved to July.

**Planning: 13,230 distinct records** — 2,287 `Zoning Permit` (Approved 1,795 · Withdrawn 218 · Void 56 ·
In Review/Corrections/Incomplete ~104 · Pending Final Action 24), plus Pre-Application 387, Zoning
Research Letter 581, and ~11,000 zoning certificates (business licence, STR, home occupation — noise
for us).

**Multi-unit universe visible today (description-parsed, first pass, needs review):**
- Planning ZP/UP records with ≥5 units in the description: **132** (2015–2026; Approved 83, Withdrawn 17,
  In Review 11, Corrections/Incomplete 8, Closed 4, Void 3). 162 at ≥2 units.
- CPRA new-construction primaries with `UnitsAdded ≥ 2`: **92** (47 at ≥5) — census status: Finaled 55,
  Issued 31, Closed Expired 1, not in census 5.
- Census building records ACTIVE/pending (Issued, Under Review, Corrections, Approved w/Conditions,
  Pending Payment) with ≥2 units in the description and **not in the CPRA feed**: **23** (19 at ≥5),
  8 of them 2026 — e.g. `B2026-02298` Pending Payment "Phase I – new construction of a 7-story
  mixed-use" — the ones v2 cannot know about.
- v2 tracked: 214 projects at ≥2 units, 141 at ≥5.

The unit-in-description regex is a screen, not a count (it catches "replace subpanel in all 6
apartments"); `UnitsAdded` (CPRA) and the ZP detail page are the real unit signals.

## 4. The plan — three tracks

**Track A — retrieve (today, John):** the three productions in §2 → `data/raw/cpra-downloads/`
(BP), `data/raw/rent_board/`, `data/raw/corridors/`. Then read #26-1971: does it carry a status column?
how far does it reach (July 2026)? does it overlap 2025 (a third snapshot point for the finaled series)?

**Track B — the Accela sweep, 2026-07-04 → today (the "new sweep"):** the tool exists and is
resumable. `sweep_recent_permits.py` with `d = date(2026,7,4); END = today`, both modules → ~20
windows × 2 modules, ~3 s politeness + page time ≈ 15–20 min. Output lands beside the existing
windows; nothing is overwritten. Then re-run §3's cross to move the July statuses to September.
**Retry rule:** a 0-row window is retried once automatically, twice-failed windows are logged, not
concluded. **Read-only against the City; no DB write.**

**Track C — build the list (derived, read-only first):** `scripts/multiunit_master_list.py` →
`data/derived/multiunit_projects_<date>.csv`: one row per (address-normalized) project, union of
(i) ZP/UP records ≥2 units, (ii) CPRA new-construction `UnitsAdded ≥ 2`, (iii) census active building
records ≥2 units; columns = ZP number(s) + planning status/date, B number(s) + building status/date
(census), CPRA issued/finaled dates, units (best source, with provenance), v2 `project_id` if matched
(3-layer APN/address match, `housing_rules`), and a `not_in_v2` flag. That flag is the ingestion
worklist; the list itself is the deliverable John asked for. Only after review: gated v2 writes
(new projects + entitlement/BP events), then re-export, then the drawing grows.

## 5. CPRA drafts (two, kept separate — fast re-production vs novel)

### Request A — the Planning "Master Permits Log", prior years (named artifact; fast)

> Under the California Public Records Act (Gov. Code § 7920.000 et seq.), I request the Planning
> Department's **"Master Permits Log"** workbooks — the same record produced to me on 2026-08-05 in
> response to request #26-1972 (`2026 Master Permits Log.xlsx`) — for each prior year the Department
> maintains one: **2018, 2019, 2020, 2021, 2022, 2023, 2024, and 2025**, in their native Excel format
> (§ 7922.570). If the log is kept as a single rolling workbook rather than per-year files, please
> produce that workbook in full, including any archived or hidden sheets.
>
> Separately, and only if it is maintained: for every **Zoning Permit / Use Permit record (ZP)** in the
> permitting system (Accela) with an application date from **January 1, 2015 through fulfilment**,
> an export of the record number, record type, application date, current record status, status date,
> project address, APN, and the **proposed dwelling-unit count** field, where the system records one.
> If no such export exists, please say so and produce only the Master Permits Log workbooks.
>
> Please identify any portion withheld and the exemption relied on (§ 7922.525), and let me know of any
> cost estimate before processing. Thank you — the prior production was exactly the record I needed.

*(Why: the City has shown it maintains this log by hand and produces it quickly; prior-year logs give the
entitlement pipeline 2018–2024 in the City's own words. The ZP export is the "either/or" already forced
in #26-2321 — cheap to include, and their written "no" is itself a finding.)*

### Request B — Building-permit report, ALL statuses (hold until #26-1971 is read)

> Under the California Public Records Act, I request the **"BP Annual Permit Report"** — the report
> previously produced to me under requests #26-1368 and #26-1971 — re-run **without a status filter**,
> for permits with any activity from **January 1, 2015 through fulfilment**, in native Excel
> (§ 7922.570). The prior productions contain only records with Issuance Status "Issued"; I am asking
> for the same columns for **all record statuses** the system carries (including Expired / Closed
> Expired, Cancelled, Withdrawn, Void, Under Review, Approved, Ready to Issue), with the **current
> status** and **status date** as two columns.
>
> Three small additions to the same report, if the system supports them: (1) the **parent / master
> permit number** on `-DEF` and `-REV` subsidiary rows; (2) the report's **selection criteria and
> run date** on the banner; (3) note that the `Completed` / `Completed Date` columns arrive empty in
> every production to date, in case that is unintended.

*(Why: the census gives us status to July as a scrape; the City's own export makes it a record. Send
only if #26-1971 did NOT deliver the status column that request asked for.)*

**Not asked again:** planning pathways / streamlining provisions — the City answered in writing on
2026-09-04 that it cannot track them. That answer is the finding; re-asking wastes the goodwill.

## 6. Open items surfaced today

- `docs/explorer.js` deep-link (`?project=<id>`) + the Excalidraw script are uncommitted and unrecorded
  in PROGRESS.md (both from a session earlier today).
- Stray 0-byte `T7` at repo root (Sep 15) — a mistyped volume path; delete.
- `PROGRESS.md` calls #26-2375 "pending" (2026-08-27) — it was fulfilled 08-17.
