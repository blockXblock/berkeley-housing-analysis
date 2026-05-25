# URL discovery scraper — single-result auto-redirect fix

**Generated:** 2026-05-22T15:06:22
**Target file:** `experiments/accela_scrape/url_discovery_scraper.py` (in-place edit)

## 1. Line range of edits

New block inserted in `_discover_with_page`, **lines 511–601** (post-edit numbering). The block sits between the post-search runtime check and the Step 3 results-page walk, so it intercepts the single-result-redirect case before the multi-result walker runs.

Key anchor lines:
- 513: `# Step 2.5: single-result auto-redirect detection` (new section banner)
- 529-562: dual-signal detection — `page.url` regex (signal 1), then form-action JS evaluator (signal 2 fallback)
- 563-598: success-path return when `sr_triplet_match` is truthy
- 600: `metadata['match_path'] = 'results_list'` set when falling through to the existing path

## 2. Algorithm summary

After the search form is submitted and the page settles, the new block runs two probes in sequence to decide whether Accela auto-redirected to the master's CapDetail page (the single-result case):

1. **Signal 1 — `page.url`:** look for `CapDetail.aspx?...capID1=…&capID2=…&capID3=…` in the current browser URL. This catches the case where Accela performed a hard redirect after the search submit.
2. **Signal 2 — form action:** if (1) misses, evaluate JS over the page's `<form>` elements to find one whose `action` attribute starts with `./CapDetail.aspx?capID1=…`. This catches the case where Accela swapped DOM content via ASP.NET UpdatePanel without changing the browser URL.

Either signal yields a capID triplet. The block then runs the existing `_extract_field_from_capdetail` helper to pull filed/issued/finaled/valuation off the loaded CapDetail DOM, builds the `master` dict directly with `permit_number_displayed = permit_number` (the search query — guaranteed to match because Accela redirected only for an exact match), sets `metadata.match_path = 'single_result_redirect'`, `records_seen = 1`, `pages_walked = 0`, `final_state = 'ok'`, and returns. `related_records` is left empty: enumerating sub-records from the CapDetail page itself is a deferred enhancement.

If neither signal fires, control falls through with `metadata.match_path = 'results_list'` and the existing `_walk_all_result_pages` flow runs unchanged.

**Backward-compat properties:**
- `discover_url` signature unchanged.
- Top-level return-dict keys unchanged.
- `metadata.match_path` is a new additive key; everything else preserved.
- The multi-result path (the one all 31 previously-succeeded permits took) is reachable when both signals miss, which is exactly when the page is a CapHome results list rather than a CapDetail page.

**Iteration note:** the first attempt at this fix used only Signal 1. It worked in a standalone probe but failed inside the scraper run — likely a timing race where `page.url` had not yet propagated when `_discover_with_page` inspected it, despite `wait_for_load_state('networkidle')` having returned. Adding Signal 2 (form action via JS) as a fallback resolved the case; the form action is rendered server-side and is present as soon as the DOM is loaded, regardless of URL-update timing.

## 3. Validation

| check | result |
|---|---|
| `python3 -c "import ast; ast.parse(...)"` | **AST OK** |
| `python3 scripts/run_url_discovery.py --help` _(unchanged orchestrator)_ — not re-run, no edit | n/a |
| `python3 experiments/accela_scrape/url_discovery_scraper.py --help` | exits 0, same flags as before |
| `from experiments.accela_scrape import url_discovery_scraper; print(...__doc__[:300])` | importable; docstring intact |

## 4. B2022-01278 post-fix result (previously NOT_FOUND)

| field | value |
|---|---|
| final_state | `ok` |
| found | `True` |
| ambiguous | `False` |
| master.permit_number_displayed | `B2022-01278` |
| master.capid_triplet | **`DUB22-00000-009C4`** (expected `DUB22-00000-009C4`) |
| master.capdetail_url | `https://aca-prod.accela.com/BERKELEY/Cap/./CapDetail.aspx?Module=Building&TabName=Building&capID1=DUB22&capID2=00000&capID3=009C4&agencyCode=BERKELEY&IsToShowInspection=` |
| match_path | **`single_result_redirect`** |
| records_seen | `1` |
| pages_walked | `0` |
| related_records count | `0` |
| scrape_duration_seconds | `9.45` |
| errors | `[]` |

Capture artifacts: `/tmp/scraper_post_fix_B2022-01278.json` and `/tmp/scraper_post_fix_B2022-01278/` (debug dir — empty for this run because the success path doesn't trigger `_save_debug`).

Note: the `capdetail_url` contains `/Cap/./CapDetail.aspx?...` (a literal `./` mid-path) because Signal 2 resolved the relative form action via `_absolutize`. The URL is functionally correct (browsers normalize `./`), but a future cleanup could strip the redundant segment.

## 5. B2019-05575 post-fix result (backward-compat check)

| field | value |
|---|---|
| final_state | `ok` |
| found | `True` |
| master.capid_triplet | **`DUB19-00000-00KIL`** (matches smoke baseline) |
| match_path | **`results_list`** (NOT single_result_redirect — correct) |
| records_seen | `3` |
| pages_walked | `1` |
| related_records count | `2` |
| errors | `[]` |
| scrape_duration_seconds | `~20s` |

The multi-result path is fully preserved: same master triplet, same records_seen, same related_records count as the original smoke test. The fix is additive.

## 6. Verdict

**PASS** — B2022-01278 now succeeds via the `single_result_redirect` path (master `DUB22-00000-009C4`, no errors, 9.5s) AND B2019-05575 still succeeds via the `results_list` path (master `DUB19-00000-00KIL`, 2 related records, 20s) with identical results to the smoke-test baseline. The fix is non-regressing for the multi-result case and recovers the previously-broken single-result case.

Caveat: only one previously-not_found permit (B2022-01278) and one previously-ok permit (B2019-05575) have been tested. Re-running URL discovery for the other 58 not_found permits is the natural next step but was deliberately not done in this prompt per the task's stop-here instruction.
