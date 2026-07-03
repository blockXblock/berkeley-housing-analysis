#!/usr/bin/env python3
"""
Accela Date-Range Discovery Scraper

Extends the HARVESTER family (sibling to url_discovery_scraper.py, same
sync-Playwright conventions) with search-by-DATE-RANGE: list every record
filed in a window, from the CapHome general search's result grid, paginating
until exhausted. Built 2026-07-03 for the mayor-presentation sweep (fresh
2025-06 -> now permits; the CPRA refresh is the durable follow-through).

Reads the RESULT GRID ONLY (permit number, type, description, date, status,
CapDetail href) — no per-record detail visits; the caller triages which
records deserve a detail/inspection pull.

Public entry point: discover_range(start_mmddyyyy, end_mmddyyyy, module)

Output discipline: caller persists; this module returns rows. The sweep
runner (sweep_recent_permits.py) writes JSONL per (module, month-window) to
data/raw/accela/date_range/ — append-only, re-runs skip existing windows.

HARVESTER RETRY RULE applies: a 0-result window is NOT evidence of absence
until retried (Accela discovery flakiness).
"""

import json
import pathlib
import re
import sys
import time
from datetime import datetime

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

DEFAULT_HOST = "https://aca-prod.accela.com"
CAPHOME_PATH = "/BERKELEY/Cap/CapHome.aspx"

# Date inputs on the general search form (candidates tried in order, same
# convention as url_discovery_scraper's PERMIT_INPUT_SELECTORS).
START_DATE_SELECTORS = (
    "input#ctl00_PlaceHolderMain_generalSearchForm_txtGSStartDate",
    "input[id$='txtGSStartDate']",
)
END_DATE_SELECTORS = (
    "input#ctl00_PlaceHolderMain_generalSearchForm_txtGSEndDate",
    "input[id$='txtGSEndDate']",
)
SUBMIT_BUTTON_SELECTORS = (
    "a#ctl00_PlaceHolderMain_btnNewSearch",
    "a[id$='btnNewSearch']",
    "input[id$='btnNewSearch']",
)
# The results grid; row parsing is positional-with-header-mapping.
GRID_SELECTORS = (
    "table[id$='gdvPermitList']",
    "table[id*='PermitList']",
)
NEXT_PAGE_TEXT = "Next >"


def _build_search_url(module: str) -> str:
    return f"{DEFAULT_HOST}{CAPHOME_PATH}?module={module}&TabName={module}"


def _fill_first(page, selectors, value, errors) -> bool:
    """JS value-set + change event: Accela's date mask swallows Playwright fill()
    (calibrated 2026-07-03 — fill() produced 'String was not recognized as a valid DateTime')."""
    for sel in selectors:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                page.evaluate(
                    """([sel, val]) => { const el = document.querySelector(sel);
                        el.value = val; el.dispatchEvent(new Event('change', {bubbles: true})); }""",
                    [sel, value])
                return True
        except Exception as e:
            errors.append(f"fill failed for {sel!r}: {e}")
    return False


def _click_first(page, selectors, errors) -> bool:
    for sel in selectors:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                el.click()
                return True
        except Exception as e:
            errors.append(f"click failed for {sel!r}: {e}")
    return False


def _find_grid(page):
    for sel in GRID_SELECTORS:
        el = page.query_selector(sel)
        if el:
            return el
    return None


def _parse_grid(grid):
    """Return (header_texts, row_dicts). Rows map header->cell text, plus
    'capdetail_href' from the first CapDetail link in the row."""
    headers = [h.inner_text().strip() for h in grid.query_selector_all("tr th")]
    rows = []
    for tr in grid.query_selector_all("tr"):
        tds = tr.query_selector_all("td")
        if not tds or len(tds) < 3:
            continue
        cells = [td.inner_text().strip() for td in tds]
        # pager rows are single-cell tables of page links; skip rows whose
        # cells are all short integers/ellipses
        if all(re.fullmatch(r"\d{1,3}|\.\.\.|Next >|< Prev|", c) for c in cells):
            continue
        row = {}
        if headers and len(headers) >= len(cells):
            for h, c in zip(headers[-len(cells):], cells):
                if h:
                    row[h] = c
        row["_cells"] = cells
        link = tr.query_selector("a[href*='CapDetail.aspx']")
        row["capdetail_href"] = link.get_attribute("href") if link else None
        rows.append(row)
    return headers, rows


