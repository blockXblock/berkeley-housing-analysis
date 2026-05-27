#!/usr/bin/env python3
"""
Accela Processing Status scraper — captures, per main permit:
  1. The Related Records list (sub-records like REV01..REVnn, DEFnn..)
  2. The Processing Status of the NEWEST sub-record (or the main permit
     if no sub-records exist).

Why the newest sub-record: Berkeley's permit revisions (REV/DEF) hold
the current workflow state. Reading the main permit's Processing Status
shows only its original lifecycle; the latest workflow lives on the
highest-numbered revision.

Tabs (Related Records, Processing Status) are loaded via JS-driven AJAX
on the Accela ACA page, so we use Playwright (not requests).

Inputs:
  --queue-db PATH     SQLite DB with record_status_queue (gives capdetail
                      URLs and a permit_number list)
  --permits-list      'all_record_status_succeeded' to read from
                      record_status_queue; OR a path to a text file with
                      one permit per line
  --output-dir        per-permit JSON output dir
  --report-path       optional markdown report destination
  --force             re-scrape permits already marked succeeded
  --dry-run           only verify URL availability; don't fetch

Outputs:
  data/raw/accela_processing_status/{permit_number}.json
  cic_recon_queue.db.processing_status_queue rows
"""

import argparse
import datetime as dt
import json
import pathlib
import re
import sqlite3
import sys
import time

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup


