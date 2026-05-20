#!/usr/bin/env python3
"""
Playwright POC: Capture inspection records from Berkeley Accela

Target: B2019-05574 (2352 Shattuck Ave, Phase II Logan Park)
Expected: ~553 inspections per recon notes

Usage:
    python playwright_inspections_poc.py           # headed mode (default)
    python playwright_inspections_poc.py --headless  # headless mode

Output: /tmp/playwright_poc_output/B2019-05574_inspections.json

V2 Fixes:
- Fixed pagination bug: JS click() wasn't triggering ASP.NET postback properly
- Now uses direct __doPostBack() call via page.evaluate()
- Added duplicate detection: stops if same inspection IDs appear on consecutive pages
- Added per-page validation: ensures new data on each page
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Constants
PERMIT_NUMBER = "B2019-05574"
TARGET_URL = (
    "https://aca-prod.accela.com/BERKELEY/Cap/CapDetail.aspx?"
    "Module=Building&TabName=Building&"
    "capID1=DUB19&capID2=00000&capID3=00KIJ&agencyCode=BERKELEY"
)
# Alternative URL with IsToShowInspection parameter
TARGET_URL_WITH_INSPECTION = TARGET_URL + "&IsToShowInspection=Y"

OUTPUT_DIR = Path("/tmp/playwright_poc_output")
OUTPUT_FILE = OUTPUT_DIR / f"{PERMIT_NUMBER}_inspections.json"

# Safety limits per task requirements
# Note: Accela shows 5 inspections per page, not 25, so 553 inspections = ~111 pages
MAX_PAGES = 120  # Stop if we exceed 120 pages
MAX_UNIQUE_INSPECTIONS = 700  # Stop if we exceed 700 unique (expect ~553)
MAX_RUNTIME_SECONDS = 900  # 15 minutes


def get_inspection_ids_on_page(page, table_selector):
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


def parse_inspection_row(row_element):
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


def extract_inspections_from_table(page, table_selector):
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
            inspection = parse_inspection_row(row)
            if inspection:
                inspections.append(inspection)

    except Exception as e:
        print(f"  Error extracting table: {e}")

    return inspections


def get_postback_target_for_page(page, target_page):
    """
    Get the __doPostBack target string for a specific page number.
    Returns the eventTarget string or None if not found.
    """
    try:
        result = page.evaluate(f'''() => {{
            // Look for the pagination link for the target page
            const links = document.querySelectorAll('.aca_pagination a');
            for (const link of links) {{
                const text = link.innerText.trim();
                if (text === '{target_page}' || text === 'Next >') {{
                    const href = link.getAttribute('href');
                    if (href && href.includes('__doPostBack')) {{
                        // Extract the event target: __doPostBack('TARGET','')
                        const match = href.match(/__doPostBack\\('([^']+)'/);
                        if (match) {{
                            return {{
                                target: match[1],
                                linkText: text
                            }};
                        }}
                    }}
                }}
            }}
            return null;
        }}''')
        return result
    except Exception as e:
        print(f"    Error finding postback target: {e}")
        return None


def click_pagination(page, target_page, previous_ids):
    """
    Navigate to the next page using ASP.NET __doPostBack.
    Returns:
        'success' - navigation succeeded and new data appeared
        'last_page' - no more pages (reached end of data)
        'failed' - pagination attempted but data didn't change
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

            new_ids = get_inspection_ids_on_page(page, table_selector)
            if new_ids and new_ids != previous_ids:
                # Table content changed!
                return 'success'

        # Final check after max wait
        new_ids = get_inspection_ids_on_page(page, table_selector)

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


