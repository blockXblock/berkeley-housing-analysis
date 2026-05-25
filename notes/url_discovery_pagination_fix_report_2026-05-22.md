# URL discovery scraper — results-page pagination fix

**Generated:** 2026-05-22T08:10:41
**Target file:** `experiments/accela_scrape/url_discovery_scraper.py` (in-place edit)

## 1. Patterns mirrored from `inspection_scraper.py::_click_pagination`

- JS evaluator scans every `<a>` for one whose text starts with `next` (case-insensitive); reads the `__doPostBack` target from either `onclick` or `href` via regex.
- Invokes `__doPostBack` by `page.evaluate(f"__doPostBack('{target}', '')")` rather than `click()` — same rationale (UpdatePanel refreshes invalidate cached hrefs).
- A missing Next link is treated as the natural last-page terminator (success), not a failure.
- Polls for DOM change at 0.5s intervals up to 8s after each click.
- Stuck-state detection: if the new page's identifier set equals the previous page's set, append an error and abort the loop.
- Errors accumulate in the caller-supplied `errors[]`; the function never raises.
- Max-page safety cap (`max_pages=30` here; inspection table uses 200 because real permits can have hundreds of inspection pages, whereas results-page pagination is bounded by sub-record count).
- Re-extracts the postback target on every iteration (Berkeley's UpdatePanel rotates the target).
- Row identity for dedup uses the CapDetail `href` (each record has a unique CapDetail anchor; analogue of the inspection scraper's inspection-ID set).
- Master identification rule is applied AFTER the walk completes, against the deduplicated full-record list — unchanged from the pre-fix flow.

## 2. Specific edits to `url_discovery_scraper.py`

Two changes only:

### a. Added two helper functions (lines 261–370)

- `_results_page_next_postback(page)`: returns the `__doPostBack` target string for the results-page Next link, or `None` if no Next link is present.
- `_walk_all_result_pages(page, search_query, errors, max_pages=30)`: parses page 1; loops while Next exists; clicks Next via `__doPostBack`; polls 8s/0.5s for the rendered href set to change; dedups across pages by href; returns `(records, pages_walked)`. Never raises.

Both helpers live between `_parse_result_rows` and `_extract_field_from_capdetail` in the module. The existing `_parse_result_rows` is unchanged and is now called once per page from inside the walker.

### b. Replaced the single-page parse with the walker (lines 515–519)

Old:
```python
print("[3] Parsing results page...")
records = _parse_result_rows(page, permit_number, errors)
metadata["records_seen"] = len(records)
print(f"    {len(records)} candidate record(s) seen")
```

New:
```python
print("[3] Walking results page(s) (with pagination)...")
records, pages_walked = _walk_all_result_pages(page, permit_number, errors)
metadata["records_seen"] = len(records)
metadata["pages_walked"] = pages_walked
print(f"    {len(records)} unique record(s) seen across {pages_walked} page(s)")
```

`discover_url`'s signature, the return-dict shape, and all helpers other than these two additions are untouched. Metadata gains exactly one new key: `pages_walked`.

## 3. Syntactic checks

| check | result |
|---|---|
| `python3 -c "import ast; ast.parse(...)"` | **AST OK** |
| `python3 url_discovery_scraper.py --help` | exits 0, lists same flags as before |
| `from experiments.accela_scrape import url_discovery_scraper; print(...__doc__)` | importable, docstring intact |

## 4. B2021-02404 smoke test result (post-fix)

| field | value |
|---|---|
| final_state | `ok` |
| found | `True` |
| ambiguous | `False` |
| master.permit_number_displayed | `B2021-02404` |
| master.capid_triplet | `DUB21-00000-00EZS` (expected DUB21-00000-00EZS) |
| pages_walked | `2` |
| records_seen | `20` |
| related_records count | `19` |
| scrape_duration_seconds | `35.87` |
| errors[] | `[]` |

### Sub-record breakdown by record_type

| record_type | count |
|---|---|
| DEF | 12 |
| REV | 7 |

### Notes ambiguity resolved

- The hand-copied note said `total_records=20` AND described the breakdown as `REV01–REV19 and DEF01–DEF17` (which would imply 36 subs). These were inconsistent.
- The scraper resolves it: **20 total records = 1 master + 19 subs**. The `total_records=20` figure was correct; the `REV01–REV19 and DEF01–DEF17` breakdown text was wrong. Actual breakdown: **7 REV + 12 DEF = 19 subs**.

## 5. Verdict

**PASS** — pagination works, master triplet matches the expected DUB21-00000-00EZS, pages_walked=2, records_seen=20, related_records=19 (= records_seen − 1), no errors. The scraper is ready for the 90-permit run.

