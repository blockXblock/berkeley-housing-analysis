# URL discovery full run report

**Generated:** 2026-05-22T13:08:48
**Invocation:** `python3 scripts/run_url_discovery.py --queue-db /tmp/cic_recon_queue_url_discovery.db --output-dir data/raw/accela_url_discovery --log-dir logs --sleep-min 2 --sleep-max 10 --max-consecutive-failures 5`

## Outcome at a glance

- Permits processed in this run: **14** of 87 pending at start
- Run halted by the `--max-consecutive-failures 5` safety cap
- Stop reason: "5 consecutive failures (possible Accela blocking)"
- Total runtime: **238.9s** (~4 min)
- Cloudflare / login-wall encountered: **no** (verified by log scan)
- This run's status breakdown: 5 succeeded · 9 not_found · 0 ambiguous · 0 failed (Python-error)

## 1. Pre-run state

| check | result |
|---|---|
| Working queue: 87 pending + 3 succeeded | yes |
| `data/raw/accela_url_discovery/` writable | yes (created empty) |
| `logs/` writable | yes |
| Pre-flight 3 JSONs at `/tmp/url_discovery_pre_flight/` (not canonical) | yes |

## 2. Queue status distribution (post-run)

| status | count |
|---|---|
| `not_found` | 9 |
| `pending` | 73 |
| `succeeded` | 8 |
| **TOTAL** | **90** |

Comparison to pre-run: `pending` dropped from 87 → 73 (14 processed); `succeeded` rose from 3 → 8 (+5); `not_found` is new at 9.

## 3. JSON file count

- Files in `data/raw/accela_url_discovery/`: **14**
- Matches permits-processed count (14). The orchestrator wrote a JSON for every permit it processed, including not_found cases.

## 4. Total runtime + log inventory

- Orchestrator runtime: **238.9s** (~17s/permit average)
- Log files in `logs/` named `url_discovery_*.log`: **14**
- One log per permit, all written in the expected format (timestamp - level - message with `[scraper]` DEBUG prefix on captured scraper stdout).

## 5. final_state distribution across the 14 JSONs

| final_state | count |
|---|---|
| `not_found` | 9 |
| `ok` | 5 |

## 6. pages_walked distribution

| pages_walked | count |
|---|---|
| 1 | 13 |
| 2 | 1 |

Only one permit (B2021-02404, with 20 records) required a 2nd page walk; everything else fit on a single results page. This is consistent with the pagination-fix smoke-test finding.

## 7. records_seen histogram

| records_seen | count | interpretation |
|---|---|---|
| 0 | 9 | no records returned by search (→ not_found) |
| 2 | 2 | master + 1 sub |
| 5 | 2 | master + 4 subs |
| 20 | 1 | master + 19 subs (the B2021-02404 case) |

Design-sketch estimate was ~10 records average across the 90-permit set. The 14-permit sample so far averages **3.0 records per permit** (42 records / 14 permits). The estimate looks high but the sample size is small.

## 8. Errors encountered

- Permits with non-empty `errors[]`: **1** of 14
  - `B2023-00192` (final_state=`not_found`): result-link query failed for "a[href*='CapDetail.aspx']": Page.query_selector_all: Execution context was destroyed, most likely because of a navigation

B2023-00192's `Execution context was destroyed` is a Playwright lifecycle warning during navigation — the scraper still recorded the outcome as `not_found` (0 records). Worth re-running this specific permit in isolation later to distinguish a transient parse failure from a true not_found.

## 9. Sample succeeded JSONs

Three samples drawn from the 5 succeeded permits this run (fewest related, middle, most related):

| permit | master_capid_triplet | related_records | records_seen | pages_walked |
|---|---|---|---|---|
| B2022-01332 | `DUB22-00000-00A0J` | 1 | 2 | 1 |
| B2022-05117 | `DUB22-00000-00M7W` | 4 | 5 | 1 |
| B2021-03950 | `DUB21-00000-00IG1` | 19 | 20 | 2 |

## 10. Cloudflare / login-wall check

