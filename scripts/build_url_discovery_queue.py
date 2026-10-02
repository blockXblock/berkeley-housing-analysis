#!/usr/bin/env python3
"""
Build the URL discovery queue.

Reads the v4 database (read-only) to find in-scope B-prefix permits that
lack a CapDetail URL, and populates the url_discovery_queue table in the
queue database. The URL discovery scraper (separate workstream) consumes
this queue to resolve each permit's Accela CapDetail URL.

Inputs:
    --v4-db        Path to berkeley_housing_v4.db (READ-ONLY; --v2-db is a retired alias)
    --queue-db     Path to cic_recon_queue.db (READ-WRITE)

Outputs:
    Rows inserted into url_discovery_queue with status='pending'.

In-scope criteria (v4, re-pointed 2026-10-02 from v2's stage-filtered `permits`):
    - the MASTER and PHASE permits of v4 structures
      (structure_events.role_in_structure IN ('master','phase') -> events.source_record_key)
    - permit_number LIKE 'B%'
    - no CapDetail href in the City's Accela list for that permit
      (no 'accela_listed' event whose raw_payload.capdetail_href points at CapDetail.aspx)
    This is the same scope build_scrape_queue.py uses; those two partitions add up to it.

Queue ids: v4 has no permit table and its event_ids renumber on every rebuild, so permit_id is
derived from the permit number (B2015-00006 -> 201500006). A queue that still holds v2 permit ids
is refused rather than mixed.

Idempotency:
    The url_discovery_queue.permit_id column is UNIQUE. Re-running the
    script INSERT-OR-IGNOREs, so existing rows are preserved and only
    newly-in-scope permits are added.

Usage:
    python3 scripts/build_url_discovery_queue.py
    python3 scripts/build_url_discovery_queue.py --dry-run
    python3 scripts/build_url_discovery_queue.py --limit 5 -v

Exit codes:
    0 on success.
    Non-zero on any error (missing DB, missing table, query failure).
"""

import argparse
import logging
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_V4_DB = "databases/berkeley_housing_v4.db"
V2_ID_CEILING = 100_000_000   # v4-derived permit_ids are >= 2006*100000; anything below is a v2 id
DEFAULT_QUEUE_DB = "databases/cic_recon_queue.db"

V4_QUERY = """
SELECT DISTINCT e.source_record_key AS permit_number
FROM structure_events se JOIN events e USING (event_id)
WHERE se.role_in_structure IN ('master', 'phase')
  AND e.source_record_key LIKE 'B%'
  AND NOT EXISTS (
      SELECT 1 FROM events a
      WHERE a.event_type_code = 'accela_listed' AND a.source_record_key = e.source_record_key
        AND json_extract(a.raw_payload, '$.capdetail_href') LIKE '%CapDetail.aspx%')
ORDER BY 1;
"""


def permit_id_of(permit_number):
    """B2015-00006 -> 201500006: a stable integer id from the permit number itself."""
    m = re.fullmatch(r"B(\d{4})-(\d{5})", permit_number)
    if not m:
        raise ValueError(f"unexpected permit number shape: {permit_number!r}")
    return int(m.group(1)) * 100000 + int(m.group(2))

INSERT_SQL = """
INSERT OR IGNORE INTO url_discovery_queue
    (permit_id, permit_number, status, attempts, created_at)
VALUES (?, ?, 'pending', 0, ?);
"""


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Build the url_discovery_queue from v4 in-scope B-permits."
    )
    parser.add_argument(
        "--queue-db",
        default=DEFAULT_QUEUE_DB,
        help=f"Path to queue database (default: {DEFAULT_QUEUE_DB})",
    )
    parser.add_argument(
        "--v4-db", "--v2-db",
        dest="v4_db",
        default=DEFAULT_V4_DB,
        help=f"Path to v4 database, opened read-only (default: {DEFAULT_V4_DB}); "
             "--v2-db is a retired alias kept so old invocations still parse",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count rows that would be inserted; do not write.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Enqueue at most N permits (default: unlimited).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose logging (DEBUG level).",
    )
    return parser.parse_args(argv)


def configure_logging(verbose: bool):
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


