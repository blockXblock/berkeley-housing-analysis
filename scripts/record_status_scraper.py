#!/usr/bin/env python3
"""
Accela Record Info scraper — extracts 4 authoritative fields per permit.

Scope is deliberately tight: one HTTP fetch per permit, parse the CapDetail
page's Record Info section, extract:
  - record_status      (e.g., 'Issued', 'Finaled', 'Closed')
  - permit_type_text   (e.g., 'Permit', 'Zoning Permit')
  - work_location      (street address verbatim)
  - applicant_name     (first chunk of the Applicant section)

NOT in scope: inspections, fees, related sub-records, processing status.
Those are handled by other scrapers.

Inputs:
  --queue-db PATH     SQLite DB containing url_discovery_queue with capdetail_url
  --permits-list PATH text file, one permit_number per line; OR keyword
                      'all_inspection_scraped' / 'all_url_discovered'
  --output-dir PATH   where to write per-permit JSON
  --report-path PATH  optional markdown report path
  --force             re-scrape permits already marked succeeded
  --dry-run           parse permit list + check URL availability, but don't fetch

Outputs:
  - data/raw/accela_record_status/{permit_number}.json (per permit)
  - cic_recon_queue.db.record_status_queue row per permit

Idempotency: re-running skips permit_numbers with status='succeeded' in
record_status_queue unless --force.
"""

import argparse
import datetime as dt
import json
import pathlib
import re
import sqlite3
import sys
import time

import requests
from bs4 import BeautifulSoup