def _click_next_page(page, errors) -> bool:
    """Click the pager's 'Next >' link if present and enabled."""
    try:
        for a in page.query_selector_all("a"):
            try:
                if (a.inner_text() or "").strip() == NEXT_PAGE_TEXT and a.is_visible():
                    a.click()
                    return True
            except Exception:
                continue
    except Exception as e:
        errors.append(f"next-page scan failed: {e}")
    return False


def discover_range(start_date: str, end_date: str, module: str = "Building",
                   headless: bool = True, max_pages: int = 200,
                   debug_dir: pathlib.Path | None = None) -> dict:
    """Search Berkeley Accela for all `module` records filed start_date..end_date
    (MM/DD/YYYY). Returns {'status', 'module', 'window', 'pages', 'rows', 'errors'}."""
    errors, all_rows = [], []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless)
        page = browser.new_page()
        try:
            page.goto(_build_search_url(module), timeout=60000)
            page.wait_for_load_state("networkidle", timeout=60000)
            if not _fill_first(page, START_DATE_SELECTORS, start_date, errors):
                _dump(page, debug_dir, module, "no-start-date-input")
                return _result("no_start_date_input", module, start_date, end_date, 0, [], errors)
            if not _fill_first(page, END_DATE_SELECTORS, end_date, errors):
                _dump(page, debug_dir, module, "no-end-date-input")
                return _result("no_end_date_input", module, start_date, end_date, 0, [], errors)
            if not _click_first(page, SUBMIT_BUTTON_SELECTORS, errors):
                return _result("no_submit", module, start_date, end_date, 0, [], errors)
            try:
                page.wait_for_selector("a[href*='CapDetail.aspx']", timeout=45000)
            except PlaywrightTimeout:
                _dump(page, debug_dir, module, "no-links-after-search")
                return _result("no_results_or_timeout", module, start_date, end_date, 0, [], errors)

            pages = 0
            while pages < max_pages:
                grid = _find_grid(page)
                if grid is None:
                    if pages == 0:
                        _dump(page, debug_dir, module, "no-grid")
                        return _result("no_results_grid", module, start_date, end_date, 0, [], errors)
                    break
                _, rows = _parse_grid(grid)
                all_rows.extend(rows)
                pages += 1
                sig_el = page.query_selector("a[href*='CapDetail.aspx']")
                sig = sig_el.get_attribute("href") if sig_el else None
                if not _click_next_page(page, errors):
                    break
                # wait for a REAL advance: the first result link must change. The old page's
                # links satisfy any presence-wait immediately (calibrated 2026-07-03: presence-
                # waiting re-parsed the same page -> duplicate rows + months truncated to their
                # newest tail when the pager stalled at block boundaries).
                advanced = False
                for _ in range(40):
                    time.sleep(0.5)
                    el = page.query_selector("a[href*='CapDetail.aspx']")
                    if el and el.get_attribute("href") != sig:
                        advanced = True
                        break
                if not advanced:
                    break             # pager did not move: treat as last page, never duplicate
            return _result("ok", module, start_date, end_date, pages, all_rows, errors)
        except PlaywrightTimeout as e:
            errors.append(f"timeout: {e}")
            _dump(page, debug_dir, module, "timeout")
            return _result("timeout", module, start_date, end_date, 0, all_rows, errors)
        finally:
            browser.close()


def _dump(page, debug_dir, module, tag):
    if debug_dir is None:
        return
    debug_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    try:
        page.screenshot(path=str(debug_dir / f"{module}_{tag}_{ts}.png"), full_page=True)
        (debug_dir / f"{module}_{tag}_{ts}.html").write_text(page.content())
    except Exception:
        pass


def _result(status, module, start, end, pages, rows, errors):
    return {"status": status, "module": module, "window": [start, end],
            "pages": pages, "rows": rows, "errors": errors}


if __name__ == "__main__":
    # smoke: tiny window, visible output
    start, end = (sys.argv[1], sys.argv[2]) if len(sys.argv) > 2 else ("06/02/2026", "06/05/2026")
    module = sys.argv[3] if len(sys.argv) > 3 else "Building"
    res = discover_range(start, end, module,
                         debug_dir=pathlib.Path("experiments/accela_scrape/debug_dr"))
    print(json.dumps({k: v for k, v in res.items() if k != "rows"}, indent=1))
    print(f"rows: {len(res['rows'])}")
    for r in res["rows"][:8]:
        print("  ", r.get("_cells", [])[:6])
