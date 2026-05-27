# Processing Status scrape report (2026-05-23, 107 permits)

**Generated:** 2026-05-23T13:11:08
**Scraper:** `scripts/processing_status_scraper.py v1.0` (Playwright + JS-handler tab nav + BeautifulSoup parse)
**Runtime:** 2,153.2s (~36 min, ~20s per permit). 107/107 succeeded, 0 failed.

## Headline

| metric | value |
|---|---|
| Permits scraped | 107 |
| Succeeded | 107 |
| Failed | 0 |
| Permits with active workflow stage | 54 |
| Permits with no active stage (all complete or pending) | 53 |
| Hourglass rows total | 45 (across 45 permits) |

## Sub-record distribution

| sub-records per permit | count |
|---|---|
| 0 | 70 |
| 1-3 | 21 |
| 4-9 | 11 |
| 10+ | 5 |

70 of 107 permits (65%) have no sub-records — the workflow lives entirely on the main permit. The 5 permits with 10+ sub-records are the largest construction projects: 1598 University (16 subs for B2024-01924), 2538 Durant (REV01-09 + DEF08 etc.), and similar.

## Newest sub-record `record_status` distribution

| record_status | count | % |
|---|---|---|
| `Finaled` | 63 | 58.9% |
| `Issued` | 37 | 34.6% |
| `Closed Expired` | 6 | 5.6% |
| `Approved` | 1 | 0.9% |

Identical distribution to the main-permit record_status from the earlier record_status_queue scrape — confirms that for these 107 permits, the workflow state on the newest sub-record matches the main permit's status.

## Active workflow stages (across all 107 permits)

| active stage | permits |
|---|---|
| Inspection | 42 |
| Inspector Final CofO Review | 9 |
| Zoning CofO Review | 8 |
| Inspector CofO Review | 6 |
| Public Works CofO Review | 5 |
| Fire CofO Review | 4 |
| Traffic CofO Review | 3 |
| Certificate of Occupancy | 2 |
| Design CofO Review | 2 |
| Consolidated Comments | 1 |
| Toxics CofO Review | 1 |

`Inspection` is the dominant active stage (42 permits — 39% of all 107). That matches expectation: most Issued permits are mid-construction, in the inspection phase. The next cluster (Inspector Final CofO Review / Zoning CofO Review / Public Works CofO Review / Fire CofO Review / etc.) represents permits that have finished inspection and are in the Certificate-of-Occupancy review phase — the final steps before being marked Finaled.

**`Consolidated Comments`** appears only once as an active stage — for B2023-02332 (the 2538 Durant permit we Chrome-verified) — confirming that the active sub-record REV09 is in Consolidated Comments review, distinct from the more common Inspection stage.

## Pending workflow stages

None observed. All workflow stages in the 107 permits are either `complete` or `active`. Pending stages (those not yet reached) aren't surfaced as named stages in the Processing Status table — they're only implicit.

## Hourglass rows

45 hourglass rows total across **45 permits** — exactly 1 hourglass row per affected permit (on average). The hourglass marks the workflow's current waiting point: a step where the staff member or applicant hasn't yet acted.

Most hourglass rows live in `Consolidated Comments`, `Inspector Final CofO Review`, and the various CofO Review stages — consistent with the active stage distribution above.

## Cross-reference: v2.completed + sub Issued + active stages

**18 permits** are v2.stage=`completed`, sub-record record_status=`Issued`, AND have an active workflow stage — i.e., projects v2 says are finished but Accela says are still actively in workflow. These are the project-139-style errors with workflow evidence (not just status mismatch).

| project_id | address | main permit | scraped sub-record | active stage(s) |
|---|---|---|---|---|
| 63 | 1716 SEVENTH St | B2022-01332 | B2022-01332-REV01 | Inspection |
| 63 | 1716 SEVENTH St | B2022-01386 | B2022-01386 | Inspection |
| 139 | 2538 DURANT Ave | B2023-02332 | B2023-02332-REV09 | Consolidated Comments |
| 92 | 3036 REGENT St | B2023-03832 | B2023-03832-REV01 | Inspection |
| 152 | 1598 UNIVERSITY Ave | B2024-00587 | B2024-00587-REV04 | Inspection |
| 88 | 705 ARLINGTON Ave | B2024-01528 | B2024-01528-REV01 | Inspection |
| 152 | 1598 UNIVERSITY Ave | B2024-01924 | B2024-01924-DEF16 | Inspection |
| 172 | 2650 TELEGRAPH Ave | B2024-03280 | B2024-03280 | Inspection |
| 83 | 1136 KEITH Ave | B2024-03997 | B2024-03997 | Inspection |
| 129 | 1614 Sixth St | B2024-04504 | B2024-04504-REV01 | Inspection |
| 176 | 2440 SHATTUCK Ave | B2024-05368 | B2024-05368 | Inspection |
| 53 | 2641 COLLEGE Ave | B2024-05471 | B2024-05471 | Inspection |
| 152 | 1598 UNIVERSITY Ave | B2024-05740 | B2024-05740-REV01 | Inspection |
| 139 | 2538 DURANT Ave | B2024-06011 | B2024-06011-REV01 | Inspection |
| 129 | 1614 Sixth St | B2024-06099 | B2024-06099-REV01 | Inspection |
| 79 | 1111 ALLSTON Way | B2025-01202 | B2025-01202 | Inspection |
| 64 | 1515 DERBY St | B2025-02754 | B2025-02754 | Inspection |
| 88 | 705 ARLINGTON Ave | B2025-04937 | B2025-04937 | Inspection |