SCRAPER_VERSION = "record_status_scraper_v1.0"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/119.0.0.0 Safari/537.36"
)
HTTP_TIMEOUT = 30


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS record_status_queue (
    permit_number TEXT PRIMARY KEY,
    capdetail_url TEXT NOT NULL,
    record_status TEXT,
    permit_type_text TEXT,
    work_location TEXT,
    applicant_name TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    output_file TEXT,
    scraped_at TEXT,
    error_message TEXT
)
"""


def _clean(s):
    if s is None:
        return None
    s = re.sub(r"\s+", " ", s).strip()
    s = s.strip(" * ")  # strip asterisks and non-breaking spaces
    return s or None


def parse_record_info(html: str) -> dict:
    """
    Parse the Accela CapDetail page HTML and extract the 4 Record Info fields.
    Returns a dict with: record_status, permit_type_text, work_location, applicant_name.
    Any field that can't be located is returned as None.
    """
    soup = BeautifulSoup(html, "html.parser")
    out = {
        "record_status": None,
        "permit_type_text": None,
        "work_location": None,
        "applicant_name": None,
    }

    # Record Status — element id="ctl00_PlaceHolderMain_lblRecordStatus"
    el = soup.find(id="ctl00_PlaceHolderMain_lblRecordStatus")
    if el:
        out["record_status"] = _clean(el.get_text())

    # Permit type — element id="ctl00_PlaceHolderMain_lblPermitType"
    el = soup.find(id="ctl00_PlaceHolderMain_lblPermitType")
    if el:
        out["permit_type_text"] = _clean(el.get_text())

    # Work location — id="divWorkLocationInfo"
    el = soup.find(id="divWorkLocationInfo")
    if el:
        out["work_location"] = _clean(el.get_text())

    # Applicant — labeled span ends in "_label_applicant<n>". The value
    # comes from the sibling content following the label's parent <h1>.
    # Strategy: locate the "Applicant:" label, walk up to its container,
    # then read all text content of the next sibling block (the value).
    label_span = soup.find(
        lambda tag: tag.name == "span"
        and tag.get("id", "").endswith(tuple([str(i) for i in range(10)]))
        and "label_applicant" in (tag.get("id") or "")
    )
    if label_span:
        # Walk up to find a containing block, then look at next siblings
        container = label_span.find_parent("h1") or label_span
        # The applicant value tends to live in the next ACA_SmLabel span sibling
        # immediately after the h1, but the structure varies. Take the entire
        # text from the label's grandparent block and remove the "Applicant:" prefix.
        block = container.find_parent("div") or container.find_parent()
        if block:
            txt = _clean(block.get_text(" ", strip=True))
            if txt:
                # Remove leading "Applicant:" if present
                txt = re.sub(r"^Applicant\s*:?\s*", "", txt, flags=re.IGNORECASE)
                # Some pages duplicate "Name Name address..." — take first 200 chars
                # for the raw capture and let downstream dedup.
                out["applicant_name"] = txt[:200].strip() or None

    return out


def fetch_and_parse(url: str, session: requests.Session) -> tuple[dict, str | None]:
    """Fetch the CapDetail page and parse fields. Returns (fields_dict, error_or_None)."""
    try:
        resp = session.get(url, timeout=HTTP_TIMEOUT)
    except requests.RequestException as e:
        return {}, f"http request failed: {e!r}"
    if resp.status_code != 200:
        return {}, f"http status {resp.status_code}"
    if "Bad gateway" in resp.text[:2000] or "502" in resp.text[:500]:
        return {}, "upstream 502 / bad gateway"
    try:
        fields = parse_record_info(resp.text)
    except Exception as e:
        return {}, f"parse exception: {e!r}"
    return fields, None


def ensure_schema(conn):
    conn.executescript(SCHEMA_SQL)
    conn.commit()


def load_capdetail_urls(conn, permit_numbers):
    """For each permit_number, look up its capdetail_url from url_discovery_queue."""
    placeholders = ",".join("?" * len(permit_numbers))
    rows = conn.execute(
        f"""
        SELECT permit_number, output_file FROM url_discovery_queue
        WHERE permit_number IN ({placeholders})
          AND status = 'succeeded'
        """,
        permit_numbers,
    ).fetchall()
    # We need the capdetail_url from the JSON output_file
    url_map = {}
    missing = []
    for pn, output_file in rows:
        if not output_file:
            missing.append(pn)
            continue
        p = pathlib.Path(output_file)
        if not p.exists():
            # Try canonical fallback
            alt = pathlib.Path("data/raw/accela_url_discovery") / f"{pn}.json"
            if alt.exists():
                p = alt
            else:
                missing.append(pn)
                continue
        try:
            data = json.loads(p.read_text())
            url = (data.get("master") or {}).get("capdetail_url")
            if url:
                url_map[pn] = url
            else:
                missing.append(pn)
        except Exception:
            missing.append(pn)
    # For permits without url_discovery entry, try v2.permits.source_url
    handled = set(url_map) | set(missing)
    leftover = [pn for pn in permit_numbers if pn not in handled]
    if leftover:
        # Fall back to source_url in v2 (read-only)
        v2 = sqlite3.connect("file:databases/berkeley_housing_v2.db?mode=ro", uri=True)
        ph = ",".join("?" * len(leftover))
        for pn, src in v2.execute(
            f"SELECT permit_number, source_url FROM permits WHERE permit_number IN ({ph})",
            leftover,
        ).fetchall():
            if src:
                url_map[pn] = src
            else:
                missing.append(pn)
        v2.close()
    return url_map, missing


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--permits-list", required=True,
                        help="Path to file with one permit_number per line, OR keyword "
                             "'all_inspection_scraped' / 'all_url_discovered'")
    parser.add_argument("--queue-db", default="databases/cic_recon_queue.db")
    parser.add_argument("--output-dir", default="data/raw/accela_record_status")
    parser.add_argument("--report-path", default=None,
                        help="Optional markdown report destination")
    parser.add_argument("--force", action="store_true",
                        help="Re-scrape permits already marked succeeded")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    output_dir = pathlib.Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Resolve the permit list
    if args.permits_list == "all_inspection_scraped":
        permits = sorted(
            p.stem for p in pathlib.Path("data/raw/accela_inspections").glob("*.json")
        )
    elif args.permits_list == "all_url_discovered":
        conn = sqlite3.connect(f"file:{args.queue_db}?mode=ro", uri=True)
        permits = sorted(
            r[0] for r in conn.execute(
                "SELECT permit_number FROM url_discovery_queue WHERE status='succeeded'"
            ).fetchall()
        )
        conn.close()
    else:
        permits = [
            line.strip() for line in pathlib.Path(args.permits_list).read_text().splitlines()
            if line.strip() and not line.startswith("#")
        ]
    print(f"Resolved {len(permits)} permits from {args.permits_list}")

    # Open queue (read-write) and ensure schema
    queue = sqlite3.connect(args.queue_db)
    ensure_schema(queue)

    # Look up capdetail URLs
    url_map, missing = load_capdetail_urls(queue, permits)
    print(f"Resolved capdetail URLs for {len(url_map)}/{len(permits)} permits")
    if missing:
        print(f"  Missing capdetail URL for {len(missing)} permits: {missing[:5]}{'...' if len(missing) > 5 else ''}")

    # Skip already-succeeded (unless --force)
    if not args.force:
        already_succeeded = {
            r[0] for r in queue.execute(
                "SELECT permit_number FROM record_status_queue WHERE status='succeeded'"
            ).fetchall()
        }
        to_run = [pn for pn in permits if pn in url_map and pn not in already_succeeded]
        skipped = len(permits) - len(to_run) - len(missing)
        print(f"  Skipping {skipped} already-succeeded (use --force to re-scrape)")
    else:
        to_run = [pn for pn in permits if pn in url_map]

    if args.dry_run:
        print(f"DRY RUN: would scrape {len(to_run)} permits; URLs resolved for all of them")
        queue.close()
        return 0

    # Scrape
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    started_at = time.time()
    n_succ = 0
    n_fail = 0
    status_counter = {}

    for i, pn in enumerate(to_run, 1):
        url = url_map[pn]
        fields, err = fetch_and_parse(url, session)
        scraped_at = dt.datetime.now().isoformat(timespec="seconds")
        if err:
            payload = {
                "permit_number": pn, "capdetail_url": url,
                "error": err, "scraped_at": scraped_at,
                "scraper_version": SCRAPER_VERSION,
            }
            output_file = str(output_dir / f"{pn}.json")
            pathlib.Path(output_file).write_text(json.dumps(payload, indent=2))
            queue.execute(
                """INSERT OR REPLACE INTO record_status_queue
                   (permit_number, capdetail_url, status, output_file, scraped_at, error_message)
                   VALUES (?, ?, 'failed', ?, ?, ?)""",
                (pn, url, output_file, scraped_at, err),
            )
            queue.commit()
            n_fail += 1
            print(f"  [{i:3}/{len(to_run)}] FAIL {pn}: {err}")
        else:
            payload = {
                "permit_number": pn, "capdetail_url": url,
                **fields,
                "scraped_at": scraped_at,
                "scraper_version": SCRAPER_VERSION,
            }
            output_file = str(output_dir / f"{pn}.json")
            pathlib.Path(output_file).write_text(json.dumps(payload, indent=2))
            queue.execute(
                """INSERT OR REPLACE INTO record_status_queue
                   (permit_number, capdetail_url, record_status, permit_type_text,
                    work_location, applicant_name, status, output_file, scraped_at, error_message)
                   VALUES (?, ?, ?, ?, ?, ?, 'succeeded', ?, ?, NULL)""",
                (pn, url, fields.get("record_status"), fields.get("permit_type_text"),
                 fields.get("work_location"), fields.get("applicant_name"),
                 output_file, scraped_at),
            )
            queue.commit()
            n_succ += 1
            rs = fields.get("record_status") or "(none)"
            status_counter[rs] = status_counter.get(rs, 0) + 1
            print(f"  [{i:3}/{len(to_run)}] ok   {pn}: status={rs!r}  type={fields.get('permit_type_text')!r}")

    elapsed = time.time() - started_at
    print(f"\nDone in {elapsed:.1f}s. succeeded={n_succ} failed={n_fail}")
    print(f"record_status distribution (this run): {status_counter}")

    queue.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
