#!/usr/bin/env python3
"""harvest_address.py — Accela ACA search BY ADDRESS (the address adapter).

The existing HARVESTER (`url_discovery_scraper.py`) searches by permit number. This adapter drives ACA's
General Search **address** fields (street number + street name) so we can enumerate EVERY record at an
address / block — the capability the Benvenue ADU pilot needs (building permits + rental licenses + RHSP
inspections that the assessor/registry all miss; see notes/2026-08-12_accela_benvenue_adu_harvest_scope.md).

It reuses the harvester's result-parsing + pagination machinery verbatim (import, don't fork). The only new
piece is filling the address inputs, whose ASP.NET field ids we cover with candidate selectors + a debug
mode — **the FIRST live run must use `--headful --debug-dir <dir>` to confirm the real selectors** (ACA field
ids vary by agency config; refine ADDRESS_*_SELECTORS from the saved HTML if the fill fails).

Login: public **Building** permit search needs NO login. **Licenses / RHSP** modules do — pass
`--storage-state <json>` exported from John's authenticated ACA session (the harvester detects
`login_required` and stops cleanly otherwise).

CLI:
  python harvest_address.py --street-name BENVENUE --module Building --headful --debug-dir scratch/aca_dbg
  python harvest_address.py --street-no 2811 --street-name BENVENUE --module Building --json out.json
"""
from __future__ import annotations
import argparse, json, pathlib, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from url_discovery_scraper import (            # reuse the proven machinery
    DEFAULT_HOST, _build_search_url, _try_click_search, _parse_result_rows,
    _walk_all_result_pages, _is_login_or_block, _save_debug,
)

# ACA General Search address inputs — field ids CONFIRMED live via Claude-in-Chrome (2026-08-13), same
# across the Building and Business-Licenses modules (both use generalSearchForm). Street number is a
# From/To PAIR; set both to the same number for one address (From must be <= To or the form errors).
ADDRESS_STREETNO_FROM_SELECTORS = (
    "input#ctl00_PlaceHolderMain_generalSearchForm_txtGSNumber_ChildControl0",
    "input[name='ctl00$PlaceHolderMain$generalSearchForm$txtGSNumber$ChildControl0']",
    "input[id$='txtGSNumber_ChildControl0']",
)
ADDRESS_STREETNO_TO_SELECTORS = (
    "input#ctl00_PlaceHolderMain_generalSearchForm_txtGSNumber_ChildControl1",
    "input[name='ctl00$PlaceHolderMain$generalSearchForm$txtGSNumber$ChildControl1']",
    "input[id$='txtGSNumber_ChildControl1']",
)
ADDRESS_STREETNAME_SELECTORS = (
    "input#ctl00_PlaceHolderMain_generalSearchForm_txtGSStreetName",
    "input[name='ctl00$PlaceHolderMain$generalSearchForm$txtGSStreetName']",
    "input[id$='txtGSStreetName']",
)
# The date window DEFAULTS to ~2 years back — widen Start Date to 1900 or OLD permits are silently missed
# (this is how the 2000 sewer permit at 2811 Benvenue is even visible).
START_DATE_SELECTORS = (
    "input[id$='txtGSStartDate']",
    "input[id*='StartDate']",
    "input[id$='txtGSPermitDateFrom']",
)

def _fill_first(page, selectors, value, errors):
    for sel in selectors:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                el.fill(value)
                return sel
        except Exception as e:
            errors.append(f"address fill failed for {sel!r}: {e}")
    return None

def search_by_address(page, street_name, street_no=None, module="Building",
                      debug_dir=None, errors=None):
    """Fill ACA address search, submit, walk all result pages. Returns records list (may be empty)."""
    errors = errors if errors is not None else []
    page.goto(_build_search_url(module), wait_until="domcontentloaded")
    block = _is_login_or_block(page)
    if block:
        return {"records": [], "blocked": block, "errors": errors}
    _save_debug(page, debug_dir, f"{street_no or ''}{street_name}", "search_form")
    name_sel = _fill_first(page, ADDRESS_STREETNAME_SELECTORS, street_name, errors)
    if not name_sel:
        errors.append("could not locate street-name input — refine ADDRESS_STREETNAME_SELECTORS from debug HTML")
        return {"records": [], "blocked": None, "errors": errors, "fill_ok": False}
    if street_no:
        # street number is a From/To pair — set both to the same value for a single address
        _fill_first(page, ADDRESS_STREETNO_FROM_SELECTORS, str(street_no), errors)
        _fill_first(page, ADDRESS_STREETNO_TO_SELECTORS, str(street_no), errors)
    # widen the date window (defaults to ~2 years) so pre-2024 permits are not silently dropped
    _fill_first(page, START_DATE_SELECTORS, "01/01/1900", errors)
    if not _try_click_search(page, errors):
        errors.append("could not click search button")
        return {"records": [], "blocked": None, "errors": errors, "fill_ok": True}
    page.wait_for_load_state("networkidle")
    _save_debug(page, debug_dir, f"{street_no or ''}{street_name}", "results")
    block = _is_login_or_block(page)
    if block:
        return {"records": [], "blocked": block, "errors": errors}
    query = f"{street_no or ''} {street_name}".strip()
    records, pages = _walk_all_result_pages(page, query, errors)
    return {"records": records, "pages_walked": pages, "blocked": None, "errors": errors, "fill_ok": True}

def run(street_name, street_no=None, module="Building", headless=True,
        storage_state=None, debug_dir=None):
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        ctx = browser.new_context(storage_state=storage_state) if storage_state else browser.new_context()
        page = ctx.new_page()
        try:
            out = search_by_address(page, street_name, street_no, module, debug_dir, errors)
        finally:
            browser.close()
    out["query"] = {"street_no": street_no, "street_name": street_name, "module": module}
    return out

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--street-name", required=True, help="e.g. BENVENUE")
    ap.add_argument("--street-no", default=None, help="e.g. 2811 (omit for whole street)")
    ap.add_argument("--module", default="Building", help="Building | Licenses | Enforcement | Planning")
    ap.add_argument("--headful", action="store_true", help="show the browser (use for the first live run)")
    ap.add_argument("--storage-state", type=pathlib.Path, default=None,
                    help="Playwright storage_state json from John's authenticated ACA session (Licenses/RHSP)")
    ap.add_argument("--debug-dir", type=pathlib.Path, default=None, help="save screenshots + HTML per step")
    ap.add_argument("--json", type=pathlib.Path, default=None, help="write results json here")
    a = ap.parse_args()
    res = run(a.street_name, a.street_no, a.module, headless=not a.headful,
              storage_state=(str(a.storage_state) if a.storage_state else None), debug_dir=a.debug_dir)
    print(f"records={len(res['records'])} blocked={res.get('blocked')} fill_ok={res.get('fill_ok')} "
          f"pages={res.get('pages_walked')} errors={len(res['errors'])}")
    for r in res["records"][:20]:
        print("  ", r.get("permit_number_displayed"), r.get("record_type"), r.get("href", "")[:90])
    if a.json:
        a.json.write_text(json.dumps(res, indent=2))
        print("wrote", a.json)
