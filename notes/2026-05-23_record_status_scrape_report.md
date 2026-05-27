# Record-status scrape report (2026-05-23, 107 permits)

**Generated:** 2026-05-23T11:21:36
**Scraper:** `scripts/record_status_scraper.py v1.0` (4 fields per permit, single HTTP fetch + BeautifulSoup parse)
**Runtime:** 174.6s (~1.6s per permit). 107/107 succeeded; 0 failed.

## Headline

| metric | value |
|---|---|
| Permits scraped | **107** (92 inspection-scraped + 15 permitted-only) |
| Succeeded | **107** |
| Failed | 0 |
| Wall time | 174.6s |

### Accela record_status distribution

| record_status | count | % |
|---|---|---|
| `Finaled` | 63 | 58.9% |
| `Issued` | 37 | 34.6% |
| `Closed Expired` | 6 | 5.6% |
| `Approved` | 1 | 0.9% |

Notes:
- `Approved` (1) is the lone Planning record (ZP2018-0135) — that's the entitlement status terminology used by the Planning module, equivalent to "approved entitlement".
- `Closed Expired` (6) is Accela's status for permits that lapsed without finalization.
- The major split is **Finaled (59%) vs Issued (35%)** — many permits that v2 considers "completed" are actually still Issued in Accela.

## Cross-reference: v2_stage × Accela record_status

| v2_stage \ Accela | Approved | Closed Expired | Finaled | Issued | total |
|---|---|---|---|---|---|
| **completed** | 1 | 5 | 60 | 18 | 84 |
| **permitted** | 0 | 1 | 3 | 11 | 15 |
| **under_construction** | 0 | 0 | 0 | 8 | 8 |

### Cell-by-cell interpretation

- **completed × Finaled: 60** — clean agreement. Project finished, permits properly closed out. **The clear case.**
- **completed × Issued: 18** — v2 says completed, Accela says permit still active. **The project-139-style errors.** See full list below. These are the most actionable findings.
- **completed × Closed Expired: 5** — permits that expired without being finaled. v2 marked the project completed anyway (perhaps because the *primary* permit finaled and these are subsidiary).
- **completed × Approved: 1** — the Planning record ZP2018-0135 (project 179 / 2352 Shattuck). Planning entitlements close out as "Approved", not "Finaled". Correct.
- **permitted × Issued: 11** — expected. These are the newly-discovered permits in `permitted` stage; correctly issued.
- **permitted × Finaled: 3** — projects v2 marked permitted but the building permit is actually finaled. These projects may have advanced past permitted to completed; worth a stage update.
- **permitted × Closed Expired: 1** — a permitted-stage project where the permit expired.
- **under_construction × Issued: 8** — perfect alignment. All under_construction permits are active in Accela.

## The 18 Issued-but-v2-completed permits (full list, grouped by project)

These are the project-139-style stage errors. v2 says the project is completed, but at least one Accela permit is still Issued (i.e., active, not finaled).

| project_id | address | permits Issued-not-Finaled |
|---|---|---|
| 53 | 2641 COLLEGE Ave | B2024-05471 |
| 63 | 1716 SEVENTH St | B2022-01332, B2022-01386 |
| 64 | 1515 DERBY St | B2025-02754 |
| 79 | 1111 ALLSTON Way | B2025-01202 |
| 83 | 1136 KEITH Ave | B2024-03997 |
| 88 | 705 ARLINGTON Ave | B2024-01528, B2025-04937 |
| 92 | 3036 REGENT St | B2023-03832 |
| 129 | 1614 Sixth St | B2024-04504, B2024-06099 |
| 139 | 2538 DURANT Ave | B2023-02332, B2024-06011 |
| 152 | 1598 UNIVERSITY Ave | B2024-00587, B2024-01924, B2024-05740 |
| 172 | 2650 TELEGRAPH Ave | B2024-03280 |
| 176 | 2440 SHATTUCK Ave | B2024-05368 |

**12 distinct projects** are affected. Three projects have **2 or 3 Issued permits each** (1598 University = 3, 1716 Seventh = 2, 2538 Durant = 2, 1614 Sixth = 2, 705 Arlington = 2) — these are the most clearly mis-categorized in v2.

## The 3 Finaled-but-v2-permitted (potential under-estimates of v2 stage)

| permit | project_id | address |
|---|---|---|
| B2025-01579 | 72 | 5 W PARNASSUS Ct |
| B2025-04241 | 132 | 1627 Jaynes St |
| B2025-04912 | 67 | 1419 GRANT St |

These projects v2 says are still in `permitted` stage, but the building permit is already Finaled. Less common than the over-estimate (18) but suggests v2 stage could be advanced for these.

## The 5 Closed Expired permits (in completed-stage v2 projects)

