# Post-fix batch-of-5 verification report

**Generated:** 2026-05-22T15:13:02
**Scope:** validate the single-result auto-redirect fix at small scale by resetting 5 diverse not_found permits to pending and re-running the orchestrator on just those 5.

## Outcome at a glance

- Permits attempted: **5 / 5**
- **Succeeded: 2** (both via the new `single_result_redirect` path)
- **Still not_found: 3** (all 3 are `Alteration` work-type permits)
- Cloudflare / login walls: none
- True failures (`final_state='error'`): none
- Total runtime: **63.2s** (~12.6s/permit avg)

## 1. The 5 picks (diverse not_found permits)

Filtered from the 59 not_found in `/tmp/cpra_join_90_permits.csv`, chosen to span work_type, year, and units-added variety.

| permit | work_type | occ_type | units_added | issued | address | description |
|---|---|---|---|---|---|---|
| B2022-01386 | New | R-3 Residential: Dwellings (1 or 2  | (null) | 2023-06-06 | 1716 SEVENTH St | Construct new two-story single family residence. |
| B2024-05471 | Demolition | U Private Garages, Carports, Sheds, | 0.0 | 2025-06-25 | 2641 COLLEGE Ave | Demolish existing 384SF wood framed detach garage |
| B2023-02303 | Alteration | R-3 Residential: Dwellings (1 or 2  | (null) | 2023-05-26 | 1716 SEVENTH St | Remove existing roof & install 2.016 KW PV solar t |
| B2024-03884 | Alteration | R-3 Residential: Dwellings (1 or 2  | (null) | 2024-12-10 | 2641 COLLEGE Ave | Unit #A, First Floor. Add bathroom & laundry close |
| B2023-04430 | Alteration | R-3 Residential: Dwellings (1 or 2  | 1.0 | 2024-07-24 | 1515 DERBY St | New 553SF ADU to be within the existing footprint  |

## 2. Reset

Transactionally reset 5 rows in `/tmp/cic_recon_queue_url_discovery.db` from `status='not_found'` to `status='pending'`, with `attempts=0`, `last_attempt_at/error_message/output_file/succeeded_at=NULL`. Rowcount: 5 affected.

Pre-run queue state: pending=5, succeeded=31, not_found=54.

## 3. Orchestrator invocation

```
python3 scripts/run_url_discovery.py \
  --queue-db /tmp/cic_recon_queue_url_discovery.db \
  --output-dir data/raw/accela_url_discovery \
  --log-dir logs \
  --limit 5 --sleep-min 2 --sleep-max 10
```

Stop reason: `Limit reached (5 permits)`. Chromium launched once, reused across all 5. Inter-permit sleeps: 2.3s, 5.0s, 7.3s, 8.2s.

## 4. Per-permit results

| permit | found | master triplet | match_path | records_seen | pages_walked | duration_s | final_state |
|---|---|---|---|---|---|---|---|
| B2022-01386 | True | `DUB22-00000-00A8H` | `single_result_redirect` | 1 | 0 | 16.25 | `ok` |
| B2024-05471 | True | `DUB24-00000-00RBG` | `single_result_redirect` | 1 | 0 | 5.64 | `ok` |
| B2023-02303 | False | `(none)` | `results_list` | 0 | 1 | 5.31 | `not_found` |
| B2024-03884 | False | `(none)` | `results_list` | 0 | 1 | 5.58 | `not_found` |
| B2023-04430 | False | `(none)` | `results_list` | 0 | 1 | 5.56 | `not_found` |

Two recovered via `single_result_redirect` (the new path). Three remained `not_found` — they fell through to the `results_list` path and saw 0 records there (i.e., neither signal of the fix detected a single-result CapDetail page; the search results page rendered with no result anchors).

## 5. Queue rows post-run

| permit | status | attempts | succeeded_at | output_file |
|---|---|---|---|---|
| B2022-01386 | `succeeded` | 1 | 2026-05-22T15:10:39.836515 | `data/raw/accela_url_discovery/B2022-01386.json` |
| B2024-05471 | `succeeded` | 1 | 2026-05-22T15:11:24.715478 | `data/raw/accela_url_discovery/B2024-05471.json` |
| B2023-02303 | `not_found` | 1 | (null) | `data/raw/accela_url_discovery/B2023-02303.json` |
| B2024-03884 | `not_found` | 1 | (null) | `data/raw/accela_url_discovery/B2024-03884.json` |
| B2023-04430 | `not_found` | 1 | (null) | `data/raw/accela_url_discovery/B2023-04430.json` |

Final queue distribution:

| status | count |
|---|---|
| `succeeded` | 33 |
| `not_found` | 57 |
| `pending` | 0 |
| `ambiguous` | 0 |
| `failed` | 0 |

JSON files in `data/raw/accela_url_discovery/`: **87** (unchanged — the 5 not_found JSONs were overwritten, 2 with new master content and 3 with refreshed not_found content).

## 6. Distribution of outcomes

| outcome | count |
|---|---|
| `found=True` via `single_result_redirect` | 2 |
| `found=True` via `results_list` | 0 |
| `found=False` (still `not_found`) | 3 |
| `ambiguous=True` | 0 |
| `final_state='error'` | 0 |

## 7. Verdict

**PARTIAL** — 2 of 5 (40%) recovered. Better than the pre-fix 0 of 5, and the recovered permits are real (verified master triplets, no errors), but well below the PASS criterion of 4-5 of 5.

### Pattern in what the fix recovers vs leaves behind

| WorkType | succeeded | not_found |
|---|---|---|
| New | 1 (B2022-01386) | 0 |
| Demolition | 1 (B2024-05471) | 0 |
| Alteration | 0 | 3 (B2023-02303, B2024-03884, B2023-04430) |

All 3 still-not_found permits are `Alteration`. All 2 succeeded permits are `New` or `Demolition`. Same sample size is small, but this aligns exactly with Part 4's CPRA-join finding ("Alteration" was 8 ok / 42 not_found, the dominant class of failures). Notable counter-example to a project-level block: B2022-01386 (New, 1716 SEVENTH St) succeeded while B2023-02303 (Alteration solar PV, also 1716 SEVENTH St) failed — same project, same address, different outcomes by work type.

Best interpretation: Accela's CapHome.aspx permit-number search appears to index `New` and `Demolition` permits (which become master records with a discrete CapDetail page) but does NOT index most `Alteration` permits — even when CPRA confirms they exist. The user's manual finding for B2022-01278 was via Dashboard.aspx, a different entry point; this hint suggests `Alteration` permits may need a fundamentally different search route (Dashboard, by-address search, or owner/applicant search) rather than a tweak to the current scraper.

### What the fix DOES achieve (confirmed)

- B2022-01386: previously not_found → now found (`DUB22-00000-00A8H`) via single_result_redirect
- B2024-05471: previously not_found → now found (`DUB24-00000-00RBG`) via single_result_redirect
- B2019-05575 (separately verified in fix-prompt step 6): still found via results_list, unchanged from baseline (`DUB19-00000-00KIL`, 2 related records)
- 31 originally-succeeded permits in the queue: untouched by this run; still status='succeeded'

Per-permit summary:
- **B2022-01386** New construction @ 1716 SEVENTH St (2023) — **SUCCEEDED via single_result_redirect** → `DUB22-00000-00A8H`
- **B2024-05471** Demolition of detached garage @ 2641 COLLEGE Ave (2025) — **SUCCEEDED via single_result_redirect** → `DUB24-00000-00RBG`
- **B2023-02303** Solar PV install @ 1716 SEVENTH St (2023) — **still not_found**
- **B2024-03884** Add bathroom/laundry to Unit A @ 2641 COLLEGE Ave (2024) — **still not_found**
- **B2023-04430** New 553SF ADU within existing footprint @ 1515 DERBY St (2024) — **still not_found**

## 8. Recommendation (informational only — not taken)

Before processing the remaining 54 not_found permits, two questions are worth answering:

1. **Is CapHome.aspx genuinely missing Alteration permits, or is the scraper landing on a different page state for them?** A targeted non-headless debug run on one Alteration permit (e.g., B2023-02303) — similar to the diagnosis we did for B2022-01278 — would reveal whether the scraper is on CapHome with 0 results, on some other page entirely, or on a CapDetail page neither signal can detect.

2. **Should the URL-discovery scope be revised?** If Alteration permits are simply not indexed in Accela's public search-by-permit-number, no scraper improvement will recover them — they need either a different search route (Dashboard, by-address) or to be accepted as data-source limitations. Part 4 of the CPRA audit found 42 of 59 not_found permits are Alteration; even a perfect single-result-redirect fix won't change that.

Processing the remaining 54 with the current fix is likely to produce roughly: ~5 New, ~7 Demolition recoveries (all single-result auto-redirects) and ~42 Alteration / 1 Addition / 2 Sign / 1 (empty) remaining not_found. Expected post-run state: succeeded ≈ 40-45, not_found ≈ 45-50. Worth doing if the per-permit cost is low, but the analytical value is limited unless the Alteration category gets its own treatment.
