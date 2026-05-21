#!/usr/bin/env python3
"""
Accela Inspection Scraper Module

Reusable module for scraping inspection records from Berkeley Accela.
Refactored from experiments/accela_scrape/playwright_inspections_poc.py.

The module exports one public function: scrape_inspections()

Usage:
    from inspection_scraper import scrape_inspections

    result = scrape_inspections(
        permit_number="B2019-05574",
        url="https://aca-prod.accela.com/BERKELEY/Cap/CapDetail.aspx?..."
    )
"""

import json
import pathlib
import re
import time
from datetime import datetime

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


def _get_inspection_ids_on_page(page, table_selector):
    """Extract just the inspection IDs from the current page for comparison."""
    try:
        ids = page.evaluate(f'''() => {{
            const rows = document.querySelectorAll('{table_selector} tr.InspectionListRow');
            const ids = [];
            rows.forEach(row => {{
                const text = row.innerText;
                const match = text.match(/\\((\\d+)\\)/);
                if (match) ids.push(match[1]);
            }});
            return ids;
        }}''')
        return set(ids) if ids else set()
    except Exception as e:
        print(f"    Error getting page IDs: {e}")
        return set()


def _parse_inspection_row(row_element):
    """
    Parse a single inspection table row into a dict.

    Berkeley Accela structure per row:
    <tr class="InspectionListRow">
      <td>
        <table>
          <tr>
            <td>
              <span style="bold">Result</span> <span>Type Code (InspectionID)</span>
              <br><span>Result/Cancelled by: Inspector on Date at Time</span>
            </td>
          </tr>
        </table>
      </td>
    </tr>
    """
    inspection = {}

    try:
        # Get the full text content
        full_text = row_element.inner_text().strip()

        # Skip pagination rows
        if 'Prev' in full_text and 'Next' in full_text:
            return None
        if full_text.startswith('<') or full_text.startswith('1 2 3'):
            return None

        # Extract result (first bold text): Approved, Cancelled, Failed, etc.
        result_span = row_element.query_selector('span[style*="bold"]')
        if result_span:
            inspection['result'] = result_span.inner_text().strip()

        # Extract type code and ID from second span (e.g., "Building 1150 Framing (727846)")
        spans = row_element.query_selector_all('td.ACA_Width45em > span')
        if len(spans) >= 2:
            type_text = spans[1].inner_text().strip()
            # Parse "Building 1150 Framing (727846)"
            match = re.match(r'^(.+?)\s*\((\d+)\)$', type_text)
            if match:
                inspection['type_code'] = match.group(1).strip()
                inspection['inspection_id'] = match.group(2)
            else:
                inspection['type_code'] = type_text

        # Extract date and inspector from the "Result by: Inspector on Date at Time" line
        # or "Cancelled by: Inspector on Date at Time"
        date_match = re.search(r'on\s+(\d{1,2}/\d{1,2}/\d{4})\s+at\s+(\d{1,2}:\d{2}\s*[AP]M)', full_text)
        if date_match:
            inspection['date'] = date_match.group(1)
            inspection['time'] = date_match.group(2)

        # Extract inspector (e.g., "by: MD" or "by: A  A")
        inspector_match = re.search(r'by:\s*([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+on', full_text)
        if inspector_match:
            inspection['inspector'] = inspector_match.group(1).strip()

    except Exception as e:
        inspection['_parse_error'] = str(e)

    return inspection if inspection.get('result') or inspection.get('type_code') else None


def _extract_inspections_from_table(page, table_selector):
    """Extract all inspection rows from a table."""
    inspections = []

    try:
        # Find rows with class InspectionListRow (the actual data rows)
        rows = page.query_selector_all(f"{table_selector} tr.InspectionListRow")

        if not rows:
            # Fallback: try all tr elements
            rows = page.query_selector_all(f"{table_selector} tbody tr")
            if not rows:
                rows = page.query_selector_all(f"{table_selector} tr")

        for row in rows:
            inspection = _parse_inspection_row(row)
            if inspection:
                inspections.append(inspection)

    except Exception as e:
        print(f"  Error extracting table: {e}")

    return inspections


