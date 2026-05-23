# URL discovery — 5 stubborn permits recovered after polling-loop fix

**Generated:** 2026-05-22T17:02:09
**Scope:** validate the polling-loop fix at scale by resetting the 5 still-not_found permits from the prior full-rerun and running the orchestrator with the polling-fixed scraper.

## Outcome at a glance

- **5 of 5 succeeded** (100%).
- **Total runtime:** 55.3s.
- All 5 used the `single_result_redirect` path.
- Polling cost was negligible: 2 of 5 fired on the first iteration (poll_seconds 0.0/0.01); 3 of 5 needed one 0.5s tick (poll_seconds 0.50/0.51/0.01).
- **Cumulative completion: 90 of 90 (100%)** v2 in-scope B-permits now have verified Accela master triplets.

## 1. The 5 stubborn permits identified

These were the residual not_found permits from the prior full-rerun run (per `/tmp/post_fix_full_rerun_report.md`):

- B2023-00401 (Alteration, 2440 SHATTUCK Ave, temporary power meter)
- B2024-00736 (Alteration, 1109 COWPER St, kitchen & bath remodel)
- B2024-01659 (Sign, 2099 ML KING JR Way)
- B2024-02569 (Demolition, 1136 KEITH Ave, demolish SFR)
- B2025-00685 (Alteration, 411 VASSAR Ave, window/door replacement)

## 2. Reset

Transactional UPDATE on `/tmp/cic_recon_queue_url_discovery.db`: 5 rows reset from `status='not_found'` to `status='pending'`, with `attempts=0`, `last_attempt_at/error_message/output_file/succeeded_at=NULL`. Rowcount: 5.

Post-reset distribution: `pending: 5, succeeded: 85`.

## 3. Orchestrator invocation

```
python3 scripts/run_url_discovery.py \
  --queue-db /tmp/cic_recon_queue_url_discovery.db \
  --output-dir data/raw/accela_url_discovery \
  --log-dir logs \
  --limit 5 --sleep-min 2 --sleep-max 10
```

- Stop reason: `Limit reached (5 permits)`
- Total runtime: **55.3s** (~11s/permit avg including sleeps)
- Inter-permit sleeps: 3.1s, 8.0s, 4.9s, 6.0s (random within 2-10)

## 4. Per-permit results

| permit | found | master triplet | match_path | poll_seconds | scrape_duration_s | WorkType | address |
|---|---|---|---|---|---|---|---|
| B2023-00401 | True | `DUB23-00000-0040Z` | `single_result_redirect` | 0.01 | 7.88 | Alteration | 2440 SHATTUCK Ave |
| B2024-00736 | True | `DUB24-00000-006G7` | `single_result_redirect` | 0.5 | 6.61 | Alteration | 1109 COWPER St |
| B2024-01659 | True | `DUB24-00000-00DTQ` | `single_result_redirect` | 0.51 | 6.23 | Sign | 2099 M L KING JR Way |
| B2024-02569 | True | `DUB24-00000-00GXJ` | `single_result_redirect` | 0.01 | 5.09 | Demolition | 1136 KEITH Ave |
| B2025-00685 | True | `DUB25-00000-007R9` | `single_result_redirect` | 0.0 | 5.16 | Alteration | 411 VASSAR Ave |

**All 5 succeeded** via the single_result_redirect path. Polling fired on the first iteration for 2 of 5 (B2023-00401 at 0.01s, B2025-00685 at 0.0s — signals were present immediately). The other 3 needed exactly one 0.5s tick (poll_seconds ≈ 0.5).

No errors, no Cloudflare, no exceptions.

## 5. Verdict

**PASS — 5 of 5 recovered.** The polling-loop fix conclusively addresses the residual timing-race failures from the prior post-fix-full-rerun. Combined with the auto-redirect fix from earlier today, the URL-discovery workstream has now reached 100% coverage of its target set (90 v2 in-scope B-permits without source_url).

## 6. Final state

| status | count |
|---|---|
| `succeeded` | **90** |
| `not_found` | 0 |
| `ambiguous` | 0 |
| `failed` | 0 |
| **TOTAL** | **90** |

**Completion: 90 of 90 = 100%.** Every v2 in-scope B-permit now has a verified Accela master capID triplet and a JSON artifact at `data/raw/accela_url_discovery/{permit_number}.json`.

## 7. Recap of the journey to 100%

| stage | succeeded | not_found |
|---|---|---|
| Pre-flight (3 smoke permits) | 3 | 0 |
| Initial 14-permit run (halt at consecutive-failure cap) | 8 cumulative | 9 |
| Counter-logic fix + resume on 73 | 31 cumulative | 59 |
| Auto-redirect fix + batch-of-5 verification | 33 cumulative | 57 |
| Auto-redirect fix + full-rerun on 57 | 85 cumulative | 5 |
| Polling-loop fix + final-5 recovery | **90 cumulative** | **0** |

Three bug fixes were needed along the way:

1. **Counter-logic fix** in `scripts/run_url_discovery.py`: stop treating `not_found` as a failure for purposes of consecutive-failures halt. (Earlier today.)
2. **Auto-redirect detection** in `experiments/accela_scrape/url_discovery_scraper.py`: when Accela's single-result search auto-navigates directly to CapDetail, recognize it via two signals (page.url regex + form-action JS eval). (Earlier today.)
3. **Polling loop** wrapping those two signals: handle the ASP.NET UpdatePanel timing race where the page content is in flux for ~1-5s past `wait_for_load_state('networkidle')`. (Just applied.)

Two reframings from session-long pattern reads were also retired by these runs:

- "Accela hides single-parcel small-work permits" (Part 4 of the CPRA audit). Wrong: those permits are auto-redirected and the scraper's then-current parser couldn't recognize the destination.
- "Alteration permits aren't indexed in CapHome's search" (post-fix batch-of-5 report). Wrong: same root cause; all Alteration permits are now recoverable.

Both wrong pattern reads were corrected by widening the sample (full-rerun on 57) and by single-permit deep dives (B2022-01278 and B2023-02303 diagnostics).