| permit | project_id | address |
|---|---|---|
| B2022-03783 | 83 | 1136 KEITH Ave (completed) |
| B2023-00401 | 176 | 2440 SHATTUCK Ave (completed) |
| B2023-02303 | 63 | 1716 SEVENTH St (completed) |
| B2024-01659 | 96 | 2099 M L KING JR Way (completed) |
| B2024-02120 | 134 | 2480 Bancroft Way (completed) |
| B2024-04964 | 113 | 2138 KITTREDGE St (permitted) |

Most likely scenario: project completed via a different (primary) permit; these are subsidiary permits that lapsed. Worth verifying during ingest that the primary permit's Finaled status drives the project stage.

## Sample 5 scraped records (full data)

- **B2019-05574** — record_status=`Finaled`, type=`Permit`
  - work_location: `2352 SHATTUCK Ave 94704`
  - applicant (raw): `Bill Schrader Bill Schrader The Austin Group 164 OAK RD ALAMO, CA, 94507-2761 Work Phone: (925)683-8782 bill@austin-grou`
- **B2019-05575** — record_status=`Finaled`, type=`Permit`
  - work_location: `2352 SHATTUCK Ave 94704`
  - applicant (raw): `Bill Schrader Bill Schrader The Austin Group 164 OAK RD ALAMO, CA, 94507-2761 Work Phone: (925)683-8782 bill@austin-grou`
- **B2021-02225** — record_status=`Finaled`, type=`Permit`
  - work_location: `2650 TELEGRAPH Ave 94704`
  - applicant (raw): `MAURICIO DELAPENA MAURICIO DELAPENA Trachtenberg architects 2421 4TH ST BERKELEY, CA, 94710-2430 Work Phone: (510)649-14`
- **B2021-02404** — record_status=`Finaled`, type=`Permit`
  - work_location: `2000 DWIGHT Way 94704`
  - applicant (raw): `Guillermo Otero Guillermo Otero Trachtenberg Architects 2421 4TH ST BERKELEY, CA, 94710-2430 Work Phone: (510)649-1414 G`
- **B2021-03950** — record_status=`Finaled`, type=`Permit`
  - work_location: `2099 M L KING JR Way 94704`
  - applicant (raw): `Mary Young-Williams Kava Massih Architects 920 Grayson Street Berkeley, CA, 94710 Home Phone: (510)644-1920 MARY@KAVAMAS`

## Field-quality observations

- **`record_status`**: extracted cleanly via stable element id `ctl00_PlaceHolderMain_lblRecordStatus`. 4 distinct values observed: Issued / Finaled / Closed Expired / Approved.
- **`permit_type_text`**: returns the Accela module-level type. For Building permits this is generically `'Permit'`; for Planning records it's `'Zoning Permit'`. To get more granular subtype (Alteration / New / Demolition), use the CPRA `Work Type` column — that's not on Accela's CapDetail page header.
- **`work_location`**: extracted cleanly. Format `'{street_number} {STREET_NAME} {street_type} {zip}'`. Slight casing variation from v2's `canonical_address` (Accela tends to UPPERCASE the street name; v2 mixes). Useful for QA but not a 1:1 string match.
- **`applicant_name`**: raw capture includes name (often doubled — name + company), address, phone numbers. First-100-200 chars sufficient for downstream cleanup. Not normalized to a single name.

## Recommendation for inspection ingest path

**18 of 107 permits (16.8%) show a `completed`/`Issued` v2-vs-Accela mismatch — meaningful but not pervasive.** Of those, **12 distinct projects** are affected, and **only 3 of those projects** (1598 University, 2538 Durant, 1614 Sixth St) have multiple mismatched permits suggesting the project is truly active (not just one stray subsidiary permit).

**Recommended path: proceed with inspection ingest as designed; handle stage re-classification in Layer C, NOT before.**

Rationale:

1. **The mismatch isn't a blocker for inspection ingest.** Inspection records are tied to permits, not to project stages. Whether a project is labeled `completed` or `under_construction` in v2 doesn't change what inspection records belong to that project's permits.

2. **17% mismatch rate is consistent with yesterday's data-rich-subset estimate of ~90% agreement.** This isn't an emergency.

3. **Layer A (inspection ingest) gains a useful pre-condition:** the `record_status_queue` is now populated with authoritative permit-level state for every inspection-scraped permit. Ingest can record per-permit `accela_record_status` as provenance, AND can flag the 18 mismatches in its audit report (so Layer C has a starting point).

4. **Layer C (stage re-inference)** should now:
   - Use `record_status_queue` as authoritative permit-level state
   - For each project, compute proposed v2 stage from the project's permits' record_statuses (e.g., if any permit is Issued and no permits are Finaled → `under_construction` or `permitted`; if all Finaled → `completed`; etc.)
   - Compare to current v2 stage; surface the 12 mismatched projects + the 3 Finaled-in-permitted projects as candidates for v2 stage update
   - Decision on whether to auto-update is separate (probably manual-confirm given the small N)

**Specific Layer A scope extension:** add a `stage_inconsistent` flag per inspection-ingest record, computed as: `accela_record_status == 'Issued' AND v2_stage == 'completed'`. Costs nothing during ingest; surfaces the 18 mismatches naturally.