def _click_pagination(page, target_page, previous_ids):
    """
    Navigate to the next page using ASP.NET __doPostBack.

    IMPORTANT: This function ONLY uses the "Next >" link, never numbered page
    links (1, 2, 3...). This is intentional: ASP.NET UpdatePanel refreshes
    cause numbered page link href targets to become stale after each postback,
    leading to clicks that appear to succeed but return the same data. The
    "Next >" link is regenerated with a fresh postback target on each page
    load, making it reliable across the full pagination sequence.

    Returns
    -------
    str
        'success' - navigation succeeded and new data appeared
        'last_page' - no more pages (reached end of data); this is a
                      successful completion, not a failure
        'failed' - pagination attempted but data didn't change after
                   waiting; may be transient, caller should retry
    """
    table_selector = '#ctl00_PlaceHolderMain_InspectionList_gvListCompleted'

    try:
        # ALWAYS prefer "Next >" link - it's more reliable than page numbers
        # Page number links can become stale after UpdatePanel refreshes
        postback_info = page.evaluate('''() => {
            const links = document.querySelectorAll('.aca_pagination a');
            for (const link of links) {
                if (link.innerText.includes('Next')) {
                    const href = link.getAttribute('href');
                    if (href && href.includes('__doPostBack')) {
                        const match = href.match(/__doPostBack\\('([^']+)'/);
                        if (match) {
                            return {
                                target: match[1],
                                linkText: 'Next'
                            };
                        }
                    }
                }
            }
            return null;
        }''')

        if not postback_info:
            print(f"    No 'Next' link found - reached last page")
            return 'last_page'  # This is success, not failure

        event_target = postback_info['target']
        link_text = postback_info['linkText']
        print(f"    Clicking '{link_text}' (target: ...{event_target[-30:]})")

        # Execute the __doPostBack function directly
        page.evaluate(f"__doPostBack('{event_target}', '')")

        # Poll for DOM change with timeout
        # Instead of fixed wait, poll until IDs change or timeout
        max_wait = 8  # seconds
        poll_interval = 0.5
        waited = 0

        while waited < max_wait:
            time.sleep(poll_interval)
            waited += poll_interval

            new_ids = _get_inspection_ids_on_page(page, table_selector)
            if new_ids and new_ids != previous_ids:
                # Table content changed!
                return 'success'

        # Final check after max wait
        new_ids = _get_inspection_ids_on_page(page, table_selector)

        if not new_ids:
            print(f"    WARNING: No inspection IDs found after {max_wait}s wait")
            return 'failed'

        if new_ids == previous_ids:
            print(f"    PAGINATION FAILED: Same IDs after {max_wait}s wait")
            print(f"    IDs on page: {sorted(new_ids)[:5]}...")
            return 'failed'

        return 'success'

    except Exception as e:
        print(f"    Pagination error: {e}")
        return 'failed'