**12 distinct projects** affected (some with multiple permits in this state):
- 1598 University (project 152): 3 permits — B2024-00587/01924/05740 all with active Inspection stage
- 1716 Seventh (63): 2 permits
- 1614 Sixth (129): 2 permits
- 2538 Durant (139): 2 permits — incl. B2023-02332 in active Consolidated Comments (unique among the 18)
- 705 Arlington (88): 2 permits
- 1111 Allston Way, 1136 Keith, 1515 Derby, 2440 Shattuck, 2641 College, 2650 Telegraph, 3036 Regent — 1 permit each

This is the **same 12-project set** identified in the record_status_queue cross-reference, now with the additional signal that workflow is actively progressing on these (active stage = Inspection / Consolidated Comments).

## Sample of 3 Processing Status JSONs (summarized)

### B2023-02332 (2538 Durant Ave, REV09 scraped)

- subrecord_count: 9 (REV01-07, DEF08, REV09) — note: a few intermediate DEFs may be missing from the Related Records view (default is direct-only, not entire tree)
- 7 stages: Application Submittal (complete), Resubmittal-Revision (complete, 69 steps), Plan Distribution (complete, 17 steps), Zoning Review (complete, 43 steps), PSC Review (complete, 8 steps), **Consolidated Comments (active, 23 steps, 1 hourglass)**, Issuance (complete, 10 steps)
- sub_status: Issued. The REV09 revision is in Consolidated Comments review — active workflow.

### B2024-01924 (1598 University Ave, DEF16 scraped)

- subrecord_count: 16 (REV01-09 + DEF01-08 hierarchy)
- 14 stages including Public Works Review, Fire Review, Toxics Review, Traffic Review, Design Review, **Inspection (active)**
- The most complex permit in the set — major mixed-use residential construction.

### B2025-01864 (2441 Le Conte Ave, main permit scraped)

- subrecord_count: 0 — no revisions
- 2 stages: an unknown pre-issuance stage (3 steps showing 'Ready to Issue' marked by Autumn Maltbie) and Issuance (complete, 6 steps showing 'Issued' marked by Ramona Smith)
- sub_status: Finaled. Clean permit, completed cleanly.

## Known scraper limitations (v1.0)

1. **Related Records: direct-only, not entire tree.** The Related Records tab defaults to direct related records. Accela has a 'View Entire Tree' button that may reveal more sub-records (incl. nested ones). For B2023-02332 we found 9 sub-records, but Berkeley's tree-view may show more. The scraper does NOT click 'View Entire Tree' — the newest direct related record is good enough for workflow state, but completeness of the sub-record list is a known gap.

2. **Related Records metadata not extracted.** `record_type`, `date`, `view_url` came back null in the smoke test. The scraper currently extracts only `permit_number`. Full row metadata requires a more sophisticated table-parsing pass; deferred.

3. **DOM step duplication** (every step rendered twice — likely accessibility duplicate). Handled via adjacent-row dedup. Step counts now match what a human counts; hourglass count halved correctly.

4. **Pre-issuance stage unrecognized.** A few permits (e.g., B2025-01864) have a pre-issuance stage that doesn't have an `alt="Complete"` or `alt="active"` image marker. Falls into `(unknown stage)` bucket. Affects a small number of permits.

## Sample row in detail

A representative `processing_status_queue` row (B2023-02332):

```
permit_number: B2023-02332
main_capdetail_url: https://aca-prod.accela.com/BERKELEY/Cap/CapDetail.aspx?...
main_record_status: Issued
subrecord_count: 9
newest_subrecord: B2023-02332-REV09
scraped_subrecord: B2023-02332-REV09
scraped_subrecord_record_status: Issued
stage_count: 7
hourglass_rows_count: 1
active_stage_names: Consolidated Comments
pending_stage_names: (empty)
status: succeeded
```
