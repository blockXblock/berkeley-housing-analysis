---
title: Tour-grade data readiness — inspections, capIDs, and whether a CO tour is possible
date: 2026-09-25
type: audit
status: open
area: docs/audit
---

# Tour-grade data readiness — inspections, capIDs, and whether a CO tour is possible

**Questions.** What should we do with the inspection files and the per-record capID? And are we close
enough to a clean data environment to confidently build **a tour of every CO in 2025 or 2026**, or
**a tour of every middle-housing application**?

**Short answers.** The 2025 CO tour is **buildable now**. The 2026 CO tour is **not**, and the reason
is an un-ingested file sitting in the repo, not a scraping problem. The middle-housing tour is
**buildable now** at parcel-centroid precision. The capID is **not a missing thing** — we already
hold 67,494 of them and have been discarding the page they point at. Inspections are at **2.6%**
coverage and should stay targeted, not be chased to completion.

All figures measured 2026-09-25 against the Accela sweep through 2026-09-19.

---

## 1. The capID is already harvested — we are throwing away the page

| module | real records | with `capdetail_href` |
|---|---|---|
| Building | 69,716 | **67,494 (96.8%)** |
| Planning | 14,955 | **14,936 (99.9%)** |

The missing few percent are `NNTMP-` draft rows, which have no capID because they were never
submitted. So **capID discovery is a solved problem**; the gap is that nothing visits those URLs at
scale, and the one thing that does visit them — the inspection scraper — keeps only the inspection
table:

```
top keys: permit_number, url, extraction_timestamp, extraction_method, inspections, errors, metadata
```

The CapDetail page also carries **parcel/APN, owner, work type, occupancy type, unit counts, and a
Related Records section** that names the linked Planning record directly. We are already paying the
page-visit cost and discarding all of it. **Extending the extractor is the single highest-leverage
change in this document**, because one visit then yields three things we currently lack:

1. **The exact Planning↔Building join.** The middle-housing tracker joins on normalised address
   because the Accela list view exposes no shared key; Related Records makes that join exact and
   retires the tracker's main documented weakness.
2. **The classifier's missing inputs.** `housing_rules.permit_role.classify` takes `work_type`,
   `occtype`, `units_added`, `units_removed`. The list scrape supplies **none** of them. Fed
   description-only, it returns **4,321 of 4,856 finaled 2025-26 permits as `ambiguous`** — and its
   22 `new_unit` hits include a 400-amp service upgrade and two solar installs. The classifier is not
   broken; it is **starved**. CapDetail is where its food is.
3. **APN, therefore geometry** — without address matching, and with it the parcel polygon rather
   than a generated square.

**Recommendation.** Extend `experiments/accela_scrape/inspection_scraper.py` to capture
parcel/APN + Related Records + work/occupancy/unit fields alongside the inspection table, and store
them in the same per-record JSON. Then run it over **cohorts, never the whole 67K**. Ordered:
the 26 middle-housing construction permits · the tracked-v2 project permits · finaled ADU permits.
That is hundreds of pages, not tens of thousands.

## 2. Inspections: keep them targeted — bulk is not worth it

1,300 inspection files on disk. Against the 2025-26 issued/finaled universe:

| year | status | permits | have inspections |
|---|---|---|---|
| 2025 | finaled | 3,720 | 104 (2.8%) |
| 2025 | issued | 1,501 | 91 (6.1%) |
| 2026 | finaled | 1,136 | 3 (0.3%) |
| 2026 | issued | 1,488 | 8 (0.5%) |
| | **total** | **7,845** | **206 (2.6%)** |

At ~40 s per permit, closing that gap is roughly **85 hours** of scraping for a signal we mostly do
not need: **a `Finaled` status in the list view already tells us the building was completed.**
Inspections earn their cost in exactly one situation — **proving a project is genuinely under
construction before it finals**, which is unobtainable any other way. That is how we established
that 2808 Ninth St is really being built (setbacks and anchor-bolt inspections approved 2026-06-11)
rather than merely permitted.

**Recommendation.** Treat inspections as *stage evidence for cohorts under active watch*, not as a
corpus to complete. Fetch them for the middle-housing cohort, the tracked v2 projects, and anything
headed for a tour or a published claim. The tracker already prints the queue (6 permits outstanding).
Standing caution from the tool-vocabulary rule: **a 0-result is not evidence of absence until
retried** — 5 of 6 "discovery-failed" buildings resolved on a plain retry on 2026-06-15.

## 3. Can we tour every CO in 2025? — **Yes**

