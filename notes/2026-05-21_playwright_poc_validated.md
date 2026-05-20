# Playwright POC validated — Accela inspection extraction

**Date:** 2026-05-21
**Status:** POC complete. Production scraper design sketched, build in next session.

## What works

Anonymous Playwright extraction of Accela inspection records.

Validated against permit B2019-05574 (2352 Shattuck Phase II):
- 557 unique inspections extracted
- Date range 10/23/2020 to 01/19/2022 (full construction period)
- All 5 known 2022-01-14 final inspections present with correct inspector (MD)
- 0 duplicates
- 112 pages traversed in 250 seconds (~2.2 sec/page)

This confirms the architectural choices from yesterdays Accela reconnaissance:
JavaScript execution is required, anonymous access is sufficient, pagination
via __doPostBack works.

## What it took

Three iterations of debugging:

1. **First POC** (CC, ~15 min): pagination logic clicked next-page link via
   `page.evaluate(() => link.click())`. The click didnt actually trigger
   ASP.NETs postback; same page returned 151 times. Result: 25 unique inspections
   duplicated 81 times each (755 total rows). Reported SUCCESS despite
   error logs documenting an infinite loop.

2. **Fix attempt 1** (CC): switched to calling `__doPostBack(event_target, '')`
   directly via `page.evaluate()` instead of JS-evaluated `link.click()`.
   Added runtime dedup tracking. Got 70 unique inspections; pagination still
   failing intermittently due to wait conditions.

3. **Fix attempt 2** (CC): improved wait conditions to verify the table
   actually changed (first inspection_id on page must differ from previous
   page) before continuing. Hit MAX_PAGES=100 cap with 500 unique
   inspections. Adjusted cap to 120 after observing Accela shows 5 per
   page (not 25 as initially assumed). Final run: 557 unique inspections,
   0 duplicates, full date range.

## Key technical findings

- **Tab activation:** `&IsToShowInspection=Y` URL parameter is reliable.
  No need to click the Inspections tab.

- **Pagination mechanism:** ASP.NET `__doPostBack` must be called directly
  via `page.evaluate(f"__doPostBack('{event_target}', '')")`. JS-evaluated
  `link.click()` does NOT trigger the postback (the original bug). Playwright's
  native `page.click()` was not used; the fix is direct `__doPostBack` invocation.

- **Wait condition for pagination:** `wait_for_load_state("load")` plus
  verifying the first row inspection_id changed. Without the verification
  step, intermittent stale-page reads occur.

- **Rows per page:** Accela shows 5 inspection rows per page. For 553
  inspections thats ~111 pages.

- **Three-state pagination return:** `click_pagination()` returns `'success'`,
  `'last_page'`, or `'failed'`. The `'last_page'` state distinguishes legitimate
  run completion (no "Next >" link found) from actual pagination failures. The
  original code conflated "reached end of data" with "pagination broke."

- **Always use "Next >" link:** Page number anchors (1, 2, 3...) become stale
  after UpdatePanel refreshes. The "Next >" link is regenerated with a fresh
  postback target on each page, making it more reliable across postbacks.

- **Anonymous access works.** No login required for inspection data on
  Berkeley Accela. The 3.4MB authenticated CIC view vs 290KB anonymous
  requests difference appears to be entirely from JS execution, not from
  authentication.

## What CC did well and not well

**Did well:**
- Diagnosed the postback bug correctly after observing duplicate data
- Implemented the dedup-and-stop-on-repeat safety we asked for
- Documented the rows-per-page discovery and explained the cap adjustment

**Didnt do well:**
- First report claimed Status: SUCCESS / 755 inspections while the
  artifact had 25 unique inspections, 730 duplicates, and explicit errors
  in the errors array. Confident-summary-that-doesnt-match-artifact is
  a recurring CC pattern this session.
- Adjusted prompt-specified caps without explicit permission (raised
  MAX_PAGES from 100 to 120). The discovery (5 per page) was correct;
  the autonomous decision to adjust the prompts numeric constraint is
  a pattern worth noting.

**Lessons for future CC use:**
- Always verify the artifact directly, not CCs summary
- Numeric constraints in prompts should be more conservative on the
  expand-allowed side; CC adjusts them anyway
- Treat SUCCESS claims as hypotheses to verify, not conclusions

## Architecture decisions for the orchestrator (next session)

**Scope of first production run:** Completed and under_construction projects
only (~43 projects, ~80-120 permits). Focused on data that directly affects
the APR.

**Storage:** Two-phase. Scrape produces JSON files in a staging directory.
Separate ingest step reads JSON and writes to v2 database with provenance.
This allows review-before-ingest and re-ingest without re-scraping.

**Queue:** SQLite table tracking permit_id, permit_number, project_id,
status (pending/running/succeeded/failed), attempts, last_run_at, error.
Resumable on failure.

**Rate limiting:** 10-30 second delays between permits to reduce
detection risk.

**Anonymous access:** Continue using anonymous mode. Authentication
adds complexity without unlocking additional data.

## Dead code in POC to address during refactor

`get_postback_target_for_page()` (line 160) is defined but never called.
`click_pagination()` has its own inline postback-target lookup that searches
for the "Next >" link specifically. When the POC is refactored into a module
for the orchestrator, the dead function should be either removed or
consolidated with the inline logic in `click_pagination()`.

## What is unresolved

1. **Production scraper not yet built.** Next session.
2. **Ingest pipeline not yet built.** After scraper produces JSON.
3. **Inspection event schema in v2.** Where do inspections fit in v2s
   normalized schema? Probably need a new `inspections` table linked to
   `permits`. Schema design pending.
4. **The deduped POC output is in /tmp**, not durable. The first
   production scraper run will re-extract this data into the staging
   directory.

## Files

- `experiments/accela_scrape/playwright_inspections_poc.py` (this commit)
- `/tmp/playwright_poc_output/B2019-05574_inspections.json` (POC output,
  not committed; ~327KB, 557 inspections)
- `/tmp/playwright_poc_report.md` (CC report, not committed; superseded
  by this notes file)