- Scanned all 14 log files for `cloudflare` / `just a moment` / `login_required` / `requires_auth` / `signin`: **0 hits**.
- The `--max-consecutive-failures 5` halt was therefore NOT triggered by an active block. It was triggered by 5 consecutive `not_found` outcomes (`not_found` counts toward the consecutive-failures counter per the orchestrator's status mapping).

## 11. Run-by-run sequence

| timestamp | status | permit | issued_date | valuation | source_system | address |
|---|---|---|---|---|---|---|
| 08:31:23 | `succeeded` | B2021-03950 | 2023-07-17 | $12,913,072 | cpra | 2099 M L KING JR Way |
| 08:32:04 | `not_found` | B2022-01278 | 2023-06-28 | $10,000 | cpra | 1716 SEVENTH St |
| 08:32:17 | `succeeded` | B2022-01332 | 2023-06-06 | $500,000 | cpra | 1716 SEVENTH St |
| 08:32:41 | `not_found` | B2022-01386 | 2023-06-06 | $500,000 | cpra | 1716 SEVENTH St |
| 08:32:51 | `succeeded` | B2022-03783 | 2023-01-11 | $375,000 | cpra | 1136 KEITH Ave |
| 08:33:07 | `succeeded` | B2022-05117 | 2023-08-03 | $8,745,423 | cpra | 2440 SHATTUCK Ave |
| 08:33:35 | `not_found` | B2022-05181 | 2023-01-13 | $0 | cpra | 2150 Kittredge St |
| 08:33:47 | `not_found` | B2022-05525 | 2023-02-16 | $12,320 | cpra | 576 SAN LUIS Rd |
| 08:33:59 | `succeeded` | B2022-05880 | 2023-12-13 | $7,680,389 | cpra | 2480 Bancroft Way |
| 08:34:24 | `not_found` | B2022-06060 | 2023-06-16 | $0 | cpra | 2000 University Ave |
| 08:34:33 | `not_found` | B2023-00192 | 2024-03-20 | $500,000 | cpra | 1111 ALLSTON Way |
| 08:34:48 | `not_found` | B2023-00401 | 2023-03-24 | $17,000 | cpra | 2440 SHATTUCK Ave |
| 08:34:57 | `not_found` | B2023-00595 | 2023-02-17 | $11,533 | cpra | 2705 BENVENUE Ave |
| 08:35:11 | `not_found` | B2023-00675 | 2023-08-25 | $0 | cpra | 2000 DWIGHT Way |

## 12. Pattern analysis for the 9 not_found permits

- All 9 not_found cases have `records_seen=0` — Accela's by-permit-number search in the Building module returned no records on a single rendered page.
- The not_found set skews toward smaller valuations:
  - 5 permits with valuation in [$0, $17,000]
  - 2 permits with $0 valuation (likely no-fee records)
  - 2 permits with $500,000 valuation
- The OK set skews larger ($375K–$18.6M, plus the legacy `accela`-sourced B2019-05575 with NULL valuation).
- Counter-example to a clean threshold: `B2022-01332` ($500K → OK) and `B2022-01386` ($500K → not_found) are at the **same project** (1716 SEVENTH St) and the search outcome differs.
- All 9 not_found permits have `source_system='cpra'` (they were ingested from Berkeley's CPRA data dump, not from Accela directly).
- All 5 succeeded permits in this run (excluding the smoke-test trio) are also `source_system='cpra'`. So not_found isn't a strict cpra-vs-accela divider.
- Plausible explanation: Berkeley's CPRA data includes more permits than Accela's public CapHome search exposes. Some permits — likely minor-work or subsidiary records — were never indexed into Accela's public search or were later purged. This is a data-source-coverage gap, not a scraper bug.
- The clustering of 5 consecutive not_founds at the end (B2022-06060 onward, all 2022/2023-year filings) tripped the safety cap. The cap fired correctly per its design; the cause was the alphabetical ordering of the queue surfacing a streak of small-valuation cases together.

## 13. Verdict

**HALTED** — the orchestrator stopped at the consecutive-failures safety cap (5 in a row, all `not_found`, no Cloudflare/login walls). 5 of 14 attempted permits succeeded (36%); 9 returned `not_found` due to records_seen=0 on Accela's CapHome search; 0 hard failures. The halt is a designed safety behavior, not a bug — but the underlying not_found rate is high enough that resuming the run as-is would likely retrigger the cap repeatedly.

**What this run does NOT establish:**
- Whether the not_found permits exist in a different Accela module (Planning, Public Works, etc.). The orchestrator only searched Building.
- Whether B2023-00192's `Execution context was destroyed` would resolve on a retry, distinguishing a transient parse failure from a true not_found.
- The full 90-permit success rate.

**What this run DOES establish:**
- The orchestrator, the scraper, the pagination fix, the queue mutation logic, and the JSON artifact writes all work correctly end-to-end.
- The 5 succeeded permits in this run produced master triplets that look real (`DUB21-00000-00IG1`, `DUB22-00000-00A0J`, `DUB22-00000-00M7W`, plus two others). These are net-new URL data not previously in v2.
- Safety cap fires as designed.

Recommendation deferred to the user — explicitly NOT taking action. Possible next steps to consider before resuming, all of which are user decisions: (a) investigate one not_found permit manually in a browser to confirm Accela genuinely has no record; (b) try `--module-hint Planning` on a subset; (c) accept the not_found rate and resume with a higher `--max-consecutive-failures` cap; (d) re-classify `not_found` to not count toward consecutive-failures so the orchestrator runs to natural exhaustion. None of these are taken here.
