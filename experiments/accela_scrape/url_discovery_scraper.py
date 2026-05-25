#!/usr/bin/env python3
"""
Accela URL Discovery Scraper Module

Resolves Accela CapDetail URLs (and core CapDetail fields) for a Berkeley
permit number, plus any related sub-records (REV / DEF). Sibling to
inspection_scraper.py; mirrors its sync-Playwright conventions.

Public entry point: discover_url()

Specification reference:
    notes/2026-05-22_url_discovery_design_sketch.md
        - "Master Identification Rule"
        - section 3 ("URL discovery scraper") return shape

The Master Identification Rule:
    The master record is the one whose DISPLAYED permit_number exactly
    equals the search query. Sub-records have a suffix matching the
    regex /-(?:REV|DEF)\\d{2}$/ on the displayed permit_number.

This module makes no v2 or queue writes; the caller (orchestrator and
ingest workstream) decides what to persist.
"""

import json
import pathlib
import re
import sys
import time
from datetime import datetime

from playwright.sync_api import (
    sync_playwright,
    Page,
    TimeoutError as PlaywrightTimeout,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Berkeley Accela host/path. CapHome is the search landing page; the module
# query string selects the search context (Building vs Planning, etc.).
# Today's in-scope set is all B-permits, so default to Building. The caller
# can pass module_hint="Planning" etc. if/when the scraper is extended.
DEFAULT_HOST = "https://aca-prod.accela.com"
CAPHOME_PATH = "/BERKELEY/Cap/CapHome.aspx"
CAPDETAIL_PATH = "/BERKELEY/Cap/CapDetail.aspx"

# Common ASP.NET selectors observed in Berkeley Accela. Tried in order; the
# first one that resolves to a visible element wins.
PERMIT_INPUT_SELECTORS = (
    "input#ctl00_PlaceHolderMain_generalSearchForm_txtGSPermitNumber",
    "input[name='ctl00$PlaceHolderMain$generalSearchForm$txtGSPermitNumber']",
    "input[id$='txtGSPermitNumber']",
)

SUBMIT_BUTTON_SELECTORS = (
    "a#ctl00_PlaceHolderMain_btnNewSearch",
    "a[id$='btnNewSearch']",
    "input#ctl00_PlaceHolderMain_btnNewSearch",
    "input[id$='btnNewSearch']",
)

# A results-page record-number link href looks like:
#   ...CapDetail.aspx?Module=Building&capID1=DUB19&capID2=00000&capID3=00KIJ&...
RESULT_LINK_SELECTORS = (
    "a[href*='CapDetail.aspx']",
)

# CapDetail field labels we try to find. The page typically renders these
# as label/value pairs inside an ASP.NET table; we search the page text and
# extract the value from the adjacent cell.
FIELD_LABEL_VARIANTS = {
    "filed_date":    ["File Date", "Application Date", "Filed Date"],
    "issued_date":   ["Issued Date", "Issue Date"],
    "finaled_date":  ["Finaled Date", "Final Date", "Completed Date"],
    "valuation":     ["Total Job Valuation", "Total Valuation", "Valuation", "Job Value"],
}

# Sub-record suffix recognizer.
SUFFIX_RE = re.compile(r"-(REV|DEF)(\d{2})$", re.IGNORECASE)

# capID parser for hrefs.
CAPID1_RE = re.compile(r"capID1=([^&]+)", re.IGNORECASE)
CAPID2_RE = re.compile(r"capID2=([^&]+)", re.IGNORECASE)
CAPID3_RE = re.compile(r"capID3=([^&]+)", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_search_url(module: str = "Building") -> str:
    return f"{DEFAULT_HOST}{CAPHOME_PATH}?module={module}&TabName={module}"


def _classify_displayed(displayed: str, search_query: str):
    """Return ('master', None) | ('sub', 'REV'|'DEF') | ('other', None)."""
    if not displayed:
        return ("other", None)
    d = displayed.strip()
    if d.upper() == search_query.upper():
        return ("master", None)
    if d.upper().startswith(search_query.upper() + "-"):
        suf = d[len(search_query) + 1:]
        m = SUFFIX_RE.fullmatch("-" + suf)  # validate REV/DEF + 2 digits
        if m:
            return ("sub", m.group(1).upper())
    return ("other", None)


def _parse_capid_triplet(href: str):
    """Return (capid1, capid2, capid3, full_url) or (None, None, None, href) on failure."""
    if not href:
        return (None, None, None, href)
    m1 = CAPID1_RE.search(href)
    m2 = CAPID2_RE.search(href)
    m3 = CAPID3_RE.search(href)
    if not (m1 and m2 and m3):
        return (None, None, None, href)
    return (m1.group(1), m2.group(1), m3.group(1), href)


def _absolutize(href: str) -> str:
    if not href:
        return href
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return DEFAULT_HOST + href
    # Relative href like "CapDetail.aspx?..." — anchor under /BERKELEY/Cap/
    return f"{DEFAULT_HOST}/BERKELEY/Cap/{href.lstrip('/')}"


def _save_debug(page, debug_dir, permit_number, step):
    """Save screenshot and HTML for debugging. No-op if debug_dir is None."""
    if debug_dir is None:
        return
    try:
        debug_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = f"{permit_number}_{ts}_{step}"
        try:
            page.screenshot(path=str(debug_dir / f"{prefix}.png"), full_page=True)
        except Exception as e:
            print(f"    (debug) screenshot failed: {e}")
        try:
            (debug_dir / f"{prefix}.html").write_text(page.content())
        except Exception as e:
            print(f"    (debug) html dump failed: {e}")
    except Exception as e:
        print(f"    (debug) save failed: {e}")


def _is_login_or_block(page) -> str | None:
    """Detect login/cloudflare interstitials. Returns a short tag or None."""
    try:
        url = (page.url or "").lower()
    except Exception:
        url = ""
    if "login" in url or "signin" in url:
        return "login_required"
    try:
        title = (page.title() or "").lower()
    except Exception:
        title = ""
    if "just a moment" in title or "checking your browser" in title:
        return "cloudflare"
    return None


def _try_fill_permit(page, permit_number, errors) -> bool:
    """Try each candidate selector to locate the permit-number input and fill it."""
    for sel in PERMIT_INPUT_SELECTORS:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                el.fill(permit_number)
                return True
        except Exception as e:
            errors.append(f"permit-input fill failed for {sel!r}: {e}")
    return False


def _try_click_search(page, errors) -> bool:
    """Try each candidate selector to locate and click the search button."""
    for sel in SUBMIT_BUTTON_SELECTORS:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                el.click()
                return True
        except Exception as e:
            errors.append(f"submit click failed for {sel!r}: {e}")
    return False


def _parse_result_rows(page, search_query: str, errors: list):
    """
    Return a list of records visible on the results page:
        [{
            "permit_number_displayed": str,
            "href": str (absolute),
            "capid1": str | None, "capid2": str | None, "capid3": str | None,
            "kind": "master" | "sub" | "other",
            "record_type": "REV" | "DEF" | "OTHER",
        }, ...]
    """
    records = []
    seen_hrefs = set()
    for sel in RESULT_LINK_SELECTORS:
        try:
            anchors = page.query_selector_all(sel)
        except Exception as e:
            errors.append(f"result-link query failed for {sel!r}: {e}")
            anchors = []
        for a in anchors:
            try:
                href = a.get_attribute("href") or ""
                if not href or "CapDetail.aspx" not in href:
                    continue
                href_abs = _absolutize(href)
                if href_abs in seen_hrefs:
                    continue
                displayed = (a.inner_text() or "").strip()
                # Some Berkeley result tables render the record number in a
                # text node next to the link. If the link text is empty, try
                # the parent row's text content.
                if not displayed:
                    try:
                        parent = a.evaluate_handle("node => node.closest('tr')")
                        if parent:
                            row_text = parent.as_element().inner_text() or ""
                            # Heuristic: take the first whitespace-separated
                            # token that looks like a Berkeley permit number.
                            m = re.search(r"\b([A-Z]{1,4}\d{2,4}-\d{4,6}(?:-(?:REV|DEF)\d{2})?)\b",
                                          row_text, re.IGNORECASE)
                            if m:
                                displayed = m.group(1)
                    except Exception:
                        pass
                c1, c2, c3, _ = _parse_capid_triplet(href_abs)
                kind, sub_kind = _classify_displayed(displayed, search_query)
                record_type = sub_kind if kind == "sub" else ("MASTER" if kind == "master" else "OTHER")
                records.append({
                    "permit_number_displayed": displayed,
                    "href": href_abs,
                    "capid1": c1, "capid2": c2, "capid3": c3,
                    "kind": kind,
                    "record_type": record_type,
                })
                seen_hrefs.add(href_abs)
            except Exception as e:
                errors.append(f"failed to read result anchor: {e}")
    return records


def _results_page_next_postback(page):
    """
    Return the __doPostBack target string for the results-page 'Next >'
    pagination link, or None if no Next link is present (i.e., we are on
    the last page). The target is extracted from either the link's
    `onclick` attribute or its `href`, mirroring the pattern used in
    inspection_scraper.py::_click_pagination for the inspection table.
    """
    js = """() => {
        const anchors = document.querySelectorAll('a');
        for (const a of anchors) {
            const text = (a.innerText || '').trim().toLowerCase();
            if (!text.startsWith('next')) continue;
            const onclick = a.getAttribute('onclick') || '';
            const href = a.getAttribute('href') || '';
            for (const src of [onclick, href]) {
                const m = src.match(/__doPostBack\\(['"]([^'"]+)['"]/);
                if (m) return m[1];
            }
        }
        return null;
    }"""
    try:
        return page.evaluate(js)
    except Exception:
        return None


def _walk_all_result_pages(page, search_query, errors, max_pages=30):
    """
    Walk every page of the results table, accumulating record dicts with
    deduplication by CapDetail href.

    Returns (records, pages_walked). Never raises. `errors` is appended
    in place on any anomaly (postback failure, stuck pagination, max-pages
    cap reached). The master identification rule is NOT applied here; the
    caller applies it to the full deduplicated record list once the walk
    finishes.
    """
    all_records = []
    seen_hrefs = set()

    def _dedup_extend(new_records):
        added = 0
        for r in new_records:
            key = r.get("href")
            if not key or key in seen_hrefs:
                continue
            seen_hrefs.add(key)
            all_records.append(r)
            added += 1
        return added

    pages_walked = 1
    page1_records = _parse_result_rows(page, search_query, errors)
    _dedup_extend(page1_records)
    prev_hrefs = {r.get("href") for r in page1_records}
    print(f"    page {pages_walked}: {len(page1_records)} record(s), {len(all_records)} unique cumulative")

    while pages_walked < max_pages:
        target = _results_page_next_postback(page)
        if not target:
            break  # no Next link = reached last page (success)
        try:
            page.evaluate(f"__doPostBack('{target}', '')")
        except Exception as e:
            errors.append(f"results-page __doPostBack failed on page {pages_walked}: {e}")
            break

        # Poll for the rendered record set to change. Mirrors the 8s/0.5s
        # poll pattern from inspection_scraper.py::_click_pagination.
        max_wait = 8.0
        poll_interval = 0.5
        waited = 0.0
        candidate = []
        candidate_hrefs = set()
        while waited < max_wait:
            time.sleep(poll_interval)
            waited += poll_interval
            # Use a throw-away errors list during poll so transient parse
            # errors during a re-render don't pollute the real errors[].
            candidate = _parse_result_rows(page, search_query, [])
            candidate_hrefs = {r.get("href") for r in candidate}
            if candidate_hrefs and candidate_hrefs != prev_hrefs:
                break

        if not candidate or not candidate_hrefs:
            errors.append(
                f"results-page pagination yielded no rows after page {pages_walked} "
                f"(max_wait={max_wait}s)"
            )
            break
        if candidate_hrefs == prev_hrefs:
            errors.append(
                f"results-page pagination stuck after page {pages_walked}: "
                f"page {pages_walked+1} identical to page {pages_walked}; aborting"
            )
            break

        pages_walked += 1
        added = _dedup_extend(candidate)
        print(f"    page {pages_walked}: {len(candidate)} record(s), "
              f"+{added} new (total unique: {len(all_records)})")
        prev_hrefs = candidate_hrefs

    if pages_walked >= max_pages:
        errors.append(f"results-page max-pages cap reached ({max_pages})")

    return all_records, pages_walked


def _extract_field_from_capdetail(page, label_variants):
    """
    Look for any of the label variants in the page text. When found, return
    the value from the adjacent cell. Returns None if no variant resolves.

    Uses a JS evaluator: for every <td>/<th>/<span> containing the label, walk
    to the next sibling cell (or the next sibling element) and read its text.
    """
    js = """(labels) => {
        const norm = s => (s || '').replace(/\\s+/g, ' ').trim();
        const all = Array.from(document.querySelectorAll('td, th, span, div, label'));
        for (const lbl of labels) {
            const lblL = lbl.toLowerCase();
            for (const el of all) {
                const text = norm(el.innerText).toLowerCase();
                if (!text) continue;
                if (text === lblL || text === lblL + ':' ||
                    text.startsWith(lblL + ':') || text === lblL.replace(/\\s+/g, '')) {
                    // Try next sibling
                    const sib = el.nextElementSibling;
                    if (sib) {
                        const v = norm(sib.innerText);
                        if (v) return v;
                    }
                    // Try parent's next sibling (label/value in nested rows)
                    if (el.parentElement) {
                        const psib = el.parentElement.nextElementSibling;
                        if (psib) {
                            const v = norm(psib.innerText);
                            if (v) return v;
                        }
                    }
                    // Look for any <span> inside the same parent that isn't the label itself
                    if (el.parentElement) {
                        const spans = el.parentElement.querySelectorAll('span, td');
                        for (const s of spans) {
                            const v = norm(s.innerText);
                            if (v && v.toLowerCase() !== lblL && !v.toLowerCase().startsWith(lblL)) {
                                return v;
                            }
                        }
                    }
                }
            }
        }
        return null;
    }"""
    try:
        return page.evaluate(js, label_variants)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Core flow (operates on an existing Page)
# ---------------------------------------------------------------------------


def _discover_with_page(
    page: Page,
    permit_number: str,
    *,
    max_runtime_seconds: int,
    debug_dir,
    start_time: float,
    module_hint: str = "Building",
) -> dict:
    errors: list[str] = []
    metadata = {
        "module_hint": module_hint,
        "records_seen": 0,
        "final_state": "not_reached",
        "page_title_initial": None,
    }
    result = {
        "permit_number": permit_number,
        "search_url": _build_search_url(module_hint),
        "found": False,
        "ambiguous": False,
        "master": None,
        "related_records": [],
        "errors": errors,
        "metadata": metadata,
    }

    def runtime_exceeded():
        return (time.time() - start_time) > max_runtime_seconds

    # =========================================================
    # Step 1: navigate to CapHome
    # =========================================================
    print(f"[1] Navigating to CapHome for module={module_hint}...")
    try:
        page.goto(result["search_url"], wait_until="networkidle", timeout=60000)
    except PlaywrightTimeout:
        errors.append("Timeout loading CapHome")
        metadata["final_state"] = "error"
        _save_debug(page, debug_dir, permit_number, "caphome_timeout")
        return result

    block = _is_login_or_block(page)
    if block:
        errors.append(block)
        metadata["final_state"] = "error"
        _save_debug(page, debug_dir, permit_number, f"block_{block}")
        return result

    try:
        metadata["page_title_initial"] = page.title()
    except Exception:
        pass
    time.sleep(2)  # let JS finish

    # =========================================================
    # Step 2: fill permit-number, click search
    # =========================================================
    print(f"[2] Searching for permit '{permit_number}'...")
    if not _try_fill_permit(page, permit_number, errors):
        errors.append("Could not locate permit-number search input")
        metadata["final_state"] = "error"
        _save_debug(page, debug_dir, permit_number, "no_search_input")
        return result

    if not _try_click_search(page, errors):
        errors.append("Could not locate search submit button")
        metadata["final_state"] = "error"
        _save_debug(page, debug_dir, permit_number, "no_submit")
        return result

    try:
        page.wait_for_load_state("networkidle", timeout=30000)
    except PlaywrightTimeout:
        errors.append("Timeout waiting for results page (networkidle)")
    time.sleep(2)

    if runtime_exceeded():
        errors.append("runtime exceeded before results parse")
        metadata["final_state"] = "error"
        return result

    # =========================================================
    # Step 2.5: single-result auto-redirect detection
    # =========================================================
    # When Accela's CapHome search returns exactly one matching record,
    # it auto-navigates directly to that record's CapDetail page rather
    # than rendering the multi-row results-list page. The result is that
    # `_walk_all_result_pages` finds 0 anchors (the CapDetail page has no
    # `a[href*='CapDetail.aspx']` link to itself) and falsely reports
    # `not_found`. Detect this case via two signals:
    #
    #   (1) page.url is the CapDetail.aspx URL with capID1/2/3 — Accela
    #       performed a hard redirect after the search submit.
    #   (2) The page's main form has action="./CapDetail.aspx?capID1=…"
    #       — UpdatePanel content swap that left the browser URL pointing
    #       at CapHome.aspx but loaded CapDetail's DOM in place.
    #
    # Either signal is sufficient. The check is wrapped in a short
    # polling loop because Accela's ASP.NET UpdatePanel content swap
    # can take an extra ~1-5s past `wait_for_load_state('networkidle')`;
    # diagnosis on B2023-02303 showed 1-in-4 single-shot checks lose
    # this race. Cost: at most ~5s on legitimate not_found cases;
    # negligible when the signal arrives quickly.
    sr_triplet_match = None
    sr_capdetail_url = None
    _CAPID_RE = re.compile(
        r"CapDetail\.aspx\?.*?capID1=([^&]+)&capID2=([^&]+)&capID3=([^&]+)"
    )
    _FORM_ACTION_JS = """() => {
        for (const f of document.querySelectorAll('form')) {
            const a = f.getAttribute('action') || '';
            if (a.includes('CapDetail.aspx') && a.includes('capID1=')) {
                return a;
            }
        }
        return null;
    }"""

    poll_start = time.time()
    poll_deadline = poll_start + 5.0
    while time.time() < poll_deadline:
        # Signal 1: page.url
        current_url = page.url or ""
        m_url = _CAPID_RE.search(current_url)
        if m_url:
            sr_triplet_match = m_url
            sr_capdetail_url = current_url
            break

        # Signal 2: form action via JS eval
        try:
            form_action = page.evaluate(_FORM_ACTION_JS)
        except Exception:
            form_action = None
        if form_action:
            m_form = _CAPID_RE.search(form_action)
            if m_form:
                sr_triplet_match = m_form
                sr_capdetail_url = _absolutize(form_action)
                break

        time.sleep(0.5)

    metadata["auto_redirect_poll_seconds"] = round(time.time() - poll_start, 2)

    if sr_triplet_match:
        print("[3] Single-result auto-redirect detected — extracting master directly from CapDetail page...")
        sr_c1 = sr_triplet_match.group(1)
        sr_c2 = sr_triplet_match.group(2)
        sr_c3 = sr_triplet_match.group(3)
        sr_triplet = f"{sr_c1}-{sr_c2}-{sr_c3}"

        print("[4] Extracting CapDetail fields (file/issued/finaled date, valuation)...")
        fields = {}
        for key, labels in FIELD_LABEL_VARIANTS.items():
            try:
                v = _extract_field_from_capdetail(page, labels)
            except Exception as e:
                v = None
                errors.append(f"field extraction error for {key}: {e}")
            fields[key] = v if v else None

        result["found"] = True
        result["master"] = {
            "permit_number_displayed": permit_number,
            "capid_triplet": sr_triplet,
            "capid1": sr_c1, "capid2": sr_c2, "capid3": sr_c3,
            "capdetail_url": sr_capdetail_url,
            "filed_date": fields.get("filed_date"),
            "issued_date": fields.get("issued_date"),
            "finaled_date": fields.get("finaled_date"),
            "valuation": fields.get("valuation"),
        }
        # related_records left empty: enumerating sub-records from the
        # CapDetail page itself is a deferred enhancement.
        metadata["records_seen"] = 1
        metadata["pages_walked"] = 0
        metadata["match_path"] = "single_result_redirect"
        metadata["final_state"] = "ok"
        return result

    # Falls through: multi-result results-list page (or zero results).
    metadata["match_path"] = "results_list"

    # =========================================================
    # Step 3: walk all pages of the results table, then parse
    # =========================================================
    print("[3] Walking results page(s) (with pagination)...")
    records, pages_walked = _walk_all_result_pages(page, permit_number, errors)
    metadata["records_seen"] = len(records)
    metadata["pages_walked"] = pages_walked
    print(f"    {len(records)} unique record(s) seen across {pages_walked} page(s)")

    if len(records) == 0:
        # Could be no-results or a results page we didn't recognize. Save
        # debug artifacts so the smoke-test can show us which.
        _save_debug(page, debug_dir, permit_number, "no_results")
        metadata["final_state"] = "not_found"
        return result

    # =========================================================
    # Step 4: apply Master Identification Rule
    # =========================================================
    masters = [r for r in records if r["kind"] == "master"]
    subs    = [r for r in records if r["kind"] == "sub"]
    others  = [r for r in records if r["kind"] == "other"]

    if others:
        errors.append(f"{len(others)} result row(s) ignored (no exact / REV / DEF match)")

    if len(masters) == 0:
        metadata["final_state"] = "not_found"
        _save_debug(page, debug_dir, permit_number, "no_master")
        return result

    if len(masters) > 1:
        result["found"] = True
        result["ambiguous"] = True
        metadata["final_state"] = "ambiguous"
        metadata["master_candidates"] = [
            {
                "permit_number_displayed": m["permit_number_displayed"],
                "capdetail_url": m["href"],
            }
            for m in masters
        ]
        _save_debug(page, debug_dir, permit_number, "ambiguous_masters")
        return result

    master = masters[0]
    result["found"] = True

    # Pre-build related_records from the results page only (no click-through)
    for s in subs:
        result["related_records"].append({
            "permit_number_displayed": s["permit_number_displayed"],
            "record_type": s["record_type"],
            "capid_triplet": (
                f"{s['capid1']}-{s['capid2']}-{s['capid3']}"
                if s["capid1"] else None
            ),
            "capid1": s["capid1"],
            "capid2": s["capid2"],
            "capid3": s["capid3"],
            "capdetail_url": s["href"],
        })

    # =========================================================
    # Step 5: visit master CapDetail and extract fields
    # =========================================================
    if runtime_exceeded():
        errors.append("runtime exceeded before CapDetail navigation")
        metadata["final_state"] = "error"
        return result

    print(f"[4] Loading master CapDetail page for {master['permit_number_displayed']}...")
    try:
        page.goto(master["href"], wait_until="networkidle", timeout=60000)
    except PlaywrightTimeout:
        errors.append("Timeout loading master CapDetail page")
        metadata["final_state"] = "error"
        _save_debug(page, debug_dir, permit_number, "capdetail_timeout")
        return result

    block = _is_login_or_block(page)
    if block:
        errors.append(block)
        metadata["final_state"] = "error"
        _save_debug(page, debug_dir, permit_number, f"capdetail_block_{block}")
        return result

    time.sleep(2)  # let JS finish

    # Re-extract capID triplet from the CURRENT URL (after navigation) — more
    # authoritative than the results-page href.
    final_url = page.url or master["href"]
    c1, c2, c3, _ = _parse_capid_triplet(final_url)
    if c1 and c2 and c3:
        capid_triplet = f"{c1}-{c2}-{c3}"
    else:
        # Fall back to triplet parsed from the original href.
        c1, c2, c3 = master["capid1"], master["capid2"], master["capid3"]
        capid_triplet = (
            f"{c1}-{c2}-{c3}" if c1 else None
        )

    print("[5] Extracting CapDetail fields (file/issued/finaled date, valuation)...")
    fields = {}
    for key, labels in FIELD_LABEL_VARIANTS.items():
        try:
            v = _extract_field_from_capdetail(page, labels)
        except Exception as e:
            v = None
            errors.append(f"field extraction error for {key}: {e}")
        fields[key] = v if v else None

    result["master"] = {
        "permit_number_displayed": master["permit_number_displayed"],
        "capid_triplet": capid_triplet,
        "capid1": c1, "capid2": c2, "capid3": c3,
        "capdetail_url": final_url,
        "filed_date": fields.get("filed_date"),
        "issued_date": fields.get("issued_date"),
        "finaled_date": fields.get("finaled_date"),
        "valuation": fields.get("valuation"),
    }
    metadata["final_state"] = "ok"
    return result


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def discover_url(
    permit_number: str,
    *,
    headless: bool = True,
    max_runtime_seconds: int = 120,
    debug_dir: pathlib.Path | None = None,
    page: Page | None = None,
    module_hint: str = "Building",
) -> dict:
    """
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
    """
    start = time.time()
    print(f"\n{'='*60}\nAccela URL Discovery\n{'='*60}")
    print(f"Permit: {permit_number}")
    print(f"Mode: {'headless' if headless else 'headed'}{'  (injected page)' if page else ''}")

    def _finalize(d):
        d["metadata"]["scrape_duration_seconds"] = round(time.time() - start, 2)
        print(f"\nFinal state: {d['metadata'].get('final_state')}  "
              f"found={d['found']}  ambiguous={d['ambiguous']}  "
              f"related={len(d['related_records'])}  "
              f"errors={len(d['errors'])}")
        return d

    if page is not None:
        try:
            return _finalize(_discover_with_page(
                page,
                permit_number,
                max_runtime_seconds=max_runtime_seconds,
                debug_dir=debug_dir,
                start_time=start,
                module_hint=module_hint,
            ))
        except Exception as e:
            # Last-resort guard. discover_url contracts to never raise.
            return _finalize({
                "permit_number": permit_number,
                "search_url": _build_search_url(module_hint),
                "found": False, "ambiguous": False,
                "master": None, "related_records": [],
                "errors": [f"unhandled exception: {e!r}"],
                "metadata": {
                    "module_hint": module_hint,
                    "records_seen": 0,
                    "final_state": "error",
                },
            })

    # Launch our own Chromium
    with sync_playwright() as p:
        print("Launching Chromium...")
        browser = p.chromium.launch(headless=headless, slow_mo=50 if not headless else 0)
        try:
            context = browser.new_context(
                viewport={"width": 1400, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36"
                ),
            )
            new_page = context.new_page()
            try:
                return _finalize(_discover_with_page(
                    new_page,
                    permit_number,
                    max_runtime_seconds=max_runtime_seconds,
                    debug_dir=debug_dir,
                    start_time=start,
                    module_hint=module_hint,
                ))
            except Exception as e:
                return _finalize({
                    "permit_number": permit_number,
                    "search_url": _build_search_url(module_hint),
                    "found": False, "ambiguous": False,
                    "master": None, "related_records": [],
                    "errors": [f"unhandled exception: {e!r}"],
                    "metadata": {
                        "module_hint": module_hint,
                        "records_seen": 0,
                        "final_state": "error",
                    },
                })
        finally:
            try:
                browser.close()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# CLI for ad-hoc testing
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Discover Accela CapDetail URL + fields for a permit."
    )
    parser.add_argument("permit_number", help="Permit number to search (e.g., B2019-05575)")
    parser.add_argument("--headful", action="store_true",
                        help="Run with a visible browser (for debugging)")
    parser.add_argument("--debug-dir", type=pathlib.Path, default=None,
                        help="Where to save screenshots/HTML on failure")
    parser.add_argument("--max-runtime-seconds", type=int, default=120,
                        help="Per-permit time budget (default: 120)")
    parser.add_argument("--module-hint", default="Building",
                        help="CapHome module context (default: Building)")
    args = parser.parse_args()

    result = discover_url(
        args.permit_number,
        headless=not args.headful,
        max_runtime_seconds=args.max_runtime_seconds,
        debug_dir=args.debug_dir,
        module_hint=args.module_hint,
    )
    json.dump(result, sys.stdout, indent=2, default=str)
    sys.stdout.write("\n")