v2 holds **732 `completes` permits, 2018-01-05 → 2025-12-11**. For 2025:

| | |
|---|---|
| projects with a 2025 CO | **98** (99 completes permits) |
| with latitude/longitude | **96 (98%)** |
| with a display address | 98 (100%) |
| with a unit count | 98 (100%) |
| with a storey count | **11 (11%)** |

Everything a tour needs except height. The existing machinery (`kml/tours/`,
`build_tour_package.py`, `docs/tours.json`) already renders per-address tours. **The two ungeocoded
projects and the storey gap are the only work**, and heights can come from the BP-description +
assessor method at 3.5 m/storey rather than blocking on plan sets.

## 4. Can we tour every CO in 2026? — **No, and the fix is an ingest, not a scrape**

**v2 holds 2 projects with a 2026 CO.** The Accela sweep shows **1,136 finaled building permits in
2026**. v2's permit feed simply stops at the end of 2025.

The data is **already in the repo, un-ingested**:

- **`data/raw/cpra-downloads/BP_Annual Permit Report-2025-2026-07-07.xlsx`** — 8,047 rows, dates
  running to **2026-07-07**. This is the 2026 completion feed. v2's newest `completes` is 2025-12-11,
  so the 2026 portion has never been loaded.
- **`data/raw/cpra-downloads/2026 Master Permits Log.xlsx`** — 9 sheets, 589 rows, also
  un-ingested. ⚠ **CORRECTED 2026-09-25 (same day):** this section originally credited the file
  with `New Units (Y/N)`, `Demolished Units`, `Total Units in Project`, BMR by income tier, Density
  Bonus and SB 9 streamlining. **Those are HEADERS with no data.** Measured fill rates: every
  column after `Date Received` is **100% empty**, including all unit counts, all BMR tiers, and
  the entitlement dates (`Date Deemed Complete`, `Date of Final Action`, `Date of NOD`, `Date
  Permit Effective`). What the file actually carries is application intake — number, type, site
  address, applicant, res/comm, description, date received. Useful for
  `application_submitted` events and for knowing what is in the planning queue; it does **not**
  close the queued entitlement-event gap, because the approval dates are the missing part. See
  `2026-09-25_cpra_2026_ingest_preview.md`. *Lesson: read fill rates, not column names.*

**Recommendation, and it is the cheapest win in this document: ingest the 2026 BP report.** It needs
the standing write discipline — snapshot, read-only preview, stop for John, transactional write with
verify-or-rollback — but it is an ingest of a file we already hold, not a new acquisition. It would
take 2026 COs from 2 to roughly a full year, and it also feeds the coverage-limited RHNA side.

Related: this is the same class of miss as the **NextRequest fulfilments** memory — productions
arriving and sitting unretrieved. Worth checking Gmail `from:nextrequest.com` for anything newer
before assuming 2026-07-07 is the latest available.

## 5. Can we tour every middle-housing application? — **Yes, at parcel-centroid precision**

**31 of 32 records geocode** against `berkeley.db` situs addresses (97%); the single miss is
**1312 Addison St**. The cohort has dates, statuses, permit state, hand-checked unit counts, and
descriptions good enough for narration.

Two honest limits to state on the tour itself:
- **Footprints are generated squares at parcel centroids**, as in `gen_adu_middle_housing.py` — not
  real building outlines. Overture footprints (already on disk) would fix this, and the same fix is
  outstanding for the 76% of tour polygons that are currently parcel boundaries.
- **Nothing is built yet.** A tour of middle housing is, today, a tour of *intentions* — 31 sites,
  one of them under construction, none finished. That is the honest frame, and it is also the
  interesting one.

---

## Ranked actions

1. **Ingest the 2026 BP report** (file already on disk) — unblocks the 2026 CO tour. Gated write.
2. **Extend the CapDetail extractor** to keep parcel/APN + Related Records + work/occupancy/units —
   one change that fixes the MH join, feeds the starved classifier, and yields geometry keys.
3. **Build the 2025 CO tour** — data is ready; geocode 2 stragglers, derive heights.
4. **Build the middle-housing tour** — geocode 1312 Addison, swap in Overture footprints.
5. **Run the extended scraper over cohorts** (MH permits, tracked projects, finaled ADUs) — hundreds
   of pages.
6. **Ingest the 2026 Master Permits Log** entitlement sheets — richest unit/BMR/density-bonus fields
   we have, and the SB 684 / Ministerial sheets are directly relevant to the gentle-density project.
7. **Do not** pursue blanket inspection coverage. 85 hours for a signal `Finaled` already gives.