def fetch_in_scope_permits(v4_db_path: Path, limit):
    if not v4_db_path.exists():
        raise SystemExit(f"ERROR: v4 database not found: {v4_db_path}")
    uri = f"file:{v4_db_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        rows = [{"permit_id": permit_id_of(n), "permit_number": n}
                for (n,) in conn.execute(V4_QUERY).fetchall()]
    finally:
        conn.close()
    if limit is not None:
        rows = rows[:limit]
    return rows


def ensure_queue_table(queue_db_path: Path):
    if not queue_db_path.exists():
        raise SystemExit(f"ERROR: queue database not found: {queue_db_path}")
    conn = sqlite3.connect(queue_db_path)
    try:
        row = conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='url_discovery_queue'"
        ).fetchone()
        if row is None:
            raise SystemExit(
                "ERROR: table 'url_discovery_queue' does not exist in "
                f"{queue_db_path}. Create it before running this script."
            )
        legacy = conn.execute(
            "SELECT COUNT(*) FROM url_discovery_queue WHERE permit_id < ?", (V2_ID_CEILING,)
        ).fetchone()[0]
        if legacy:
            raise SystemExit(
                f"ERROR: {queue_db_path} holds {legacy} v2-era rows (v2 permit ids). Point "
                "--queue-db at a fresh queue; the v4 queue keys permits by their permit number."
            )
    finally:
        conn.close()


def enqueue(queue_db_path: Path, permits, dry_run: bool):
    inserted = 0
    skipped = 0
    if dry_run:
        # Compute what WOULD happen by reading the existing permit_ids.
        conn = sqlite3.connect(f"file:{queue_db_path}?mode=ro", uri=True)
        try:
            existing = {
                r[0]
                for r in conn.execute(
                    "SELECT permit_id FROM url_discovery_queue"
                ).fetchall()
            }
        finally:
            conn.close()
        for p in permits:
            if p["permit_id"] in existing:
                skipped += 1
            else:
                inserted += 1
        return inserted, skipped

    now = datetime.now().isoformat()
    conn = sqlite3.connect(queue_db_path)
    try:
        try:
            conn.execute("BEGIN")
            for p in permits:
                cur = conn.execute(
                    INSERT_SQL, (p["permit_id"], p["permit_number"], now)
                )
                if cur.rowcount == 1:
                    inserted += 1
                else:
                    skipped += 1
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    finally:
        conn.close()
    return inserted, skipped


def report_status_counts(queue_db_path: Path):
    conn = sqlite3.connect(f"file:{queue_db_path}?mode=ro", uri=True)
    try:
        rows = conn.execute(
            "SELECT status, COUNT(*) FROM url_discovery_queue "
            "GROUP BY status ORDER BY status"
        ).fetchall()
        total = conn.execute(
            "SELECT COUNT(*) FROM url_discovery_queue"
        ).fetchone()[0]
    finally:
        conn.close()
    return total, rows


def main(argv=None):
    args = parse_args(argv)
    configure_logging(args.verbose)
    log = logging.getLogger("build_url_discovery_queue")

    v4_db = Path(args.v4_db)
    queue_db = Path(args.queue_db)

    log.info("v4 database: %s", v4_db)
    log.info("Queue database: %s", queue_db)
    log.info("Dry run: %s", args.dry_run)
    if args.limit is not None:
        log.info("Limit: %d", args.limit)

    ensure_queue_table(queue_db)

    log.info("Querying v4 for in-scope B-permits without a listed CapDetail URL...")
    permits = fetch_in_scope_permits(v4_db, args.limit)
    log.info("v4 returned %d in-scope permits", len(permits))

    if len(permits) == 0:
        log.warning("No in-scope permits found. Nothing to do.")
        return 0

    inserted, skipped = enqueue(queue_db, permits, args.dry_run)
    verb = "WOULD insert" if args.dry_run else "Inserted"
    log.info("%s: %d  Skipped (already in queue): %d", verb, inserted, skipped)

    total, status_counts = report_status_counts(queue_db)
    log.info("url_discovery_queue total rows: %d", total)
    for status, count in status_counts:
        log.info("  %s: %d", status, count)

    return 0


if __name__ == "__main__":
    sys.exit(main())
