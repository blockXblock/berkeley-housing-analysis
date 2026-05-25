#!/usr/bin/env python3
"""
Build the URL discovery queue.

Reads the v2 database (read-only) to find in-scope B-prefix permits that
lack a source_url, and populates the url_discovery_queue table in the
queue database. The URL discovery scraper (separate workstream) consumes
this queue to resolve each permit's Accela CapDetail URL.

Inputs:
    --v2-db        Path to berkeley_housing_v2.db (READ-ONLY)
    --queue-db     Path to cic_recon_queue.db (READ-WRITE)

Outputs:
    Rows inserted into url_discovery_queue with status='pending'.

In-scope criteria (mirrors notes/2026-05-22_url_discovery_design_sketch.md):
    - permit_number LIKE 'B%'
    - project.current_stage_type_id maps to vocabulary_stage_types.code
      in ('completed', 'under_construction')
    - source_url IS NULL or empty

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
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_V2_DB = "databases/berkeley_housing_v2.db"
DEFAULT_QUEUE_DB = "databases/cic_recon_queue.db"

V2_QUERY = """
SELECT p.id AS permit_id, p.permit_number
FROM permits p
JOIN projects pr ON p.project_id = pr.id
JOIN vocabulary_stage_types vst ON pr.current_stage_type_id = vst.id
WHERE p.permit_number LIKE 'B%'
  AND vst.code IN ('completed', 'under_construction')
  AND (p.source_url IS NULL OR p.source_url = '')
ORDER BY p.permit_number;
"""

INSERT_SQL = """
INSERT OR IGNORE INTO url_discovery_queue
    (permit_id, permit_number, status, attempts, created_at)
VALUES (?, ?, 'pending', 0, ?);
"""


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Build the url_discovery_queue from v2 in-scope B-permits."
    )
    parser.add_argument(
        "--queue-db",
        default=DEFAULT_QUEUE_DB,
        help=f"Path to queue database (default: {DEFAULT_QUEUE_DB})",
    )
    parser.add_argument(
        "--v2-db",
        default=DEFAULT_V2_DB,
        help=f"Path to v2 database (default: {DEFAULT_V2_DB})",
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


def fetch_in_scope_permits(v2_db_path: Path, limit):
    if not v2_db_path.exists():
        raise SystemExit(f"ERROR: v2 database not found: {v2_db_path}")
    uri = f"file:{v2_db_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(V2_QUERY).fetchall()
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

    v2_db = Path(args.v2_db)
    queue_db = Path(args.queue_db)

    log.info("v2 database: %s", v2_db)
    log.info("Queue database: %s", queue_db)
    log.info("Dry run: %s", args.dry_run)
    if args.limit is not None:
        log.info("Limit: %d", args.limit)

    ensure_queue_table(queue_db)

    log.info("Querying v2 for in-scope B-permits...")
    permits = fetch_in_scope_permits(v2_db, args.limit)
    log.info("v2 returned %d in-scope permits", len(permits))

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