def run_poc(headless=False):
    """Main POC execution."""

    start_time = time.time()
    results = {
        "permit_number": PERMIT_NUMBER,
        "url": TARGET_URL,
        "extraction_timestamp": datetime.now().isoformat(),
        "extraction_method": "playwright_v2",
        "inspections": [],
        "errors": [],
        "metadata": {}
    }

    print(f"\n{'='*60}")
    print(f"PLAYWRIGHT POC V2: Accela Inspection Extraction")
    print(f"{'='*60}")
    print(f"Permit: {PERMIT_NUMBER}")
    print(f"Mode: {'headless' if headless else 'headed (visible browser)'}")
    print(f"Target: {TARGET_URL[:60]}...")
    print(f"Safety limits: {MAX_PAGES} pages, {MAX_UNIQUE_INSPECTIONS} unique IDs, {MAX_RUNTIME_SECONDS}s")
    print()

    # Track all seen inspection IDs for deduplication
    all_seen_ids = set()

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
            page.goto(TARGET_URL_WITH_INSPECTION, wait_until="networkidle", timeout=60000)
            print(f"    Page loaded: {page.title()}")
        except PlaywrightTimeout:
            results["errors"].append("Timeout loading main page")
            print("    ERROR: Page load timeout")
            browser.close()
            return results

        # Check for login redirect
        current_url = page.url.lower()
        if "login" in current_url or "signin" in current_url:
            results["errors"].append("Redirected to login page - authentication required")
            results["metadata"]["requires_auth"] = True
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

        try:
            # Wait for the inspection table
            page.wait_for_selector(
                '#ctl00_PlaceHolderMain_InspectionList_gvListCompleted',
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
        page_num = 1
        consecutive_failures = 0
        table_selector = '#ctl00_PlaceHolderMain_InspectionList_gvListCompleted'

        # Save debug HTML for first page
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        debug_html = page.content()
        debug_file = OUTPUT_DIR / f"{PERMIT_NUMBER}_page1_debug.html"
        debug_file.write_text(debug_html)
        print(f"    Saved page 1 debug HTML to {debug_file}")

        # Check if table exists
        table = page.query_selector(table_selector)
        if not table:
            print("    No inspection table found!")
            results["errors"].append("Could not locate inspection table")
            browser.close()
            return results

        # Extract first page
        page_inspections = extract_inspections_from_table(page, table_selector)
        current_page_ids = get_inspection_ids_on_page(page, table_selector)

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
            if elapsed > MAX_RUNTIME_SECONDS:
                print(f"    STOPPING: Runtime exceeded {MAX_RUNTIME_SECONDS}s")
                results["errors"].append(f"Runtime limit exceeded ({elapsed:.0f}s)")
                break

            if page_num >= MAX_PAGES:
                print(f"    STOPPING: Page limit exceeded ({MAX_PAGES})")
                results["errors"].append(f"Page limit exceeded ({MAX_PAGES})")
                break

            if len(all_seen_ids) >= MAX_UNIQUE_INSPECTIONS:
                print(f"    STOPPING: Unique ID limit exceeded ({MAX_UNIQUE_INSPECTIONS})")
                results["errors"].append(f"Unique ID limit exceeded ({len(all_seen_ids)})")
                break

            # Try to navigate to next page
            target_page = page_num + 1
            pagination_result = click_pagination(page, target_page, previous_page_ids)

            if pagination_result == 'last_page':
                # Reached the end of data - this is success, not failure
                print(f"    Reached last page (page {page_num})")
                break

            if pagination_result == 'failed':
                # Check if this is a transient failure worth retrying
                if consecutive_failures >= 2:
                    print(f"    STOPPING: Multiple consecutive pagination failures")
                    # Save debug HTML for failure page
                    fail_debug = OUTPUT_DIR / f"{PERMIT_NUMBER}_page{page_num}_fail_debug.html"
                    fail_debug.write_text(page.content())
                    print(f"    Saved failure debug HTML to {fail_debug}")
                    results["errors"].append(f"Pagination failed at page {page_num}")
                    break
                consecutive_failures += 1
                print(f"    Retrying pagination (attempt {consecutive_failures})...")
                time.sleep(2)
                continue

            # Pagination succeeded (pagination_result == 'success')
            consecutive_failures = 0
            page_num += 1

            # Extract this page
            page_inspections = extract_inspections_from_table(page, table_selector)
            current_page_ids = get_inspection_ids_on_page(page, table_selector)

            if not page_inspections:
                print(f"    Page {page_num}: No inspections found, likely last page")
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
                # Save debug HTML
                dup_debug = OUTPUT_DIR / f"{PERMIT_NUMBER}_page{page_num}_dup_debug.html"
                dup_debug.write_text(page.content())
                print(f"    Saved duplicate page debug HTML to {dup_debug}")

                # Check if IDs are same as previous page
                if current_page_ids == previous_page_ids:
                    print(f"    STOPPING: Same data as previous page - pagination not working")
                    results["errors"].append(f"Duplicate data on page {page_num}")
                    break

            previous_page_ids = current_page_ids

        results["inspections"] = all_inspections
        results["metadata"]["total_pages"] = page_num
        results["metadata"]["unique_inspection_count"] = len(all_seen_ids)

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
    # Step 5: Save results
    # =====================================================
    elapsed = time.time() - start_time
    results["metadata"]["extraction_duration_seconds"] = round(elapsed, 2)

    print(f"\n[5] Saving results...")

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"    Saved to: {OUTPUT_FILE}")

    # =====================================================
    # Validation and Summary
    # =====================================================
    print(f"\n{'='*60}")
    print("VALIDATION")
    print(f"{'='*60}")

    # Get actual unique IDs from saved data
    saved_ids = set(i.get('inspection_id') for i in all_inspections if i.get('inspection_id'))
    dates = sorted(set(i.get('date') for i in all_inspections if i.get('date')))

    print(f"Total rows in JSON: {len(all_inspections)}")
    print(f"Unique inspection IDs: {len(saved_ids)}")
    print(f"Date range: {dates[0] if dates else 'N/A'} to {dates[-1] if dates else 'N/A'}")
    print(f"Pages traversed: {page_num}")
    print(f"Duration: {elapsed:.1f} seconds")
    print(f"Errors: {len(results['errors'])}")

    # Check success criteria
    success = True
    if len(saved_ids) < 400 or len(saved_ids) > 700:
        print(f"\nFAIL: Unique count {len(saved_ids)} outside expected range 400-700")
        success = False

    if len(saved_ids) != len(all_inspections):
        print(f"\nFAIL: Duplicates in output ({len(all_inspections)} rows, {len(saved_ids)} unique)")
        success = False

    # Check for critical errors (ignore non-fatal ones like timeout warnings)
    critical_errors = [e for e in results['errors']
                       if 'Pagination failed' in e or 'Duplicate data' in e]
    if critical_errors:
        print(f"\nFAIL: Critical errors occurred:")
        for err in critical_errors:
            print(f"  - {err}")
        success = False

    if results['errors']:
        print(f"\nNon-critical warnings:")
        for err in results['errors']:
            print(f"  - {err}")

    if dates and not (dates[0].endswith('2020') and '2021' in dates[-1] or '2022' in dates[-1]):
        print(f"\nWARN: Date range may not span full construction period")

    if success:
        print(f"\nSUCCESS: {len(saved_ids)} unique inspections extracted")
    else:
        print(f"\nFAILED: See errors above")

    if all_inspections:
        print(f"\nFirst 3 inspections:")
        for i, insp in enumerate(all_inspections[:3]):
            print(f"  {i+1}. ID={insp.get('inspection_id')}, {insp.get('date')}, {insp.get('result')}")

        print(f"\nLast 3 inspections:")
        for i, insp in enumerate(all_inspections[-3:]):
            idx = len(all_inspections) - 2 + i
            print(f"  {idx}. ID={insp.get('inspection_id')}, {insp.get('date')}, {insp.get('result')}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Playwright POC V2 for Accela inspection extraction")
    parser.add_argument('--headless', action='store_true', help="Run in headless mode")
    args = parser.parse_args()

    try:
        results = run_poc(headless=args.headless)

        # Exit with error code if validation failed
        unique_count = results["metadata"].get("unique_inspection_count", 0)
        if unique_count < 400 or unique_count > 700:
            sys.exit(1)
        # Only fail on critical pagination errors
        critical_errors = [e for e in results['errors']
                          if 'Pagination failed' in e or 'Duplicate data' in e]
        if critical_errors:
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
