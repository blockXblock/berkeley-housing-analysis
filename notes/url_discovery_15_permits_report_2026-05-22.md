# URL discovery run: 15 B-permits (permitted stage)

**Generated:** 2026-05-22T23:24:28
**Scope:** ran `scripts/run_url_discovery.py --limit 15` against the 15 new pending rows inserted earlier. Output to canonical paths. Post-polling-fix scraper. No CLI flag changes.

## Outcome at a glance

- Permits processed: **15 / 15**
- **Succeeded: 14** (single_result_redirect: 9, results_list: 5)
- **Failed: 1** (B2025-05247 — Accela returned HTTP 502 Bad Gateway)
- Total runtime: **266.8s** (~4.4 min); avg ~12s/permit incl. sleeps
- Stop reason: `Limit reached (15 permits)` — clean exit
- Consecutive failed (true-error) count at end: 0 (the 1 failure was last to second-last; B2025-05288 succeeded after)

## 1. Pre-run state

`url_discovery_queue`: succeeded=90, pending=15. Confirmed before launch.

## 2. Per-permit results

| permit | found | match_path | master_capid_triplet | rs | poll_s | dur_s | final_state | error |
|---|---|---|---|---|---|---|---|---|
| B2022-04987 | True | `results_list` | `DUB22-00000-00LXV` | 2 | 5.06 | 23.24 | `ok` |  |
| B2022-05881 | True | `single_result_redirect` | `DUB22-00000-00O0I` | 1 | 0.0 | 11.62 | `ok` |  |
| B2022-05957 | True | `results_list` | `DUB22-00000-00OAI` | 4 | 5.07 | 21.7 | `ok` |  |
| B2024-02508 | True | `single_result_redirect` | `DUB24-00000-00GS8` | 1 | 0.0 | 12.34 | `ok` |  |
| B2024-04964 | True | `single_result_redirect` | `DUB24-00000-00PPB` | 1 | 0.0 | 10.65 | `ok` |  |
| B2025-00168 | True | `results_list` | `DUB25-00000-0021P` | 2 | 5.07 | 19.16 | `ok` |  |
| B2025-00820 | True | `results_list` | `DUB25-00000-009IJ` | 2 | 5.06 | 17.97 | `ok` |  |
| B2025-01579 | True | `single_result_redirect` | `DUB25-00000-00ELP` | 1 | 0.0 | 10.4 | `ok` |  |
| B2025-02361 | True | `results_list` | `DUB25-00000-00HPK` | 2 | 5.07 | 17.94 | `ok` |  |
| B2025-02795 | True | `single_result_redirect` | `DUB25-00000-00J84` | 1 | 0.29 | 6.03 | `ok` |  |
| B2025-04241 | True | `single_result_redirect` | `DUB25-00000-00NMY` | 1 | 0.01 | 5.16 | `ok` |  |
| B2025-04363 | True | `single_result_redirect` | `DUB25-00000-00O51` | 1 | 0.01 | 6.68 | `ok` |  |
| B2025-04912 | True | `single_result_redirect` | `DUB25-00000-00PQC` | 1 | 0.01 | 5.7 | `ok` |  |
| B2025-05247 | False | `None` | `(none)` | 0 | None | 2.85 | `error` | Could not locate permit-number search input |
| B2025-05288 | True | `single_result_redirect` | `DUB25-00000-00QK8` | 1 | 0.0 | 5.01 | `ok` |  |

## 3. Distribution

| outcome | count |
|---|---|
| `found=True` via `single_result_redirect` | 9 |
| `found=True` via `results_list` | 5 |
| `found=False`, `final_state='error'` | 1 |
| `ambiguous` | 0 |

Pleasant pattern observation: in this 15-permit run, **5 permits triggered the multi-result `results_list` path** (B2022-04987, B2022-05957, B2025-00168, B2025-00820, B2025-02361 — most have a `records_seen` of 2 or 4, indicating master + REV/DEF subs). This is more multi-result variety than today's main 90-permit run, where almost everything was `single_result_redirect`. Indicates the 'permitted'-stage B-permits more often have related sub-records than the 'completed'/'under_construction' B-permits did.

Polling-loop telemetry (`auto_redirect_poll_seconds`):
- 5 results_list permits: poll ran the full ~5s budget (correct — neither auto-redirect signal ever fires on multi-result pages)
- 9 single_result_redirect permits: poll fired immediately (0.0/0.01/0.29 — all under 1s)
- 1 error permit: None (the error fired before reaching the polling block)

## 4. The failed permit (B2025-05247) — root cause

From the JSON:

```json
{
  "errors": ["Could not locate permit-number search input"],
  "metadata": {
    "page_title_initial": "accela.com | 502: Bad gateway",
    "final_state": "error",
    "scrape_duration_seconds": 2.85
  }
}
```

**Root cause: Accela returned an HTTP 502 Bad Gateway response page** instead of CapHome.aspx. The scraper landed on the 502 error page, captured its title ("accela.com | 502: Bad gateway") as `page_title_initial`, and then correctly reported that it couldn't find the search input on that page (because the 502 page doesn't have one). 2.85s total — fast fail.

This is a transient upstream failure unrelated to the scraper or the permit's existence in Accela. A retry on this permit (next URL discovery pass) would almost certainly recover it. The orchestrator left B2025-05247's queue row in `status='failed'`, with `error_message='Could not locate permit-number search input'` — visible for the operator to reset to `pending` and re-attempt.

## 5. Project 131 (811 Cedar) — 3 distinct triplets check

Three permits at the same address (811 Cedar):

| permit_number | master_capid_triplet | match_path |
|---|---|---|
| B2025-02361 | `DUB25-00000-00HPK` | results_list |
| B2025-02795 | `DUB25-00000-00J84` | single_result_redirect |
| B2025-04363 | `DUB25-00000-00O51` | single_result_redirect |

**All 3 distinct.** Accela treated them as separate records (no cross-permit confusion), as expected. The triplets are alphabetically near each other (HPK / J84 / O51) — consistent with their permit-number proximity (2361 / 2795 / 4363 all 2025-issued).

## 6. Final queue distribution

| status | count |
|---|---|
| `succeeded` | 104 |
| `failed` | 1 |
| `pending` | 0 |
| `ambiguous` | 0 |
| **TOTAL** | **105** |

Cumulative URL-discovery success: 104 of 105 = **99.0%**. Only B2025-05247 needs a retry.

## 7. Verdict

**PASS** — 14 of 15 succeeded with correct master triplets and proper path distribution (5 results_list + 9 single_result_redirect). The 1 failure is a transient Accela 502 unrelated to the scraper or permit-class behavior. 3 distinct projects-at-same-address resolved cleanly to 3 distinct triplets.

Recommendation for follow-up (NOT taken in this prompt): reset B2025-05247's queue row from `failed` → `pending` and re-run; expected to succeed on retry given the 502 was server-side and transient.