def scrape_inspections(
    permit_number: str,
    url: str,
    *,
    headless: bool = True,
    max_pages: int = 200,
    max_unique: int = 1500,
    max_runtime_seconds: int = 1200,
    debug_dir: pathlib.Path | None = None,
) -> dict:
    """
    Scrape Accela inspection records for a single permit.

    Parameters
    ----------
    permit_number : str
        Human-facing permit number (e.g., "B2019-05574"). Used only
        for labeling in the results dict and debug filenames.
    url : str
        Full Accela CapDetail.aspx URL with capID1/2/3 params.
        The function appends &IsToShowInspection=Y if not present.
    headless : bool
        Run Chromium headless. Default True for orchestrator use.
    max_pages, max_unique, max_runtime_seconds : int
        Safety caps. Defaults are wider than the POC's values
        (POC: 120/700/900) to accommodate larger permits.
    debug_dir : Path or None
        If provided, write page-1 HTML and any failure HTML to this
        directory. If None, skip debug HTML capture entirely.

    Returns
    -------
    dict with keys:
      permit_number, url, extraction_timestamp, extraction_method,
      inspections (list of dicts), errors (list of str; may contain
      non-fatal warnings that did NOT prevent successful extraction,
      e.g., "Timeout waiting for inspection table" when the table
      appeared just after the 20s wait—callers should consult
      metadata.final_pagination_state to determine success, not just
      whether errors is empty), metadata (dict with total_pages,
      unique_inspection_count, extraction_duration_seconds, page_title,
      requires_auth, page_content_length, final_pagination_state)

    The function does NOT write any JSON output file. The caller
    writes results to disk.
    """
    start_time = time.time()

    # Ensure URL has the inspection tab parameter
    navigation_url = url
    if "IsToShowInspection" not in url:
        navigation_url = url + "&IsToShowInspection=Y"

    results = {
        "permit_number": permit_number,
        "url": url,
        "extraction_timestamp": datetime.now().isoformat(),
        "extraction_method": "playwright_v2",
        "inspections": [],
        "errors": [],
        "metadata": {
            "final_pagination_state": "not_reached"  # Will be updated during pagination
        }
    }

    print(f"\n{'='*60}")
    print(f"Accela Inspection Extraction")
    print(f"{'='*60}")
    print(f"Permit: {permit_number}")
    print(f"Mode: {'headless' if headless else 'headed (visible browser)'}")
    print(f"Target: {url[:60]}...")
    print(f"Safety limits: {max_pages} pages, {max_unique} unique IDs, {max_runtime_seconds}s")
    print()

    # Track all seen inspection IDs for deduplication
    all_seen_ids = set()
    final_pagination_state = "not_reached"
    page_num = 1

    with sync_playwright() as p:
        # Launch browser
        print("Launching Chromium...")
        browser = p.chromium.launch(
            headless=headless,
            slow_mo=50 if not headless else 0  # Slight slowdown for visibility
        )

        context = browser.new_context(
            viewport={"width": 1400, "height": 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = context.new_page()

        # =====================================================
        # Step 1: Navigate to the permit page
        # =====================================================
        print("\n[1] Navigating to permit page...")
        try:
            page.goto(navigation_url, wait_until="networkidle", timeout=60000)
            print(f"    Page loaded: {page.title()}")
        except PlaywrightTimeout:
            results["errors"].append("Timeout loading main page")
            print("    ERROR: Page load timeout")
            results["metadata"]["final_pagination_state"] = "not_reached"
            browser.close()
            return results

        # Check for login redirect
        current_url = page.url.lower()
        if "login" in current_url or "signin" in current_url:
            results["errors"].append("Redirected to login page - authentication required")
            results["metadata"]["requires_auth"] = True
            results["metadata"]["final_pagination_state"] = "not_reached"
            print("    ERROR: Redirected to login page. Authentication required.")
            browser.close()
            return results

        results["metadata"]["page_title"] = page.title()
        results["metadata"]["requires_auth"] = False

        # Wait for JS to execute
        print("    Waiting for JavaScript execution...")
        time.sleep(3)

        # =====================================================
        # Step 2: Wait for inspection data to load
        # =====================================================
        print("\n[2] Waiting for inspection data...")

        table_selector = '#ctl00_PlaceHolderMain_InspectionList_gvListCompleted'

        try:
            # Wait for the inspection table
            page.wait_for_selector(
                table_selector,
                timeout=20000
            )
            print("    Inspection table found")
        except PlaywrightTimeout:
            print("    Timeout waiting for inspection table")
            results["errors"].append("Timeout waiting for inspection table")

        # Additional wait for content
        time.sleep(2)

        # =====================================================
        # Step 3: Extract inspections with pagination
        # =====================================================
        print("\n[3] Extracting inspection data...")

        all_inspections = []
        consecutive_failures = 0

        # Save debug HTML for first page (if debug_dir provided)
        if debug_dir is not None:
            debug_dir.mkdir(parents=True, exist_ok=True)
            debug_html = page.content()
            debug_file = debug_dir / f"{permit_number}_page1_debug.html"
            debug_file.write_text(debug_html)
            print(f"    Saved page 1 debug HTML to {debug_file}")

        # Check if table exists
        table = page.query_selector(table_selector)
        if not table:
            print("    No inspection table found!")
            results["errors"].append("Could not locate inspection table")
            results["metadata"]["final_pagination_state"] = "not_reached"
            browser.close()
            return results

        # Extract first page
        page_inspections = _extract_inspections_from_table(page, table_selector)
        current_page_ids = _get_inspection_ids_on_page(page, table_selector)

        print(f"    Page {page_num}: {len(page_inspections)} inspections, IDs: {sorted(current_page_ids)[:3]}...")

        # Add to results (only unique ones)
        for insp in page_inspections:
            insp_id = insp.get('inspection_id')
            if insp_id and insp_id not in all_seen_ids:
                all_inspections.append(insp)
                all_seen_ids.add(insp_id)

        previous_page_ids = current_page_ids

        # Handle pagination
        while True:
            # Check safety limits
            elapsed = time.time() - start_time
            if elapsed > max_runtime_seconds:
                print(f"    STOPPING: Runtime exceeded {max_runtime_seconds}s")
                results["errors"].append(f"Runtime limit exceeded ({elapsed:.0f}s)")
                final_pagination_state = "failed"
                break

            if page_num >= max_pages:
                print(f"    STOPPING: Page limit exceeded ({max_pages})")
                results["errors"].append(f"Page limit exceeded ({max_pages})")
                final_pagination_state = "failed"
                break

            if len(all_seen_ids) >= max_unique:
                print(f"    STOPPING: Unique ID limit exceeded ({max_unique})")
                results["errors"].append(f"Unique ID limit exceeded ({len(all_seen_ids)})")
                final_pagination_state = "failed"
                break

            # Try to navigate to next page
            target_page = page_num + 1
            pagination_result = _click_pagination(page, target_page, previous_page_ids)

            if pagination_result == 'last_page':
                # Reached the end of data - this is success, not failure
                print(f"    Reached last page (page {page_num})")
                final_pagination_state = "last_page"
                break

            if pagination_result == 'failed':
                # Check if this is a transient failure worth retrying
                if consecutive_failures >= 2:
                    print(f"    STOPPING: Multiple consecutive pagination failures")
                    # Save debug HTML for failure page (if debug_dir provided)
                    if debug_dir is not None:
                        fail_debug = debug_dir / f"{permit_number}_page{page_num}_fail_debug.html"
                        fail_debug.write_text(page.content())
                        print(f"    Saved failure debug HTML to {fail_debug}")
                    results["errors"].append(f"Pagination failed at page {page_num}")
                    final_pagination_state = "failed"
                    break
                consecutive_failures += 1
                print(f"    Retrying pagination (attempt {consecutive_failures})...")
                time.sleep(2)
                continue

            # Pagination succeeded (pagination_result == 'success')
            consecutive_failures = 0
            page_num += 1
            final_pagination_state = "success"

            # Extract this page
            page_inspections = _extract_inspections_from_table(page, table_selector)
            current_page_ids = _get_inspection_ids_on_page(page, table_selector)

            if not page_inspections:
                print(f"    Page {page_num}: No inspections found, likely last page")
                final_pagination_state = "last_page"
                break

            # Count new vs duplicate
            new_on_page = 0
            for insp in page_inspections:
                insp_id = insp.get('inspection_id')
                if insp_id and insp_id not in all_seen_ids:
                    all_inspections.append(insp)
                    all_seen_ids.add(insp_id)
                    new_on_page += 1

            print(f"    Page {page_num}: {len(page_inspections)} rows, {new_on_page} new unique (total: {len(all_seen_ids)})")

            # If we got zero new inspections, pagination might have failed silently
            if new_on_page == 0:
                print(f"    WARNING: No new inspections on page {page_num}")
                # Save debug HTML (if debug_dir provided)
                if debug_dir is not None:
                    dup_debug = debug_dir / f"{permit_number}_page{page_num}_dup_debug.html"
                    dup_debug.write_text(page.content())
                    print(f"    Saved duplicate page debug HTML to {dup_debug}")

                # Check if IDs are same as previous page
                if current_page_ids == previous_page_ids:
                    print(f"    STOPPING: Same data as previous page - pagination not working")
                    results["errors"].append(f"Duplicate data on page {page_num}")
                    final_pagination_state = "failed"
                    break

            previous_page_ids = current_page_ids

        results["inspections"] = all_inspections
        results["metadata"]["total_pages"] = page_num
        results["metadata"]["unique_inspection_count"] = len(all_seen_ids)
        results["metadata"]["final_pagination_state"] = final_pagination_state

        # =====================================================
        # Step 4: Capture additional metadata
        # =====================================================
        print("\n[4] Capturing metadata...")

        try:
            results["metadata"]["page_content_length"] = len(page.content())
        except Exception as e:
            print(f"    Metadata capture error: {e}")

        # Close browser
        browser.close()

    # =====================================================
    # Step 5: Finalize results
    # =====================================================
    elapsed = time.time() - start_time
    results["metadata"]["extraction_duration_seconds"] = round(elapsed, 2)

    print(f"\n[5] Extraction complete")
    print(f"    Total inspections: {len(all_inspections)}")
    print(f"    Unique IDs: {len(all_seen_ids)}")
    print(f"    Pages: {page_num}")
    print(f"    Duration: {elapsed:.1f}s")
    print(f"    Final state: {final_pagination_state}")
    if results["errors"]:
        print(f"    Errors: {len(results['errors'])}")

    return results


if __name__ == "__main__":
    # Minimal CLI for ad-hoc testing against a single permit.
    # Production callers should import scrape_inspections() directly.
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Scrape Accela inspection records for a single permit"
    )
    parser.add_argument("permit_number", help="Human-facing permit number (e.g., B2019-05574)")
    parser.add_argument("url", help="Full Accela CapDetail.aspx URL with capID params")
    parser.add_argument("--headed", action="store_true", help="Run with visible browser")
    parser.add_argument("--debug-dir", type=pathlib.Path, help="Directory for debug HTML output")
    args = parser.parse_args()

    result = scrape_inspections(
        args.permit_number,
        args.url,
        headless=not args.headed,
        debug_dir=args.debug_dir,
    )
    json.dump(result, sys.stdout, indent=2)