SCRAPER_VERSION = "processing_status_scraper_v1.0"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36"
)
NAV_TIMEOUT = 60000
TAB_WAIT_SECONDS = 4   # AJAX settle time after tab navigation


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS processing_status_queue (
    permit_number TEXT PRIMARY KEY,
    main_capdetail_url TEXT NOT NULL,
    main_record_status TEXT,
    subrecord_count INTEGER,
    newest_subrecord TEXT,
    scraped_subrecord TEXT,
    scraped_subrecord_record_status TEXT,
    stage_count INTEGER,
    hourglass_rows_count INTEGER,
    active_stage_names TEXT,
    pending_stage_names TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    output_file TEXT,
    scraped_at TEXT,
    error_message TEXT
)
"""


SUFFIX_RE = re.compile(r"^([A-Z]\d{4}-\d{4,6})-(REV|DEF|ALT|ADD)(\d+)$", re.IGNORECASE)
SUFFIX_RANK = {"REV": 4, "DEF": 3, "ALT": 2, "ADD": 1}


def sort_key_subrecord(perm):
    """Return a sort key for a sub-record permit_number. Higher = newer."""
    m = SUFFIX_RE.match(perm)
    if not m:
        return (-1, 0)
    suffix_type = m.group(2).upper()
    seq = int(m.group(3))
    return (seq, SUFFIX_RANK.get(suffix_type, 0))


def select_tab(page, tab_name: str) -> bool:
    """Call handlePortletNavigation for the given tab. Returns True if invoked."""
    try:
        result = page.evaluate(f"""() => {{
            const a = document.querySelector('a[data-control="{tab_name}"]');
            if (a && typeof handlePortletNavigation === 'function') {{
                handlePortletNavigation(a);
                return 'invoked';
            }}
            return 'no-handler';
        }}""")
        return result == "invoked"
    except Exception:
        return False


def parse_related_records(html: str, main_permit: str) -> list[dict]:
    """
    Parse the Related Records table. Returns a list of dicts:
      [{permit_number, record_type, project_name, date, view_url}, ...]

    Strategy: find anchors whose text matches the main permit's suffix
    pattern (B....-REV.. / -DEF.. etc.); for each, walk to its enclosing
    <tr> and read sibling <td> cells for the other columns.
    """
    soup = BeautifulSoup(html, "html.parser")
    subs = []
    seen_permits = set()
    # Match permits with the same parent permit number, with REV/DEF/ALT/ADD suffix
    permit_pattern = re.compile(
        re.escape(main_permit) + r"-(REV|DEF|ALT|ADD)\d+", re.IGNORECASE
    )
    # Also match the main permit itself if it appears in the table
    main_pattern = re.compile(rf"^{re.escape(main_permit)}$", re.IGNORECASE)

    # Find all elements whose text content matches a sub-record permit number
    for el in soup.find_all(string=permit_pattern):
        text = str(el).strip()
        m = permit_pattern.search(text)
        if not m:
            continue
        # The matched text might be wrapped in more text; extract the permit
        for sub_match in re.finditer(
            re.escape(main_permit) + r"-(REV|DEF|ALT|ADD)\d+", text
        ):
            permit = sub_match.group(0)
            if permit in seen_permits:
                continue
            seen_permits.add(permit)
            # Walk to enclosing <tr> to find sibling cells
            parent = el.parent
            tr = None
            while parent is not None:
                if parent.name == "tr":
                    tr = parent
                    break
                parent = parent.parent
            row = {
                "permit_number": permit,
                "record_type": None,
                "project_name": None,
                "date": None,
                "view_url": None,
            }
            if tr is not None:
                tds = tr.find_all("td", recursive=False)
                # Standard Accela 5-column layout: Permit / Record Type / Project / Date / View
                cells = [td.get_text(" ", strip=True) for td in tds]
                # Common ordering — but check by content
                # Find the View link
                view_link = tr.find("a", href=re.compile(r"capID1=", re.IGNORECASE))
                if view_link:
                    row["view_url"] = view_link.get("href")
                # Date is typically MM/DD/YYYY format
                for c in cells:
                    if re.match(r"\d{1,2}/\d{1,2}/\d{4}", c.strip()):
                        row["date"] = c.strip().split()[0]
                        break
                # Record Type: short string, no permit prefix
                for c in cells:
                    if c and c != permit and not re.match(r"\d{1,2}/\d{1,2}", c) \
                            and "View" not in c[:10] and len(c) < 80:
                        if c.lower() not in (permit.lower(),):
                            row["record_type"] = c
                            break
            subs.append(row)
    return subs


def parse_processing_status(html: str) -> tuple[list[dict], int]:
    """
    Parse the Processing Status table. Returns (stages, hourglass_count).

    Each stage is:
      {stage_name, stage_state, steps: [...]}
    Each step is:
      {due_date, assigned_to, action, action_date, marked_by, comment, is_hourglass}

    Strategy: find all <tr> rows in the Processing Status panel; classify
    each row as either a stage header (contains alt="Complete"/"active"
    image or stage label) or a step row (matches the "Due on ..." pattern).
    """
    soup = BeautifulSoup(html, "html.parser")
    # Locate the Processing Status panel by section header id
    panel = soup.find(id="ctl00_PlaceHolderMain_divProcessStatus")
    if not panel:
        # Fallback — scan full page for "Due on" rows
        panel = soup
    rows = panel.find_all("tr")

    stages = []
    current_stage = None
    hourglass = 0

    # Regex for step rows
    step_re = re.compile(
        r"Due\s*on\s*(?P<due_date>\d{1,2}/\d{1,2}/\d{4}|TBD)\s*,\s*"
        r"assigned\s*to\s*(?P<assigned_to>.+?)"
        r"(?:Marked\s*as\s*(?P<action>.+?)\s*on\s*(?P<action_date>\d{1,2}/\d{1,2}/\d{4}|TBD)\s*by\s*(?P<marked_by>.+?))?"
        r"(?:Comment:\s*(?P<comment>.*?))?$",
        re.IGNORECASE | re.DOTALL,
    )

    for row in rows:
        text = row.get_text(" ", strip=True)
        if not text:
            continue
        # Check for stage state image inside this row
        img = row.find("img", alt=True)
        alt = (img.get("alt") if img else "").lower() if img else ""
        is_complete = (alt == "complete")
        is_active = (alt == "active")
        is_step = "Due on" in text and "assigned to" in text
        is_stage_header = (is_complete or is_active) and not is_step

        if is_stage_header:
            stage_name = text.strip()
            # Strip leading/trailing whitespace, "Complete" status text
            stage_state = "complete" if is_complete else "active"
            current_stage = {
                "stage_name": stage_name,
                "stage_state": stage_state,
                "steps": [],
            }
            stages.append(current_stage)
            continue

        if is_step:
            m = step_re.search(text)
            if not m:
                # Couldn't parse; record raw text
                step = {"raw": text, "is_hourglass": False, "parse_error": True}
            else:
                gd = m.groupdict()
                action = (gd.get("action") or "").strip() or None
                action_date = (gd.get("action_date") or "").strip() or None
                marked_by = (gd.get("marked_by") or "").strip() or None
                is_hourglass = (action == "TBD" and action_date == "TBD" and marked_by == "TBD")
                step = {
                    "due_date": (gd.get("due_date") or "").strip() or None,
                    "assigned_to": (gd.get("assigned_to") or "").strip() or None,
                    "action": action,
                    "action_date": action_date,
                    "marked_by": marked_by,
                    "comment": ((gd.get("comment") or "").strip() or None),
                    "is_hourglass": is_hourglass,
                }
                if is_hourglass:
                    hourglass += 1
            if current_stage is None:
                # Step before any stage header — create a default container
                current_stage = {"stage_name": "(unknown stage)", "stage_state": "unknown", "steps": []}
                stages.append(current_stage)
            # Accela renders each step twice in the DOM (likely an
            # accessibility/mobile duplicate). Dedup adjacent steps that
            # share the same identity tuple.
            prev = current_stage["steps"][-1] if current_stage["steps"] else None
            def _key(s):
                if not isinstance(s, dict) or "raw" in s:
                    return None
                return (s.get("due_date"), s.get("assigned_to"),
                        s.get("action"), s.get("action_date"),
                        s.get("marked_by"), s.get("comment"))
            new_key = _key(step)
            if prev is not None and new_key is not None and _key(prev) == new_key:
                # Skip the duplicate; don't double-count hourglass either
                if step.get("is_hourglass"):
                    hourglass -= 1
                continue
            current_stage["steps"].append(step)
        # else: structural row, skip

    return stages, hourglass


def scrape_one(page, main_permit: str, main_url: str) -> dict:
    """Scrape one permit. Returns the output JSON dict."""
    payload = {
        "main_permit": main_permit,
        "main_permit_capdetail_url": main_url,
        "scraped_at": dt.datetime.now().isoformat(timespec="seconds"),
        "scraper_version": SCRAPER_VERSION,
    }
    try:
        page.goto(main_url, wait_until="networkidle", timeout=NAV_TIMEOUT)
        time.sleep(2)
    except PlaywrightTimeout as e:
        return {**payload, "error": f"main goto timeout: {e!r}", "step_failed": "A"}
    except Exception as e:
        return {**payload, "error": f"main goto error: {e!r}", "step_failed": "A"}

    # Capture main record status from the same page
    main_html = page.content()
    rs_match = re.search(
        r'id="ctl00_PlaceHolderMain_lblRecordStatus"[^>]*>([^<]{0,100})', main_html
    )
    payload["main_permit_record_status"] = rs_match.group(1).strip() if rs_match else None

    # Click Related Records tab
    if not select_tab(page, "tab-related_records"):
        return {**payload, "error": "could not invoke tab-related_records", "step_failed": "B"}
    time.sleep(TAB_WAIT_SECONDS)

    related_html = page.content()
    related = parse_related_records(related_html, main_permit)
    payload["related_records"] = related
    payload["subrecord_count"] = len(related)

    # Identify newest sub-record (max sort key); fall back to main permit if none
    if related:
        # Sort by sort_key (highest = newest)
        sorted_subs = sorted(related, key=lambda r: sort_key_subrecord(r["permit_number"]), reverse=True)
        newest = sorted_subs[0]
        payload["newest_subrecord"] = newest["permit_number"]
        scraped_target_url = newest.get("view_url")
        if scraped_target_url and not scraped_target_url.startswith("http"):
            # Resolve relative URL
            if scraped_target_url.startswith("/"):
                scraped_target_url = "https://aca-prod.accela.com" + scraped_target_url
            else:
                scraped_target_url = "https://aca-prod.accela.com/BERKELEY/Cap/" + scraped_target_url.lstrip("./")
        payload["scraped_subrecord"] = newest["permit_number"]
        payload["scraped_subrecord_url"] = scraped_target_url
    else:
        payload["newest_subrecord"] = main_permit
        payload["scraped_subrecord"] = main_permit
        payload["scraped_subrecord_url"] = main_url

    # If sub-record URL differs from main, navigate to it
    target_url = payload.get("scraped_subrecord_url") or main_url
    if target_url != page.url:
        try:
            page.goto(target_url, wait_until="networkidle", timeout=NAV_TIMEOUT)
            time.sleep(2)
        except Exception as e:
            return {**payload, "error": f"subrecord goto error: {e!r}", "step_failed": "E"}

    # Capture sub-record status
    sub_html = page.content()
    sub_rs = re.search(
        r'id="ctl00_PlaceHolderMain_lblRecordStatus"[^>]*>([^<]{0,100})', sub_html
    )
    payload["scraped_subrecord_record_status"] = sub_rs.group(1).strip() if sub_rs else None

    # Click Processing Status tab
    if not select_tab(page, "tab-processing_status"):
        return {**payload, "error": "could not invoke tab-processing_status", "step_failed": "F"}
    time.sleep(TAB_WAIT_SECONDS)

    proc_html = page.content()
    stages, hourglass = parse_processing_status(proc_html)
    payload["stages"] = stages
    payload["stage_count"] = len(stages)
    payload["hourglass_rows_count"] = hourglass

    return payload


def ensure_schema(conn):
    conn.executescript(SCHEMA_SQL)
    conn.commit()


def load_capdetail_urls(conn, permits):
    """Look up capdetail_url per permit from record_status_queue."""
    ph = ",".join("?" * len(permits))
    rows = conn.execute(
        f"SELECT permit_number, capdetail_url FROM record_status_queue WHERE permit_number IN ({ph})",
        permits,
    ).fetchall()
    return {r[0]: r[1] for r in rows}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--permits-list", required=True)
    parser.add_argument("--queue-db", default="databases/cic_recon_queue.db")
    parser.add_argument("--output-dir", default="data/raw/accela_processing_status")
    parser.add_argument("--report-path", default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    output_dir = pathlib.Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    queue = sqlite3.connect(args.queue_db)
    ensure_schema(queue)

    # Resolve permit list
    if args.permits_list == "all_record_status_succeeded":
        permits = sorted(
            r[0] for r in queue.execute(
                "SELECT permit_number FROM record_status_queue WHERE status='succeeded'"
            ).fetchall()
        )
    else:
        permits = [
            line.strip() for line in pathlib.Path(args.permits_list).read_text().splitlines()
            if line.strip() and not line.startswith("#")
        ]
    print(f"Resolved {len(permits)} permits from {args.permits_list}")

    url_map = load_capdetail_urls(queue, permits)
    print(f"Got capdetail_url for {len(url_map)}/{len(permits)}")
    missing = [p for p in permits if p not in url_map]
    if missing:
        print(f"  Missing URLs for {len(missing)} permits: {missing[:5]}{'...' if len(missing) > 5 else ''}")

    # Skip already succeeded
    if not args.force:
        already = {r[0] for r in queue.execute(
            "SELECT permit_number FROM processing_status_queue WHERE status='succeeded'"
        ).fetchall()}
        to_run = [p for p in permits if p in url_map and p not in already]
        skipped = len(permits) - len(to_run) - len(missing)
        print(f"  Skipping {skipped} already-succeeded (use --force to re-scrape)")
    else:
        to_run = [p for p in permits if p in url_map]

    if args.dry_run:
        print(f"DRY RUN: would scrape {len(to_run)} permits")
        queue.close()
        return 0

    if not to_run:
        print("Nothing to do.")
        queue.close()
        return 0

    started = time.time()
    n_succ = 0
    n_fail = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1400, "height": 900}, user_agent=USER_AGENT)
        page = ctx.new_page()
        try:
            for i, pn in enumerate(to_run, 1):
                url = url_map[pn]
                payload = scrape_one(page, pn, url)
                output_file = str(output_dir / f"{pn}.json")
                pathlib.Path(output_file).write_text(json.dumps(payload, indent=2))
                scraped_at = payload.get("scraped_at")
                if "error" in payload:
                    queue.execute(
                        """INSERT OR REPLACE INTO processing_status_queue
                           (permit_number, main_capdetail_url, status, output_file, scraped_at, error_message)
                           VALUES (?, ?, 'failed', ?, ?, ?)""",
                        (pn, url, output_file, scraped_at, payload.get("error")),
                    )
                    queue.commit()
                    n_fail += 1
                    print(f"  [{i:3}/{len(to_run)}] FAIL {pn} ({payload.get('step_failed')}): {payload.get('error')[:100]}")
                else:
                    stages = payload.get("stages") or []
                    active_stages = [s["stage_name"] for s in stages if s.get("stage_state") == "active"]
                    pending_stages = [s["stage_name"] for s in stages if s.get("stage_state") not in ("complete", "active")]
                    queue.execute(
                        """INSERT OR REPLACE INTO processing_status_queue
                           (permit_number, main_capdetail_url, main_record_status,
                            subrecord_count, newest_subrecord, scraped_subrecord,
                            scraped_subrecord_record_status, stage_count, hourglass_rows_count,
                            active_stage_names, pending_stage_names,
                            status, output_file, scraped_at, error_message)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'succeeded', ?, ?, NULL)""",
                        (pn, url, payload.get("main_permit_record_status"),
                         payload.get("subrecord_count"), payload.get("newest_subrecord"),
                         payload.get("scraped_subrecord"), payload.get("scraped_subrecord_record_status"),
                         payload.get("stage_count"), payload.get("hourglass_rows_count"),
                         ",".join(active_stages), ",".join(pending_stages),
                         output_file, scraped_at),
                    )
                    queue.commit()
                    n_succ += 1
                    print(f"  [{i:3}/{len(to_run)}] ok   {pn}: subs={payload.get('subrecord_count')} "
                          f"scraped={payload.get('scraped_subrecord')} "
                          f"stages={payload.get('stage_count')} "
                          f"sub_status={payload.get('scraped_subrecord_record_status')!r}")
        finally:
            try:
                browser.close()
            except Exception:
                pass

    elapsed = time.time() - started
    print(f"\nDone in {elapsed:.1f}s. succeeded={n_succ} failed={n_fail}")
    queue.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
