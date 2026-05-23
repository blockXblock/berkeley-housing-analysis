# URL discovery scraper — polling-loop fix for auto-redirect timing flakiness

**Generated:** 2026-05-22T16:54:56
**Target file:** `experiments/accela_scrape/url_discovery_scraper.py` (in-place edit)

## 1. Line range of edits

- Auto-redirect detection block: previously a one-shot check at lines ~528-562; now a polling loop wrapping the same two signals at **lines 549-573**.
- New metadata key written at **line 574**: `metadata['auto_redirect_poll_seconds']`.
- Fall-through to `results_list` unchanged (line 613).
- Outer block boundary still at line 513 (`# Step 2.5: single-result auto-redirect detection`).

Approximately +20 net lines added; nothing else in the file touched.

## 2. Algorithm summary

The dual-signal auto-redirect check (signal 1 = `page.url` regex; signal 2 = form-action via JS evaluator) is now wrapped in a polling loop with a 5-second deadline and a 0.5-second tick. Each iteration re-evaluates both signals. On first match the loop breaks and the master is built normally. After the deadline with no match, control falls through to the existing `results_list` path unchanged. A new `metadata['auto_redirect_poll_seconds']` field records how long the polling took (rounded to 2 decimals), letting us observe in post-run JSONs whether the recovery actually needed polling or fired immediately. The regex and JS-eval payload were hoisted to module-private constants inside the function (`_CAPID_RE`, `_FORM_ACTION_JS`) so they're compiled once per `discover_url` call rather than each tick.

## 3. AST + --help validation

| check | result |
|---|---|
| `python3 -c "import ast; ast.parse(...)"` | **AST OK** |
| `python3 experiments/accela_scrape/url_discovery_scraper.py --help` | exits 0; same CLI surface as before |

## 4. B2023-02303 4-run table (verifies flakiness gone)

Per the prior diagnostic, this permit was 3/4 in headless runs before this fix. After the fix:

| run | found | match_path | poll_seconds | scrape_duration_s | master_triplet |
|---|---|---|---|---|---|
| 1 | True | single_result_redirect | 0.00 | 8.72 | DUB23-00000-00EYO |
| 2 | True | single_result_redirect | 0.53 | 10.27 | DUB23-00000-00EYO |
| 3 | True | single_result_redirect | 0.01 | 9.55 | DUB23-00000-00EYO |
| 4 | True | single_result_redirect | 0.01 | 8.50 | DUB23-00000-00EYO |

**4 of 4 runs succeeded** with the expected master triplet. Polling cost was negligible — 3 of 4 runs fired on the first iteration (signal already present at the moment polling started); 1 run (the formerly-flaky case) needed a single 0.5s tick before the form-action signal became readable.

## 5. Backward-compat: B2022-01278 + B2019-05575

| permit | found | match_path | master triplet | related | poll_seconds | scrape_duration_s |
|---|---|---|---|---|---|---|
| B2022-01278 | True | `single_result_redirect` | DUB22-00000-009C4 | 0 | 0.52 | 11.32 |
| B2019-05575 | True | `results_list` | DUB19-00000-00KIL | 2 | 5.07 | 25.28 |

- B2022-01278 (a known single_result_redirect case): unchanged behavior — succeeded via the same path with the expected triplet.
- B2019-05575 (a multi-result results-list case): still works via the results_list path with the expected master + 2 related records. Note `poll_seconds = 5.07` — the polling loop ran its full 5s budget before falling through, since neither signal ever fires on a multi-result page. This is the expected worst-case cost: **~5s overhead per multi-result permit**. Per-permit total duration went from ~20s pre-fix to ~25s post-fix; for the 31 already-succeeded multi-result permits in the queue, a full re-run would add ~2.6 minutes total. Acceptable.

## 6. Verdict

**PASS** — B2023-02303 is now 4/4 deterministic (previously 3/4 flaky), B2022-01278 still succeeds via single_result_redirect, B2019-05575 still succeeds via results_list with full related-records enumeration. No regression on either known-working case. The 5-second worst-case polling cost on multi-result permits is acceptable given the recovery of the timing-race failures.

Cost-benefit summary:
- Cost: ~0.5–5s per permit (negligible when signal arrives fast, full 5s on legitimate multi-result/not_found cases).
- Benefit: eliminates the auto-redirect timing race that produced the 5 residual not_found permits from the post-fix full-rerun (per `/tmp/post_fix_full_rerun_report.md`). Likely recovery rate on those 5 if re-attempted: high, though not yet measured.

Next step (not taken in this prompt): reset the 5 stubborn permits and re-run with the polling-loop fix to confirm recovery at scale.
