# Overnight candidate set — inventory

**Generated:** 2026-05-22T23:10:02
**Scope:** read-only inventory of v2 permits NOT yet in `scrape_queue.status='succeeded'`. No actions proposed; no DB writes.

## Headline

**152 candidate permits** in v2 are not yet scraped (244 total − 92 succeeded). **Zero of the 152 have a `source_url`.** None are immediately runnable through the inspection orchestrator without a URL-discovery step first. The 49 B-prefix candidates are all in project stages OUTSIDE `completed`/`under_construction`; the 11 candidates that ARE in eligible stages are all non-B (ZP/PLN/DRCF/etc., Planning module, where the inspection scraper's behavior was already shown to produce 0-inspection results — see ZP2018-0135 earlier today).

## 1. Totals

| field | value |
|---|---|
| v2 `permits` total | 244 |
| `scrape_queue.status='succeeded'` | 92 |
| Candidates (v2 − done) | **152** |

## 2. Candidate distribution

### By source_system

| source_system | count |
|---|---|
| `accela` | 78 |
| `planning` | 36 |
| `cpra` | 32 |
| `building` | 5 |
| `v1_events_reconstruction` | 1 |

### By permit-number prefix

| prefix | count |
|---|---|
| `ZP` | 62 |
| `B` | 49 |
| `PLN` | 14 |
| `ZCBP` | 8 |
| `DRCP` | 5 |
| `DRCF` | 3 |
| `DRSL` | 2 |
| `DRSA` | 2 |
| `ZCBL` | 2 |
| `(non-alpha)` | 1 |
| `LMSAP` | 1 |
| `P` | 1 |
| `PREAPP` | 1 |
| `LMIN` | 1 |

### By project stage

| stage | count |
|---|---|
| `in_review` | 62 |
| `entitled` | 47 |
| `permitted` | 17 |
| `withdrawn` | 13 |
| `completed` | 9 |
| `under_construction` | 2 |
| `stalled` | 1 |
| `pre_application` | 1 |

### URL availability

| field | count |
|---|---|
| Candidates with non-null `source_url` | **0** |
| Candidates with CapDetail-format URL (orchestrator-runnable) | **0** |
| Candidates with CapDetail URL AND completed/under_construction | **0** |

All zero. The candidate set has no v2-stored URLs.

## 3. The 11 eligible-stage candidates

All 11 are non-B-prefix (Planning module records) with `source_system='accela'`. The inspection scraper was designed for the Building module — when run against a Planning-module CapDetail (ZP2018-0135 this morning), it returned 0 inspections in 'succeeded' state (no inspection table on the page).

| permit | stage | source | address |
|---|---|---|---|
| DRCF2023-0005 | completed | accela | 2480 Bancroft Way |
| ZP2022-0115 | completed | accela | 2427 San Pablo |
| ZP2023-0089 | completed | accela | 2441 LE CONTE Ave |
| ZP2024-0008 | completed | accela | 1614 Sixth St |
| ZP2024-0070 | under_construction | accela | 2442 HASTE St |
| ZP2024-0122 | completed | accela | 3036 REGENT St |
| DRCF2024-0004 | completed | accela | 1598 UNIVERSITY Ave |
| PLN2024-0072 | under_construction | accela | 1701 SAN PABLO Ave |
| ZP2022-0011 | completed | accela | 1598 UNIVERSITY Ave |
| ZP2022-0170 | completed | accela | 3030 TELEGRAPH Ave |
| DRCF2020-0003 | completed | accela | 2352 Shattuck Ave |

## 4. Stage × prefix cross-tab (full)

Notable cells:

- B-prefix completed/under_construction: **0** (all 90 in-scope B-permits in eligible stages are already in `done_pns`)
- B-prefix permitted: **15** (issued but not yet finaled — likely in Accela)
- B-prefix in_review: **16** (not yet issued — probably not yet in Accela)
- B-prefix entitled: **4**
- B-prefix withdrawn: **12**
- All B-prefix candidates total: **49**

Full B-prefix distribution by stage:

| stage | count |
|---|---|
| `in_review` | 16 |
| `permitted` | 15 |
| `withdrawn` | 12 |
| `entitled` | 4 |
| `stalled` | 1 |
| `pre_application` | 1 |

## 5. URL discovery candidates (strict in-scope)

- B-prefix AND no source_url AND completed/under_construction: **0**

All eligible-stage B-permits were processed today.

## 6. Recommendation matrix

| Workstream | Count | Est. runtime | Notes |
|---|---|---|---|
| **A. Inspection on existing-URL candidates** | 0 | n/a | Zero v2-stored URLs in the candidate set. No work to do. |
| **B. URL discovery (strict in-scope: B + eligible stage)** | 0 | n/a | All 90 already done. |
| **C. Combined A+B** | 0 | n/a | Nothing to combine. |
| **D. Expanded B: URL discovery on B-prefix `permitted` permits (issued, not finaled)** | 15 | ~3 min discovery + ~15 min inspection = ~18 min | New scope. These are B-permits issued but not yet finaled — likely in Accela. Inspection results likely partial (in-progress). |
| **E. Expanded D: also include B-prefix `entitled` (4) + `in_review` (16)** | 35 | ~6 min discovery + ~35 min inspection = ~41 min | New scope. `in_review` permits may not yet be in Accela; expect higher not_found rate. |
| **F. Planning-module work (11 ZP/DRCF/PLN in eligible stages)** | 11 | Unknown | Different module. URL discovery scraper's `--module-hint` is currently Building-only; would need adjustment. Inspection scraper produces 0 inspections on Planning pages (per ZP2018-0135 today). |

## 7. Deal-breakers / non-B-prefix caution

- **103 of 152 candidates are non-B-prefix** (ZP, PLN, DRCF, DRCP, DRSA, DRSL, LMSAP, LMIN, P, PREAPP, ZCBL, ZCBP).
- The inspection scraper was built around the Building module's inspection-table DOM. ZP2018-0135 tested earlier today and returned `final_state='not_reached', inspections=0` in succeeded state (no inspection table).
- For non-B permits, the inspection scraper's behavior is: it runs, finds no inspection table, marks the row succeeded with 0 inspections, and exits cleanly. No errors, but no useful data either.
- The URL discovery scraper was built around the Building module's CapHome.aspx search; the `--module-hint` flag exists but Planning behavior is untested.

## Bottom-line

- **No 152-permit overnight run is available** as the user envisioned. The candidate set has zero URL-ready, zero in-scope-no-URL, and a mix of stages + prefixes where the scrapers' behavior is either known to produce no data (Planning) or untested.
- The most defensible **expanded-scope** overnight run would be **Workstream D**: 15 B-prefix `permitted` candidates — they've been issued (so likely in Accela's index), they share permit type with everything we successfully processed today, and the runtime is small (~18 min). This wouldn't fill an overnight slot but it would meaningfully extend coverage.
- Anything beyond Workstream D involves new scope decisions: (a) accept higher not_found rate on `entitled`/`in_review` permits, (b) extend the scrapers to Planning module, or (c) accept that the inspection scraper produces 0-inspection successes on non-Building records.

Inventory only. No actions proposed; no DB writes; no orchestrator launch.
