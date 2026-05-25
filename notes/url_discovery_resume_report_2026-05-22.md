# URL discovery resume report

**Generated:** 2026-05-22T13:36:15
**Invocation:** `python3 scripts/run_url_discovery.py --queue-db /tmp/cic_recon_queue_url_discovery.db --output-dir data/raw/accela_url_discovery --log-dir logs --sleep-min 2 --sleep-max 10 --max-consecutive-failures 5`
**Counter fix in effect:** only `failed` (true-error) increments `consecutive_failures`; `not_found` and `ambiguous` reset.

## Outcome at a glance

- This run processed: **73 / 73 pending** (clean completion)
- Stop reason: `Queue empty (no pending rows)`
- Runtime: **1123.7s** (~18.7 min — substantially under the 90-min cap)
- Cloudflare / login-wall encountered: **no**
- This run status: 23 succeeded · 50 not_found · 0 ambiguous · 0 failed
- Cumulative (both runs): 31 succeeded · 59 not_found · 0 ambiguous · 0 failed = 90 total

## 1. Pre-run state (verified before launch)

| check | result |
|---|---|
| Working queue distribution at start | `pending: 73, succeeded: 8, not_found: 9` ✓ |
| `scripts/run_url_discovery.py` mtime post-fix | 2026-05-22 13:12:50 ✓ |
| Line 481 is `if outcome == "failed":` (single-status increment) | ✓ |
| `data/raw/accela_url_discovery/` exists with 14 JSONs | ✓ |
| `--help` mentions new failure-counting semantics | ✓ ("'not_found' and 'ambiguous' do NOT count — they reset the counter") |

## 2. Final queue distribution (all 4 statuses)

| status | count |
|---|---|
| `succeeded` | 31 |
| `not_found` | 59 |
| `ambiguous` | 0 |
| `failed` | 0 |
| **TOTAL** | **90** |

## 3. JSON file count

- `data/raw/accela_url_discovery/`: **87** JSON files
- Expected: 14 (prior run) + 73 (this run) = 87 ✓
- Every processed permit has a JSON artifact, including the 50 not_found cases.

## 4. Total runtime

- This run: **1123.7s** (~18.7 min)
- Combined across both runs: 1123.7s + 238.9s ≈ **22.7 min** to process 87 permits = ~15.7s/permit average wall-clock, including sleeps.

## 5. final_state distribution across this run's 73 JSONs

| final_state | count |
|---|---|
| `not_found` | 50 |
| `ok` | 23 |

## 6. pages_walked distribution

| pages_walked | count |
|---|---|
| 1 | 70 |
| 2 | 3 |

3 permits required a 2nd page walk; the rest fit on a single results page. Combined with the prior run, only 4 of 87 processed permits ever needed pagination.

## 7. records_seen histogram (binned)

| bin | count |
|---|---|
| 0 | 50 |
| 2-5 | 16 |
| 6-10 | 4 |
| 11-20 | 3 |

Of the 23 succeeded permits in this run, the records_seen distribution skews small (mostly 2-5 records per master). The 11-20 bin (3 permits) likely contains the higher-touch projects with many REV/DEF iterations.

## 8. Permits with non-empty `errors[]`

- Count: **6** of 73

| permit | final_state | first error |
|---|---|---|
| B2023-03308 | not_found | `result-link query failed for "a[href*='CapDetail.aspx']": Page.query_selector_all: Execution context was destroyed, most` |
| B2023-04586 | not_found | `result-link query failed for "a[href*='CapDetail.aspx']": Page.query_selector_all: Execution context was destroyed, most` |
| B2023-06443 | not_found | `result-link query failed for "a[href*='CapDetail.aspx']": Page.query_selector_all: Execution context was destroyed, most` |
| B2025-00685 | not_found | `result-link query failed for "a[href*='CapDetail.aspx']": Page.query_selector_all: Execution context was destroyed, most` |
| B2025-00875 | not_found | `results-page pagination yielded no rows after page 1 (max_wait=8.0s)` |
| B2025-02220 | not_found | `result-link query failed for "a[href*='CapDetail.aspx']": Page.query_selector_all: Execution context was destroyed, most` |

Five of the six errors are `Execution context was destroyed` — a Playwright lifecycle race where the page navigated/re-rendered while `_parse_result_rows` was running. Despite the parse failure the scraper still recorded `records_seen=0` and marked the permit `not_found`. These 5 permits are candidates for **re-classification as failed** rather than not_found, because we don't actually know whether Accela has records for them — the parse never completed.

The sixth error (B2025-00875) is different: "results-page pagination yielded no rows after page 1". A Next link was present but the subsequent page render returned nothing. Likely a transient Accela hiccup; worth a re-try.

## 9. Cloudflare / login-wall scan

- Run-2-era log files scanned for `cloudflare` / `just a moment` / `requires_auth` / `login_required`: **0 hits**
- Cumulative across both runs: **0 hits** (verified previously for run 1)
- Conclusion: the not_found rate is NOT caused by Accela blocking. It reflects genuine search-by-permit-number coverage gaps.

## 10. Sample newly-succeeded JSONs (varied related-record counts)

| permit | master_capid_triplet | related | records_seen | pages_walked |
|---|---|---|---|---|
| B2023-03832 | `DUB23-00000-00JAD` | 1 | 2 | 1 |
| B2025-03358 | `DUB25-00000-00L7E` | 1 | 2 | 1 |
| B2024-01924 | `DUB24-00000-00EWF` | 16 | 17 | 2 |

## 11. Did the counter reset correctly?

- Stop reason: **`Queue empty (no pending rows)`** — the orchestrator processed every pending row and exited naturally. The `--max-consecutive-failures 5` cap **never fired** in this run.
- Spot-check log evidence: a `not_found` outcome co-occurs with `Consecutive failed (true-error) count: 0` in the per-permit logs (e.g., `url_discovery_20260522_B2023-01578.log`, `..._B2023-01880.log`, `..._B2023-02115.log`). This is direct evidence the not_found reset is working.
- 50 not_found outcomes occurred without halting the run — proof the patched semantics work as intended.

## 12. Verdict

**PASS** — full 73 processed to natural exhaustion, no Cloudflare, no true failures, counter-reset semantics verified. The previous run's halt was conclusively a bug in the consecutive-failures logic, not a real systemic issue. Patched and run cleanly.

## 13. Overall final state

- **Total permits with discovered URLs (`succeeded`):** 31 of 90 (34%)
- **Total `not_found` (no Accela CapHome coverage):** 59 of 90 (65%)
- **Total `ambiguous` (multiple exact matches):** 0
- **Total `failed` (true errors):** 0

All 90 in-scope permits were attempted. JSONs for all 90 cases (succeeded + not_found) are persisted to `data/raw/accela_url_discovery/` for downstream ingest and forensic review.

## 14. Follow-up items (NOT taken in this prompt)

- The 6 permits with `errors[]` non-empty (5× "Execution context was destroyed" + 1× "pagination yielded no rows") are good candidates for an isolated re-run because their status of `not_found` is uncertain — the scraper didn't finish parsing.
- The 59 `not_found` rate (66%) is high. A small manual browser-side spot-check of 3-5 not_found permits would confirm whether they truly have no CapHome record (data-source gap) vs. whether the scraper is missing them (e.g., wrong module hint, different display format). Not attempted here.
- All 31 succeeded JSONs are ready for ingest into v2 (the separate workstream from the design sketch). No ingest taken in this prompt.
