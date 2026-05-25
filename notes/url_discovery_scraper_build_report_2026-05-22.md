# url_discovery_scraper build report

**Generated:** 2026-05-22T07:55:34
**Module:** `experiments/accela_scrape/url_discovery_scraper.py`
**Lines:** 712

## 1. Patterns mirrored from `inspection_scraper.py`

- **Sync Playwright API** (`sync_playwright()`, `page.goto`, `page.query_selector`, `page.evaluate`). No mixing of async.
- **Module-level functions, no class.** Public `discover_url(...)` plus private `_helpers`.
- **Public signature shape:** positional `permit_number`, keyword-only arguments after `*` for `headless`, `max_runtime_seconds`, `debug_dir`, plus the new `page` injection.
- **Returns a dict; never raises.** Errors accumulate in `results['errors']: list[str]`; an outer try/except wraps the core flow as a last-resort guard.
- **`metadata` with a `final_state` field** (`ok` / `not_found` / `ambiguous` / `error`), mirroring inspection_scraper's `final_pagination_state` semantics.
- **`headless: bool = True`** plus `slow_mo=50` when headful (matches inspection_scraper).
- **Initial nav** uses `wait_until='networkidle'` with a 60s timeout; same UA and viewport (`1400x900`).
- **Debug artifacts** are saved only when `debug_dir` is provided; screenshot + HTML named `{permit_number}_{timestamp}_{step}.png/.html`.
- **`if __name__ == '__main__':` block** with argparse, same convention (`--headful`, `--debug-dir`).
- **Progress printed to stdout** (so the orchestrator's logging shim can capture it).
- **`PlaywrightTimeout` imported as alias** (`from playwright.sync_api import ..., TimeoutError as PlaywrightTimeout`).

## 2. Module path and line count

| field | value |
|---|---|
| Path | `experiments/accela_scrape/url_discovery_scraper.py` |
| Lines | 712 |
| Executable | yes (chmod +x) |

## 3. Public function signature (live, imported)

```python
discover_url(permit_number: str, *, headless: bool = True, max_runtime_seconds: int = 120, debug_dir: pathlib.Path | None = None, page: playwright.sync_api._generated.Page | None = None, module_hint: str = 'Building') -> dict
```

## 4. Helper functions (name + one-line purpose)

| function | purpose |
|---|---|
| `_build_search_url` | (no docstring) |
| `_classify_displayed` | Return ('master', None) \| ('sub', 'REV'\|'DEF') \| ('other', None). |
| `_parse_capid_triplet` | Return (capid1, capid2, capid3, full_url) or (None, None, None, href) on failure. |
| `_absolutize` | (no docstring) |
| `_save_debug` | Save screenshot and HTML for debugging. No-op if debug_dir is None. |
| `_is_login_or_block` | Detect login/cloudflare interstitials. Returns a short tag or None. |
| `_try_fill_permit` | Try each candidate selector to locate the permit-number input and fill it. |
| `_try_click_search` | Try each candidate selector to locate and click the search button. |
| `_parse_result_rows` | Return a list of records visible on the results page: |
| `_extract_field_from_capdetail` | Look for any of the label variants in the page text. When found, return |
| `_discover_with_page` | (no docstring) |
| `discover_url` | Discover the Accela CapDetail URL and core fields for a permit, plus |

## 5. `--help` output

```
usage: url_discovery_scraper.py [-h] [--headful] [--debug-dir DEBUG_DIR]
                                [--max-runtime-seconds MAX_RUNTIME_SECONDS]
                                [--module-hint MODULE_HINT]
                                permit_number

Discover Accela CapDetail URL + fields for a permit.

positional arguments:
  permit_number         Permit number to search (e.g., B2019-05575)

options:
  -h, --help            show this help message and exit
  --headful             Run with a visible browser (for debugging)
  --debug-dir DEBUG_DIR
                        Where to save screenshots/HTML on failure
  --max-runtime-seconds MAX_RUNTIME_SECONDS
                        Per-permit time budget (default: 120)
  --module-hint MODULE_HINT
                        CapHome module context (default: Building)
```

## 6. AST parse result

```
python3 -c "import ast; ast.parse(open('experiments/accela_scrape/url_discovery_scraper.py').read())"  # AST OK
```

## 7. `discover_url` docstring (as imported)

```
Discover the Accela CapDetail URL and core fields for a permit, plus
any related sub-records (REV / DEF) tied to the same master.

Parameters
----------
permit_number : str
    Berkeley permit number to search (e.g., "B2019-05575").
headless : bool, default True
    Run Chromium headless. Ignored if a `page` is supplied.
max_runtime_seconds : int, default 120
    Total time budget for the discovery attempt.
debug_dir : pathlib.Path or None
    If provided, on any error or unrecognized state save a screenshot
    and full-page HTML named `{permit_number}_{timestamp}_{step}.png/.html`.
page : playwright.sync_api.Page or None
    Optional existing Playwright Page to reuse (e.g., from a long-lived
    orchestrator session). If None, Chromium is launched and closed.
module_hint : str, default "Building"
    Selects the CapHome search context (Building / Planning / etc.).

Returns
-------
dict
    Always a dict. Never raises. Shape per
    notes/2026-05-22_url_discovery_design_sketch.md section 3:

        {
          "permit_number": str,
          "search_url": str,
          "found": bool,
          "ambiguous": bool,
          "master": {
            "permit_number_displayed": str,
            "capid_triplet": str,
            "capid1": str, "capid2": str, "capid3": str,
            "capdetail_url": str,
            "filed_date": str | None,
            "issued_date": str | None,
            "finaled_date": str | None,
            "valuation": str | None,
          } | None,
          "related_records": [
            {
              "permit_number_displayed": str,
              "record_type": "REV" | "DEF",
              "capid_triplet": str,
              "capid1": str, "capid2": str, "capid3": str,
              "capdetail_url": str,
            },
            ...
          ],
          "errors": list[str],
          "metadata": {
            "module_hint": str,
            "records_seen": int,
            "final_state": "ok" | "not_found" | "ambiguous" | "error",
            "scrape_duration_seconds": float,
            ...
          },
        }
```

## Notes for the smoke test (next prompt)

Two assumptions are baked into this scraper that smoke-testing will validate or refute:

1. **Search-input selector.** The scraper tries three ASP.NET selector variants (`#ctl00_PlaceHolderMain_generalSearchForm_txtGSPermitNumber` and ID-suffix patterns). If Berkeley Accela's actual control name differs, the smoke test will surface this via `final_state='error'` and `errors=['Could not locate permit-number search input']`. The `debug_dir` flag will dump the rendered HTML so we can extract the correct selector.
2. **Field-extraction labels.** The CapDetail field extractor walks the DOM for label text (`File Date` / `Application Date` / `Issued Date` / `Finaled Date` / `Total Job Valuation` / etc.) and reads the next sibling. If Berkeley's CapDetail layout uses a structure the JS walker doesn't anticipate, those fields will come back `None` while the master triplet is still successfully captured.

Validation targets from `notes/hand_copied_capids_2026-05-21.md`:

| permit_number | expected master triplet | expected related count |
|---|---|---|
| B2019-05575 | DUB19-00000-00KIL | 2 (1 master + 2 subs) |
| B2021-02225 | DUB21-00000-00EMR | 9 (1 master + 9 subs) |
| B2021-02404 | DUB21-00000-00EZS | 19 (1 master + 19 subs: REV01-REV19 + DEF01-DEF17 = 36 total subs — note discrepancy worth verifying) |

(The hand-copied note says B2021-02404 has 20 total records with 19 subs broken as REV01–REV19 and DEF01–DEF17 — 19 REVs plus 17 DEFs is 36 subs, not 19, so the breakdown text and the total-record count in the hand-copied note disagree. The smoke test will tell us which is right.)
